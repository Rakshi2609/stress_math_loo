"""
Vision Detection & ML Pipeline for Robot Arm Color Sorting.
Detects Pick Objects (Sponges) and Target Zones (Drawn Circles/Boxes) for RED, GREEN, and BLUE.
Handles color shuffling by dynamically locating where each target color is positioned in the camera frame.
"""

import cv2
import numpy as np
import torch
import torch.nn as nn
import os

# ============================================
# 1. HSV COLOR DEFINITIONS (Calibrated to Sponges & Markers)
# ============================================
COLOR_HSV_RANGES = {
    "RED": [
        (np.array([0, 110, 80]), np.array([10, 255, 255])),
        (np.array([160, 110, 80]), np.array([180, 255, 255]))
    ],
    "GREEN": [
        (np.array([35, 70, 50]), np.array([85, 255, 255]))
    ],
    "BLUE": [
        (np.array([95, 100, 60]), np.array([135, 255, 255]))
    ]
}

# ============================================
# 2. LIGHTWEIGHT PYTORCH COLOR CLASSIFIER (ML MODEL)
# ============================================
class ColorClassifierCNN(nn.Module):
    """
    Lightweight CNN for classifying 64x64 cropped object regions into:
    [0: RED, 1: GREEN, 2: BLUE, 3: BACKGROUND]
    """
    def __init__(self, num_classes=4):
        super(ColorClassifierCNN, self).__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 16, kernel_size=3, padding=1),
            nn.BatchNorm2d(16),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2), # 32x32

            nn.Conv2d(16, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2), # 16x16

            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d((4, 4)) # 4x4
        )
        self.classifier = nn.Sequential(
            nn.Linear(64 * 4 * 4, 64),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(64, num_classes)
        )

    def forward(self, x):
        x = self.features(x)
        x = x.view(x.size(0), -1)
        return self.classifier(x)

# ============================================
# 3. DETECTOR ENGINE
# ============================================
class ColorDetector:
    def __init__(self, model_weights_path=None):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.classes = ["RED", "GREEN", "BLUE", "BACKGROUND"]
        self.ml_model = None

        if model_weights_path and os.path.exists(model_weights_path):
            try:
                self.ml_model = ColorClassifierCNN(num_classes=4).to(self.device)
                self.ml_model.load_state_dict(torch.load(model_weights_path, map_location=self.device))
                self.ml_model.eval()
                print(f"[+] Loaded ML Color Classifier weights from {model_weights_path}")
            except Exception as e:
                print(f"[!] Warning: Could not load ML model: {e}")

    def detect_colored_regions(self, frame, min_area=1500, roi=None):
        """
        Scans frame for RED, GREEN, and BLUE regions using HSV masks & contour analysis.
        Returns a dictionary of detections categorized by color.
        """
        if roi:
            x_r, y_r, w_r, h_r = roi
            scan_area = frame[y_r:y_r+h_r, x_r:x_r+w_r]
            offset_x, offset_y = x_r, y_r
        else:
            scan_area = frame
            offset_x, offset_y = 0, 0

        hsv = cv2.cvtColor(scan_area, cv2.COLOR_BGR2HSV)
        detections = {"RED": [], "GREEN": [], "BLUE": []}

        for color_name, ranges in COLOR_HSV_RANGES.items():
            mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
            for lower, upper in ranges:
                mask = cv2.bitwise_or(mask, cv2.inRange(hsv, lower, upper))

            # Clean noise with morphological open & close
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for c in contours:
                area = cv2.contourArea(c)
                if area >= min_area:
                    x, y, w, h = cv2.boundingRect(c)
                    M = cv2.moments(c)
                    cx = int(M["m10"] / M["m00"]) if M["m00"] != 0 else x + w // 2
                    cy = int(M["m01"] / M["m00"]) if M["m00"] != 0 else y + h // 2

                    # Global coordinates
                    gx = x + offset_x
                    gy = y + offset_y
                    gcx = cx + offset_x
                    gcy = cy + offset_y

                    # Differentiate shape: circle ring vs solid sponge block
                    # Ring has hollow center (lower fill ratio or lower solidity)
                    hull = cv2.convexHull(c)
                    solidity = float(area) / cv2.contourArea(hull) if cv2.contourArea(hull) > 0 else 0

                    detections[color_name].append({
                        "color": color_name,
                        "centroid": (gcx, gcy),
                        "bbox": (gx, gy, w, h),
                        "area": area,
                        "solidity": solidity,
                        "contour": c
                    })

        return detections

    def analyze_workspace(self, frame):
        """
        Analyzes the full workspace:
        1. Identifies the Pick Stack (sponges)
        2. Identifies the Target Circles (drop zones) even if they are shuffled!
        """
        h, w = frame.shape[:2]
        
        # In typical camera setup:
        # Sponges are in pick zone (e.g. top-left or specified bounding box)
        # Target circles are arranged along the workspace sweep arc
        all_detections = self.detect_colored_regions(frame, min_area=2000)

        sponge_candidate = None
        target_zones = {}

        # Scan for detected items
        for color, items in all_detections.items():
            for item in items:
                cx, cy = item["centroid"]
                bx, by, bw, bh = item["bbox"]

                # Exclude edge clutter or top background boxes
                if cy < h * 0.15 or cy > h * 0.95:
                    continue
                if cx > w * 0.8: # Arm base area
                    continue

                # Heuristic: Pick stack is near the top-left area (cy ~ 400-650 in the 1600x900 image)
                # Circles are drawn along y ~ 700-1400
                if cy < h * 0.45:
                    if sponge_candidate is None or item["area"] > sponge_candidate["area"]:
                        sponge_candidate = item
                else:
                    # Target drop circle
                    target_zones[color] = item

        return sponge_candidate, target_zones

    def draw_overlay(self, frame, sponge, target_zones):
        """Draws visual feedback on frame with bounding boxes and color labels."""
        annotated = frame.copy()

        # Draw detected pick sponge
        if sponge:
            x, y, w, h = sponge["bbox"]
            color = sponge["color"]
            cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 255, 255), 3)
            label = f"PICK: {color} SPONGE"
            cv2.putText(annotated, label, (x, max(30, y - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
            cv2.circle(annotated, sponge["centroid"], 6, (0, 0, 255), -1)

        # Draw detected target zones
        for color, zone in target_zones.items():
            x, y, w, h = zone["bbox"]
            cx, cy = zone["centroid"]
            b_color = (0, 0, 255) if color == "RED" else (0, 255, 0) if color == "GREEN" else (255, 0, 0)
            cv2.rectangle(annotated, (x, y), (x + w, y + h), b_color, 2)
            cv2.putText(annotated, f"TARGET: {color}", (x, max(30, y - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, b_color, 2)
            cv2.circle(annotated, (cx, cy), 8, b_color, -1)

        return annotated
