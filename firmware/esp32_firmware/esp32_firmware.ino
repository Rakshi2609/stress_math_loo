#include <WiFi.h>
#include <ESP32Servo.h>

// ============================================
// 1. WIFI SETTINGS (Change to match local WiFi)
// ============================================
const char* WIFI_SSID     = "nishu";
const char* WIFI_PASSWORD = "nishu0987";

// ============================================
// 2. TCP SERVER SETTINGS
// ============================================
WiFiServer server(5000);
WiFiClient client;

// ============================================
// 3. SERVO GPIO PINS
// ============================================
const int WAIST_PIN    = 13;
const int SHOULDER_PIN = 26;
const int ELBOW_PIN    = 25;
const int GRIPPER_PIN  = 27;

// ============================================
// 4. SERVO OBJECTS
// ============================================
Servo waistServo;
Servo shoulderServo;
Servo elbowServo;
Servo gripperServo;

bool waistAttached = false;
bool shoulderAttached = false;
bool elbowAttached = false;
bool gripperAttached = false;

// Pulse range from calibration (TowerPro SG90 standard)
const int MIN_PULSE = 500;
const int MAX_PULSE = 2400;

// ============================================
// 5. SERVO HELPER FUNCTIONS
// ============================================
bool validAngle(int angle) {
  return angle >= 0 && angle <= 180;
}

void setWaist(int angle) {
  if (!validAngle(angle)) return;
  if (!waistAttached) {
    waistServo.attach(WAIST_PIN, MIN_PULSE, MAX_PULSE);
    waistAttached = true;
  }
  waistServo.write(angle);
  Serial.printf("Waist = %d degrees\n", angle);
}

void setShoulder(int angle) {
  if (!validAngle(angle)) return;
  if (!shoulderAttached) {
    shoulderServo.attach(SHOULDER_PIN, MIN_PULSE, MAX_PULSE);
    shoulderAttached = true;
  }
  shoulderServo.write(angle);
  Serial.printf("Shoulder = %d degrees\n", angle);
}

void setElbow(int angle) {
  if (!validAngle(angle)) return;
  if (!elbowAttached) {
    elbowServo.attach(ELBOW_PIN, MIN_PULSE, MAX_PULSE);
    elbowAttached = true;
  }
  elbowServo.write(angle);
  Serial.printf("Elbow = %d degrees\n", angle);
}

void setGripper(int angle) {
  if (!validAngle(angle)) return;
  if (!gripperAttached) {
    gripperServo.attach(GRIPPER_PIN, MIN_PULSE, MAX_PULSE);
    gripperAttached = true;
  }
  gripperServo.write(angle);
  Serial.printf("Gripper = %d degrees\n", angle);
}

// ============================================
// 6. SEND REPLY TO CLIENT
// ============================================
void reply(String message) {
  Serial.println(message);
  if (client && client.connected()) {
    client.println(message);
  }
}

// ============================================
// 7. PROCESS COMMANDS
// ============================================
void processCommand(String command) {
  command.trim();
  Serial.print("Received command: ");
  Serial.println(command);

  if (command.length() == 0) return;

  if (command.startsWith("WAIST:")) {
    int angle = command.substring(6).toInt();
    if (!validAngle(angle)) { reply("ERROR: Invalid waist angle"); return; }
    setWaist(angle);
    reply("OK: WAIST");
    return;
  }

  if (command.startsWith("SHOULDER:")) {
    int angle = command.substring(9).toInt();
    if (!validAngle(angle)) { reply("ERROR: Invalid shoulder angle"); return; }
    setShoulder(angle);
    reply("OK: SHOULDER");
    return;
  }

  if (command.startsWith("ELBOW:")) {
    int angle = command.substring(6).toInt();
    if (!validAngle(angle)) { reply("ERROR: Invalid elbow angle"); return; }
    setElbow(angle);
    reply("OK: ELBOW");
    return;
  }

  if (command.startsWith("GRIPPER:")) {
    int angle = command.substring(8).toInt();
    if (!validAngle(angle)) { reply("ERROR: Invalid gripper angle"); return; }
    setGripper(angle);
    reply("OK: GRIPPER");
    return;
  }

  if (command.startsWith("POSE:")) {
    int w, s, e, g;
    int count = sscanf(command.c_str() + 5, "%d,%d,%d,%d", &w, &s, &e, &g);

    if (count != 4 || !validAngle(w) || !validAngle(s) || !validAngle(e) || !validAngle(g)) {
      reply("ERROR: Use POSE:w,s,e,g with angles 0-180");
      return;
    }

    setWaist(w);
    setShoulder(s);
    setElbow(e);
    setGripper(g);
    reply("OK: POSE_COMMAND_ACCEPTED");
    return;
  }

  if (command == "HOME") {
    setWaist(90);
    setShoulder(90);
    setElbow(90);
    setGripper(120);
    reply("OK: HOME");
    return;
  }

  reply("ERROR: Unknown command");
}

// ============================================
// 8. SETUP & INITIALIZATION
// ============================================
void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println();
  Serial.println("================================");
  Serial.println(" 4-DOF ROBOT ARM - ESP32 SERVER ");
  Serial.println("================================");

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  Serial.print("Connecting to WiFi");
  unsigned long startTime = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - startTime < 30000) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi connection failed. Check SSID and password.");
    return;
  }

  Serial.println("WiFi connected successfully!");
  Serial.print("ESP32 IP address: ");
  Serial.println(WiFi.localIP());

  server.begin();
  server.setNoDelay(true);

  Serial.println("TCP server started on port 5000");
  Serial.println("Waiting for Robot Client controller...");
}

// ============================================
// 9. CONTINUOUS LOOP
// ============================================
void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    delay(500);
    return;
  }

  if (!client || !client.connected()) {
    WiFiClient newClient = server.available();
    if (newClient) {
      client = newClient;
      client.setTimeout(1000);
      Serial.println("\nCLIENT CONNECTED!");
      client.println("CONNECTED: ESP32 robot arm ready");
    }
  }

  if (client && client.connected() && client.available()) {
    String command = client.readStringUntil('\n');
    processCommand(command);
  }

  delay(2);
}
