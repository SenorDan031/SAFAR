"""
SAFAR Simulator — Safety Scoring & Results System
Calculates comprehensive driving safety metrics and generates the final Scenario Results Report.
"""
from dataclasses import dataclass
import time
from typing import Dict, Any, List

@dataclass
class SimulationMetrics:
    distance_km: float = 0.0
    avg_speed_kmh: float = 0.0
    max_speed_kmh: float = 0.0
    hazards_encountered: int = 0
    threats_detected: int = 0
    warnings_issued: int = 0
    braking_events: int = 0
    emergency_braking_events: int = 0
    collisions: int = 0
    near_misses: int = 0
    min_ttc_seconds: float = 999.0
    safety_score: int = 100
    duration_s: float = 0.0


class SafetyScoringSystem:
    def __init__(self):
        self.metrics = SimulationMetrics()
        self.speed_samples: List[float] = []
        self.last_update_time = time.time()
        self.prev_action = "CONTINUE"
        self.prev_threat = "LOW"

    def record_tick(
        self,
        speed_kmh: float,
        threat_level: str,
        threat_score: float,
        decision_action: str,
        ttc_seconds: float,
        is_hazard_active: bool,
        dt: float
    ):
        self.speed_samples.append(speed_kmh)
        self.metrics.max_speed_kmh = max(self.metrics.max_speed_kmh, speed_kmh)
        self.metrics.distance_km += (speed_kmh / 3600.0) * dt
        self.metrics.duration_s += dt

        if ttc_seconds < self.metrics.min_ttc_seconds:
            self.metrics.min_ttc_seconds = ttc_seconds

        # Record events on transition
        if threat_level in ["MEDIUM", "HIGH", "CRITICAL"] and self.prev_threat == "LOW":
            self.metrics.threats_detected += 1

        if decision_action == "WARN" and self.prev_action != "WARN":
            self.metrics.warnings_issued += 1
        elif decision_action == "BRAKE" and self.prev_action != "BRAKE":
            self.metrics.braking_events += 1
        elif decision_action == "EMERGENCY_BRAKE" and self.prev_action != "EMERGENCY_BRAKE":
            self.metrics.emergency_braking_events += 1

        # Near miss detection
        if ttc_seconds < 1.0 and ttc_seconds > 0.1 and decision_action != "EMERGENCY_BRAKE":
            self.metrics.near_misses += 1

        self.prev_action = decision_action
        self.prev_threat = threat_level

    def record_hazard_encountered(self):
        self.metrics.hazards_encountered += 1

    def record_collision(self):
        self.metrics.collisions += 1

    def compute_final_score(self) -> SimulationMetrics:
        if self.speed_samples:
            self.metrics.avg_speed_kmh = sum(self.speed_samples) / len(self.speed_samples)

        score = 100

        # Penalize collisions heavily (-50 per collision)
        score -= self.metrics.collisions * 50

        # Penalize near misses (-10 per near miss)
        score -= self.metrics.near_misses * 10

        # Reward successful hazard mitigations
        if self.metrics.hazards_encountered > 0:
            mitigation_ratio = min(1.0, (self.metrics.braking_events + self.metrics.emergency_braking_events) / max(1, self.metrics.hazards_encountered))
            if mitigation_ratio < 0.5:
                score -= 20

        # Clamp score to [0, 100]
        self.metrics.safety_score = max(0, min(100, score))
        return self.metrics

    def format_results_screen(self, scenario_name: str) -> str:
        m = self.compute_final_score()

        rating = "EXCELLENT (A+)" if m.safety_score >= 90 else (
            "GOOD (A)" if m.safety_score >= 80 else (
                "ADEQUATE (B)" if m.safety_score >= 70 else (
                    "NEEDS IMPROVEMENT (C)" if m.safety_score >= 50 else "FAILED (F)"
                )
            )
        )

        report = f"""
======================================================================
                 🏁 SCENARIO COMPLETE: {scenario_name.upper()} 🏁
======================================================================

 [DRIVING METRICS]
   • Distance Driven:          {m.distance_km:.2f} km
   • Average Speed:            {m.avg_speed_kmh:.1f} km/h
   • Maximum Speed:            {m.max_speed_kmh:.1f} km/h
   • Total Duration:           {m.duration_s:.1f} s

 [SAFAR ADAS PERFORMANCE]
   • Hazards Encountered:      {m.hazards_encountered}
   • Threats Detected:         {m.threats_detected}
   • Warning Alerts:           {m.warnings_issued}
   • Slowdown Interventions:   {m.braking_events}
   • Emergency Braking (AEB):  {m.emergency_braking_events}

 [SAFETY & COLLISION METRICS]
   • Collisions:               {m.collisions} (Target: 0)
   • Near Misses:              {m.near_misses}
   • Minimum Recorded TTC:     {m.min_ttc_seconds if m.min_ttc_seconds < 100 else 0.0:.2f} s

----------------------------------------------------------------------
 SAFAR SAFETY SCORE:          {m.safety_score}/100  [{rating}]
======================================================================
 [R] Retry Scenario    |    [N] Next Scenario    |    [M] Main Menu
======================================================================
"""
        return report
