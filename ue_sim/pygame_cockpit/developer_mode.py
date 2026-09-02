"""
SAFAR Simulator — Developer Mode & Live Sandbox Controller
Allows instant triggering of hazards, weather changes, time changes, and perception modes.
"""
from dataclasses import dataclass
from typing import Optional
from .scenario_engine import HazardEvent, WeatherType, TimeOfDay

@dataclass
class DeveloperSandboxState:
    perception_mode: str = "real"
    weather: WeatherType = WeatherType.CLEAR
    time_of_day: TimeOfDay = TimeOfDay.DAY
    simulation_speed: float = 1.0
    is_paused: bool = False
    forced_brake: bool = False
    active_manual_hazard: Optional[HazardEvent] = None


class DeveloperModeController:
    def __init__(self):
        self.state = DeveloperSandboxState()

    def print_help(self):
        print("""
======================================================================
                  🧪 SAFAR TEST LAB — DEVELOPER CONTROLS               
======================================================================
 [1] Spawn Lead Vehicle Sudden Brake (Distance: 15m)
 [2] Spawn Crossing Pedestrian Jaywalker (Distance: 12m)
 [3] Spawn Aggressive Vehicle Cut-In (Distance: 9m)
 [4] Spawn Stationary Road Barrier (Distance: 18m)
 [M] Toggle Real YOLO vs Mock Perception Mode
 [F] Force Emergency Brake Override (Toggle)
 [T] Cycle Time of Day (Day -> Sunset -> Night)
 [W] Cycle Weather (Clear -> Rain -> Fog)
 [P] Pause / Resume Simulation
 [H] Show This Help Menu
======================================================================
""")

    def handle_key(self, key_char: str) -> Optional[str]:
        key = key_char.upper().strip()

        if key == "1":
            self.state.active_manual_hazard = HazardEvent(
                trigger_time_s=0.0,
                hazard_type="lead_vehicle_brake",
                distance_m=15.0,
                closing_speed_kmh=35.0,
                duration_s=4.0,
                description="[DEV] Spawned Lead Vehicle Sudden Brake"
            )
            return "Spawned: Lead Vehicle Sudden Brake"

        elif key == "2":
            self.state.active_manual_hazard = HazardEvent(
                trigger_time_s=0.0,
                hazard_type="pedestrian_cross",
                distance_m=12.0,
                closing_speed_kmh=40.0,
                duration_s=3.5,
                description="[DEV] Spawned Crossing Pedestrian"
            )
            return "Spawned: Crossing Pedestrian"

        elif key == "3":
            self.state.active_manual_hazard = HazardEvent(
                trigger_time_s=0.0,
                hazard_type="vehicle_cut_in",
                distance_m=9.0,
                closing_speed_kmh=45.0,
                duration_s=3.0,
                description="[DEV] Spawned Aggressive Vehicle Cut-In"
            )
            return "Spawned: Aggressive Vehicle Cut-In"

        elif key == "4":
            self.state.active_manual_hazard = HazardEvent(
                trigger_time_s=0.0,
                hazard_type="stationary_barrier",
                distance_m=18.0,
                closing_speed_kmh=50.0,
                duration_s=4.0,
                description="[DEV] Spawned Stationary Barrier"
            )
            return "Spawned: Stationary Barrier"

        elif key == "M":
            self.state.perception_mode = "mock" if self.state.perception_mode == "real" else "real"
            return f"Perception Mode Toggled: {self.state.perception_mode.upper()}"

        elif key == "F":
            self.state.forced_brake = not self.state.forced_brake
            return f"Forced Brake: {'ARMED' if self.state.forced_brake else 'DISARMED'}"

        elif key == "T":
            if self.state.time_of_day == TimeOfDay.DAY:
                self.state.time_of_day = TimeOfDay.SUNSET
            elif self.state.time_of_day == TimeOfDay.SUNSET:
                self.state.time_of_day = TimeOfDay.NIGHT
            else:
                self.state.time_of_day = TimeOfDay.DAY
            return f"Time of Day: {self.state.time_of_day.value}"

        elif key == "W":
            if self.state.weather == WeatherType.CLEAR:
                self.state.weather = WeatherType.RAIN
            elif self.state.weather == WeatherType.RAIN:
                self.state.weather = WeatherType.FOG
            else:
                self.state.weather = WeatherType.CLEAR
            return f"Weather: {self.state.weather.value}"

        elif key == "P":
            self.state.is_paused = not self.state.is_paused
            return f"Simulation: {'PAUSED' if self.state.is_paused else 'RESUMED'}"

        elif key == "H":
            self.print_help()
            return None

        return None
