"""
SAFAR Multiple-Threat Arbitration Engine
Unifies dynamic obstacles (vehicles, pedestrians, two-wheelers, animals) and road surface hazards (potholes, craters)
onto a single unified physical risk and priority scale.
"""

from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from .risk import PotholeRiskAssessment, PotholeSeverity
from .decision import PotholeAction, PotholeDecision


class ThreatSource(Enum):
    DYNAMIC_OBSTACLE = "DYNAMIC_OBSTACLE"
    ROAD_SURFACE_HAZARD = "ROAD_SURFACE_HAZARD"


@dataclass
class UnifiedThreatItem:
    """
    Unified representation of any road threat (dynamic or static surface).
    """
    threat_id: int
    source_type: ThreatSource
    class_name: str
    confidence: float
    distance_forward_m: float
    distance_lateral_m: float
    in_corridor: bool
    ttc_s: float
    stopping_distance_m: float
    safety_ratio: float
    required_decel_mps2: float
    risk_score: float              # Unified continuous danger score [0.0, 1.0]
    severity: str                  # "SAFE", "LOW", "MEDIUM", "HIGH", "CRITICAL"
    recommended_action: str        # "MAINTAIN", "MONITOR", "SLOW", "BRAKE", "EMERGENCY_BRAKE"
    vulnerability_weight: float    # Priority multiplier (Pedestrians/Bikes = 1.25, Craters = 1.15, Cars = 1.0)
    reason: str


class MultiThreatArbitrationEngine:
    """
    Evaluates all concurrent dynamic and static hazards in a scene,
    arbitrates priority on a unified physics scale, and generates the final vehicle command.
    """

    def __init__(self, ego_vehicle_half_width_m: float = 1.05):
        self.vehicle_half_width_m = ego_vehicle_half_width_m

    def arbitrate(
        self,
        dynamic_objects: List[Dict[str, Any]],
        pothole_assessments: List[PotholeRiskAssessment],
        ego_speed_mps: float,
        stopping_distance_m: float
    ) -> Tuple[UnifiedThreatItem, List[UnifiedThreatItem], PotholeDecision]:
        """
        Unifies and prioritizes all active threats in the scene.
        """
        unified_threats: List[UnifiedThreatItem] = []

        # 1. Ingest Dynamic Obstacles
        for dyn in dynamic_objects:
            c_name = dyn.get("class", "object").lower()
            dist_z = dyn.get("distance_forward_m", 50.0)
            lat_x = dyn.get("distance_lateral_m", 0.0)
            conf = dyn.get("confidence", 1.0)
            in_corr = dyn.get("in_corridor", abs(lat_x) <= 1.85)
            ttc = dyn.get("ttc_s") or (dist_z / max(0.1, ego_speed_mps) if in_corr else 99.0)

            # Kinematic stopping safety ratio
            s_ratio = dist_z / max(0.1, stopping_distance_m)
            a_req = (ego_speed_mps ** 2) / (2.0 * max(0.2, dist_z - (ego_speed_mps * 0.18))) if in_corr else 0.0

            # Vulnerability weights: Vulnerable Road Users (VRUs) prioritized
            v_weight = {
                "person": 1.30,
                "dog": 1.20,
                "motorcycle_rider": 1.25,
                "motorcycle": 1.15,
                "auto_rickshaw": 1.10,
                "car": 1.00,
                "truck": 1.00,
                "bus": 1.00
            }.get(c_name, 1.00)

            # Continuous Dynamic Risk Score
            if in_corr and s_ratio <= 1.0:
                dyn_risk = min(1.0, (1.1 - s_ratio) * v_weight * conf)
                sev = "CRITICAL" if s_ratio <= 0.80 else "HIGH"
                rec_act = "EMERGENCY_BRAKE" if s_ratio <= 0.80 else "BRAKE"
                reason = f"Imminent collision threat with {c_name.upper()} in corridor at {dist_z:.1f}m (TTC: {ttc:.1f}s <= 1.5s, d_stop: {stopping_distance_m:.1f}m, Required Decel: {a_req:.1f}m/s²)."
            elif in_corr and s_ratio <= 1.5:
                dyn_risk = 0.50 * v_weight * conf
                sev = "MEDIUM"
                rec_act = "SLOW"
                reason = f"Approaching {c_name.upper()} in corridor at {dist_z:.1f}m (TTC: {ttc:.1f}s). Moderating speed."
            elif in_corr:
                dyn_risk = 0.20 * conf
                sev = "LOW"
                rec_act = "MONITOR"
                reason = f"Tracking lead {c_name.upper()} ahead at {dist_z:.1f}m (TTC: {ttc:.1f}s)."
            else:
                dyn_risk = 0.02
                sev = "SAFE"
                rec_act = "MAINTAIN"
                reason = f"{c_name.upper()} on road shoulder / adjacent lane at {lat_x:+.1f}m. Path clear."

            unified_threats.append(UnifiedThreatItem(
                threat_id=dyn.get("id", len(unified_threats) + 1),
                source_type=ThreatSource.DYNAMIC_OBSTACLE,
                class_name=c_name,
                confidence=conf,
                distance_forward_m=dist_z,
                distance_lateral_m=lat_x,
                in_corridor=in_corr,
                ttc_s=ttc,
                stopping_distance_m=stopping_distance_m,
                safety_ratio=s_ratio,
                required_decel_mps2=a_req,
                risk_score=dyn_risk,
                severity=sev,
                recommended_action=rec_act,
                vulnerability_weight=v_weight,
                reason=reason
            ))

        # 2. Ingest Road Surface Hazards (Potholes / Craters)
        for ph in pothole_assessments:
            if not ph.is_valid or ph.pothole_type == 0:
                continue

            v_weight = 1.15 if ph.pothole_type == 3 else 1.00 # Severe craters carry high mechanical weight
            in_corr = (ph.path_intersection.value != "PATH_CLEAR")

            unified_threats.append(UnifiedThreatItem(
                threat_id=ph.pothole_id + 100,
                source_type=ThreatSource.ROAD_SURFACE_HAZARD,
                class_name=ph.pothole_name,
                confidence=ph.confidence,
                distance_forward_m=ph.distance_forward_m,
                distance_lateral_m=ph.distance_lateral_m,
                in_corridor=in_corr,
                ttc_s=ph.time_to_pothole_s,
                stopping_distance_m=ph.stopping_distance_m,
                safety_ratio=ph.safety_ratio,
                required_decel_mps2=ph.required_decel_mps2,
                risk_score=ph.risk_score * v_weight,
                severity=ph.severity.value,
                recommended_action=ph.recommended_action,
                vulnerability_weight=v_weight,
                reason=ph.reason
            ))

        # 3. Deterministic Priority Ranking
        # Priority order: (1) Severe corridor collision threats with highest required decel, (2) Lowest TTC, (3) Highest Risk Score
        severity_rank = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "SAFE": 0}

        in_corridor_threats = [t for t in unified_threats if t.in_corridor]

        if in_corridor_threats:
            primary_threat = max(
                in_corridor_threats,
                key=lambda t: (severity_rank.get(t.severity, 0), t.risk_score, -t.distance_forward_m)
            )
        elif unified_threats:
            primary_threat = max(unified_threats, key=lambda t: (severity_rank.get(t.severity, 0), t.risk_score))
        else:
            # Clear road
            primary_threat = UnifiedThreatItem(
                threat_id=0,
                source_type=ThreatSource.ROAD_SURFACE_HAZARD,
                class_name="drivable_path",
                confidence=1.0,
                distance_forward_m=50.0,
                distance_lateral_m=0.0,
                in_corridor=True,
                ttc_s=float("inf"),
                stopping_distance_m=stopping_distance_m,
                safety_ratio=99.0,
                required_decel_mps2=0.0,
                risk_score=0.0,
                severity="SAFE",
                recommended_action="MAINTAIN",
                vulnerability_weight=1.0,
                reason="Road corridor is completely clear. Manual driver control active."
            )

        # 4. Synthesize Final Vehicle Decision
        action_map = {
            "EMERGENCY_BRAKE": PotholeAction.EMERGENCY_BRAKE,
            "BRAKE": PotholeAction.BRAKE,
            "SLOW": PotholeAction.SLOW,
            "SLOW_DOWN": PotholeAction.SLOW,
            "MONITOR": PotholeAction.MONITOR,
            "MAINTAIN": PotholeAction.MAINTAIN,
            "MAINTAIN_SPEED": PotholeAction.MAINTAIN
        }
        final_action = action_map.get(primary_threat.recommended_action, PotholeAction.MAINTAIN)
        has_intervention = (final_action in [PotholeAction.BRAKE, PotholeAction.EMERGENCY_BRAKE])

        decision = PotholeDecision(
            state=final_action,
            has_intervention=has_intervention,
            recommended_action=final_action,
            target_pothole_id=primary_threat.threat_id,
            target_pothole_name=primary_threat.class_name,
            risk_score=primary_threat.risk_score,
            recommended_speed_mps=12.0 if final_action == PotholeAction.SLOW else 0.0 if has_intervention else ego_speed_mps,
            time_to_pothole_s=primary_threat.ttc_s,
            distance_forward_m=primary_threat.distance_forward_m,
            confidence=primary_threat.confidence,
            hold_timer_active=False,
            reason=primary_threat.reason
        )

        return primary_threat, unified_threats, decision
