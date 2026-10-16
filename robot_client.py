"""
Robot Arm TCP Client Controller.
Connects to either MockESP32Server (localhost:5000) or Physical ESP32 (WiFi IP:5000).
Includes smooth trajectory interpolation to prevent SG90 servo gear stripping and voltage drops.
"""

import socket
import time
import sys
from config import ROBOT_HOST, ROBOT_PORT, POSES, GRIPPER_OPEN, GRIPPER_CLOSE, LIMITS

class RobotArmClient:
    def __init__(self, host=ROBOT_HOST, port=ROBOT_PORT):
        self.host = host
        self.port = port
        self.sock = None
        self.connected = False
        
        # Track current angles
        self.current_angles = {
            "waist": 90,
            "shoulder": 90,
            "elbow": 90,
            "gripper": GRIPPER_OPEN
        }

    def connect(self):
        print(f"[*] Connecting to Robot Arm Server at {self.host}:{self.port}...")
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5.0)
            self.sock.connect((self.host, self.port))
            
            # Read greeting
            greeting = self.sock.recv(1024).decode("utf-8").strip()
            print(f"[+] Server Handshake: '{greeting}'")
            self.connected = True
            return True
        except Exception as e:
            print(f"[-] Connection failed: {e}")
            self.connected = False
            return False

    def send_raw_command(self, cmd):
        if not self.connected or not self.sock:
            raise RuntimeError("Robot not connected!")
        
        message = (cmd.strip() + "\n").encode("utf-8")
        self.sock.sendall(message)
        
        # Read reply
        reply = self.sock.recv(1024).decode("utf-8").strip()
        return reply

    def send_pose(self, w, s, e, g):
        """Send exact POSE:w,s,e,g command to ESP32 / Mock server."""
        # Clamp to physical safe limits
        w = max(LIMITS["waist"][0], min(LIMITS["waist"][1], int(w)))
        s = max(LIMITS["shoulder"][0], min(LIMITS["shoulder"][1], int(s)))
        e = max(LIMITS["elbow"][0], min(LIMITS["elbow"][1], int(e)))
        g = max(LIMITS["gripper"][0], min(LIMITS["gripper"][1], int(g)))

        cmd = f"POSE:{w},{s},{e},{g}"
        reply = self.send_raw_command(cmd)
        
        if "OK" in reply:
            self.current_angles["waist"] = w
            self.current_angles["shoulder"] = s
            self.current_angles["elbow"] = e
            self.current_angles["gripper"] = g
            return True
        else:
            print(f"[!] Server returned error: {reply}")
            return False

    def move_smooth(self, target_w, target_s, target_e, target_g, steps=15, step_delay=0.02):
        """
        Interpolates smoothly from current pose to target pose.
        Crucial for SG90 micro-servos to avoid current spikes and mechanical jerking.
        """
        start_w = self.current_angles["waist"]
        start_s = self.current_angles["shoulder"]
        start_e = self.current_angles["elbow"]
        start_g = self.current_angles["gripper"]

        for i in range(1, steps + 1):
            alpha = i / float(steps)
            # Smooth cosine acceleration curve
            # alpha = (1 - math.cos(alpha * math.pi)) / 2
            
            interp_w = int(start_w + (target_w - start_w) * alpha)
            interp_s = int(start_s + (target_s - start_s) * alpha)
            interp_e = int(start_e + (target_e - start_e) * alpha)
            interp_g = int(start_g + (target_g - start_g) * alpha)
            
            self.send_pose(interp_w, interp_s, interp_e, interp_g)
            time.sleep(step_delay)

    def go_home(self):
        """Move arm to safe neutral home position."""
        p = POSES["HOME"]
        print("[*] Returning to HOME position...")
        self.move_smooth(p["waist"], p["shoulder"], p["elbow"], p["gripper"])

    def pick_sponge(self):
        """
        Executes calibrated pick sequence from the sponge stack.
        (Uses angles calibrated from your physical test notes)
        """
        print("\n--- [ACTION: PICK SPONGE] ---")
        
        # 1. Pre-approach above the stack with gripper open
        p_pre = POSES["PICK_PRE_APPROACH"]
        print(f"[*] 1. Approaching above stack: W={p_pre['waist']} S={p_pre['shoulder']} E={p_pre['elbow']}")
        self.move_smooth(p_pre["waist"], p_pre["shoulder"], p_pre["elbow"], GRIPPER_OPEN)
        time.sleep(0.4)

        # 2. Lower onto the sponge block
        p_grip = POSES["PICK_GRIP"]
        print(f"[*] 2. Lowering to contact sponge: S={p_grip['shoulder']} E={p_grip['elbow']}")
        self.move_smooth(p_grip["waist"], p_grip["shoulder"], p_grip["elbow"], GRIPPER_OPEN)
        time.sleep(0.3)

        # 3. Close gripper firmly
        print(f"[*] 3. Clamping gripper on sponge (angle={GRIPPER_CLOSE})...")
        self.move_smooth(p_grip["waist"], p_grip["shoulder"], p_grip["elbow"], GRIPPER_CLOSE, steps=10, step_delay=0.03)
        time.sleep(0.5)

        # 4. Lift the gripped sponge up
        p_lift = POSES["PICK_LIFT"]
        print(f"[*] 4. Lifting sponge: S={p_lift['shoulder']} E={p_lift['elbow']}")
        self.move_smooth(p_lift["waist"], p_lift["shoulder"], p_lift["elbow"], GRIPPER_CLOSE)
        time.sleep(0.4)
        print("[+] Sponge successfully picked!\n")

    def place_in_zone(self, color_name):
        """
        Moves the arm to the designated color drop circle and releases the sponge.
        """
        color_key = f"DROP_{color_name.upper()}"
        if color_key not in POSES:
            print(f"[-] Unknown drop color: {color_name}")
            return False

        zone = POSES[color_key]
        pre = zone["pre"]
        drop = zone["drop"]

        print(f"\n--- [ACTION: PLACE IN {color_name.upper()} ZONE] ---")
        
        # 1. Rotate waist towards target circle (high clearance)
        print(f"[*] 1. Rotating to {color_name} circle at Waist={pre['waist']}°...")
        self.move_smooth(pre["waist"], pre["shoulder"], pre["elbow"], GRIPPER_CLOSE)
        time.sleep(0.4)

        # 2. Lower arm towards the circle
        print(f"[*] 2. Lowering above target circle...")
        self.move_smooth(drop["waist"], drop["shoulder"], drop["elbow"], GRIPPER_CLOSE)
        time.sleep(0.3)

        # 3. Open gripper to drop
        print(f"[*] 3. Opening gripper to release sponge...")
        self.move_smooth(drop["waist"], drop["shoulder"], drop["elbow"], GRIPPER_OPEN, steps=8, step_delay=0.02)
        time.sleep(0.4)

        # 4. Retract back up to clear the dropped sponge
        print(f"[*] 4. Raising arm to clear zone...")
        self.move_smooth(drop["waist"], pre["shoulder"], pre["elbow"], GRIPPER_OPEN)
        time.sleep(0.3)

        # 5. Return to home
        self.go_home()
        print(f"[+] Successfully sorted into {color_name.upper()} zone!\n")
        return True

    def disconnect(self):
        if self.sock:
            self.sock.close()
        self.connected = False
        print("[*] Robot client disconnected.")
