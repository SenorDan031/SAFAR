# SAFAR Communication & Wire Protocols Specification

## Architecture Overview
The SAFAR simulation pipeline decouples the Unreal Engine 5 simulation environment, the Python AI/Perception Layer, and the C++ Real-Time Reasoning Core via standard, low-overhead network socket protocols:

```
[UE5 Simulation / Virtual Sensors]
         │
         │  PORT 9001: Frame Stream (RGB JPG/RAW + Speed/IMU metadata)
         ▼
[Python Perception Node (YOLO)]
         │
         │  PORT 9002: Standardized Detections (JSON/Binary Packets)
         ▼
[C++ SAFAR Core (Threat + Decision + Control)]
         │
         │  PORT 9003: Decision & Actuator Intervention Commands
         ▼
[UE5 Chaos Vehicle / HUD Receiver]
```

---

## 1. Port 9001: UE5 Sensor Stream $\rightarrow$ Python Perception
Transmits raw camera frames alongside vehicle physical state (velocity, heading, IMU).

### Packet Framing:
- **Header (8 bytes)**: `Magic (4 bytes: "SFRM")` + `Payload Length (4 bytes uint32_t big-endian)`.
- **Payload**:
  - `JSON Metadata String (null-terminated)`:
    ```json
    {
      "timestamp_us": 1787118000123456,
      "frame_id": 1042,
      "ego_speed_mps": 14.5,
      "ego_heading_deg": 0.0,
      "image_format": "jpeg",
      "image_bytes_len": 45120
    }
    ```
  - `Raw Image Bytes`: JPEG or RGB24 raw byte buffer.

---

## 2. Port 9002: Python Perception $\rightarrow$ C++ SAFAR Core
Transmits standardized object detections extracted by YOLO in normalized coordinates $(x, y \in [0.0, 1.0])$.

### JSON Payload Contract:
```json
{
  "timestamp_us": 1787118000123456,
  "frame_id": 1042,
  "ego_speed_mps": 14.5,
  "detections": [
    {
      "track_id": 1,
      "class_name": "car",
      "confidence": 0.94,
      "bbox_normalized": [0.42, 0.35, 0.58, 0.68],
      "center_x": 0.50,
      "bottom_y": 0.68
    }
  ]
}
```

---

## 3. Port 9003: C++ SAFAR Core $\rightarrow$ UE5 Simulation
Transmits evaluated threat scores, high-level safety decisions, and low-level vehicle actuator control commands.

### JSON Payload Contract:
```json
{
  "timestamp_us": 1787118000128910,
  "frame_id": 1042,
  "threat_score": 0.72,
  "decision": "WARN",
  "control": {
    "throttle": 0.50,
    "brake": 0.00,
    "steering": 0.00,
    "emergency_stop": false
  },
  "hud_message": "SAFAR: VEHICLE DETECTED | THREAT: 0.72 | ACTION: WARN",
  "latency_ms": 5.45
}
```
