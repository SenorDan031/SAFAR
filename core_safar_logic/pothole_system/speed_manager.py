"""
SAFAR Pothole Speed Management & Kinematics Engine.
Combines exact graduated speed policies with longitudinal physics and wheel-track geometry.
"""

import math
from dataclasses import dataclass
from typing import Tuple, Optional, Dict, Any
from .config import (
    CLASS_ID_TO_LABEL,
    VEHICLE_HALF_WIDTH_M,
    DECEL_NOMINAL_MPS2,
    DECEL_EMERGENCY_MPS2,
)


@dataclass(frozen=True)
class PotholeActionPlan:
    """Actionable recommendation emitted by the pothole speed manager."""
    hazard_class: int                  # 0: drivable_path, 1: Sml_ph, 2: Mid_ph, 3: Crater
    hazard_name: str
    target_speed_mps: float
    new_speed_mps: float
    required_decel_mps2: float
    brake_command: float               # Normalized brake authority [0.0, 1.0]
    throttle_command: float            # Normalized throttle authority [0.0, 1.0]
    action: str                        # User-facing action description
    is_wheel_strike: bool              # True if hazard intersects wheel track
    strike_location: str               # "LEFT_WHEEL", "RIGHT_WHEEL", "BOTH_WHEELS", "UNDERCARRIAGE", "CLEAR"


class PotholeSpeedManager:
    """
    Manages vehicle speed reaction to detected road surface conditions.
    Supports both discrete stepped simulation and continuous physical closed-loop ADAS control.
    """

    CLASS_NAMES = {
        0: "drivable_path",
        1: "Sml_ph",
        2: "Mid_ph",
        3: "Crater"
    }

    # Target speeds in m/s
    TARGET_SPEEDS = {
        0: None,       # Maintain driver speed
        1: 12.0,       # Smooth safe speed (~43.2 km/h)
        2: 7.0,        # Controlled crawl (~25.2 km/h)
        3: 0.0         # Full stop before impact
    }

    # Nominal braking rates in m/s^2
    BRAKING_RATES = {
        0: 0.0,
        1: 2.0,        # Smooth slowdown
        2: 4.0,        # Stronger braking
        3: 8.0         # Emergency braking
    }

    def __init__(
        self,
        track_width_m: float = 1.60,
        tire_width_m: float = 0.25,
        ground_clearance_m: float = 0.16,
        max_emergency_decel: float = 8.0
    ):
        self.track_width_m = track_width_m
        self.tire_width_m = tire_width_m
        self.ground_clearance_m = ground_clearance_m
        self.max_emergency_decel = max_emergency_decel

        # Tire track bounds (meters relative to vehicle centerline)
        half_track = track_width_m / 2.0
        half_tire = tire_width_m / 2.0
        self.left_tire_span = (-half_track - half_tire, -half_track + half_tire)
        self.right_tire_span = (half_track - half_tire, half_track + half_tire)

    def manage_speed(self, current_speed: float, pothole_type: int) -> Tuple[float, str]:
        """
        Core graduated speed policy implementation matching user specification.
        Returns: (new_speed, action_string)
        """
        if current_speed <= 0.0:
            return 0.0, "STOPPED waiting for driver to take action!!!"

        if pothole_type == 0:
            new_speed = current_speed
            action = "Allow the driver to adjust speed"

        elif pothole_type == 1:
            target_speed = self.TARGET_SPEEDS[1]  # 12.0
            braking_rate = self.BRAKING_RATES[1]  # 2.0

            if current_speed > target_speed:
                new_speed = max(target_speed, current_speed - braking_rate)
                action = "Smooth slowdown"
            else:
                new_speed = current_speed
                action = "Maintain safe speed"

        elif pothole_type == 2:
            target_speed = self.TARGET_SPEEDS[2]  # 7.0
            braking_rate = self.BRAKING_RATES[2]  # 4.0

            if current_speed > target_speed:
                new_speed = max(target_speed, current_speed - braking_rate)
                action = "Slow down / consider avoidance"
            else:
                new_speed = current_speed
                action = "Maintain low speed"

        elif pothole_type == 3:
            braking_rate = self.BRAKING_RATES[3]  # 8.0
            new_speed = max(0.0, current_speed - braking_rate)
            action = "EMERGENCY BRAKING / AVOID"

        else:
            raise ValueError(f"Unknown pothole type: {pothole_type}")

        if new_speed <= 0.0:
            return 0.0, "STOPPED waiting for driver to take action!!!"

        return new_speed, action

    def check_wheel_strike(
        self,
        width_m: float,
        depth_m: float,
        lateral_offset_m: float = 0.0
    ) -> Tuple[bool, str]:
        """
        Determines if the road hazard intersects either tire path or passes undercarriage safely.
        """
        p_left = lateral_offset_m - (width_m / 2.0)
        p_right = lateral_offset_m + (width_m / 2.0)

        hit_left = not (p_right < self.left_tire_span[0] or p_left > self.left_tire_span[1])
        hit_right = not (p_right < self.right_tire_span[0] or p_left > self.right_tire_span[1])

        if hit_left and hit_right:
            return True, "BOTH_WHEELS"
        if hit_left:
            return True, "LEFT_WHEEL"
        if hit_right:
            return True, "RIGHT_WHEEL"

        # Center-straddled hazard: check if void or mound exceeds vehicle ground clearance
        if depth_m > self.ground_clearance_m:
            return True, "UNDERCARRIAGE_STRIKE"

        return False, "CLEAR"

    def evaluate_with_physics(
        self,
        current_speed_mps: float,
        pothole_type: int,
        width_m: float,
        length_m: float,
        depth_m: float,
        distance_forward_m: Optional[float] = None,
        lateral_offset_m: float = 0.0
    ) -> PotholeActionPlan:
        """
        Full closed-loop evaluation calculating required physical deceleration,
        normalized brake/throttle commands, and wheel-strike avoidance.
        """
        hazard_name = self.CLASS_NAMES.get(pothole_type, "Unknown")
        is_strike, strike_loc = self.check_wheel_strike(width_m, depth_m, lateral_offset_m)

        # If vehicle is stopped:
        if current_speed_mps <= 0.0:
            return PotholeActionPlan(
                hazard_class=pothole_type,
                hazard_name=hazard_name,
                target_speed_mps=0.0,
                new_speed_mps=0.0,
                required_decel_mps2=0.0,
                brake_command=1.0,
                throttle_command=0.0,
                action="STOPPED waiting for driver to take action!!!",
                is_wheel_strike=is_strike,
                strike_location=strike_loc
            )

        # Clear path or straddled hazard with safe clearance:
        if pothole_type == 0 or not is_strike:
            return PotholeActionPlan(
                hazard_class=pothole_type,
                hazard_name=hazard_name,
                target_speed_mps=current_speed_mps,
                new_speed_mps=current_speed_mps,
                required_decel_mps2=0.0,
                brake_command=0.0,
                throttle_command=0.45,
                action="Allow the driver to adjust speed" if pothole_type == 0 else f"Path clear ({strike_loc})",
                is_wheel_strike=is_strike,
                strike_location=strike_loc
            )

        target_speed = self.TARGET_SPEEDS.get(pothole_type, current_speed_mps)
        if target_speed is None:
            target_speed = current_speed_mps

        # Distance-coupled deceleration: a_req = (v^2 - v_target^2) / (2 * distance)
        if distance_forward_m is not None and distance_forward_m > 0.1:
            if current_speed_mps > target_speed:
                eff_dist = max(0.5, distance_forward_m)
                req_decel = (current_speed_mps**2 - target_speed**2) / (2.0 * eff_dist)
            else:
                req_decel = 0.0
        else:
            req_decel = self.BRAKING_RATES.get(pothole_type, 0.0)

        # Normalized brake authority (0.0 to 1.0)
        norm_brake = min(1.0, max(0.0, req_decel / self.max_emergency_decel))
        norm_throttle = 0.0 if norm_brake > 0.1 else 0.45

        # Stepped new speed
        new_speed, action_text = self.manage_speed(current_speed_mps, pothole_type)

        return PotholeActionPlan(
            hazard_class=pothole_type,
            hazard_name=hazard_name,
            target_speed_mps=target_speed,
            new_speed_mps=new_speed,
            required_decel_mps2=round(req_decel, 2),
            brake_command=round(norm_brake, 2),
            throttle_command=round(norm_throttle, 2),
            action=action_text,
            is_wheel_strike=is_strike,
            strike_location=strike_loc
        )
