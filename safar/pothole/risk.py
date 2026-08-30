"""
SAFAR Pothole Risk Engine
Combines ML observation, vehicle kinematics, stopping dynamics, and path intersection geometry.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, Optional

from .config import (
    SAFE_SPEED_MAPPINGS,
    CONFIDENCE_THRESHOLD,
    ACTIVATION_THRESHOLD,
    RELEASE_THRESHOLD
)
from .classifier import PotholeObservation
from .physics import PotholePhysicsEngine
from .path import PotholePathGeometry, PathIntersectionStatus


class PotholeSeverity(Enum):
    SAFE = "SAFE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class PotholeRiskAssessment:
    """
    Structured risk output for a single pothole hazard.
    """
    pothole_id: int
    risk_score: float              # Continuous normalized threat score [0.0, 1.0]
    severity: PotholeSeverity      # Discrete severity level
    pothole_type: int
    pothole_name: str
    confidence: float
    distance_forward_m: float
    distance_lateral_m: float
    vehicle_speed_mps: float
    time_to_pothole_s: float
    stopping_distance_m: float
    safety_ratio: float
    path_intersection: PathIntersectionStatus
    recommended_speed_mps: float   # Target safe speed for this surface condition
    recommended_action: str        # Initial risk recommendation
    is_valid: bool
    reason: str


class PotholeRiskEngine:
    """
    Evaluates physical danger of a road surface anomaly.
    Pure reasoning layer: Does NOT actuate vehicle controls directly.
    """

    def __init__(
        self,
        physics_engine: Optional[PotholePhysicsEngine] = None,
        path_geometry: Optional[PotholePathGeometry] = None
    ):
        self.physics = physics_engine or PotholePhysicsEngine()
        self.geometry = path_geometry or PotholePathGeometry()

    def assess_risk(
        self,
        observation: PotholeObservation,
        vehicle_speed_mps: float,
        steering_angle_rad: float = 0.0
    ) -> PotholeRiskAssessment:
        """
        Evaluates risk for a given pothole observation and vehicle kinematic state.
        """
        # 1. Invalid or Inactive Guardrails (NO DATA != DANGER)
        if not observation.is_valid or observation.pothole_type == -1 or observation.confidence < CONFIDENCE_THRESHOLD:
            return PotholeRiskAssessment(
                pothole_id=observation.pothole_id,
                risk_score=0.0,
                severity=PotholeSeverity.SAFE,
                pothole_type=observation.pothole_type,
                pothole_name=observation.pothole_name,
                confidence=observation.confidence,
                distance_forward_m=observation.distance_forward,
                distance_lateral_m=observation.distance_lateral,
                vehicle_speed_mps=vehicle_speed_mps,
                time_to_pothole_s=float("inf"),
                stopping_distance_m=0.0,
                safety_ratio=99.0,
                path_intersection=PathIntersectionStatus.PATH_CLEAR,
                recommended_speed_mps=vehicle_speed_mps,
                recommended_action="MAINTAIN_SPEED",
                is_valid=False,
                reason=f"Observation is uncertain or invalid ({observation.status})"
            )

        # 2. Drivable Path (Class 0) -> Completely Safe
        if observation.pothole_type == 0:
            return PotholeRiskAssessment(
                pothole_id=observation.pothole_id,
                risk_score=0.0,
                severity=PotholeSeverity.SAFE,
                pothole_type=0,
                pothole_name="drivable_path",
                confidence=observation.confidence,
                distance_forward_m=observation.distance_forward,
                distance_lateral_m=observation.distance_lateral,
                vehicle_speed_mps=vehicle_speed_mps,
                time_to_pothole_s=float("inf"),
                stopping_distance_m=self.physics.calculate_stopping_distance(vehicle_speed_mps),
                safety_ratio=99.0,
                path_intersection=PathIntersectionStatus.PATH_CLEAR,
                recommended_speed_mps=SAFE_SPEED_MAPPINGS[0],
                recommended_action="MAINTAIN_SPEED",
                is_valid=True,
                reason="Drivable road path detected. Road surface clear."
            )

        # 3. Vehicle At Rest Check (Speed <= 0.2 m/s -> No immediate kinematic danger)
        if vehicle_speed_mps <= 0.2:
            return PotholeRiskAssessment(
                pothole_id=observation.pothole_id,
                risk_score=0.0,
                severity=PotholeSeverity.SAFE,
                pothole_type=observation.pothole_type,
                pothole_name=observation.pothole_name,
                confidence=observation.confidence,
                distance_forward_m=observation.distance_forward,
                distance_lateral_m=observation.distance_lateral,
                vehicle_speed_mps=vehicle_speed_mps,
                time_to_pothole_s=float("inf"),
                stopping_distance_m=0.0,
                safety_ratio=99.0,
                path_intersection=PathIntersectionStatus.PATH_CLEAR,
                recommended_speed_mps=0.0,
                recommended_action="MAINTAIN_SPEED",
                is_valid=True,
                reason="Vehicle is stationary. No dynamic risk."
            )

        # 4. Geometry and Corridor Evaluation
        corridor = self.geometry.evaluate_intersection(
            distance_forward_m=observation.distance_forward,
            distance_lateral_m=observation.distance_lateral,
            pothole_width_m=observation.width,
            vehicle_speed_mps=vehicle_speed_mps,
            steering_angle_rad=steering_angle_rad
        )

        # 5. Physics and Stopping Calculation
        phys = self.physics.compute_physics_profile(
            speed_mps=vehicle_speed_mps,
            distance_forward_m=observation.distance_forward
        )

        # If pothole is completely outside driving path:
        if corridor.status == PathIntersectionStatus.PATH_CLEAR:
            return PotholeRiskAssessment(
                pothole_id=observation.pothole_id,
                risk_score=0.05,
                severity=PotholeSeverity.SAFE,
                pothole_type=observation.pothole_type,
                pothole_name=observation.pothole_name,
                confidence=observation.confidence,
                distance_forward_m=observation.distance_forward,
                distance_lateral_m=observation.distance_lateral,
                vehicle_speed_mps=vehicle_speed_mps,
                time_to_pothole_s=phys["time_to_reach_s"],
                stopping_distance_m=phys["nominal_stopping_dist_m"],
                safety_ratio=phys["safety_ratio"],
                path_intersection=corridor.status,
                recommended_speed_mps=vehicle_speed_mps,
                recommended_action="MAINTAIN_SPEED",
                is_valid=True,
                reason=f"{observation.pothole_name} located outside vehicle corridor (lateral offset {observation.distance_lateral:.1f}m)."
            )

        # 6. Physical Severity Base Weight
        # Depth is the single most destructive parameter to wheel/suspension
        depth_severity = min(1.0, observation.depth / 0.15)  # 15cm depth = max severity
        class_base_weight = {1: 0.25, 2: 0.55, 3: 0.90}.get(observation.pothole_type, 0.2)
        base_severity = 0.5 * class_base_weight + 0.5 * depth_severity

        # 7. Speed vs. Distance Kinematic Factor
        # Kinematic factor depends on whether speed exceeds safe speed and safety ratio
        target_safe_speed = SAFE_SPEED_MAPPINGS.get(observation.pothole_type, 10.0)
        speed_excess = max(0.0, vehicle_speed_mps - target_safe_speed) / max(1.0, target_safe_speed)
        speed_factor = min(1.0, speed_excess)

        # Distance urgency (Safety Ratio < 1.0 means vehicle cannot stop in time nominally)
        if phys["safety_ratio"] <= 0.8:
            distance_urgency = 1.0
        elif phys["safety_ratio"] <= 1.2:
            distance_urgency = 0.8
        elif phys["safety_ratio"] <= 2.0:
            distance_urgency = 0.5
        elif phys["safety_ratio"] <= 3.5:
            distance_urgency = 0.25
        else:
            distance_urgency = 0.05

        # Lateral relevance multiplier (1.0 directly in path, 0.6 if grazing/possible)
        lat_multiplier = 1.0 if corridor.status == PathIntersectionStatus.INTERSECTION else 0.60

        # 8. Transparent Risk Score Formulation
        # Risk = base_severity * (0.6 * distance_urgency + 0.4 * speed_factor) * lat_multiplier * confidence
        risk_score = base_severity * (0.65 * distance_urgency + 0.35 * speed_factor) * lat_multiplier * observation.confidence
        risk_score = max(0.0, min(1.0, risk_score))

        # 9. Determine Discrete Severity & Recommended Action
        if observation.pothole_type == 3 and phys["safety_ratio"] <= 1.25 and corridor.is_directly_in_path:
            severity = PotholeSeverity.CRITICAL
            rec_action = "EMERGENCY_BRAKE"
            rec_speed = target_safe_speed
            reason = f"CRITICAL: Severe crater ({observation.depth*100:.0f}cm deep) directly in path at {observation.distance_forward:.1f}m (TTC: {phys['time_to_reach_s']:.1f}s, d_stop: {phys['nominal_stopping_dist_m']:.1f}m)."
        elif risk_score >= 0.70 or (observation.pothole_type >= 2 and phys["safety_ratio"] <= 1.5 and corridor.is_directly_in_path):
            severity = PotholeSeverity.HIGH
            rec_action = "BRAKE"
            rec_speed = target_safe_speed
            reason = f"HIGH RISK: {observation.pothole_name} in path at {observation.distance_forward:.1f}m exceeding safe approach speed."
        elif risk_score >= 0.40 or (vehicle_speed_mps > target_safe_speed and corridor.is_relevant):
            severity = PotholeSeverity.MEDIUM
            rec_action = "SLOW_DOWN"
            rec_speed = target_safe_speed
            reason = f"MEDIUM: Approaching {observation.pothole_name} at {observation.distance_forward:.1f}m; recommend moderating speed to {target_safe_speed:.0f}m/s."
        elif risk_score >= 0.15:
            severity = PotholeSeverity.LOW
            rec_action = "MONITOR"
            rec_speed = vehicle_speed_mps
            reason = f"LOW: {observation.pothole_name} observed ahead at {observation.distance_forward:.1f}m; path clear for current speed."
        else:
            severity = PotholeSeverity.SAFE
            rec_action = "MAINTAIN_SPEED"
            rec_speed = vehicle_speed_mps
            reason = "SAFE: Pothole hazard does not threaten current vehicle path or speed."

        return PotholeRiskAssessment(
            pothole_id=observation.pothole_id,
            risk_score=risk_score,
            severity=severity,
            pothole_type=observation.pothole_type,
            pothole_name=observation.pothole_name,
            confidence=observation.confidence,
            distance_forward_m=observation.distance_forward,
            distance_lateral_m=observation.distance_lateral,
            vehicle_speed_mps=vehicle_speed_mps,
            time_to_pothole_s=phys["time_to_reach_s"],
            stopping_distance_m=phys["nominal_stopping_dist_m"],
            safety_ratio=phys["safety_ratio"],
            path_intersection=corridor.status,
            recommended_speed_mps=rec_speed,
            recommended_action=rec_action,
            is_valid=True,
            reason=reason
        )
