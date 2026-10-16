"""
Configuration settings for the 4-DOF Robotic Arm Color Sorting System.
Includes servo pin mappings, mechanical limits, calibrated angles, and network config.
"""

# ============================================
# 1. NETWORK / TCP SETTINGS
# ============================================
# Connect to '127.0.0.1' for mock simulator, or the ESP32 IP (e.g. '192.168.1.50') when hardware is ready.
ROBOT_HOST = "127.0.0.1"
ROBOT_PORT = 5000

# ============================================
# 2. PHYSICAL SERVO ANGLES & CALIBRATION
# (Directly calibrated from your robot arm notes)
# ============================================
# Safe mechanical angle limits (0-180)
LIMITS = {
    "waist":    (0, 180),
    "shoulder": (45, 170),
    "elbow":    (30, 160),
    "gripper":  (110, 175)
}

# Gripper state angles
GRIPPER_OPEN  = 120   # Jaw fully open to receive sponge block
GRIPPER_CLOSE = 165   # Jaw firmly grips sponge block

# Calibrated Key Poses: (waist, shoulder, elbow, gripper)
POSES = {
    # Neutral resting pose (retracted, upright)
    "HOME": {
        "waist": 90,
        "shoulder": 90,
        "elbow": 90,
        "gripper": GRIPPER_OPEN
    },
    
    # Ready pose above the pick stack
    "PICK_PRE_APPROACH": {
        "waist": 108,
        "shoulder": 150,
        "elbow": 125,
        "gripper": GRIPPER_OPEN
    },
    
    # Grip pose on the sponge block (from your handwritten notes)
    "PICK_GRIP": {
        "waist": 108,
        "shoulder": 120,
        "elbow": 110,
        "gripper": GRIPPER_CLOSE
    },
    
    # Lift after gripping
    "PICK_LIFT": {
        "waist": 108,
        "shoulder": 155,
        "elbow": 125,
        "gripper": GRIPPER_CLOSE
    },

    # Target Drop Zones (Waist sweeps across the drawn target circles)
    # Circle sequence in front of the arm: BLUE, RED, GREEN
    "DROP_BLUE": {
        "pre":  {"waist": 70, "shoulder": 145, "elbow": 120, "gripper": GRIPPER_CLOSE},
        "drop": {"waist": 70, "shoulder": 125, "elbow": 105, "gripper": GRIPPER_OPEN}
    },
    "DROP_RED": {
        "pre":  {"waist": 50, "shoulder": 145, "elbow": 120, "gripper": GRIPPER_CLOSE},
        "drop": {"waist": 50, "shoulder": 125, "elbow": 105, "gripper": GRIPPER_OPEN}
    },
    "DROP_GREEN": {
        "pre":  {"waist": 30, "shoulder": 145, "elbow": 120, "gripper": GRIPPER_CLOSE},
        "drop": {"waist": 30, "shoulder": 125, "elbow": 105, "gripper": GRIPPER_OPEN}
    }
}

# Link lengths in mm (meArm standard for Kit4Curious)
LINK_BASE_HEIGHT = 55.0  # L0 (ground to shoulder axis)
LINK_HUMERUS     = 80.0  # L1 (shoulder to elbow)
LINK_FOREARM     = 80.0  # L2 (elbow to wrist)
LINK_GRIPPER     = 50.0  # L3 (wrist to gripper center)
