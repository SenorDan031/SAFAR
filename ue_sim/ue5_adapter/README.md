# SAFAR Unreal Engine 5 Simulation Integration Guide

This guide describes how the **Unreal Engine 5 (UE5)** Chaos Vehicle simulation connects directly with the SAFAR AI Perception & Decision Pipeline.

---

## 1. Architecture Overview

```
[UE5 Chaos Vehicle]
       │
       ├─► USAFARSensorComponent ──► USAFARCommunicationComponent (TCP Port 9001) ──► Python Perception
       │
       └─◄ USAFARControlComponent ◄── USAFARCommunicationComponent (UDP Port 9003) ◄── C++ SAFAR Core
```

---

## 2. Implemented UE5 C++ Components

All components are located in [`ue5_adapter/components/`](file:///C:/Users/shrey/OneDrive/Desktop/Projects/SAFAR/ue5_adapter/components/):

1. **`USAFARSensorComponent`** (`SAFARSensorComponent.h` / `SAFARSensorComponent.cpp`):
   * Captures raw camera frame buffers from `USceneCaptureComponent2D` (`TextureRenderTarget2D`).
   * Encodes frames as JPEG at decoupled target FPS (default 30–60 FPS) without blocking game rendering.
   * Extracts metric IMU telemetry (`VehicleVelocity`, `VehicleSpeedKmh`, `VehicleAcceleration`, `VehicleHeadingDeg`) from `UChaosWheeledVehicleMovementComponent`.

2. **`USAFARCommunicationComponent`** (`SAFARCommunicationComponent.h` / `SAFARCommunicationComponent.cpp`):
   * **TCP Client on Port 9001**: Uses a dedicated background worker thread (`FSAFARTcpStreamerWorker`) to send `SFRM` framed packets (`Magic` + `Length` + `Metadata JSON` + `JPEG bytes`) to Python Perception.
   * **UDP Receiver on Port 9003**: Uses `FUdpSocketReceiver` to parse JSON safety commands from C++ SAFAR Core and dispatch them to the game thread.

3. **`USAFARControlComponent`** (`SAFARControlComponent.h` / `SAFARControlComponent.cpp`):
   * **Passive Driver Principle**: Evaluates `ThreatScore` against `InterventionThreshold` ($0.70$). Player retains 100% manual control until an imminent collision requires intervention.
   * **Reverse-Protection Anti-Roll**: Applies service braking $> 0.5\text{ m/s}$, and locks the handbrake $\le 0.5\text{ m/s}$ to prevent automatic transmissions from creeping or rolling backward on inclines.

4. **`ASAFARVehiclePawn`** & **`ASAFARHUD`**:
   * Pre-configured Chaos Vehicle pawn with follow camera, windshield virtual camera, and real-time on-screen telemetry overlay.

---

## 3. End-to-End Verification

Follow the step-by-step verification checklist in [`ue5_adapter/VERIFICATION.md`](file:///C:/Users/shrey/OneDrive/Desktop/Projects/SAFAR/ue5_adapter/VERIFICATION.md):

```bash
# Terminal 1: Start C++ SAFAR Core
./safar_core/build/Release/safar_core.exe

# Terminal 2: Start Python AI Perception Node
python -m safar_perception.perception_node

# Terminal 3: (Optional) Monitor Control Bridge
python -m ue5_adapter.ue5_receiver

# Terminal 4: Launch Unreal Engine 5 with ASAFARGameModeBase / ASAFARVehiclePawn
```
