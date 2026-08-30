## Day 5 - Physics-Aware Pothole Intelligence & UE5 Closed-Loop Safety Integration

**Date of Log:** [30/08/2026]  
**Log Author:** [Yazdaan Ansari](https://github.com/SenorDan031)  
---

### 1. Robust Physics-Aware Pothole Safety System
- **Decoupled Architecture**: Refactored the pothole system into modular layers: `validation`, `model`, `classifier`, `physics`, `path`, `risk`, `decision`, `simulation`.
- **Data Validation Layer**: Added strict physical boundary checking to sanitize input dimensions, rejecting NaNs, infinite values, and negative dimensions without causing false interventions.
- **ML Model Benchmarking**: Evaluated Decision Trees, Random Forest, Extra Trees, and Gradient Boosting on `pothole_dataset.csv` using stratified 5-fold cross-validation.
- **Production Classifier**: Selected Gradient Boosting achieving **99.0% test accuracy**, **99.4% 5-fold CV**, and **100% recall on severe craters** with calibrated confidence estimation.
- **Kinematic Physics Engine**: Implemented dynamic stopping distance $d_{\text{stop}} = v \cdot t_{\text{react}} + \frac{v^2}{2a}$, required buffer margins, and time-to-pothole ($t = \frac{d}{v}$).
- **Driving Corridor Geometry**: Built lateral envelope tracking ($|Y| \le 1.05\text{m}$) ensuring potholes outside the vehicle's driving path never trigger braking.
- **State Machine with Hysteresis**: Added `MAINTAIN` $\to$ `MONITOR` $\to$ `SLOW` $\to$ `BRAKE` $\to$ `EMERGENCY_BRAKE` with temporal confirmation ($\ge 2$ frames) and anti-jitter hold timers.
- **Verification**: Validated 100% pass rate across the 12-scenario deterministic benchmark suite and built interactive standalone CLI (`safar.pothole.main`).

### 2. Unreal Engine 5 Closed-Loop Vehicle Safety Integration
- **Passive Driver Principle**: Configured SAFAR to silently observe during normal driving, leaving 100% authoritative control to the player until an imminent physical hazard is confirmed.
- **Chaos Vehicle Reverse Gear Fix**: Implemented speed-gated service braking ($Speed > 0.5\text{ m/s}$) and stationary handbrake locking ($Speed \le 0.5\text{ m/s}$) to prevent Chaos automatic transmission from shifting into reverse.
- **Traffic Isolation & Self-Exclusion**: Filtered ego vehicle out of ground-truth perception queries and isolated SAFAR actuation strictly to player-controlled pawns, ensuring ambient AI traffic runs without interference.

---

## END OF Dlog
---

## Day 4 - Advanced Detection system and Enhanced Logic Engine

**Date of Log:** [14/08/2026]  
**Log Author:** [Yazdaan Ansari](https://github.com/SenorDan031)  
---

- Refined [Krish Agarwal](https://github.com/Krishagarwal558) previous day documentations.
- Added documentation in code files to make the work more descriptive and detailed.
- Refined Repository structure.
- Resolved some merge conflicts, restored certain files and pushed a back up folder as well.


## END OF Dlog
---

## Day 3 - Advanced Detection system and Enhanced Logic Engine

**Date of Log:** [13/08/2026]  
**Log Author:** [Krish Agarwal](https://github.com/Krishagarwal558)  
---
- **Trajectory relevance**: predicts whether a vehicle, pedestrian, or two-wheeler will intersect the ego’s future path. 
- **Path-aware prioritization**: a crossing pedestrian can be selected before entering the current lane corridor.                   
- **Structured event record**: stores bounded in-memory events with hazard type, distance, ego speed, risk, and trajectory conflict.  
- Added persistent vehicle encounter logging [encounter_log.py] 
- Fixed issues: Detects close side vehicles even when they are outside the predicted lane corridor, Triggers the existing risk/override flow before a side collision, Ignores vehicles behind the ego, so rear
  traffic does not cause braking.
-The full_validation scene now also spawns 8 distant mixed background entities—vehicles, pedestrians, two-wheelers, and hazards—for more realistic perception context.


## END OF Dlog
---
  

## Day 2 - Enhanced detection and module scripts

**Date of Log:** [12/08/2026]  
**Log Author:** [Krish Agarwal](https://github.com/Krishagarwal558) 
---

- Added detecting system for pedestrians and static objects.
- Added virtual car control system for simulation (pygames and CARLA)


**[Yazdaan Ansari's](https://github.com/SenorDan031)** Dlogs

- Renamed folder 'safar' to 'Logic_Engine' to avoid name conflicts.
- Revamped some import modules to make them compatible for  project.
- Added a new member in the team, [Saksham Dixit](https://github.com/sakshamd19).

## END OF Dlog
---


# Day 1 - Project Establishment Record

**Date of Log:** [11/08/2026]  
**Log Author:** [Yazdaan](https://github.com/SenorDan031) 
**Repository Created:** [11/08/2026]

---

## Project Establishment Acknowledgement

The **SAFAR** project was officially established with the creation of its central GitHub repository, **SAFAR** is an **Assisted Automated Driving System** that is help enhance driver's experience.

**[Krish Agarwal's](https://github.com/Krishagarwal558)** DLogs

- Made the prototype folder structure and pushed the files in repo.

- Developed the hazard detection scripts with time to collision logic

- Tested them via scenarios on CARLA **SAFAR\Logic_Engine\run_carla_safar.py**

- Essential commands to check :

    - **Go to SAFAR project**;    cd $projectRoot

    -  **Create the Python**; 3.7 environment    py -3.7 -m venv $venvPath

    -  **Activate it**;    & "$venvPath\Scripts\Activate.ps1"

    -  **Install CARLA Python API**;    python -m pip install "$carlaRoot\PythonAPI\carla\dist\carla-0.9.15-cp37-cp37m-win_amd64.whl"

    -  **Install test runner**;    python -m pip install "pytest<8"

    -  **Start CARLA server**;    Start-Process "$carlaRoot\CarlaUE4.exe"
   
    -  **Run SAFAR tests**;    python -m pytest  Logic_Engine\tests -q

    -  **Run live SAFAR scenario**;    python -m Logic_Engine.run_carla_safar

    -  **Run one selected scenario**;    python -m Logic_Engine.run_carla_safar --scenario emergency_stop

      
**[Yazdaan Ansari's](https://github.com/SenorDan031)** Dlogs

- Structured Krish Agarwal's dlog, aligning it with Dlog rules.
- Made few changes regarding team members for this project :
  - Removed Japnoor Kaur.
  - Removed Kashish Kushwaha.
    
## END OF Dlog
---

## Our Fellow Team Members

- [Yazdaan Ansari](https://github.com/SenorDan031)
- [Krish Agarwal](https://github.com/Krishagarwal558)
- [Saksham Dixit](https://github.com/sakshamd19)
