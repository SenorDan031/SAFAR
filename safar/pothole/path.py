"""
SAFAR Pothole Ego Path Corridor and Geometry Analysis
Determines spatial relevance and collision envelope overlap.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Tuple
from .config import EGO_CORRIDOR_HALF_WIDTH_M, PATH_LOOKAHEAD_HORIZON_S


class PathIntersectionStatus(Enum):
    PATH_CLEAR = "PATH_CLEAR"
    POSSIBLE_INTERSECTION = "POSSIBLE_INTERSECTION"
    INTERSECTION = "INTERSECTION"


@dataclass
class CorridorEvaluation:
    status: PathIntersectionStatus
    overlap_amount_m: float
    lateral_offset_m: float
    is_directly_in_path: bool
    is_relevant: bool


class PotholePathGeometry:
    """
    Evaluates geometric intersection between predicted vehicle corridor and pothole footprint.
    """

    def __init__(
        self,
        corridor_half_width_m: float = EGO_CORRIDOR_HALF_WIDTH_M,
        lookahead_horizon_s: float = PATH_LOOKAHEAD_HORIZON_S
    ):
        self.corridor_half_width_m = corridor_half_width_m
        self.lookahead_horizon_s = lookahead_horizon_s

    def evaluate_intersection(
        self,
        distance_forward_m: float,
        distance_lateral_m: float,
        pothole_width_m: float,
        vehicle_speed_mps: float,
        steering_angle_rad: float = 0.0
    ) -> CorridorEvaluation:
        """
        Determines whether the pothole footprint overlaps the vehicle's driving envelope.
        """
        # Behind the vehicle
        if distance_forward_m < -0.5:
            return CorridorEvaluation(
                status=PathIntersectionStatus.PATH_CLEAR,
                overlap_amount_m=0.0,
                lateral_offset_m=distance_lateral_m,
                is_directly_in_path=False,
                is_relevant=False
            )

        # Compute predicted lateral offset of ego center at target distance
        time_to_reach = distance_forward_m / vehicle_speed_mps if vehicle_speed_mps > 0.5 else 0.0
        predicted_ego_lat_shift = vehicle_speed_mps * time_to_reach * steering_angle_rad * 0.5

        effective_lateral_offset = distance_lateral_m - predicted_ego_lat_shift

        # Pothole lateral span [min_y, max_y]
        half_ph_width = max(0.05, pothole_width_m * 0.5)
        ph_left = effective_lateral_offset - half_ph_width
        ph_right = effective_lateral_offset + half_ph_width

        # Ego vehicle corridor span [-W_ego/2, +W_ego/2]
        ego_left = -self.corridor_half_width_m
        ego_right = self.corridor_half_width_m

        # Calculate overlap
        overlap_min = max(ph_left, ego_left)
        overlap_max = min(ph_right, ego_right)
        overlap_amount = max(0.0, overlap_max - overlap_min)

        if overlap_amount > 0.15:
            status = PathIntersectionStatus.INTERSECTION
            is_in_path = True
            is_relevant = True
        elif overlap_amount > 0.0 or abs(effective_lateral_offset) <= (self.corridor_half_width_m + half_ph_width + 0.3):
            status = PathIntersectionStatus.POSSIBLE_INTERSECTION
            is_in_path = False
            is_relevant = True
        else:
            status = PathIntersectionStatus.PATH_CLEAR
            is_in_path = False
            is_relevant = False

        return CorridorEvaluation(
            status=status,
            overlap_amount_m=overlap_amount,
            lateral_offset_m=effective_lateral_offset,
            is_directly_in_path=is_in_path,
            is_relevant=is_relevant
        )
