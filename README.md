# 🛡️ SAFAR — Safety Assisting Forward-looking AI Reflex

**SAFAR** is an advanced, physics-aware, AI-assisted road safety and collision avoidance subsystem designed for realistic vehicle simulation environments (Unreal Engine 5 Chaos Physics) and next-generation Advanced Driver Assistance Systems (ADAS).

---

## 🌟 Core Operating Philosophy

1. **Passive Driver Principle (Player-Authoritative Control)**:
   * During normal driving, the player has **100% authoritative control** over steering, throttle, and braking.
   * SAFAR silently observes the environment, predicts trajectories, and evaluates stopping limits.
   * SAFAR **only intervenes** when a physical, predicted, multi-frame confirmed safety hazard requires emergency intervention.
2. **Decoupled Perception and Reasoning**:
   * Machine Learning answers **only**: *"What object/surface is this?"*
   * Kinematics and Geometry answer: *"Does it intersect our driving corridor, and can we stop in time?"*
   * Control is never surrendered directly to raw ML probability.
3. **Failure-Safe Guarantee**:
   * $\text{NO\_DATA} \ne \text{DANGER}$.
   * $\text{INVALID\_DATA} \ne \text{EMERGENCY\_BRAKE}$.
   * Disconnected perception sockets, startup warmups, or sensor noise default strictly to `PASSIVE` ($Brake = 0.0$).

---

## 🔄 End-to-End Pipeline Architecture

```
                    WORLD SENSORS / CAMERAS / TELEMETRY
                                     │
                                     ▼
                    ┌─────────────────────────────────┐
                    │      1. PERCEPTION LAYER        │
                    │  Virtual Stereo Pair / YOLO CV  │
                    └────────────────┬────────────────┘
                                     │ Detections (Class, Confidence, Disparity)
                                     ▼
                    ┌─────────────────────────────────┐
                    │      2. KINEMATIC TRACKER       │
                    │   60 Hz Relative Velocity & DR  │
                    └────────────────┬────────────────┘
                                     │ Tracked Objects (V_rel, Distance, Lateral Offset)
                                     ▼
                    ┌─────────────────────────────────┐
                    │    3. TRAJECTORY & CORRIDOR     │
                    │  Ego Envelope (|Y| <= 1.85m)    │
                    │  Time-To-Collision (TTC) Math   │
                    └────────────────┬────────────────┘
                                     │ Trajectory Intersections & TTC
                                     ▼
                    ┌─────────────────────────────────┐
                    │     4. DYNAMIC THREAT ENGINE    │
                    │  Stopping Distance: d = v*t+v²/2a│
                    │  Safety Ratio: R = dist / d_stop│
                    └────────────────┬────────────────┘
                                     │ Threat Level (LOW / MONITOR / HIGH / CRITICAL)
                                     ▼
                    ┌─────────────────────────────────┐
                    │    5. DECISION STATE MACHINE    │
                    │  Temporal Filter (>= 2 frames)  │
                    │  Hysteresis (0.70 on / 0.40 off)│
                    └────────────────┬────────────────┘
                                     │ Vehicle Command (PASSIVE vs INTERVENTION)
                                     ▼
                     CHAOS VEHICLE CLOSED-LOOP ACTUATION
                  (Automatic Transmission Reverse Protection)
```

---

## 🏆 What SAFAR Has Achieved

### 1. Unreal Engine 5 Closed-Loop Safety Integration
* **Substrate**: Native integration with `UETrafficGame` running on Unreal Engine 5 with Chaos Wheeled Vehicle Movement.
* **Stereo Depth Rig**: Calibrated virtual stereo baseline ($B = 0.25\text{m}, f = 650\text{px}, \text{FOV} = 78^\circ$) calculating metric depth $Z = \frac{f \cdot B}{d_{\text{disp}}}$ with Gaussian disparity noise injection.
* **Chaos Automatic Transmission Reverse Protection**: Speed-gated service braking ($Speed > 0.5\text{ m/s}$) combined with stationary handbrake hold ($Speed \le 0.5\text{ m/s}$), preventing automatic transmissions from reversing at zero speed.
* **Fleet Isolation**: Ego-vehicle self-detection filter and player-pawn execution gate (`IsPlayerControlled()`), ensuring 50+ ambient AI traffic vehicles navigate freely without false braking.
* **10/10 Deterministic Vehicle Scenarios Passed**: Verified under vehicle cut-ins, sudden braking, adjacent lane bypasses, separating traffic, static walls, and sensor failure modes.

### 2. Physics-Aware Pothole Intelligence (`safar/pothole/`)
* **Data Sanitization Layer**: Validates input measurements, rejecting negative dimensions, `NaN`, `Inf`, and unrealistic outliers without false emergency triggers.
* **High-Accuracy Production Classifier**: Gradient Boosting model trained on `pothole_dataset.csv` achieving:
  * **99.00% Test Accuracy**
  * **99.40% ± 0.80% 5-Fold Stratified Cross-Validation Accuracy**
  * **100% Precision & 100% Recall on Severe Craters**
* **Kinematic Stopping Distance**: Physics-backed required stopping envelope $d_{\text{stop}} = v \cdot t_{\text{react}} + \frac{v^2}{2a}$ with reaction latency ($t_{\text{react}} = 0.18\text{s}$).
* **Corridor Geometry**: Rejects potholes outside the vehicle's wheel envelope ($|Y| > 1.05\text{m}$).
* **12/12 Deterministic Pothole Scenarios Passed**: Verified under empty roads, far-away hazards, close craters, high-speed approach, invalid data, stationary states, and multi-pothole scenarios.

---

## 📁 Repository Structure

```
SAFAR/
├── data/
│   └── pothole_dataset.csv         # 499-sample road surface benchmark dataset
├── safar/
│   ├── pothole/                    # Decoupled Python Pothole Intelligence
│   │   ├── config.py               # Constants, thresholds, and safe speed maps
│   │   ├── validation.py           # Physical dimension sanity & range checking
│   │   ├── model.py                # Stratified ML benchmarking and serialization
│   │   ├── classifier.py           # Calibrated probability inference & uncertainty gate
│   │   ├── physics.py              # Stopping distance & time-to-pothole kinematics
│   │   ├── path.py                 # Ego corridor geometry overlap evaluation
│   │   ├── risk.py                 # Continuous transparent risk scoring [0.0, 1.0]
│   │   ├── decision.py             # State machine with temporal stability & hysteresis
│   │   ├── simulation.py           # Multi-hazard prioritizer & pipeline orchestrator
│   │   ├── test_scenarios.py       # 12-scenario deterministic verification benchmark
│   │   ├── train_model.py          # Model training CLI
│   │   └── main.py                 # Interactive standalone CLI analyzer
│   ├── perception/                 # Computer vision, continuous predictors, stereo depth
│   ├── integrations/               # UE5 and CARLA network bridges
│   └── core/                       # Core Python coordination types
├── safar_core/                     # C++ Cross-Platform Safety Core & Unit Tests
├── tools/                          # Latency profilers, test harnesses, and scenario runners
├── Devlogs/                        # Project development logs and history
└── README.md                       # Master documentation
```

---

## 🚀 Quickstart & Usage

### 1. Run Pothole Safety Intelligence Tests (12 Scenarios)
```powershell
python -m safar.pothole.test_scenarios
```

### 2. Train and Serialize Pothole Model
```powershell
python -m safar.pothole.train_model
```

### 3. Interactive CLI Analysis Tool
```powershell
# Syntax: python -m safar.pothole.main <speed_mps> <distance_m> <width_m> <length_m> <depth_m> [lateral_m]
python -m safar.pothole.main 20.0 35.0 0.70 1.40 0.06 0.0
```

### 4. Run Unreal Engine 5 Vehicle Simulation
1. Open `TrafficGame.uproject` in Unreal Engine 5.
2. Load map `Maps/Levels/City/DaytimeCity.umap`.
3. Press **`Play (▶)`** and drive with **`W` / `A` / `S` / `D`**. SAFAR will silently monitor and intervene only during imminent collisions.

---

## 🔮 Future Roadmap: What SAFAR Is Expected to Do

```
  ┌────────────────────────┐      ┌────────────────────────┐      ┌────────────────────────┐
  │        PHASE 1         │      │        PHASE 2         │      │        PHASE 3         │
  │ Real-Time Vision & CV  │ ──►  │ Active Evasive Steering│ ──►  │ Indian Road Conditions │
  │ YOLOv8 + Disparity Strm│      │ Lateral Maneuvering    │      │ Cattle, Auto-Rickshaws │
  └────────────────────────┘      └────────────────────────┘      └────────────────────────┘
                                                                               │
                                                                               ▼
  ┌────────────────────────┐      ┌────────────────────────┐      ┌────────────────────────┐
  │        PHASE 6         │      │        PHASE 5         │      │        PHASE 4         │
  │ Physical Testbed       │ ◄──  │ Automotive Embedded    │ ◄──  │ Multi-Sensor Fusion    │
  │ Drive-by-Wire Car Test │      │ Jetson Orin + CAN Bus  │      │ Camera + LiDAR + Radar │
  └────────────────────────┘      └────────────────────────┘      └────────────────────────┘
```

### 🔹 Phase 1: Real-Time Onboard Computer Vision Pipeline
* Direct render target frame capture from Unreal Engine 5 virtual stereo cameras into PyTorch.
* Real-time YOLOv8 object detection paired with Semi-Global Block Matching (SGBM) stereo disparity maps streaming at 60 FPS.

### 🔹 Phase 2: Active Evasive Steering Assistance (AES)
* When $d_{\text{stop}} > d_{\text{forward}}$ and braking alone cannot prevent impact, compute safe adjacent lane escape corridors.
* Apply smooth, torque-limited steering intervention if adjacent lanes are verified clear of traffic.

### 🔹 Phase 3: Indian Road & Complex Traffic Specializations
* Specialized models trained for unstructured traffic: auto-rickshaws, motorcycles filtering between lanes, stray animals/cattle, unmarked speed breakers, and construction blockades.

### 🔹 Phase 4: Multi-Sensor Extended Kalman Filter Fusion
* Fuse virtual stereo cameras with solid-state LiDAR point clouds and millimeter-wave (mmWave) radar vectors for all-weather robustness (dense fog, torrential rain, direct glare).

### 🔹 Phase 5: Automotive Embedded Hardware Deployment
* Port the C++ core (`safar_core`) and TensorRT models to automotive-grade hardware (**NVIDIA Jetson AGX Orin** and **NXP S32G Automotive Processors**).
* Integration with standard automotive protocols: **CAN Bus (J1939 / CAN-FD)**, **AUTOSAR Adaptive Platform**, and **ROS 2 Humble**.

---

## 👥 Team Members

* **[Yazdaan Ansari](https://github.com/SenorDan031)** — *Project Lead & System Architect*
* **[Krish Agarwal](https://github.com/Krishagarwal558)** — *Perception & Logic Engine Developer*
* **[Saksham Dixit](https://github.com/sakshamd19)** — *Simulation & Control Systems Engineer*

---

## 📄 License
This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
