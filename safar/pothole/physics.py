"""
SAFAR Pothole Physics Engine
Calculates vehicle stopping distance, reaction latency, time-to-pothole, and deceleration profiles.
"""

import math
from typing import Dict, Any
from .config import (
    DEFAULT_REACTION_TIME_S,
    NOMINAL_DECELERATION_MPS2,
    EMERGENCY_DECELERATION_MPS2,
    SAFETY_MARGIN_M
)


class PotholePhysicsEngine:
    """
    Pure physics calculations for vehicle-pothole interactions.
    Separated from ML classification and decision logic.
    """

    def __init__(
        self,
        reaction_time_s: float = DEFAULT_REACTION_TIME_S,
        nominal_decel_mps2: float = NOMINAL_DECELERATION_MPS2,
        emergency_decel_mps2: float = EMERGENCY_DECELERATION_MPS2,
        safety_margin_m: float = SAFETY_MARGIN_M
    ):
        self.reaction_time_s = reaction_time_s
        self.nominal_decel_mps2 = nominal_decel_mps2
        self.emergency_decel_mps2 = emergency_decel_mps2
        self.safety_margin_m = safety_margin_m

    def calculate_stopping_distance(
        self,
        speed_mps: float,
        is_emergency: bool = False
    ) -> float:
        """
        Calculates theoretical physical stopping distance:
        d_stop = (v * t_reaction) + (v^2 / (2 * a))
        """
        v = max(0.0, speed_mps)
        a = self.emergency_decel_mps2 if is_emergency else self.nominal_decel_mps2
        
        reaction_dist = v * self.reaction_time_s
        braking_dist = (v * v) / (2.0 * a)
        return reaction_dist + braking_dist

    def calculate_required_stopping_distance(
        self,
        speed_mps: float,
        is_emergency: bool = False
    ) -> float:
        """
        Calculates total required stopping distance including configured safety buffer.
        """
        base_stop = self.calculate_stopping_distance(speed_mps, is_emergency=is_emergency)
        return base_stop + self.safety_margin_m if speed_mps > 0.1 else 0.0

    def calculate_time_to_pothole(
        self,
        distance_forward_m: float,
        speed_mps: float
    ) -> float:
        """
        Calculates time until vehicle reaches pothole:
        t = distance / speed
        Gracefully handles speed <= 0 without division by zero.
        """
        if distance_forward_m <= 0.0:
            return 0.0

        if speed_mps <= 0.05:
            # Vehicle stationary or creeping: Time to pothole is effectively infinite
            return float("inf")

        return distance_forward_m / speed_mps

    def calculate_safety_ratio(
        self,
        distance_forward_m: float,
        speed_mps: float,
        is_emergency: bool = False
    ) -> float:
        """
        Calculates ratio of available distance to required stopping distance.
        Ratio > 1.5 -> Safe / Ample room to stop
        Ratio < 1.0 -> Cannot stop in time with nominal braking
        Ratio < 0.8 -> Imminent collision without emergency intervention
        """
        if speed_mps <= 0.2:
            return 99.0  # Stationary

        req_stop = self.calculate_required_stopping_distance(speed_mps, is_emergency)
        if req_stop <= 0.1:
            return 99.0

        return distance_forward_m / req_stop

    def compute_physics_profile(
        self,
        speed_mps: float,
        distance_forward_m: float
    ) -> Dict[str, Any]:
        """
        Aggregates complete physics evaluation for risk analysis.
        """
        nom_stop = self.calculate_stopping_distance(speed_mps, is_emergency=False)
        emg_stop = self.calculate_stopping_distance(speed_mps, is_emergency=True)
        time_to_reach = self.calculate_time_to_pothole(distance_forward_m, speed_mps)
        safety_ratio = self.calculate_safety_ratio(distance_forward_m, speed_mps, is_emergency=False)

        return {
            "speed_mps": speed_mps,
            "speed_kmh": speed_mps * 3.6,
            "distance_forward_m": distance_forward_m,
            "nominal_stopping_dist_m": nom_stop,
            "emergency_stopping_dist_m": emg_stop,
            "time_to_reach_s": time_to_reach,
            "safety_ratio": safety_ratio,
            "can_stop_nominally": distance_forward_m >= nom_stop + self.safety_margin_m,
            "can_stop_emergently": distance_forward_m >= emg_stop
        }
