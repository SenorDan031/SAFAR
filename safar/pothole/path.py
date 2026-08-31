"""
SAFAR Pothole Ego Corridor and Wheel Path Intersection Geometry
Tracks Left Wheel Track, Right Wheel Track, and Undercarriage Overlap.
"""

import math
from enum import Enum
from dataclasses import dataclass
from typing import Tuple, Dict, Any
from .config import VEHICLE_HALF_WIDTH_M, LANE_HALF_WIDTH_M


class PathIntersectionStatus(Enum):
    PATH_CLEAR = "PATH_CLEAR"
    POSSIBLE_INTERSECTION = "POSSIBLE_INTERSECTION"
    INTERSECTION = "INTERSECTION"
    LEFT_WHEEL_STRIKE = "LEFT_WHEEL_STRIKE"
    RIGHT_WHEEL_STRIKE = "RIGHT_WHEEL_STRIKE"
    UNDERCARRIAGE_STRIKE = "UNDERCARRIAGE_STRIKE"


@dataclass
class PotholeCorridorEvaluation:
    """
    Detailed geometric breakdown of road hazard vs vehicle wheel tracks.
    """
    status: PathIntersectionStatus
    is_directly_in_path: bool
    is_wheel_strike: bool
    strike_location: str          # "LEFT_WHEEL", "RIGHT_WHEEL", "UNDERCARRIAGE", "MARGIN", "CLEAR"
    lateral_overlap_m: float      # Metric width of overlap in meters
    lateral_offset_m: float       # Centerline offset
    pothole_span: Tuple[float, float]
    vehicle_envelope: Tuple[float, float]


class PotholePathGeometry:
    """
    Evaluates exact spatial collision geometry between pothole coordinates and vehicle chassis/wheels.
    """

    def __init__(
        self,
        vehicle_half_width_m: float = VEHICLE_HALF_WIDTH_M,
        lane_half_width_m: float = LANE_HALF_WIDTH_M,
        track_width_m: float = 1.60,
        tire_width_m: float = 0.25,
        ground_clearance_m: float = 0.16
    ):
        self.vehicle_half_width_m = vehicle_half_width_m
        self.lane_half_width_m = lane_half_width_m
        self.track_width_m = track_width_m
        self.tire_width_m = tire_width_m
        self.ground_clearance_m = ground_clearance_m

        # Tire Track Coordinates
        self.left_wheel_center = -0.5 * track_width_m   # e.g. -0.80m
        self.right_wheel_center = 0.5 * track_width_m   # e.g. +0.80m
        self.left_tire_span = (self.left_wheel_center - 0.5 * tire_width_m, self.left_wheel_center + 0.5 * tire_width_m)
        self.right_tire_span = (self.right_wheel_center - 0.5 * tire_width_m, self.right_wheel_center + 0.5 * tire_width_m)

    def evaluate_intersection(
        self,
        distance_forward_m: float,
        distance_lateral_m: float,
        pothole_width_m: float,
        pothole_depth_m: float = 0.04,
        vehicle_speed_mps: float = 10.0,
        steering_angle_rad: float = 0.0
    ) -> PotholeCorridorEvaluation:
        """
        Calculates exact wheel strike and corridor envelope intersection.
        """
        # Dynamic path curvature projection based on steering angle
        if abs(steering_angle_rad) > 0.01 and vehicle_speed_mps > 0.5:
            curve_offset = 0.5 * (vehicle_speed_mps ** 2 / 2.5) * math.tan(steering_angle_rad) * (distance_forward_m / max(1.0, vehicle_speed_mps))
            eff_lateral = distance_lateral_m - curve_offset
        else:
            eff_lateral = distance_lateral_m

        half_pw = max(0.05, pothole_width_m * 0.5)
        p_min = eff_lateral - half_pw
        p_max = eff_lateral + half_pw

        v_min = -self.vehicle_half_width_m
        v_max = self.vehicle_half_width_m

        # Calculate overlap with whole vehicle envelope
        overlap = max(0.0, min(p_max, v_max) - max(p_min, v_min))

        # Check Left Wheel Strike
        left_overlap = max(0.0, min(p_max, self.left_tire_span[1]) - max(p_min, self.left_tire_span[0]))
        right_overlap = max(0.0, min(p_max, self.right_tire_span[1]) - max(p_min, self.right_tire_span[0]))

        if left_overlap > 0.05 and right_overlap > 0.05:
            status = PathIntersectionStatus.INTERSECTION
            strike_loc = "BOTH_WHEELS"
            is_wheel = True
            is_in_path = True
        elif left_overlap > 0.05:
            status = PathIntersectionStatus.LEFT_WHEEL_STRIKE
            strike_loc = "LEFT_WHEEL"
            is_wheel = True
            is_in_path = True
        elif right_overlap > 0.05:
            status = PathIntersectionStatus.RIGHT_WHEEL_STRIKE
            strike_loc = "RIGHT_WHEEL"
            is_wheel = True
            is_in_path = True
        elif overlap > 0.10:
            status = PathIntersectionStatus.UNDERCARRIAGE_STRIKE
            strike_loc = "UNDERCARRIAGE"
            is_wheel = False
            is_in_path = True
        elif abs(eff_lateral) <= self.lane_half_width_m:
            status = PathIntersectionStatus.POSSIBLE_INTERSECTION
            strike_loc = "MARGIN"
            is_wheel = False
            is_in_path = False
        else:
            status = PathIntersectionStatus.PATH_CLEAR
            strike_loc = "CLEAR"
            is_wheel = False
            is_in_path = False

        return PotholeCorridorEvaluation(
            status=status,
            is_directly_in_path=is_in_path,
            is_wheel_strike=is_wheel,
            strike_location=strike_loc,
            lateral_overlap_m=overlap,
            lateral_offset_m=eff_lateral,
            pothole_span=(p_min, p_max),
            vehicle_envelope=(v_min, v_max)
        )
