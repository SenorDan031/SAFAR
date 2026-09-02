@echo off
title SAFAR Autonomous Vehicle Simulation Game
cd /d "%~dp0"

echo ======================================================================
echo       SAFAR AUTONOMOUS ROAD-SAFETY SIMULATION GAME
echo ======================================================================
echo Starting SAFAR ADAS and connecting to Unreal Engine 5...
echo.

python -m tools.run_safar_game

pause
