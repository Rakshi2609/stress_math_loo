"""
Animated Simulation & Dashboard Generator.
Creates a visual step-by-step animation of the robot arm picking the Red sponge
and dropping it in the target Red circle, saving it as 'color_sorting_simulation.gif'
and a visual overview 'sorting_dashboard.png'.
"""

import math
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import cv2
import os

from config import LINK_BASE_HEIGHT, LINK_HUMERUS, LINK_FOREARM, LINK_GRIPPER, POSES

def forward_kinematics(w_deg, s_deg, e_deg):
    w_rad = math.radians(w_deg)
    s_rad = math.radians(s_deg)
    e_rad = math.radians(e_deg - 90)

    L0, L1, L2, L3 = LINK_BASE_HEIGHT, LINK_HUMERUS, LINK_FOREARM, LINK_GRIPPER

    p0 = (0.0, 0.0, 0.0)
    p1 = (0.0, 0.0, L0)

    r1 = L1 * math.sin(s_rad)
    z1 = L0 + L1 * math.cos(s_rad)
    x1 = r1 * math.cos(w_rad)
    y1 = r1 * math.sin(w_rad)
    p2 = (x1, y1, z1)

    tot_pitch = s_rad + e_rad
    r2 = r1 + L2 * math.sin(tot_pitch)
    z2 = z1 - L2 * math.cos(tot_pitch)
    x2 = r2 * math.cos(w_rad)
    y2 = r2 * math.sin(w_rad)
    p3 = (x2, y2, z2)

    r3 = r2 + L3 * math.sin(tot_pitch)
    z3 = z2 - L3 * math.cos(tot_pitch)
    x3 = r3 * math.cos(w_rad)
    y3 = r3 * math.sin(w_rad)
    p4 = (x3, y3, z3)

    return [p0, p1, p2, p3, p4]

def interpolate_waypoints(waypoints, steps_per_segment=10):
    trajectory = []
    for i in range(len(waypoints) - 1):
        p_start, g_start, text_start = waypoints[i]
        p_end, g_end, text_end = waypoints[i + 1]

        for s in range(steps_per_segment):
            alpha = s / float(steps_per_segment)
            # Smooth cosine ease in/out
            smooth_alpha = (1.0 - math.cos(alpha * math.pi)) / 2.0

            w = p_start["waist"] + (p_end["waist"] - p_start["waist"]) * smooth_alpha
            sh = p_start["shoulder"] + (p_end["shoulder"] - p_start["shoulder"]) * smooth_alpha
            el = p_start["elbow"] + (p_end["elbow"] - p_start["elbow"]) * smooth_alpha
            g = g_start + (g_end - g_start) * smooth_alpha
            desc = text_end if alpha > 0.5 else text_start

            trajectory.append((w, sh, el, g, desc))
    
    # Add final frame
    p_last, g_last, text_last = waypoints[-1]
    trajectory.append((p_last["waist"], p_last["shoulder"], p_last["elbow"], g_last, text_last))
    return trajectory

def generate_simulation():
    print("[*] Generating simulation trajectory...")
    
    # Define Pick & Place Waypoints based on calibrated notes
    p_home = POSES["HOME"]
    p_pre = POSES["PICK_PRE_APPROACH"]
    p_grip = POSES["PICK_GRIP"]
    p_lift = POSES["PICK_LIFT"]
    
    # Red drop zone (dynamically calibrated at waist=52)
    p_red_pre = {"waist": 52, "shoulder": 145, "elbow": 120}
    p_red_drop = {"waist": 52, "shoulder": 125, "elbow": 105}

    waypoints = [
        (p_home, 120, "1. HOME (Ready)"),
        (p_pre, 120, "2. Pre-approach above Sponge Stack"),
        (p_grip, 120, "3. Lower onto Red Sponge"),
        (p_grip, 165, "4. Grip Sponge Firmly (Claw 165°)"),
        (p_lift, 165, "5. Lift Sponge into Clear Air"),
        (p_red_pre, 165, "6. Rotate to Red Target Zone (Waist=52°)"),
        (p_red_drop, 165, "7. Lower Sponge over Red Circle"),
        (p_red_drop, 120, "8. Open Claw - Release Sponge (Drop)"),
        (p_red_pre, 120, "9. Retract Arm to Clear Table"),
        (p_home, 120, "10. Return to HOME Pose")
    ]

    trajectory = interpolate_waypoints(waypoints, steps_per_segment=8)
    print(f"[+] Total animation frames: {len(trajectory)}")

    # Load camera detection image
    img_path = "/home/appu/intership/stress_math_lo/detection_test.jpg"
    cam_img = None
    if os.path.exists(img_path):
        bgr = cv2.imread(img_path)
        cam_img = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

    fig = plt.figure(figsize=(15, 6), dpi=100)
    fig.patch.set_facecolor('#1a1a1a')

    # Grid: 1 row, 3 columns
    # Col 1: Camera Vision
    # Col 2: Top-down table sweep (X-Y)
    # Col 3: Side elevation (R-Z)
    ax_cam = fig.add_subplot(1, 3, 1)
    ax_top = fig.add_subplot(1, 3, 2)
    ax_side = fig.add_subplot(1, 3, 3)

    for ax in [ax_cam, ax_top, ax_side]:
        ax.set_facecolor('#222222')
        ax.tick_params(colors='white')
        for spine in ax.spines.values():
            spine.set_color('#555555')

    if cam_img is not None:
        ax_cam.imshow(cam_img)
        ax_cam.set_title("1. Real-Time Camera Feed & ML Detection", color='white', fontsize=10, pad=10)
        ax_cam.axis('off')

    # Fixed elements on Top View
    ax_top.set_xlim([-140, 140])
    ax_top.set_ylim([-20, 200])
    ax_top.set_aspect('equal')
    ax_top.set_title("2. Top-Down Table Workspace (X-Y)", color='white', fontsize=10, pad=10)
    ax_top.set_xlabel("X (mm)", color='white')
    ax_top.set_ylabel("Y (mm)", color='white')
    ax_top.grid(True, linestyle='--', alpha=0.3, color='gray')

    # Target circles
    ax_top.scatter([-40], [130], color='#2979ff', s=350, edgecolors='white', linewidths=2, label="Blue Zone")
    ax_top.scatter([10], [140], color='#ff1744', s=350, edgecolors='white', linewidths=2, label="Red Zone")
    ax_top.scatter([60], [130], color='#00e676', s=350, edgecolors='white', linewidths=2, label="Green Zone")
    ax_top.scatter([-100], [80], color='#ff9100', s=350, marker='s', edgecolors='white', linewidths=2, label="Pick Stack")

    # Fixed elements on Side View
    ax_side.set_xlim([-10, 220])
    ax_side.set_ylim([-10, 200])
    ax_side.set_aspect('equal')
    ax_side.set_title("3. Side Elevation Reach & Height (R-Z)", color='white', fontsize=10, pad=10)
    ax_side.set_xlabel("Radial Reach R (mm)", color='white')
    ax_side.set_ylabel("Height Z (mm)", color='white')
    ax_side.grid(True, linestyle='--', alpha=0.3, color='gray')
    ax_side.axhline(0, color='white', linewidth=2, linestyle='-', label="Table Surface (Z=0)")

    # Dynamic line and scatter elements
    line_top, = ax_top.plot([], [], '-o', linewidth=5, color='#ffcc80', markersize=7)
    claw_top = ax_top.scatter([], [], s=180, zorder=6)

    line_side, = ax_side.plot([], [], '-o', linewidth=5, color='#ffcc80', markersize=7)
    claw_side = ax_side.scatter([], [], s=180, zorder=6)

    status_text = fig.text(0.5, 0.03, "", ha="center", color="#00e5ff", fontsize=12, fontweight="bold")
    angles_text = fig.text(0.5, 0.95, "", ha="center", color="white", fontsize=11)

    def init():
        line_top.set_data([], [])
        line_side.set_data([], [])
        return line_top, line_side

    def update(frame_idx):
        w, s, e, g, desc = trajectory[frame_idx]
        joints = forward_kinematics(w, s, e)

        xs = [p[0] for p in joints]
        ys = [p[1] for p in joints]
        zs = [p[2] for p in joints]
        rs = [math.sqrt(p[0]**2 + p[1]**2) for p in joints]

        # Top view
        line_top.set_data(xs, ys)
        claw_top.set_offsets([[xs[-1], ys[-1]]])
        claw_top.set_color('#ff1744' if g > 140 else '#76ff03')

        # Side view
        line_side.set_data(rs, zs)
        claw_side.set_offsets([[rs[-1], zs[-1]]])
        claw_side.set_color('#ff1744' if g > 140 else '#76ff03')

        claw_status = "CLOSED (Gripped)" if g > 140 else "OPEN"
        status_text.set_text(f"Action: {desc}")
        angles_text.set_text(f"Servos: Waist={int(w)}°  Shoulder={int(s)}°  Elbow={int(e)}°  Gripper={int(g)}° [{claw_status}]")

        return line_top, line_side, claw_top, claw_side

    print("[*] Rendering animated GIF (this may take ~10-15 seconds)...")
    ani = animation.FuncAnimation(fig, update, frames=len(trajectory), init_func=init, blit=False, interval=100)
    
    gif_path = "/home/appu/intership/stress_math_lo/color_sorting_simulation.gif"
    ani.save(gif_path, writer='pillow', fps=10)
    print(f"[+] Animation saved to {gif_path}")

    # Also save a high-res static multi-step overview
    update(len(trajectory) // 2)
    static_path = "/home/appu/intership/stress_math_lo/sorting_dashboard.png"
    plt.savefig(static_path, dpi=120, bbox_inches='tight')
    print(f"[+] Static dashboard saved to {static_path}")
    plt.close()

if __name__ == "__main__":
    generate_simulation()
