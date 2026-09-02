# SAFAR Unreal Engine 5 Real-Time Integration & Verification Guide

This document provides the step-by-step verification checklist to test the real **Unreal Engine 5 Chaos Vehicle** integration end-to-end against the existing Python AI perception pipeline and C++ `safar_core` reasoning engine.

---

## 🏗️ 1. Architecture & Protocol Map

The integration connects the real Unreal Engine 5 vehicle via the strict protocol defined in `interfaces/protocols.md`:

```
┌────────────────────────────────────────────────────────┐
│              UNREAL ENGINE 5 SIMULATION                │
│                                                        │
│  [ASAFARVehiclePawn (Chaos Wheeled Vehicle)]           │
│    ├── USceneCaptureComponent2D (Virtual Front Camera) │
│    ├── USAFARSensorComponent (JPEG Encoder + IMU)      │
│    │     │                                             │
│    │     ▼ (TCP Socket Client)                         │
│    ├── USAFARCommunicationComponent                    │
│    │     │                   ▲ (UDP Socket Listener)   │
│    │     │                   │                         │
│    │     │ Port 9001         │ Port 9003               │
│    │     │ SFRM Packets      │ JSON Control Commands   │
│    │     ▼                   │                         │
│    └── USAFARControlComponent ─┘                       │
│          └── Applies Throttle/Brake/Handbrake Override │
│          └── Enforces Passive Driver Principle         │
│          └── Renders On-Screen ADAS HUD (ASAFARHUD)    │
└──────────┼───────────────────▲─────────────────────────┘
           │                   │
           │ Port 9001 (TCP)   │ Port 9003 (UDP)
           ▼                   │
┌─────────────────────────┐    │
│ Python Perception Node  │    │
│ (YOLOv8 + AutoRickshaw) │    │
└──────────┬──────────────┘    │
           │                   │
           │ Port 9002 (TCP)   │
           ▼                   │
┌─────────────────────────┐    │
│ C++ SAFAR Real-Time Core│────┘
│ (Tracking/TTC/Decision) │
└─────────────────────────┘
```

---

## 🔌 2. Wire Protocol Conformance Checklist

| Port | Protocol | Sender $\rightarrow$ Receiver | Payload Format | Status |
|---|---|---|---|---|
| **9001** | **TCP** | `USAFARCommunicationComponent` $\rightarrow$ `safar_perception.perception_node` | **Header (8 bytes)**: `SFRM` (4B) + Big-Endian Payload Length (4B)<br/>**Payload**: Null-terminated JSON metadata (`timestamp_us`, `frame_id`, `ego_speed_mps`, `ego_heading_deg`, `image_format`, `image_bytes_len`) + Raw JPEG bytes | ✅ Conforms |
| **9002** | **TCP** | `safar_perception.perception_node` $\rightarrow$ `safar_core.exe` | Standardized object detections JSON (`timestamp_us`, `frame_id`, `ego_speed_mps`, `detections[...]`) | ✅ Conforms |
| **9003** | **UDP** | `safar_core.exe` $\rightarrow$ `USAFARCommunicationComponent` | Real-time decision & control JSON (`threat_score`, `decision`, `control.throttle/brake/emergency_stop`, `hud_message`, `latency_ms`) | ✅ Conforms |

---

## 🚀 3. End-to-End Live Verification Steps

### Step 1: Start C++ SAFAR Real-Time Reasoning Core
In **Terminal 1**:
```powershell
cd C:\Users\shrey\OneDrive\Desktop\Projects\SAFAR
.\safar_core\build\Release\safar_core.exe
```
*Expected Output:*
```
[SAFAR CORE] [COMMUNICATION] Listening for Perception Stream on TCP Port 9002
[SAFAR C++ CORE] Real-Time Supervisor & UE5 Vehicle Bridge Active on UDP Port 8888.
```

---

### Step 2: Start Python AI Perception Node
In **Terminal 2**:
```powershell
cd C:\Users\shrey\OneDrive\Desktop\Projects\SAFAR
python -m safar_perception.perception_node
```
*Expected Output:*
```
[PERCEPTION] Waiting for virtual camera stream from UE5 on port 9001...
[PERCEPTION] Connected to C++ SAFAR Core on port 9002.
```

---

### Step 3: (Optional) Monitor Control Bridge Telemetry
In **Terminal 3**:
```powershell
cd C:\Users\shrey\OneDrive\Desktop\Projects\SAFAR
python -m ue5_adapter.ue5_receiver
```
*Expected Output:*
```
Listening on UDP port 9003 for C++ SAFAR Core Decisions...
```

---

### Step 4: Launch Unreal Engine 5 Simulation
1. Open the project in Unreal Engine 5 (`TrafficGame.uproject`).
2. Open your driving level.
3. In **World Settings**, set **GameMode Override** to `ASAFARGameModeBase` (or assign `ASAFARVehiclePawn` as Default Pawn).
4. Hit **Play in Editor (PIE)** (`Alt + P`).

---

## 🧪 4. Expected Real-Time In-Game Behavior

1. **Virtual Camera Streaming**:
   * As soon as UE5 starts, `FSAFARTcpStreamerWorker` connects to Python on `127.0.0.1:9001`.
   * Terminal 2 will report: `[PERCEPTION] UE5 simulation connected. Streaming frames...`
2. **On-Screen ADAS HUD**:
   * The top-left corner of the UE5 viewport renders the `ASAFARHUD` telemetry box showing:
     * **Mode**: `PASSIVE DRIVER` (🟢 Green)
     * **Speed**: Real-time vehicle speedometer in km/h
     * **Threat Score**: Gauge bar ($0.00 \to 1.00$)
     * **Core Link**: `ACTIVE (UDP 9003)`
3. **Passive Driver Principle Verification**:
   * Drive the car using `W`, `A`, `S`, `D`.
   * When no obstacle is in the direct driving corridor, the threat score remains $< 0.35$.
   * Player input is 100% authoritative with zero latency or throttle fighting.
4. **Active Autonomous Emergency Braking (AEB) Verification**:
   * Accelerate directly towards an obstacle (another car, pedestrian, or barricade).
   * As distance drops below $d_{\text{stop}}$, `safar_core` escalates threat score $\ge 0.70$ (`decision: "BRAKE"` / `"EMERGENCY_BRAKE"`).
   * `USAFARControlComponent` automatically engages `bOverrideActive = true`:
     * Cuts throttle to `0.0`.
     * Applies full service brake `1.0`.
     * When speed reaches $\le 0.5\text{ m/s}$, locks handbrake (`SetHandbrakeInput(true)`) to prevent reverse roll.
     * HUD flashes `AUTONOMOUS BRAKE OVERRIDE` (🔴 Red).
