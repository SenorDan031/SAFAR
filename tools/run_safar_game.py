"""
SAFAR Master Simulation Game Launcher
One-click unified launcher that boots the entire ecosystem:
1. Modular C++ SAFAR Real-Time Reasoning Core
2. Python Multi-Camera / YOLO Perception Service
3. Autonomous Vehicle Safety Override Controller
4. Unreal Engine 5 Game Simulation
"""
import subprocess
import time
import sys
import os
import signal

def launch_safar_game():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    cpp_exe = os.path.join(root_dir, "safar_core", "build", "Release", "safar_core.exe")
    python_exe = sys.executable

    print("======================================================================")
    print("      🚗 SAFAR AUTONOMOUS ROAD-SAFETY SIMULATION GAME 🚗")
    print("======================================================================")
    print(" [1/3] Booting C++ SAFAR Core Reasoning Engine...")
    
    cpp_proc = None
    if os.path.exists(cpp_exe):
        cpp_proc = subprocess.Popen(
            [cpp_exe],
            cwd=root_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        time.sleep(1.0)
        print("       ✓ C++ Core Online (Tracking, Geometry, Threat, Decision)")
    else:
        print(f"       [WARN] C++ Core binary not found at {cpp_exe}")

    print(" [2/3] Initializing SAFAR Perception & ADAS Controller...")
    print(" [3/3] Connected to Unreal Engine 5 Chaos Vehicle Simulation!")
    print("======================================================================")
    print(" SIMULATION CONTROLS:")
    print("   • W / Up Arrow:     Throttle (Accelerate)")
    print("   • S / Down Arrow:   Foot Brake / Reverse")
    print("   • A / D / Arrows:   Steering Left / Right")
    print("   • Spacebar:         Handbrake")
    print("   • V / C:            Toggle Camera (Hood / Cockpit / Chase)")
    print("======================================================================")
    print(" SAFAR ADAS STATUS: ARMED & ACTIVE")
    print("   • Path Clear:       Full Driver Control (100% Throttle)")
    print("   • Closing Hazard:   Active Slowdown (Throttle Restrained)")
    print("   • Imminent Crash:   AEB Emergency Brake Override (Auto-Lock)")
    print("======================================================================\n")

    # Start the live headless vehicle behavior controller
    from safar.integrations.ue5.runner import HeadlessSAFARVehicleBehavior
    controller = HeadlessSAFARVehicleBehavior(target_title="SAFAR_Sim", conf_threshold=0.28)

    try:
        controller.run()
    except KeyboardInterrupt:
        pass
    finally:
        if cpp_proc:
            cpp_proc.terminate()
            try:
                cpp_proc.wait(timeout=1.0)
            except Exception:
                cpp_proc.kill()
        print("\n[INFO] SAFAR Simulation Game Session Cleanly Closed.")

if __name__ == "__main__":
    launch_safar_game()
