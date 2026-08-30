@echo off
title SAFAR SIMULATOR — Master Game Launcher
cd /d "%~dp0"

echo ======================================================================
echo          🚗 SAFAR SIMULATOR — AUTONOMOUS ROAD SAFETY GAME 🚗
echo ======================================================================
echo Starting Unified Simulation Ecosystem...
echo.

:: 1. Launch Unreal Engine 5 in Game Play Mode in the background
echo [1/3] Launching Unreal Engine 5 Simulation Environment...
start "" "C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe" "C:\Users\shrey\OneDrive\Desktop\Projects\SAFAR_Sim\SAFAR_Sim\SAFAR_Sim.uproject" -game -ResX=1280 -ResY=720 -WinX=50 -WinY=50

:: 2. Wait for UE5 to initialize
echo [2/3] Initializing Chaos Vehicle Physics & Sensors (waiting 5 seconds)...
timeout /t 5 /nobreak >nul

:: 3. Launch SAFAR Autonomous Core & Perception
echo [3/3] Booting SAFAR Autonomous Safety Engine...
echo ======================================================================
echo READY! Switch to the game window and drive!
echo ======================================================================

python -m tools.launch_safar_simulator

pause
