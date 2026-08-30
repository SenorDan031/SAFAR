@echo off
title SAFAR SIMULATOR — Autonomous Road Safety Game
cd /d "C:\Users\shrey\OneDrive\Desktop\Projects\SAFAR"

echo ======================================================================
echo          🚗 SAFAR SIMULATOR — AUTONOMOUS ROAD SAFETY GAME 🚗
echo ======================================================================
echo Loading SAFAR ADAS Engine and connecting to Unreal Engine 5...
echo.

python -m tools.launch_safar_simulator

pause
