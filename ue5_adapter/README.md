# SAFAR Unreal Engine 5 Simulation Integration Guide

This guide describes how to connect **Unreal Engine 5 (UE5)** with the SAFAR AI Perception & Decision Pipeline.

---

## 1. Architecture Overview

```
[UE5 Chaos Vehicle]
       │
       ├─► SceneCaptureComponent2D (Virtual Camera) ──► TCP Socket (Port 9001) ──► Python Perception
       │
       └─◄ Set Throttle / Set Brake (Actuator Override) ◄── UDP Socket (Port 9003) ◄── C++ SAFAR Core
```

---

## 2. UE5 Scene Setup

### A. Add a Chaos Vehicle
1. Create a new UE5 Project using the **Vehicle Template** (or open an existing Automotive scene).
2. Ensure the vehicle uses the **Chaos Vehicle Movement Component**.

### B. Add a Virtual RGB Camera
1. Attach a **`SceneCaptureComponent2D`** to the front bumper or windshield of the vehicle.
2. Set `Capture Source` to `SceneColor (HDR) in RGB, Inv Opacity in A` or `Final Color (LDR) in RGB`.
3. Create a **`TextureRenderTarget2D`** (e.g. `RT_FrontCamera`) with resolution `640x480` or `1280x720` and assign it to the Scene Capture component.

### C. Stream Virtual Camera Frames (Port 9001)
Use Unreal Engine's C++ Socket API or a TCP Socket Plugin to send each rendered frame buffer to Python:
- **Header**: Magic `SFRM` (4 bytes) + `Length` (4 bytes uint32).
- **Metadata**: JSON containing `timestamp_us`, `frame_id`, `ego_speed_mps`.
- **Payload**: Compressed JPEG or raw RGB image bytes.

### D. Receive Control Commands (Port 9003)
1. Open a UDP Socket listener on port `9003`.
2. Parse incoming `ControlCommand` JSON.
3. Apply values to the vehicle:
   - **`Set Throttle Input`** (`control.throttle`)
   - **`Set Brake Input`** (`control.brake`)
   - **`Set Handbrake Input`** (`control.emergency_stop`)
4. Draw the **`hud_message`** on the vehicle HUD (e.g. `SAFAR: VEHICLE DETECTED | THREAT: 0.72 | ACTION: WARN`).

---

## 3. Standalone Verification (Without Opening UE5)

You can verify the complete pipeline headlessly anytime using the provided mock tools:

```bash
# Terminal 1: Start C++ SAFAR Core
./safar_core/build/Release/safar_core.exe

# Terminal 2: Start Python Perception Node
python -m safar_perception.perception_node

# Terminal 3: Start UE5 HUD Receiver
python -m ue5_adapter.ue5_receiver

# Terminal 4: Stream simulated frames
python -m ue5_adapter.mock_ue5_streamer --frames 50
```
