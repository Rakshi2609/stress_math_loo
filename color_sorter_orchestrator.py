"""
Color Sorting Orchestrator.
Integrates Vision Detection (HSV + PyTorch ML Model), Dynamic Target Mapping,
and Robot Arm Motion via TCP to ESP32 (or Mock Server).
Supports Shuffled Target Zones!
"""

import time
import os
import cv2
import numpy as np
from config import ROBOT_HOST, ROBOT_PORT, POSES, GRIPPER_OPEN, GRIPPER_CLOSE
from robot_client import RobotArmClient
from vision_detector import ColorDetector

class ColorSortingOrchestrator:
    def __init__(self, host=ROBOT_HOST, port=ROBOT_PORT, model_path="color_model.pth"):
        self.client = RobotArmClient(host=host, port=port)
        self.detector = ColorDetector(model_weights_path=model_path)
        
    def connect_robot(self):
        return self.client.connect()

    def map_target_to_waist_angle(self, target_centroid, frame_shape):
        """
        Dynamically calculates the Waist servo angle based on where the
        target circle is detected on the desk/paper in the camera frame.
        Handles shuffled circle positions automatically!
        """
        cx, cy = target_centroid
        h, w = frame_shape[:2]

        # Normalized position along the workspace table (Y-axis sweep in top-down view)
        # cy ~ 750 (Blue) -> Waist ~ 70°
        # cy ~ 1050 (Red) -> Waist ~ 50°
        # cy ~ 1350 (Green) -> Waist ~ 30°
        y_min = h * 0.45
        y_max = h * 0.90
        norm_y = np.clip((cy - y_min) / (y_max - y_min), 0.0, 1.0)
        
        # Interpolate between 75° and 25°
        computed_waist = int(75 - norm_y * 50)
        return computed_waist

    def process_frame(self, frame):
        """Runs detection on frame and identifies pick object and drop zones."""
        sponge, target_zones = self.detector.analyze_workspace(frame)
        return sponge, target_zones

    def execute_sort(self, detected_color, target_zone_info=None, frame_shape=None):
        """
        Executes the full Pick-and-Place sequence:
        1. Pick sponge from the stack
        2. Move to matching color target zone (using dynamic waist angle if available)
        3. Release sponge
        4. Return Home
        """
        print("\n" + "="*60)
        print(f" [ORCHESTRATOR] STARTING PICK & PLACE FOR: {detected_color}")
        print("="*60)

        # 1. Execute Pick
        self.client.pick_sponge()

        # 2. Determine target drop pose
        color_key = f"DROP_{detected_color.upper()}"
        default_zone = POSES.get(color_key, POSES["DROP_RED"])
        
        pre_pose = default_zone["pre"].copy()
        drop_pose = default_zone["drop"].copy()

        # If target circles were dynamically detected in the camera frame,
        # adjust waist angle to land precisely on the circle (even if shuffled!)
        if target_zone_info and frame_shape:
            dynamic_waist = self.map_target_to_waist_angle(target_zone_info["centroid"], frame_shape)
            print(f"[+] Dynamic Angle Adjustment: Detected {detected_color} circle at {target_zone_info['centroid']}")
            print(f"    Adjusting Waist Angle from default {pre_pose['waist']}° -> {dynamic_waist}°")
            pre_pose["waist"] = dynamic_waist
            drop_pose["waist"] = dynamic_waist

        # 3. Move to Target Drop Zone
        print(f"[*] Moving to {detected_color} drop zone...")
        self.client.move_smooth(pre_pose["waist"], pre_pose["shoulder"], pre_pose["elbow"], GRIPPER_CLOSE)
        time.sleep(0.4)

        # 4. Lower above circle
        print(f"[*] Lowering over target circle...")
        self.client.move_smooth(drop_pose["waist"], drop_pose["shoulder"], drop_pose["elbow"], GRIPPER_CLOSE)
        time.sleep(0.3)

        # 5. Open Gripper (Drop object)
        print(f"[*] Releasing {detected_color} sponge...")
        self.client.move_smooth(drop_pose["waist"], drop_pose["shoulder"], drop_pose["elbow"], GRIPPER_OPEN, steps=8)
        time.sleep(0.4)

        # 6. Retract arm
        print(f"[*] Clearing drop zone...")
        self.client.move_smooth(drop_pose["waist"], pre_pose["shoulder"], pre_pose["elbow"], GRIPPER_OPEN)
        time.sleep(0.3)

        # 7. Return to Home
        self.client.go_home()
        print(f"[✓] Successfully placed {detected_color} sponge in the target box/circle!\n")

    def run_image_demo(self, image_path):
        """Runs complete sort test on a still image (e.g. user's desk setup photo)."""
        print(f"[*] Loading workspace photo: {image_path}")
        frame = cv2.imread(image_path)
        if frame is None:
            print(f"[-] Error: Could not read image at {image_path}")
            return

        sponge, target_zones = self.process_frame(frame)
        
        if not sponge:
            print("[-] No pick sponge detected in frame!")
            return

        detected_color = sponge["color"]
        print(f"\n[+] Vision Detection Found: Top Sponge is '{detected_color}'")
        print(f"    Sponge Bounding Box: {sponge['bbox']}")
        print(f"    Available Target Zones: {list(target_zones.keys())}")

        matching_target = target_zones.get(detected_color)
        if matching_target:
            print(f"[+] Matching target circle for '{detected_color}' located at {matching_target['centroid']}")
        else:
            print(f"[!] Warning: No matching target circle detected for '{detected_color}', using calibrated default zone.")

        # Execute sort routine
        self.execute_sort(detected_color, matching_target, frame.shape)

    def run_webcam(self, camera_index=0):
        """Runs continuous real-time sorting loop using live webcam feed."""
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            print(f"[-] Error: Cannot open camera index {camera_index}")
            return

        print("[*] Camera stream started. Press 's' to sort detected object, 'q' to quit.")

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            sponge, target_zones = self.process_frame(frame)
            overlay = self.detector.draw_overlay(frame, sponge, target_zones)

            cv2.imshow("Robot Arm Vision - Color Sorter", overlay)
            key = cv2.waitKey(1) & 0xFF

            if key == ord('s'):
                if sponge:
                    print(f"[*] Triggering sort for {sponge['color']}...")
                    matching = target_zones.get(sponge["color"])
                    self.execute_sort(sponge["color"], matching, frame.shape)
                else:
                    print("[!] No sponge detected to pick.")
            elif key == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    import sys
    model_path = "/home/appu/intership/stress_math_lo/color_model.pth"
    orchestrator = ColorSortingOrchestrator(model_path=model_path)
    
    if orchestrator.connect_robot():
        demo_img = "/home/appu/.gemini/antigravity-cli/brain/6b33a9ea-9efa-44b4-8ccd-ee81904198f4/.user_uploaded/uploaded_media_0_1792176089996.png"
        orchestrator.run_image_demo(demo_img)
    else:
        print("[-] Could not connect to robot server. Ensure mock_esp32_server.py is running.")
