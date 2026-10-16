#!/usr/bin/env bash
# ==============================================================================
# Setup & Dependency Checker for 4-DOF Robotic Arm Color Sorting System
# ==============================================================================

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=================================================================${NC}"
echo -e "${BLUE}    4-DOF ROBOTIC ARM COLOR SORTER - SETUP & DEPENDENCY CHECK    ${NC}"
echo -e "${BLUE}=================================================================${NC}"

# 1. Check Python 3
echo -e "\n${YELLOW}[1/5] Checking Python 3 Installation...${NC}"
if command -v python3 &>/dev/null; then
    PY_VER=$(python3 --version)
    echo -e "${GREEN}✓ Python is installed: ${PY_VER}${NC}"
else
    echo -e "${RED}✗ Python 3 not found! Please install python3.${NC}"
    exit 1
fi

# 2. Check pip
echo -e "\n${YELLOW}[2/5] Checking pip...${NC}"
if python3 -m pip --version &>/dev/null; then
    echo -e "${GREEN}✓ pip is available${NC}"
else
    echo -e "${RED}✗ pip is missing! Installing python3-pip...${NC}"
    sudo apt update && sudo apt install -y python3-pip
fi

# 3. Install Python Dependencies
echo -e "\n${YELLOW}[3/5] Installing/Verifying Python Dependencies (PyTorch, OpenCV, Matplotlib, NumPy)...${NC}"
python3 -m pip install -r requirements.txt --quiet --break-system-packages 2>/dev/null || python3 -m pip install -r requirements.txt --quiet

# Verify imports in Python
python3 -c "
import cv2, torch, numpy, matplotlib
print('  All core libraries imported successfully!')
print(f'  - OpenCV: {cv2.__version__}')
print(f'  - PyTorch: {torch.__version__} (CUDA: {torch.cuda.is_available()})')
print(f'  - NumPy: {numpy.__version__}')
print(f'  - Matplotlib: {matplotlib.__version__}')
"
echo -e "${GREEN}✓ Python environment verified.${NC}"

# 4. Check for Connected Webcams
echo -e "\n${YELLOW}[4/5] Checking Video / Camera Devices...${NC}"
CAMERAS=$(ls -d /dev/video* 2>/dev/null || true)
if [ -n "$CAMERAS" ]; then
    echo -e "${GREEN}✓ Detected camera devices:${NC}"
    for cam in $CAMERAS; do
        echo -e "   - $cam"
    done
else
    echo -e "${YELLOW}! No physical /dev/video* webcam found right now.${NC}"
    echo -e "  (The system will run in simulation/test-image mode until you connect a USB webcam)."
fi

# 5. Check or Train ML Model Weights
echo -e "\n${YELLOW}[5/5] Checking ML Color Classifier Model ('color_model.pth')...${NC}"
if [ -f "color_model.pth" ]; then
    echo -e "${GREEN}✓ Pre-trained model weights found at color_model.pth${NC}"
else
    echo -e "${YELLOW}! Model weights not found. Training model now...${NC}"
    python3 train_color_model.py
    echo -e "${GREEN}✓ Model trained and saved to color_model.pth${NC}"
fi

echo -e "\n${BLUE}=================================================================${NC}"
echo -e "${GREEN}✓ SETUP COMPLETE! You are ready to run the system.${NC}"
echo -e "${BLUE}=================================================================${NC}"
echo -e "
Quick Start Commands:

1. Start the Virtual ESP32 Server (if hardware is not plugged in):
   ${GREEN}python3 mock_esp32_server.py${NC}

2. Run the Color Sorting Orchestrator (Demo on desk photo):
   ${GREEN}python3 color_sorter_orchestrator.py${NC}

3. Run with Live USB Webcam:
   ${GREEN}python3 -c \"from color_sorter_orchestrator import ColorSortingOrchestrator; orc = ColorSortingOrchestrator(); orc.connect_robot() and orc.run_webcam(0)\"${NC}

4. Render 2D/3D Kinematics Poses:
   ${GREEN}python3 arm_visualizer.py${NC}
"
