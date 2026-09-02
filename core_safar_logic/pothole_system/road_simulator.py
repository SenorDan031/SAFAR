"""
SAFAR Road Simulation Engine.
Simulates a vehicle traversing a sequence of road surface nodes with active pothole safety responses.
"""

from typing import List, Optional, Tuple, Dict, Any
import pandas as pd
from .classifier import PotholeClassifier
from .speed_manager import PotholeSpeedManager, PotholeActionPlan
from .config import CLASS_ID_TO_LABEL


def simulate_road(
    road: List[List[float]],
    starting_speed: float = 20.0,
    classifier: Optional[PotholeClassifier] = None,
    speed_manager: Optional[PotholeSpeedManager] = None,
    verbose: bool = True
) -> List[Dict[str, Any]]:
    """
    Simulate vehicle driving over a sequence of road surface nodes.
    
    Each element in road must contain:
    [Width, Length, Depth] or [Width, Length, Depth, Distance, LateralOffset]
    
    Returns structured log of each node's transition.
    """
    if classifier is None:
        classifier = PotholeClassifier()
    if speed_manager is None:
        speed_manager = PotholeSpeedManager()

    car_speed = starting_speed
    history = []

    if verbose:
        print("\n" + "=" * 45)
        print("       SAFAR ROAD SIMULATION")
        print("=" * 45)
        print(f"Initial Vehicle Speed: {car_speed:.1f} m/s ({car_speed * 3.6:.1f} km/h)\n")

    for node_idx, road_data in enumerate(road):
        width = road_data[0]
        length = road_data[1]
        depth = road_data[2]
        dist = road_data[3] if len(road_data) > 3 else 20.0
        lat = road_data[4] if len(road_data) > 4 else 0.0

        # Classify the road condition
        obs = classifier.classify(width=width, length=length, depth=depth, distance_forward=dist, distance_lateral=lat)
        detected_type = obs.pothole_type if obs.is_valid else 0
        detected_name = obs.pothole_name if obs.is_valid else "drivable_path"

        # Speed manager reaction
        old_speed = car_speed
        plan = speed_manager.evaluate_with_physics(
            current_speed_mps=old_speed,
            pothole_type=detected_type,
            width_m=width,
            length_m=length,
            depth_m=depth,
            distance_forward_m=dist,
            lateral_offset_m=lat
        )
        car_speed = plan.new_speed_mps

        step_info = {
            "node": node_idx,
            "width_m": width,
            "length_m": length,
            "depth_m": depth,
            "detected_type": detected_type,
            "detected_name": detected_name,
            "old_speed_mps": old_speed,
            "new_speed_mps": car_speed,
            "required_decel_mps2": plan.required_decel_mps2,
            "brake_command": plan.brake_command,
            "action": plan.action,
            "strike_location": plan.strike_location
        }
        history.append(step_info)

        if verbose:
            print(
                f"Node {node_idx}\n"
                f"  Dimensions: W={width:.3f} m, L={length:.3f} m, D={depth:.3f} m\n"
                f"  Detected:   {detected_name} (Class {detected_type})\n"
                f"  Speed:      {old_speed:.1f} -> {car_speed:.1f} m/s ({car_speed * 3.6:.1f} km/h)\n"
                f"  Brake:      {plan.brake_command * 100:.0f}% (a_req: {plan.required_decel_mps2:.1f} m/s^2)\n"
                f"  Action:     {plan.action}\n"
            )

    return history


def main():
    test_road = [
        [0.1, 0.1, 0.001],      # Normal road
        [0.20, 0.75, 0.08],     # Small pothole
        [0.20, 1.00, 0.08],     # Boundary case
        [0.65, 1.21, 0.070],    # Medium pothole
        [0.733, 1.57, 0.085],   # Medium / severe boundary
        [1.59, 2.10, 0.220],    # Crater
        [0.2, 0.0, 0.1]         # Normal road
    ]

    simulate_road(test_road, starting_speed=20.0)


if __name__ == "__main__":
    main()
