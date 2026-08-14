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
