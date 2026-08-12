# SAFAR

SAFAR is a CARLA-based driving-safety prototype. It evaluates a forward obstacle, calculates collision risk, and applies a driving decision such as warning, slowdown, or emergency braking.

## Current capabilities

- Connects to a live CARLA simulator.
- Spawns an ego vehicle and a lead vehicle.
- Reads vehicle distance and relative speed.
- Classifies risk as `safe`, `medium`, `high`, or `critical`.
- Applies `none`, `warn`, `slowdown`, or `emergency_brake` actions.
- Moves the CARLA spectator camera behind the ego vehicle.
- Cleans up spawned actors when the scenario ends.
- Includes automated tests for the risk and decision engines.

## Current workflow

```text
CARLA vehicles
→ distance and relative-speed measurement
→ RiskEngine
→ RiskAssessment
→ DecisionEngine
→ CARLA throttle and brake control
```

## Our Fellow Team Members

- [Yazdaan Ansari](https://github.com/SenorDan031)
- [Krish Agarwal](https://github.com/Krishagarwal558)
- [Saksham Dixit](https://github.com/sakshamd19)

