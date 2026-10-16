# stress_math_loo: 4-DOF Robotic Arm Autonomous Color Sorting System

An autonomous, vision-guided pick-and-place robotic arm system built for the **Kit4Curious / meArm 4-DOF Robotic Arm** powered by **TowerPro SG90 micro-servos** and an **ESP32** microcontroller over a TCP socket interface.

The system uses **OpenCV** and a custom **PyTorch Deep Learning CNN Model** to detect colored objects (Red, Green, Blue sponges) and sort them into matching colored target circles or boxes on a workspace table—even if the targets are shuffled or placed dynamically.

---

## System Architecture

```
                       [ Overhead Camera ]
                                |
                                v
               [ Computer Vision & ML Pipeline ]
                 - HSV Adaptive Segmentation
                 - PyTorch CNN (color_model.pth)
                 - Dynamic Target Tracking (Handles Shuffling)
                                |
                                v
               [ Trajectory & Kinematics Engine ]
                 - Calibrated Poses
                 - Smooth Angle Interpolation
                                |
                                v
                   [ TCP Socket (Port 5000) ]
                   /                        \
                  v                          v
    [ Virtual Mock ESP32 Server ]      [ Physical ESP32 Hardware ]
      - Runs without hardware            - WiFi Client / TCP Server
      - 2D/3D Kinematic Visualizer       - 4x SG90 Servo PWM Controller
```

---

## Features

1. **Hardware-Free Simulation (Mock ESP32 Server)**:
   - A complete TCP server (`mock_esp32_server.py`) that matches the exact ESP32 Arduino firmware protocol (`POSE:w,s,e,g`, `WAIST:...`, `OK: ...`).
   - Allows developing and debugging the entire vision and control pipeline without physical hardware.

2. **PyTorch ML Color Classifier & Vision Pipeline**:
   - Classifies Red, Green, Blue objects and background surfaces under varying lighting, textures, and shadows.
   - Detects both the object to pick and the target drop circles.

3. **Dynamic Shuffling Support**:
   - The arm dynamically recalculates its waist rotation angle based on the detected centroid coordinates of each target circle on the table.

4. **Gear Protection & Smooth Trajectory Interpolation**:
   - Smooth step interpolation prevents SG90 plastic gears from stripping and prevents high current spikes that cause ESP32 brownout resets.

5. **2D/3D Multi-View Kinematics Visualizer & Simulator**:
   - Visualizes table workspace reach ($X-Y$ top view) and arm elevation ($R-Z$ side view).
   - Generates animated GIFs and multi-view dashboards (`color_sorting_simulation.gif`, `sorting_dashboard.png`).

6. **One-Click ESP32 Firmware Flasher (`flash_esp32.sh`)**:
   - Compiles and uploads firmware to the ESP32 with zero manual IDE setup.

---

## Hardware Configuration (When ESP32 is Connected)

| Servo Joint | ESP32 GPIO Pin | Description | Calibrated Safe Range |
| :--- | :--- | :--- | :--- |
| **Waist (Base)** | `GPIO 13` | Horizontal yaw rotation | $0^\circ \to 180^\circ$ ($90^\circ$ center) |
| **Shoulder** | `GPIO 26` | Lower arm pitch / lift | $45^\circ \to 170^\circ$ |
| **Elbow** | `GPIO 25` | Upper arm pitch / reach | $30^\circ \to 160^\circ$ |
| **Gripper** | `GPIO 27` | End-effector claw | $120^\circ$ (Open) $\to 165^\circ$ (Grip) |

---

## Quick Start & Testing Guide

### 1. Run Setup Script (One-Click Environment Setup)
```bash
chmod +x setup.sh
./setup.sh
```

### 2. Start the Virtual Robot Arm Server (Active by Default)
If testing without the physical ESP32, start the mock server:
```bash
python3 mock_esp32_server.py
```
*(Runs on `0.0.0.0:5000` and emulates the exact ESP32 firmware).*

### 3. Run the Color Sorting Orchestrator
To test end-to-end with the workspace test photo:
```bash
python3 color_sorter_orchestrator.py
```

To run with live USB webcam:
```bash
python3 -c "
from color_sorter_orchestrator import ColorSortingOrchestrator
orc = ColorSortingOrchestrator()
if orc.connect_robot():
    orc.run_webcam(camera_index=0)
"
```
*(Press `s` to sort the detected object, `q` to quit).*

### 4. Generate Animated Kinematics Simulation
```bash
python3 run_animated_simulation.py
```
Outputs `color_sorting_simulation.gif` and `sorting_dashboard.png`.

### 5. Flash the Physical ESP32 (When Connected via USB)
```bash
chmod +x flash_esp32.sh
./flash_esp32.sh
```
*(Automatically installs `ESP32Servo`, compiles the sketch, flashes the board, and displays the WiFi IP address in the serial monitor).*

---

## Manual TCP Testing Commands

You can connect directly to the server via `nc` (netcat) or `telnet`:
```bash
nc localhost 5000
```
Then send any of the supported commands:
- `POSE:90,90,90,120` (Sets all 4 servos: waist, shoulder, elbow, gripper)
- `WAIST:105` (Rotates waist to 105°)
- `GRIPPER:165` (Closes gripper claw)
- `GRIPPER:120` (Opens gripper claw)
- `HOME` (Returns arm to safe default upright pose)

---

## Project Repository Structure

- `config.py`: Calibrated angles, link dimensions, safe limits, and TCP settings.
- `mock_esp32_server.py`: Virtual TCP server emulating the ESP32.
- `robot_client.py`: TCP client with smooth acceleration and pick-and-place routines.
- `vision_detector.py`: Color detection and target circle tracking module.
- `train_color_model.py`: PyTorch training script for color classification.
- `color_model.pth`: Trained ML model weights.
- `color_sorter_orchestrator.py`: Master state machine orchestrating vision and arm movement.
- `arm_visualizer.py`: 2D multi-view kinematics visualizer.
- `run_animated_simulation.py`: Step-by-step trajectory animation generator.
- `flash_esp32.sh`: One-click firmware compilation and flashing script.
- `firmware/esp32_firmware/esp32_firmware.ino`: Arduino C++ firmware for the ESP32.
- `setup.sh`: Automated dependency verification and environment setup.
