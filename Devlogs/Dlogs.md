# Day 1 - Project Establishment Record

**Date of Log:** [11/08/2026]  
**Log Author:** [Yazdaan](https://github.com/SenorDan031) 
**Repository Created:** [11/08/2026]

---

## Project Establishment Acknowledgement

The **SAFAR** project was officially established with the creation of its central GitHub repository, **SAFAR** is an **Assisted Automated Driving System** that is help enhance driver's experience.

## [Krish Agarwal's] (https://github.com/Krishagarwal558) DLog

- Made the prototype folder structure and pushed the files in repo.

- Developed the hazard detection scripts with time to collision logic

- Tested them via scenarios on CARLA **SAFAR\safar\run_carla_safar.py**

- Essential commands to check :

    - **Go to SAFAR project**;    cd $projectRoot

    -  **Create the Python**; 3.7 environment    py -3.7 -m venv $venvPath

    -  **Activate it**;    & "$venvPath\Scripts\Activate.ps1"

    -  **Install CARLA Python API**;    python -m pip install "$carlaRoot\PythonAPI\carla\dist\carla-0.9.15-cp37-cp37m-win_amd64.whl"

    -  **Install test runner**;    python -m pip install "pytest<8"

    -  **Start CARLA server**;    Start-Process "$carlaRoot\CarlaUE4.exe"
   
    -  **Run SAFAR tests**;    python -m pytest safar\tests -q

    -  **Run live SAFAR scenario**;    python -m safar.run_carla_safar

    -  **Run one selected scenario**;    python -m safar.run_carla_safar --scenario emergency_stop

---

## Our Fellow Team Members

- [Yazdaan Ansari](https://github.com/SenorDan031)
- [Krish Agarwal](https://github.com/Krishagarwal558)
- [Japnoor Kaur](https://github.com/kaurjapnoor60-max)
- [Kashish Kushwaha](https://github.com/kash-12)
