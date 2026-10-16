#!/usr/bin/env bash
# ==============================================================================
# One-Click ESP32 Firmware Flasher
# Compiles and flashes the 4-DOF Robot Arm TCP server onto the ESP32
# ==============================================================================

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}=================================================================${NC}"
echo -e "${BLUE}        ESP32 ROBOT ARM - ONE-CLICK FIRMWARE FLASHER            ${NC}"
echo -e "${BLUE}=================================================================${NC}"

SKETCH_DIR="firmware/esp32_firmware"
FQBN="esp32:esp32:esp32"

# 1. Check arduino-cli
if ! command -v arduino-cli &>/dev/null; then
    echo -e "${RED}✗ arduino-cli is not installed!${NC}"
    echo -e "Install with: curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh"
    exit 1
fi
echo -e "${GREEN}✓ Found arduino-cli${NC}"

# 2. Check ESP32 core
echo -e "\n${YELLOW}[1/4] Checking ESP32 Board Core...${NC}"
if ! arduino-cli core list | grep -q "esp32:esp32"; then
    echo -e "${YELLOW}Installing esp32 core (this may take a few minutes)...${NC}"
    arduino-cli config init --overwrite
    arduino-cli config set board_manager.additional_urls https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
    arduino-cli core update-index
    arduino-cli core install esp32:esp32
fi
echo -e "${GREEN}✓ ESP32 board core ready.${NC}"

# 3. Check ESP32Servo library
echo -e "\n${YELLOW}[2/4] Ensuring ESP32Servo library is installed...${NC}"
arduino-cli lib install "ESP32Servo" --quiet || true
echo -e "${GREEN}✓ ESP32Servo library verified.${NC}"

# 4. Auto-detect ESP32 Port
echo -e "\n${YELLOW}[3/4] Detecting connected ESP32 over USB...${NC}"
PORT=""
for p in /dev/ttyUSB* /dev/ttyACM* /dev/cu.usbserial* /dev/cu.SLAB_USBtoUART*; do
    if [ -e "$p" ]; then
        PORT="$p"
        break
    fi
done

if [ -z "$PORT" ]; then
    echo -e "${RED}✗ No ESP32 serial port detected!${NC}"
    echo -e "Please plug the ESP32 into a USB port using a data-capable cable, then re-run this script."
    echo -e "Available ports from arduino-cli:"
    arduino-cli board list
    exit 1
fi
echo -e "${GREEN}✓ Found ESP32 on port: ${PORT}${NC}"

# 5. Compile Sketch
echo -e "\n${YELLOW}[4/4] Compiling and Uploading Firmware to ESP32...${NC}"
arduino-cli compile --fqbn "$FQBN" "$SKETCH_DIR"
echo -e "${GREEN}✓ Compilation successful! Uploading...${NC}"

arduino-cli upload -p "$PORT" --fqbn "$FQBN" "$SKETCH_DIR"

echo -e "\n${BLUE}=================================================================${NC}"
echo -e "${GREEN}✓ ESP32 FLASHED SUCCESSFULLY!${NC}"
echo -e "${BLUE}=================================================================${NC}"
echo -e "\nNow listening to Serial Output (115200 baud) to view the WiFi IP address:"
echo -e "Press Ctrl+C to exit monitor.\n"

arduino-cli monitor -p "$PORT" -c baudrate=115200
