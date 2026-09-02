"""
SAFAR Simulator — Live In-Game HUD & Indian Road Diagnostics Cluster
Renders fixed, non-scrolling, high-visibility telemetry for Indian road driving & autonomous safety overrides.
"""
from dataclasses import dataclass
import time

@dataclass
class HUDState:
    speed_kmh: float = 0.0
    gear: int = 1
    sensors_online: bool = True
    perception_mode: str = "REAL_YOLO11"
    core_online: bool = True
    control_armed: bool = True
    road_environment: str = "INDIAN URBAN (LEFT-HAND TRAFFIC)"
    tracked_objects_count: int = 0
    primary_hazard_id: str = "none"
    primary_hazard_class: str = "none"
    primary_hazard_distance_m: float = 100.0
    primary_hazard_ttc_s: float = 999.0
    threat_state: str = "LOW"
    threat_score: float = 0.0
    decision_action: str = "CONTINUE"
    is_intervening: bool = False
    warning_flashing: bool = False
    active_scenario_name: str = "Indian Urban Road"
    elapsed_time_s: float = 0.0
    scenario_progress_pct: float = 0.0


class HUDCluster:
    @staticmethod
    def render_compact_line(state: HUDState) -> str:
        """High-visibility single-line live telemetry."""
        threat_tag = f"[{state.threat_state:<8} {state.threat_score:4.2f}]"
        hazard_str = f"{state.primary_hazard_class.upper()} #{state.primary_hazard_id} ({state.primary_hazard_distance_m:4.1f}m | TTC: {state.primary_hazard_ttc_s:3.1f}s)" if state.primary_hazard_id != "none" else "Path Clear"
        action_tag = f"[{'⚠ ' + state.decision_action if state.is_intervening else state.decision_action:<15}]"
        
        return f"[SAFAR ADAS] SPEED: {state.speed_kmh:3.0f} km/h | {threat_tag} | HAZARD: {hazard_str:<28} | ACTION: {action_tag} | OVERRIDE: {'[AEB LOCKED]' if state.is_intervening else '[STANDBY]'}"

    @staticmethod
    def format_screen_banner(state: HUDState) -> str:
        """Fixed on-screen diagnostics banner for vehicle HUD / terminal."""
        intervention_alert = """
       ╔═══════════════════════════════════════════════════════════════════╗
       ║             ⚠  SAFAR AUTONOMOUS INTERVENTION ACTIVE  ⚠            ║
       ║        CRITICAL FORWARD HAZARD DETECTED — AEB BRAKES LOCKED       ║
       ╚═══════════════════════════════════════════════════════════════════╝
""" if state.is_intervening else ""

        banner = f"""
================================================================================
 🚗 SAFAR ADAS — {state.active_scenario_name.upper()} | {state.road_environment}
 Time: {state.elapsed_time_s:4.1f}s [{state.scenario_progress_pct:3.0f}%] | Speed: {state.speed_kmh:3.0f} km/h (Gear {state.gear})
--------------------------------------------------------------------------------
 [SENSORS & AI]   Sensors: ONLINE | Perception: {state.perception_mode} | Core: ONLINE | Control: ARMED
 [ROAD TRAFFIC]   Tracked Road Objects: {state.tracked_objects_count}
 [LEAD HAZARD]    {state.primary_hazard_class.upper()} #{state.primary_hazard_id} | Distance: {state.primary_hazard_distance_m:4.1f}m | TTC: {state.primary_hazard_ttc_s if state.primary_hazard_ttc_s < 50 else 0.0:3.1f}s
 [THREAT ENGINE]  Risk Level: {state.threat_state} (Score: {state.threat_score:.2f}/1.00)
 [SAFAR DECISION] Policy: {state.decision_action}
 [VEHICLE STATE]  Throttle: {'0.00 (CUT)' if state.is_intervening else '1.00'} | Brake: {'1.00 (AEB LOCKED)' if state.is_intervening else '0.00'}
{intervention_alert}================================================================================
"""
        return banner
