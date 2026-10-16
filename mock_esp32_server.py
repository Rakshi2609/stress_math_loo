"""
Dual-Protocol ESP32 Mock Server & Interactive Web Dashboard.
Listens on Port 5000:
1. Web Browser (http://localhost:5000): Serves an interactive HTML5 visualizer with live arm animation, sliders, and camera view.
2. TCP Sockets (ROS2, Python, netcat): Handles raw ESP32 protocol ('POSE:w,s,e,g', 'WAIST:...', etc.).
"""

import socket
import threading
import time
import math
import json
import os
import sys

# HTML5 Web Visualizer Template
WEB_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>4-DOF Robot Arm - Web Visualizer & Controller</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
  body { background: #0f172a; color: #f8fafc; padding: 20px; }
  .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; padding-bottom: 15px; margin-bottom: 20px; }
  .header h1 { font-size: 22px; color: #38bdf8; display: flex; align-items: center; gap: 10px; }
  .badge { background: #10b981; color: #022c22; font-size: 12px; font-weight: bold; padding: 4px 10px; border-radius: 999px; }
  .grid { display: grid; grid-template-columns: 1fr 340px; gap: 20px; }
  @media(max-width: 900px) { .grid { grid-template-columns: 1fr; } }
  .card { background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 18px; }
  .card-title { font-size: 15px; font-weight: 600; color: #94a3b8; margin-bottom: 14px; text-transform: uppercase; letter-spacing: 0.5px; }
  .canvas-container { position: relative; width: 100%; height: 420px; background: #0b1120; border-radius: 8px; overflow: hidden; }
  canvas { width: 100%; height: 100%; display: block; }
  .control-group { margin-bottom: 16px; }
  .slider-header { display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 14px; font-weight: 500; }
  .slider-val { color: #38bdf8; font-weight: bold; }
  input[type=range] { width: 100%; height: 6px; border-radius: 3px; background: #334155; outline: none; -webkit-appearance: none; }
  input[type=range]::-webkit-slider-thumb { -webkit-appearance: none; width: 18px; height: 18px; border-radius: 50%; background: #38bdf8; cursor: pointer; }
  .btn-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 15px; }
  .btn { background: #334155; color: white; border: none; padding: 10px 14px; border-radius: 8px; font-weight: 600; cursor: pointer; transition: all 0.2s; font-size: 13px; text-align: center; }
  .btn:hover { background: #475569; }
  .btn-red { background: #dc2626; } .btn-red:hover { background: #ef4444; }
  .btn-green { background: #16a34a; } .btn-green:hover { background: #22c55e; }
  .btn-blue { background: #2563eb; } .btn-blue:hover { background: #3b82f6; }
  .btn-home { background: #0284c7; grid-column: span 2; } .btn-home:hover { background: #0ea5e9; }
  .camera-box { margin-top: 20px; }
  .camera-img { width: 100%; border-radius: 8px; border: 1px solid #334155; }
  .console { background: #020617; border-radius: 8px; padding: 12px; font-family: monospace; font-size: 12px; color: #38bdf8; height: 130px; overflow-y: auto; margin-top: 15px; }
</style>
</head>
<body>

<div class="header">
  <h1><span>🤖</span> 4-DOF Robotic Arm - Live Simulation & Controller</h1>
  <div class="badge" id="connStatus">LIVE TCP PORT 5000</div>
</div>

<div class="grid">
  <!-- Left Column: Visualizer Canvas & Camera -->
  <div>
    <div class="card">
      <div class="card-title">Real-Time Kinematics Simulator (Top & Side Views)</div>
      <div class="canvas-container">
        <canvas id="armCanvas"></canvas>
      </div>
    </div>

    <div class="card camera-box">
      <div class="card-title">Camera Feed & ML Color Detection</div>
      <img class="camera-img" src="/camera.jpg" alt="Camera Feed">
    </div>
  </div>

  <!-- Right Column: Interactive Sliders & Actions -->
  <div>
    <div class="card">
      <div class="card-title">Manual Servo Controls</div>

      <div class="control-group">
        <div class="slider-header"><span>Waist (Base Yaw)</span><span class="slider-val" id="waistVal">90°</span></div>
        <input type="range" id="waist" min="0" max="180" value="90" oninput="sendPose()">
      </div>

      <div class="control-group">
        <div class="slider-header"><span>Shoulder (Lift)</span><span class="slider-val" id="shoulderVal">90°</span></div>
        <input type="range" id="shoulder" min="45" max="170" value="90" oninput="sendPose()">
      </div>

      <div class="control-group">
        <div class="slider-header"><span>Elbow (Reach)</span><span class="slider-val" id="elbowVal">90°</span></div>
        <input type="range" id="elbow" min="30" max="160" value="90" oninput="sendPose()">
      </div>

      <div class="control-group">
        <div class="slider-header"><span>Gripper Claw</span><span class="slider-val" id="gripperVal">120° (Open)</span></div>
        <input type="range" id="gripper" min="110" max="170" value="120" oninput="sendPose()">
      </div>

      <div class="card-title" style="margin-top: 20px;">Automated Sorting Routines</div>
      <div class="btn-grid">
        <button class="btn btn-red" onclick="triggerAction('sort_red')">🔴 Sort Red</button>
        <button class="btn btn-green" onclick="triggerAction('sort_green')">🟢 Sort Green</button>
        <button class="btn btn-blue" onclick="triggerAction('sort_blue')">🔵 Sort Blue</button>
        <button class="btn" onclick="triggerAction('pick')">📦 Pick Sponge</button>
        <button class="btn btn-home" onclick="triggerAction('home')">🏠 Return HOME</button>
      </div>
    </div>

    <div class="card" style="margin-top: 20px;">
      <div class="card-title">Activity Log</div>
      <div class="console" id="logBox">
        <div>[System] Connected to ESP32 Mock Server on port 5000</div>
        <div>[System] Calibrated angles active</div>
      </div>
    </div>
  </div>
</div>

<script>
let state = { waist: 90, shoulder: 90, elbow: 90, gripper: 120 };
const canvas = document.getElementById("armCanvas");
const ctx = canvas.getContext("2d");

function resize() {
  canvas.width = canvas.parentElement.clientWidth;
  canvas.height = canvas.parentElement.clientHeight;
  draw();
}
window.addEventListener("resize", resize);

function log(msg) {
  const box = document.getElementById("logBox");
  const el = document.createElement("div");
  el.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
  box.appendChild(el);
  box.scrollTop = box.scrollHeight;
}

function sendPose() {
  const w = parseInt(document.getElementById("waist").value);
  const s = parseInt(document.getElementById("shoulder").value);
  const e = parseInt(document.getElementById("elbow").value);
  const g = parseInt(document.getElementById("gripper").value);

  document.getElementById("waistVal").textContent = w + "°";
  document.getElementById("shoulderVal").textContent = s + "°";
  document.getElementById("elbowVal").textContent = e + "°";
  document.getElementById("gripperVal").textContent = g + "° " + (g > 140 ? "(Closed)" : "(Open)");

  state = { waist: w, shoulder: s, elbow: e, gripper: g };
  draw();

  fetch("/api/pose", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(state)
  });
}

function triggerAction(action) {
  log("Triggering: " + action.toUpperCase());
  fetch("/api/action", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action: action })
  });
}

// Poll state periodically so external python/ROS commands reflect in the UI!
setInterval(async () => {
  try {
    const res = await fetch("/api/state");
    const data = await res.json();
    if (data.waist !== undefined) {
      if (data.waist !== state.waist || data.shoulder !== state.shoulder || data.elbow !== state.elbow || data.gripper !== state.gripper) {
        state = data;
        document.getElementById("waist").value = state.waist;
        document.getElementById("shoulder").value = state.shoulder;
        document.getElementById("elbow").value = state.elbow;
        document.getElementById("gripper").value = state.gripper;
        document.getElementById("waistVal").textContent = state.waist + "°";
        document.getElementById("shoulderVal").textContent = state.shoulder + "°";
        document.getElementById("elbowVal").textContent = state.elbow + "°";
        document.getElementById("gripperVal").textContent = state.gripper + "° " + (state.gripper > 140 ? "(Closed)" : "(Open)");
        draw();
      }
    }
  } catch(e) {}
}, 200);

function draw() {
  const W = canvas.width;
  const H = canvas.height;
  ctx.clearRect(0, 0, W, H);

  // Divide canvas: Left half = Top View (X-Y), Right half = Side View (R-Z)
  const halfW = W / 2;

  // Background divider
  ctx.strokeStyle = "#334155";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(halfW, 0); ctx.lineTo(halfW, H);
  ctx.stroke();

  // Titles
  ctx.fillStyle = "#94a3b8";
  ctx.font = "bold 12px sans-serif";
  ctx.fillText("TOP-DOWN VIEW (X-Y SWEEP)", 20, 25);
  ctx.fillText("SIDE ELEVATION (R-Z HEIGHT)", halfW + 20, 25);

  // Arm Kinematics Calculation
  const wRad = (state.waist * Math.PI) / 180;
  const sRad = (state.shoulder * Math.PI) / 180;
  const eRad = ((state.elbow - 90) * Math.PI) / 180;

  const L0 = 55, L1 = 80, L2 = 80, L3 = 50;

  // Joint 1: Shoulder
  const r1 = L1 * Math.sin(sRad);
  const z1 = L0 + L1 * Math.cos(sRad);
  const x1 = r1 * Math.cos(wRad);
  const y1 = r1 * Math.sin(wRad);

  // Joint 2: Elbow
  const totPitch = sRad + eRad;
  const r2 = r1 + L2 * Math.sin(totPitch);
  const z2 = z1 - L2 * Math.cos(totPitch);
  const x2 = r2 * Math.cos(wRad);
  const y2 = r2 * Math.sin(wRad);

  // Joint 3: End Effector Claw
  const r3 = r2 + L3 * Math.sin(totPitch);
  const z3 = z2 - L3 * Math.cos(totPitch);
  const x3 = r3 * Math.cos(wRad);
  const y3 = r3 * Math.sin(wRad);

  // ================= 1. DRAW TOP VIEW =================
  const topCx = halfW / 2;
  const topCy = H * 0.75;
  const topScale = 1.1;

  // Target Zones on Top View
  function drawTarget(tx, ty, color, label) {
    const px = topCx + tx * topScale;
    const py = topCy - ty * topScale;
    ctx.strokeStyle = color;
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.arc(px, py, 18, 0, Math.PI * 2);
    ctx.stroke();
    ctx.fillStyle = color;
    ctx.font = "10px sans-serif";
    ctx.fillText(label, px - 12, py + 30);
  }

  drawTarget(-40, 130, "#3b82f6", "Blue");
  drawTarget(10, 140, "#ef4444", "Red");
  drawTarget(60, 130, "#22c55e", "Green");

  // Pick stack
  const pickPx = topCx - 90 * topScale;
  const pickPy = topCy - 80 * topScale;
  ctx.fillStyle = "#f97316";
  ctx.fillRect(pickPx - 14, pickPy - 14, 28, 28);
  ctx.fillStyle = "#ffffff";
  ctx.font = "10px sans-serif";
  ctx.fillText("Pick", pickPx - 10, pickPy + 4);

  // Arm Links Top View
  ctx.strokeStyle = "#e2e8f0";
  ctx.lineWidth = 6;
  ctx.lineCap = "round";
  ctx.beginPath();
  ctx.moveTo(topCx, topCy);
  ctx.lineTo(topCx + x1 * topScale, topCy - y1 * topScale);
  ctx.lineTo(topCx + x2 * topScale, topCy - y2 * topScale);
  ctx.lineTo(topCx + x3 * topScale, topCy - y3 * topScale);
  ctx.stroke();

  // Base pivot
  ctx.fillStyle = "#0284c7";
  ctx.beginPath(); ctx.arc(topCx, topCy, 8, 0, Math.PI * 2); ctx.fill();

  // Claw
  ctx.fillStyle = state.gripper > 140 ? "#ef4444" : "#22c55e";
  ctx.beginPath(); ctx.arc(topCx + x3 * topScale, topCy - y3 * topScale, 7, 0, Math.PI * 2); ctx.fill();

  // ================= 2. DRAW SIDE VIEW =================
  const sideCx = halfW + 60;
  const sideCy = H * 0.85;
  const sideScale = 1.1;

  // Table Surface line
  ctx.strokeStyle = "#475569";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(halfW + 20, sideCy); ctx.lineTo(W - 20, sideCy);
  ctx.stroke();
  ctx.fillStyle = "#64748b";
  ctx.font = "10px sans-serif";
  ctx.fillText("Table Surface (Z=0)", W - 130, sideCy + 15);

  // Arm links side view (Base, Shoulder, Elbow, Claw)
  ctx.strokeStyle = "#f59e0b";
  ctx.lineWidth = 6;
  ctx.lineCap = "round";
  ctx.beginPath();
  ctx.moveTo(sideCx, sideCy);
  ctx.lineTo(sideCx, sideCy - L0 * sideScale);
  ctx.lineTo(sideCx + r1 * sideScale, sideCy - z1 * sideScale);
  ctx.lineTo(sideCx + r2 * sideScale, sideCy - z2 * sideScale);
  ctx.lineTo(sideCx + r3 * sideScale, sideCy - z3 * sideScale);
  ctx.stroke();

  // Shoulder, Elbow joints
  ctx.fillStyle = "#0284c7";
  ctx.beginPath(); ctx.arc(sideCx, sideCy - L0 * sideScale, 6, 0, Math.PI * 2); ctx.fill();
  ctx.beginPath(); ctx.arc(sideCx + r1 * sideScale, sideCy - z1 * sideScale, 6, 0, Math.PI * 2); ctx.fill();
  ctx.beginPath(); ctx.arc(sideCx + r2 * sideScale, sideCy - z2 * sideScale, 6, 0, Math.PI * 2); ctx.fill();

  // Claw Side
  ctx.fillStyle = state.gripper > 140 ? "#ef4444" : "#22c55e";
  ctx.beginPath(); ctx.arc(sideCx + r3 * sideScale, sideCy - z3 * sideScale, 8, 0, Math.PI * 2); ctx.fill();
}

setTimeout(resize, 100);
</script>
</body>
</html>
"""

class DualServer:
    def __init__(self, host="0.0.0.0", port=5000):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False
        
        self.angles = {
            "waist": 90,
            "shoulder": 90,
            "elbow": 90,
            "gripper": 120
        }
        self.image_path = "/home/appu/intership/stress_math_lo/detection_test.jpg"

    def valid_angle(self, angle):
        return 0 <= angle <= 180

    def move_smooth(self, target_w, target_s, target_e, target_g, steps=12, delay=0.03):
        start_w, start_s, start_e, start_g = self.angles["waist"], self.angles["shoulder"], self.angles["elbow"], self.angles["gripper"]
        for i in range(1, steps + 1):
            a = i / float(steps)
            self.angles["waist"] = int(start_w + (target_w - start_w) * a)
            self.angles["shoulder"] = int(start_s + (target_s - start_s) * a)
            self.angles["elbow"] = int(start_e + (target_e - start_e) * a)
            self.angles["gripper"] = int(start_g + (target_g - start_g) * a)
            time.sleep(delay)

    def run_action(self, action_name):
        def worker():
            if action_name == "home":
                self.move_smooth(90, 90, 90, 120)
            elif action_name == "pick":
                # Pre-approach -> lower -> grip -> lift
                self.move_smooth(108, 150, 125, 120)
                time.sleep(0.3)
                self.move_smooth(108, 120, 110, 120)
                time.sleep(0.3)
                self.move_smooth(108, 120, 110, 165) # Grip
                time.sleep(0.3)
                self.move_smooth(108, 155, 125, 165) # Lift
            elif action_name == "sort_red":
                # Pick -> Rotate to Red (52°) -> Drop -> Home
                self.run_action("pick")
                time.sleep(0.4)
                self.move_smooth(52, 145, 120, 165)
                time.sleep(0.3)
                self.move_smooth(52, 125, 105, 165)
                time.sleep(0.3)
                self.move_smooth(52, 125, 105, 120) # Drop
                time.sleep(0.3)
                self.move_smooth(52, 145, 120, 120)
                self.move_smooth(90, 90, 90, 120)
            elif action_name == "sort_green":
                self.run_action("pick")
                time.sleep(0.4)
                self.move_smooth(30, 145, 120, 165)
                time.sleep(0.3)
                self.move_smooth(30, 125, 105, 165)
                time.sleep(0.3)
                self.move_smooth(30, 125, 105, 120)
                time.sleep(0.3)
                self.move_smooth(30, 145, 120, 120)
                self.move_smooth(90, 90, 90, 120)
            elif action_name == "sort_blue":
                self.run_action("pick")
                time.sleep(0.4)
                self.move_smooth(70, 145, 120, 165)
                time.sleep(0.3)
                self.move_smooth(70, 125, 105, 165)
                time.sleep(0.3)
                self.move_smooth(70, 125, 105, 120)
                time.sleep(0.3)
                self.move_smooth(70, 145, 120, 120)
                self.move_smooth(90, 90, 90, 120)
        threading.Thread(target=worker, daemon=True).start()

    def handle_http(self, client_sock, initial_data):
        req_lines = initial_data.decode("utf-8", errors="ignore").split("\r\n")
        first_line = req_lines[0]
        method, path, _ = first_line.split(" ")

        if method == "GET" and path == "/":
            body = WEB_HTML.encode("utf-8")
            header = f"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n".encode("utf-8")
            client_sock.sendall(header + body)
        elif method == "GET" and path == "/camera.jpg":
            if os.path.exists(self.image_path):
                with open(self.image_path, "rb") as f:
                    body = f.read()
                header = f"HTTP/1.1 200 OK\r\nContent-Type: image/jpeg\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n".encode("utf-8")
                client_sock.sendall(header + body)
            else:
                client_sock.sendall(b"HTTP/1.1 404 Not Found\r\n\r\n")
        elif method == "GET" and path == "/api/state":
            body = json.dumps(self.angles).encode("utf-8")
            header = f"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n".encode("utf-8")
            client_sock.sendall(header + body)
        elif method == "POST" and path == "/api/pose":
            body_start = initial_data.find(b"\r\n\r\n") + 4
            content = initial_data[body_start:].decode("utf-8", errors="ignore")
            try:
                data = json.loads(content)
                self.angles["waist"] = data.get("waist", self.angles["waist"])
                self.angles["shoulder"] = data.get("shoulder", self.angles["shoulder"])
                self.angles["elbow"] = data.get("elbow", self.angles["elbow"])
                self.angles["gripper"] = data.get("gripper", self.angles["gripper"])
            except:
                pass
            client_sock.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{\"status\":\"ok\"}")
        elif method == "POST" and path == "/api/action":
            body_start = initial_data.find(b"\r\n\r\n") + 4
            content = initial_data[body_start:].decode("utf-8", errors="ignore")
            try:
                data = json.loads(content)
                self.run_action(data.get("action"))
            except:
                pass
            client_sock.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{\"status\":\"ok\"}")
        else:
            client_sock.sendall(b"HTTP/1.1 404 Not Found\r\n\r\n")
        client_sock.close()

    def handle_tcp(self, client_sock, initial_data):
        client_sock.sendall(b"CONNECTED: ESP32 robot arm ready\n")
        buffer = initial_data.decode("utf-8", errors="ignore")

        while self.running:
            try:
                if "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if line:
                        reply = self.process_command(line)
                        if reply:
                            client_sock.sendall((reply + "\n").encode("utf-8"))
                else:
                    data = client_sock.recv(1024)
                    if not data:
                        break
                    buffer += data.decode("utf-8", errors="ignore")
            except Exception:
                break
        client_sock.close()

    def process_command(self, cmd):
        cmd = cmd.strip()
        if cmd.startswith("POSE:"):
            try:
                w, s, e, g = map(int, cmd[5:].split(","))
                self.angles["waist"] = w
                self.angles["shoulder"] = s
                self.angles["elbow"] = e
                self.angles["gripper"] = g
                return "OK: POSE_COMMAND_ACCEPTED"
            except:
                return "ERROR: Invalid angles"
        elif cmd.startswith("WAIST:"):
            self.angles["waist"] = int(cmd[6:])
            return "OK: WAIST"
        elif cmd.startswith("SHOULDER:"):
            self.angles["shoulder"] = int(cmd[9:])
            return "OK: SHOULDER"
        elif cmd.startswith("ELBOW:"):
            self.angles["elbow"] = int(cmd[6:])
            return "OK: ELBOW"
        elif cmd.startswith("GRIPPER:"):
            self.angles["gripper"] = int(cmd[8:])
            return "OK: GRIPPER"
        elif cmd == "HOME":
            self.angles = {"waist": 90, "shoulder": 90, "elbow": 90, "gripper": 120}
            return "OK: HOME"
        return "ERROR: Unknown command"

    def handle_connection(self, client_sock, addr):
        client_sock.settimeout(0.15)
        initial_data = b""
        try:
            initial_data = client_sock.recv(1024)
        except (socket.timeout, BlockingIOError):
            pass
        except Exception:
            client_sock.close()
            return

        client_sock.settimeout(None)

        if initial_data and (initial_data.startswith(b"GET ") or initial_data.startswith(b"POST ") or initial_data.startswith(b"HEAD ")):
            self.handle_http(client_sock, initial_data)
        else:
            self.handle_tcp(client_sock, initial_data)

    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.running = True

        print(f"\n[+] Dual-Protocol Server LIVE on http://localhost:{self.port} (Web Browser) & TCP Port {self.port} (Sockets)!")
        
        try:
            while self.running:
                client_sock, addr = self.server_socket.accept()
                threading.Thread(target=self.handle_connection, args=(client_sock, addr), daemon=True).start()
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()

if __name__ == "__main__":
    server = DualServer(host="0.0.0.0", port=5000)
    server.start()
