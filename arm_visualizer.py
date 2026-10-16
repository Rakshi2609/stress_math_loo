"""
Robotic Arm Kinematics 2D Multi-View Visualizer.
Plots Top-Down (X-Y workspace sweep) and Side Elevation (R-Z elevation) views
of the 4-DOF Arm links, sponge pick stack, and target drop circles.
Works reliably in any standard Matplotlib / headless Linux environment.
"""

import math
import numpy as np
import matplotlib.pyplot as plt
from config import LINK_BASE_HEIGHT, LINK_HUMERUS, LINK_FOREARM, LINK_GRIPPER

class ArmVisualizer:
    def __init__(self):
        self.L0 = LINK_BASE_HEIGHT  # Base to shoulder (55mm)
        self.L1 = LINK_HUMERUS      # Shoulder to elbow (80mm)
        self.L2 = LINK_FOREARM      # Elbow to wrist (80mm)
        self.L3 = LINK_GRIPPER      # Wrist to gripper tip (50mm)

    def forward_kinematics(self, waist_deg, shoulder_deg, elbow_deg, gripper_deg):
        w_rad = math.radians(waist_deg)
        s_rad = math.radians(shoulder_deg)
        e_rad = math.radians(elbow_deg - 90)

        # Base origin
        p0 = (0.0, 0.0, 0.0)

        # Shoulder pivot
        p1 = (0.0, 0.0, self.L0)

        # Elbow pivot
        r1 = self.L1 * math.sin(s_rad)
        z1 = self.L0 + self.L1 * math.cos(s_rad)
        x1 = r1 * math.cos(w_rad)
        y1 = r1 * math.sin(w_rad)
        p2 = (x1, y1, z1)

        # Wrist pivot
        tot_pitch = s_rad + e_rad
        r2 = r1 + self.L2 * math.sin(tot_pitch)
        z2 = z1 - self.L2 * math.cos(tot_pitch)
        x2 = r2 * math.cos(w_rad)
        y2 = r2 * math.sin(w_rad)
        p3 = (x2, y2, z2)

        # Gripper tip
        r3 = r2 + self.L3 * math.sin(tot_pitch)
        z3 = z2 - self.L3 * math.cos(tot_pitch)
        x3 = r3 * math.cos(w_rad)
        y3 = r3 * math.sin(w_rad)
        p4 = (x3, y3, z3)

        return [p0, p1, p2, p3, p4]

    def render_pose(self, waist, shoulder, elbow, gripper, save_path=None, title="4-DOF Robot Arm"):
        joints = self.forward_kinematics(waist, shoulder, elbow, gripper)
        xs = [p[0] for p in joints]
        ys = [p[1] for p in joints]
        zs = [p[2] for p in joints]
        rs = [math.sqrt(p[0]**2 + p[1]**2) for p in joints]

        fig, (ax_top, ax_side) = plt.subplots(1, 2, figsize=(12, 5))

        # 1. TOP-DOWN VIEW (X - Y)
        ax_top.plot(xs, ys, '-o', linewidth=4, color='sienna', markersize=6, label="Arm")
        gripper_state = "OPEN" if gripper <= 130 else "CLOSED"
        ax_top.scatter([xs[-1]], [ys[-1]], color='red' if gripper_state == "CLOSED" else 'green',
                       s=140, label=f"Claw ({gripper_state})", zorder=5)

        # Drop zones on table
        ax_top.scatter([-40], [130], color='blue', s=250, label="Target Blue")
        ax_top.scatter([10], [140], color='red', s=250, label="Target Red")
        ax_top.scatter([60], [130], color='green', s=250, label="Target Green")
        ax_top.scatter([-100], [80], color='darkorange', s=280, marker='s', label="Pick Stack")

        ax_top.set_xlim([-140, 140])
        ax_top.set_ylim([-20, 200])
        ax_top.set_aspect('equal')
        ax_top.set_title("Top-Down View (Table Workspace)")
        ax_top.set_xlabel("X (mm)")
        ax_top.set_ylabel("Y (mm)")
        ax_top.grid(True, linestyle='--', alpha=0.6)
        ax_top.legend(loc='upper right', fontsize=8)

        # 2. SIDE ELEVATION VIEW (Radial Reach vs Height Z)
        ax_side.plot(rs, zs, '-o', linewidth=4, color='sienna', markersize=6)
        ax_side.scatter([rs[-1]], [zs[-1]], color='red' if gripper_state == "CLOSED" else 'green', s=140, zorder=5)
        ax_side.axhline(0, color='black', linewidth=2, linestyle='-', label="Table Surface (Z=0)")
        
        ax_side.set_xlim([-20, 220])
        ax_side.set_ylim([-10, 200])
        ax_side.set_aspect('equal')
        ax_side.set_title("Side Elevation (Reach R vs Height Z)")
        ax_side.set_xlabel("Radial Distance R (mm)")
        ax_side.set_ylabel("Height Z (mm)")
        ax_side.grid(True, linestyle='--', alpha=0.6)
        ax_side.legend(loc='upper right', fontsize=8)

        fig.suptitle(f"{title} | Angles: W={waist}° S={shoulder}° E={elbow}° G={gripper}°", fontsize=12, fontweight='bold')
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=120)
            print(f"[+] Render saved to {save_path}")
        plt.close()

if __name__ == "__main__":
    viz = ArmVisualizer()
    viz.render_pose(108, 120, 110, 165, save_path="/home/appu/intership/stress_math_lo/arm_pick_pose.png", title="Pick Pose (Calibrated)")
    viz.render_pose(52, 125, 105, 120, save_path="/home/appu/intership/stress_math_lo/arm_drop_pose.png", title="Drop Pose (Red Circle)")
