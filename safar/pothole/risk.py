"""
SAFAR Pothole Risk Engine
Physics-grounded risk evaluation with dynamic stopping distance, TTC, wheel strike geometry, and transparent causal reasoning.
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
from .path import PotholePathGeometry, PathIntersectionStatus, PotholeCorridorEvaluation


class PotholeSeverity(Enum):
    SAFE = "SAFE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class PotholeRiskAssessment:
    """
    Structured, fully explainable risk output for a single road hazard.
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
    time_to_pothole_s: float       # Kinematic Time-To-Pothole (TTC = dist / speed)
    stopping_distance_m: float     # Required stopping distance d_stop
    required_decel_mps2: float     # Deceleration needed to stop before hazard
    safety_ratio: float            # R = distance / d_stop
    path_intersection: PathIntersectionStatus
    strike_location: str           # "LEFT_WHEEL", "RIGHT_WHEEL", "UNDERCARRIAGE", "MARGIN", "CLEAR"
    recommended_speed_mps: float   # Target safe speed for this surface condition
    recommended_action: str        # Initial risk recommendation
    is_valid: bool
    reason: str                    # Detailed, transparent causal reasoning chain


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
        # 1. Failure-Safe Guardrail: Invalid data or Low Confidence (< 0.70) -> SAFE
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
                required_decel_mps2=0.0,
                safety_ratio=99.0,
                path_intersection=PathIntersectionStatus.PATH_CLEAR,
                strike_location="CLEAR",
                recommended_speed_mps=vehicle_speed_mps,
                recommended_action="MAINTAIN_SPEED",
                is_valid=False,
                reason=f"Observation uncertain or invalid ({observation.status}, confidence {observation.confidence*100:.1f}% < {CONFIDENCE_THRESHOLD*100:.0f}%). Defaulting to safe passive monitoring."
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
                required_decel_mps2=0.0,
                safety_ratio=99.0,
                path_intersection=PathIntersectionStatus.PATH_CLEAR,
                strike_location="CLEAR",
                recommended_speed_mps=SAFE_SPEED_MAPPINGS[0],
                recommended_action="MAINTAIN_SPEED",
                is_valid=True,
                reason="Drivable road path detected. Road surface clear of destructive hazards."
            )

        # 3. Vehicle At Rest Check (Speed <= 0.2 m/s -> No dynamic danger)
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
                required_decel_mps2=0.0,
                safety_ratio=99.0,
                path_intersection=PathIntersectionStatus.PATH_CLEAR,
                strike_location="CLEAR",
                recommended_speed_mps=0.0,
                recommended_action="MAINTAIN_SPEED",
                is_valid=True,
                reason="Vehicle is stationary (Speed <= 0.2 m/s). Zero kinematic collision danger."
            )

        # 4. Geometry and Wheel Strike Evaluation
        corridor = self.geometry.evaluate_intersection(
            distance_forward_m=observation.distance_forward,
            distance_lateral_m=observation.distance_lateral,
            pothole_width_m=observation.width,
            pothole_depth_m=observation.depth,
            vehicle_speed_mps=vehicle_speed_mps,
            steering_angle_rad=steering_angle_rad
        )

        # 5. Physics and Stopping Profile
        phys = self.physics.compute_physics_profile(
            speed_mps=vehicle_speed_mps,
            distance_forward_m=observation.distance_forward
        )
        d_stop = phys["nominal_stopping_dist_m"]
        safety_ratio = phys["safety_ratio"]
        ttc = phys["time_to_reach_s"]
        a_req = phys["required_decel_mps2"]

        # If pothole is completely outside driving corridor:
        if corridor.status == PathIntersectionStatus.PATH_CLEAR:
            return PotholeRiskAssessment(
                pothole_id=observation.pothole_id,
                risk_score=0.02,
                severity=PotholeSeverity.SAFE,
                pothole_type=observation.pothole_type,
                pothole_name=observation.pothole_name,
                confidence=observation.confidence,
                distance_forward_m=observation.distance_forward,
                distance_lateral_m=observation.distance_lateral,
                vehicle_speed_mps=vehicle_speed_mps,
                time_to_pothole_s=ttc,
                stopping_distance_m=d_stop,
                required_decel_mps2=a_req,
                safety_ratio=safety_ratio,
                path_intersection=corridor.status,
                strike_location=corridor.strike_location,
                recommended_speed_mps=vehicle_speed_mps,
                recommended_action="MAINTAIN_SPEED",
                is_valid=True,
                reason=f"{observation.pothole_name} located outside vehicle corridor (lateral offset {observation.distance_lateral:+.1f}m > envelope). No path intersection."
            )

        # 6. Physical Severity Base Weight
        # Depth is the primary destructive parameter to tires/rims/suspension
        depth_severity = min(1.0, observation.depth / 0.14)  # 14cm depth = max destructiveness
        class_base_weight = {1: 0.20, 2: 0.50, 3: 0.90}.get(observation.pothole_type, 0.20)
        base_severity = 0.5 * class_base_weight + 0.5 * depth_severity

        # 7. Dynamic Stopping Distance & TTC Urgency Scaling
        # Explicit continuous coupling: If d < d_stop, urgency is maximum (1.0)
        if safety_ratio <= 0.85 or ttc <= 1.0:
            distance_urgency = 1.0
        elif safety_ratio <= 1.25 or ttc <= 1.8:
            distance_urgency = 0.80
        elif safety_ratio <= 2.0 or ttc <= 3.0:
            distance_urgency = 0.45
        elif safety_ratio <= 3.5:
            distance_urgency = 0.20
        else: # Far away -> Low urgency regardless of size
            distance_urgency = 0.05

        # Speed Excess vs Safe Speed
        target_safe_speed = SAFE_SPEED_MAPPINGS.get(observation.pothole_type, 10.0)
        speed_excess = max(0.0, vehicle_speed_mps - target_safe_speed) / max(1.0, target_safe_speed)
        speed_factor = min(1.0, speed_excess)

        # Lateral relevance multiplier based on wheel strike vs undercarriage
        if corridor.is_wheel_strike:
            lat_multiplier = 1.00  # Direct wheel impact
        elif corridor.status == PathIntersectionStatus.UNDERCARRIAGE_STRIKE:
            # Undercarriage strike is critical only if depth exceeds clearance (14cm)
            lat_multiplier = 0.90 if observation.depth > 0.12 else 0.40
        else: # Grazing
            lat_multiplier = 0.50

        # 8. Continuous Transparent Risk Score
        risk_score = base_severity * (0.60 * distance_urgency + 0.40 * speed_factor) * lat_multiplier * observation.confidence
        risk_score = max(0.0, min(1.0, risk_score))

        # 9. Discrete Severity & Causal Reason Chain Generation
        if (observation.pothole_type == 3 and safety_ratio <= 1.20 and corridor.is_directly_in_path) or (corridor.is_wheel_strike and a_req > 7.5 and observation.pothole_type >= 2):
            severity = PotholeSeverity.CRITICAL
            rec_action = "EMERGENCY_BRAKE"
            rec_speed = target_safe_speed
            reason = (
                f"CRITICAL THREAT: Severe {observation.pothole_name} ({observation.depth*100:.0f}cm deep) in {corridor.strike_location} path at {observation.distance_forward:.1f}m. "
                f"TTC: {ttc:.2f}s, d_stop: {d_stop:.1f}m (dist <= d_stop * 1.2), Required Decel: {a_req:.1f}m/s² > Nominal 6.0m/s². Initiating emergency intervention."
            )
        elif risk_score >= 0.70 or (observation.pothole_type >= 2 and safety_ratio <= 1.50 and corridor.is_directly_in_path):
            severity = PotholeSeverity.HIGH
            rec_action = "BRAKE"
            rec_speed = target_safe_speed
            reason = (
                f"HIGH RISK: {observation.pothole_name} in {corridor.strike_location} path at {observation.distance_forward:.1f}m. "
                f"TTC: {ttc:.2f}s, Approach Speed {vehicle_speed_mps*3.6:.0f}km/h exceeds Safe Speed {target_safe_speed*3.6:.0f}km/h. Distance {observation.distance_forward:.1f}m approaching d_stop ({d_stop:.1f}m). Applying service brake."
            )
        elif risk_score >= 0.35 or (vehicle_speed_mps > target_safe_speed and corridor.is_directly_in_path):
            severity = PotholeSeverity.MEDIUM
            rec_action = "SLOW_DOWN"
            rec_speed = target_safe_speed
            reason = (
                f"MEDIUM RISK: Approaching {observation.pothole_name} at {observation.distance_forward:.1f}m (TTC: {ttc:.1f}s, safety ratio: {safety_ratio:.2f}). "
                f"Recommend moderating approach speed from {vehicle_speed_mps*3.6:.0f}km/h to {target_safe_speed*3.6:.0f}km/h."
            )
        elif risk_score >= 0.15:
            severity = PotholeSeverity.LOW
            rec_action = "MONITOR"
            rec_speed = vehicle_speed_mps
            reason = f"LOW RISK: {observation.pothole_name} observed at {observation.distance_forward:.1f}m (TTC: {ttc:.1f}s). Ample stopping buffer ({safety_ratio:.1f}x d_stop). Monitoring path."
        else:
            severity = PotholeSeverity.SAFE
            rec_action = "MAINTAIN_SPEED"
            rec_speed = vehicle_speed_mps
            reason = "SAFE: Road surface anomaly does not threaten current vehicle trajectory or speed."

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
            time_to_pothole_s=ttc,
            stopping_distance_m=d_stop,
            required_decel_mps2=a_req,
            safety_ratio=safety_ratio,
            path_intersection=corridor.status,
            strike_location=corridor.strike_location,
            recommended_speed_mps=rec_speed,
            recommended_action=rec_action,
            is_valid=True,
            reason=reason
        )
