"""
SAFAR Pothole Physics and Stopping Distance Kinematics Engine
Calculates dynamic stopping envelopes, required decelerations, and Time-To-Pothole (TTC).
"""

import math
from typing import Dict, Any, Optional
from .config import (
    REACTION_TIME_S,
    DECEL_NOMINAL_MPS2,
    DECEL_EMERGENCY_MPS2,
    STOPPING_DISTANCE_MARGIN_M
)


class PotholePhysicsEngine:
    """
    Computes exact longitudinal kinematics and stopping envelopes for vehicular road hazards.
    """

    def __init__(
        self,
        reaction_time_s: float = REACTION_TIME_S,
        nominal_decel_mps2: float = DECEL_NOMINAL_MPS2,
        emergency_decel_mps2: float = DECEL_EMERGENCY_MPS2,
        safety_margin_m: float = STOPPING_DISTANCE_MARGIN_M
    ):
        self.reaction_time_s = max(0.01, reaction_time_s)
        self.nominal_decel_mps2 = max(0.5, nominal_decel_mps2)
        self.emergency_decel_mps2 = max(self.nominal_decel_mps2, emergency_decel_mps2)
        self.safety_margin_m = max(0.0, safety_margin_m)

    def calculate_stopping_distance(
        self,
        speed_mps: float,
        decel_mps2: Optional[float] = None,
        reaction_time_s: Optional[float] = None
    ) -> float:
        """
        Calculates total stopping distance: d_stop = v * t_react + v^2 / (2 * a)
        """
        if speed_mps <= 0.05:
            return 0.0

        t_react = reaction_time_s if reaction_time_s is not None else self.reaction_time_s
        a = decel_mps2 if decel_mps2 is not None else self.nominal_decel_mps2

        reaction_dist = speed_mps * t_react
        braking_dist = (speed_mps ** 2) / (2.0 * a)
        return float(reaction_dist + braking_dist)

    def calculate_required_stopping_distance(
        self,
        speed_mps: float,
        decel_mps2: Optional[float] = None
    ) -> float:
        """Total required stopping distance including vehicle safety buffer."""
        return self.calculate_stopping_distance(speed_mps, decel_mps2) + self.safety_margin_m

    def calculate_time_to_pothole(
        self,
        distance_forward_m: float,
        speed_mps: float
    ) -> float:
        """
        Calculates kinematic Time-To-Pothole (TTC_pothole = distance / speed).
        If vehicle is stationary (v <= 0.05 m/s) or distance <= 0, handles gracefully.
        """
        if distance_forward_m <= 0.0:
            return 0.0
        if speed_mps <= 0.05:
            return float("inf")
        return float(distance_forward_m / speed_mps)

    def calculate_required_deceleration(
        self,
        distance_forward_m: float,
        speed_mps: float
    ) -> float:
        """
        Calculates the exact deceleration required to come to a complete stop before the pothole:
        Taking reaction time into account:
        d_brake = distance - (v * t_react)
        a_req = v^2 / (2 * d_brake)
        """
        if speed_mps <= 0.05 or distance_forward_m <= 0.0:
            return 0.0

        reaction_dist = speed_mps * self.reaction_time_s
        effective_brake_dist = distance_forward_m - reaction_dist - self.safety_margin_m

        if effective_brake_dist <= 0.1:
            # Physical stopping impossible within available distance
            return 99.0

        return float((speed_mps ** 2) / (2.0 * effective_brake_dist))

    def calculate_safety_ratio(
        self,
        distance_forward_m: float,
        speed_mps: float,
        decel_mps2: Optional[float] = None
    ) -> float:
        """
        Safety Ratio: R = distance / required_stopping_distance
        R > 1.5 : Safe buffer
        1.0 <= R <= 1.5 : Caution zone
        R < 1.0 : Cannot stop in time with nominal braking
        """
        if speed_mps <= 0.05:
            return 99.0
        req_dist = self.calculate_required_stopping_distance(speed_mps, decel_mps2)
        if req_dist <= 0.001:
            return 99.0
        return float(distance_forward_m / req_dist)

    def compute_physics_profile(
        self,
        speed_mps: float,
        distance_forward_m: float
    ) -> Dict[str, Any]:
        """Comprehensive kinematic telemetry snapshot."""
        d_stop_nom = self.calculate_stopping_distance(speed_mps, self.nominal_decel_mps2)
        d_stop_emg = self.calculate_stopping_distance(speed_mps, self.emergency_decel_mps2)
        d_req = self.calculate_required_stopping_distance(speed_mps, self.nominal_decel_mps2)
        ttc = self.calculate_time_to_pothole(distance_forward_m, speed_mps)
        a_req = self.calculate_required_deceleration(distance_forward_m, speed_mps)
        safety_ratio = self.calculate_safety_ratio(distance_forward_m, speed_mps)

        return {
            "speed_mps": speed_mps,
            "speed_kmh": speed_mps * 3.6,
            "distance_forward_m": distance_forward_m,
            "nominal_stopping_dist_m": d_stop_nom,
            "emergency_stopping_dist_m": d_stop_emg,
            "required_stopping_dist_m": d_req,
            "time_to_reach_s": ttc,
            "required_decel_mps2": a_req,
            "safety_ratio": safety_ratio,
            "is_stoppable_nominally": distance_forward_m >= d_req,
            "is_stoppable_emergently": a_req <= self.emergency_decel_mps2
        }
