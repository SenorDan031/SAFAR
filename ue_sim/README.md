# SAFAR Unreal Engine 5 Simulator & Cockpit

This directory contains the entire simulation environment for SAFAR:
1. **`ue5_adapter/`**: Native Unreal Engine 5 C++ Chaos Vehicle integration components:
   - `SAFARVehicleComponent`: Coordinates perception, threat assessment, decision, and Chaos vehicle braking/throttle.
   - `GroundTruthPerceptionProvider`: Gathers dynamic vehicle states and forward raycast obstacles.
   - `UEPotholeScanner`: Ground line-tracing module scanning road surface depth depressions and craters.
   - `SAFARThreatEngine`: Stopping distance kinematics and Time-To-Collision calculation.
   - `SAFARDecisionEngine`: State machine (PASSIVE -> ASSESSING -> INTERVENTION) with hysteresis hold timers.
   - `SAFARHUDWidget`: In-game driver warning overlay.
   - `SAFARBridgeComponent`: UDP/IPC telemetry bridge.
2. **`live_runner/`**: Python bridge running live telemetry loops with Unreal Engine 5.
3. **`pygame_cockpit/`**: Interactive 2D Pygame HUD evaluation cockpit.
4. **`launchers/`**: 1-click launch scripts for running the simulator.
