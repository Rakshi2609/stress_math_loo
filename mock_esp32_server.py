"""
ESP32 Mock TCP Server & Arm Kinematics Visualizer
Emulates the exact behavior and socket protocol of your ESP32 Arduino firmware on port 5000.
Allows 100% full end-to-end software testing without physical hardware.
"""

import socket
import threading
import time
import math
import sys

class MockESP32Server:
    def __init__(self, host="0.0.0.0", port=5000, visual=True):
        self.host = host
        self.port = port
        self.visual = visual
        self.server_socket = None
        self.running = False
        
        # Current servo states (matching ESP32 initialized state)
        self.angles = {
            "waist": 90,
            "shoulder": 90,
            "elbow": 90,
            "gripper": 120
        }
        self.attached = {
            "waist": False,
            "shoulder": False,
            "elbow": False,
            "gripper": False
        }

    def valid_angle(self, angle):
        return 0 <= angle <= 180

    def print_arm_status(self):
        w = self.angles["waist"]
        s = self.angles["shoulder"]
        e = self.angles["elbow"]
        g = self.angles["gripper"]
        
        grip_state = "OPEN" if g <= 130 else "CLOSED"
        
        print("\n" + "="*50)
        print(f" [VIRTUAL ESP32] Arm Pose Update:")
        print(f"   Waist    : {w:3d}° {'[' + '#'*(w//6) + ' '*(30-w//6) + ']'}")
        print(f"   Shoulder : {s:3d}° {'[' + '#'*(s//6) + ' '*(30-s//6) + ']'}")
        print(f"   Elbow    : {e:3d}° {'[' + '#'*(e//6) + ' '*(30-e//6) + ']'}")
        print(f"   Gripper  : {g:3d}° ({grip_state})")
        print("="*50)

    def process_command(self, cmd_str):
        cmd = cmd_str.strip()
        if not cmd:
            return None

        # WAIST
        if cmd.startswith("WAIST:"):
            try:
                angle = int(cmd[6:])
                if not self.valid_angle(angle):
                    return "ERROR: Invalid waist angle"
                self.angles["waist"] = angle
                self.attached["waist"] = True
                if self.visual:
                    self.print_arm_status()
                return "OK: WAIST"
            except ValueError:
                return "ERROR: Invalid waist angle"

        # SHOULDER
        if cmd.startswith("SHOULDER:"):
            try:
                angle = int(cmd[9:])
                if not self.valid_angle(angle):
                    return "ERROR: Invalid shoulder angle"
                self.angles["shoulder"] = angle
                self.attached["shoulder"] = True
                if self.visual:
                    self.print_arm_status()
                return "OK: SHOULDER"
            except ValueError:
                return "ERROR: Invalid shoulder angle"

        # ELBOW
        if cmd.startswith("ELBOW:"):
            try:
                angle = int(cmd[6:])
                if not self.valid_angle(angle):
                    return "ERROR: Invalid elbow angle"
                self.angles["elbow"] = angle
                self.attached["elbow"] = True
                if self.visual:
                    self.print_arm_status()
                return "OK: ELBOW"
            except ValueError:
                return "ERROR: Invalid elbow angle"

        # GRIPPER
        if cmd.startswith("GRIPPER:"):
            try:
                angle = int(cmd[8:])
                if not self.valid_angle(angle):
                    return "ERROR: Invalid gripper angle"
                self.angles["gripper"] = angle
                self.attached["gripper"] = True
                if self.visual:
                    self.print_arm_status()
                return "OK: GRIPPER"
            except ValueError:
                return "ERROR: Invalid gripper angle"

        # POSE:w,s,e,g
        if cmd.startswith("POSE:"):
            try:
                parts = cmd[5:].split(",")
                if len(parts) != 4:
                    return "ERROR: Use POSE:w,s,e,g with angles 0-180"
                w, s, e, g = map(int, parts)
                if not (self.valid_angle(w) and self.valid_angle(s) and self.valid_angle(e) and self.valid_angle(g)):
                    return "ERROR: Use POSE:w,s,e,g with angles 0-180"
                
                self.angles["waist"] = w
                self.angles["shoulder"] = s
                self.angles["elbow"] = e
                self.angles["gripper"] = g
                for k in self.attached:
                    self.attached[k] = True
                    
                if self.visual:
                    self.print_arm_status()
                return "OK: POSE_COMMAND_ACCEPTED"
            except ValueError:
                return "ERROR: Use POSE:w,s,e,g with angles 0-180"

        if cmd == "HOME":
            return "ERROR: HOME pose is not configured yet"

        return "ERROR: Unknown command"

    def handle_client(self, client_sock, client_addr):
        print(f"\n[MOCK ESP32] ROS/Python Client connected from {client_addr}")
        # Send greeting exact as ESP32:
        client_sock.sendall(b"CONNECTED: ESP32 robot arm ready\n")
        
        buffer = ""
        while self.running:
            try:
                data = client_sock.recv(1024)
                if not data:
                    break
                buffer += data.decode("utf-8", errors="ignore")
                
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if line:
                        reply = self.process_command(line)
                        if reply:
                            client_sock.sendall((reply + "\n").encode("utf-8"))
            except Exception as ex:
                print(f"[MOCK ESP32] Connection error: {ex}")
                break

        print(f"[MOCK ESP32] Client {client_addr} disconnected.")
        client_sock.close()

    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(1)
        self.running = True
        
        print("\n" + "="*50)
        print("  VIRTUAL ESP32 ROBOT ARM SERVER STARTED")
        print(f"  Listening on: {self.host}:{self.port}")
        print("  Compatible with exact ESP32 TCP protocol")
        print("="*50 + "\n")

        try:
            while self.running:
                client_sock, client_addr = self.server_socket.accept()
                t = threading.Thread(target=self.handle_client, args=(client_sock, client_addr), daemon=True)
                t.start()
        except KeyboardInterrupt:
            print("\n[MOCK ESP32] Shutting down.")
        finally:
            self.stop()

    def stop(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()

if __name__ == "__main__":
    server = MockESP32Server()
    server.start()
