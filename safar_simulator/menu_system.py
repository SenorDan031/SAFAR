"""
SAFAR Simulator — Interactive Main Menu System
Automotive interface for selecting simulation modes, traffic density, and ADAS configurations.
"""
import os
import sys
from typing import Optional, Tuple
from .scenario_engine import ScenarioCatalog, ScenarioDefinition

class MenuSystem:
    @staticmethod
    def print_banner():
        print("""
======================================================================
     ███████╗ █████╗ ███████╗ █████╗ ██████╗ 
     ██╔════╝██╔══██╗██╔════╝██╔══██╗██╔══██╗
     ███████╗███████║█████╗  ███████║██████╔╝
     ╚════██║██╔══██║██╔══╝  ██╔══██║██╔══██╗
     ███████║██║  ██║██║     ██║  ██║██║  ██║
     ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝
          AUTONOMOUS ROAD SAFETY SIMULATOR (UE5)
======================================================================
""")

    @staticmethod
    def show_main_menu(current_density: str, current_mode: str) -> str:
        MenuSystem.print_banner()
        print(f" [1] 🚗  FREE DRIVE (Ambient Traffic | Density: {current_density})")
        print(f" [2] ⚡  RANDOM TEST (Continuous Dynamic Hazard Generation)")
        print(f" [3] 📋  SCENARIO SELECT (10 Curated Road Challenges)")
        print(f" [4] 🧪  DEVELOPER SANDBOX (Interactive Hazard Spawner)")
        print(f" [5] ⚙️   SIMULATION SETTINGS (Traffic Density & Perception Mode: [{current_mode.upper()}])")
        print(f" [6] ❌  EXIT")
        print("======================================================================")
        choice = input(" Select mode [1-6]: ").strip()
        return choice

    @staticmethod
    def show_density_settings(current_density: str, current_mode: str) -> Tuple[str, str]:
        print("\n======================================================================")
        print("                     ⚙️  SIMULATION SETTINGS                          ")
        print("======================================================================")
        print(f" 1. Traffic Density (Current: [{current_density}])")
        print("    [L] LOW (10 Entities - Best Laptop Performance)")
        print("    [M] MEDIUM (30 Entities - Balanced Traffic)")
        print("    [H] HIGH (60+ Entities - Dense Urban Traffic)")
        print(f" 2. Perception Engine (Current: [{current_mode.upper()}])")
        print("    [R] Real AI Mode (Ultralytics YOLO11)")
        print("    [K] Mock Perception Mode (Synthetic Simulated Detections)")
        print("    [B] Back to Main Menu")
        print("======================================================================")
        choice = input(" Select setting to change: ").strip().upper()
        if choice == "L":
            return "LOW", current_mode
        elif choice == "M":
            return "MEDIUM", current_mode
        elif choice == "H":
            return "HIGH", current_mode
        elif choice == "R":
            return current_density, "real"
        elif choice == "K":
            return current_density, "mock"
        return current_density, current_mode
