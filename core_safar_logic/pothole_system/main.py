"""
SAFAR Pothole Interactive CLI Interface
Enables standalone interactive testing and live evaluation of vehicle-pothole scenarios.
"""

import sys
from safar.pothole.classifier import PotholeClassifier
from safar.pothole.physics import PotholePhysicsEngine
from safar.pothole.path import PotholePathGeometry
from safar.pothole.risk import PotholeRiskEngine
from safar.pothole.decision import PotholeDecisionEngine


def print_banner():
    print("=" * 65)
    print("           SAFAR POTHOLE INTELLIGENCE ANALYSIS SYSTEM")
    print("=" * 65)


def run_analysis(
    vehicle_speed_mps: float,
    distance_forward_m: float,
    width_m: float,
    length_m: float,
    depth_m: float,
    lateral_offset_m: float = 0.0
):
    print_banner()

    classifier = PotholeClassifier()
    physics = PotholePhysicsEngine()
    geometry = PotholePathGeometry()
    risk_engine = PotholeRiskEngine(physics, geometry)
    decision_engine = PotholeDecisionEngine()

    # 1. Classification
    obs = classifier.classify(
        width=width_m,
        length=length_m,
        depth=depth_m,
        distance_forward=distance_forward_m,
        distance_lateral=lateral_offset_m
    )

    # 2. Risk Assessment
    risk = risk_engine.assess_risk(obs, vehicle_speed_mps=vehicle_speed_mps)

    # 3. Decision
    # Run 2 frames to simulate confirmed temporal state
    decision_engine.evaluate_decision(risk)
    decision = decision_engine.evaluate_decision(risk)

    print("\n[INPUT PARAMETERS]")
    print(f"  Vehicle Speed   : {vehicle_speed_mps:.1f} m/s ({vehicle_speed_mps*3.6:.1f} km/h)")
    print(f"  Distance Ahead  : {distance_forward_m:.1f} m")
    print(f"  Lateral Offset  : {lateral_offset_m:.2f} m")
    print(f"  Dimensions (WxLxD): {width_m:.2f}m x {length_m:.2f}m x {depth_m*100:.1f}cm")

    print("\n[SAFAR POTHOLE ANALYSIS]")
    print(f"  Classification  : {obs.pothole_name} (Class {obs.pothole_type})")
    print(f"  Confidence      : {obs.confidence*100:.1f}%")
    print(f"  Status          : {obs.status}")
    print(f"  Path Corridor   : {risk.path_intersection.value}")
    print(f"  Time to Reach   : {risk.time_to_pothole_s:.2f} s" if risk.time_to_pothole_s < 900 else "  Time to Reach   : N/A (Stationary)")
    print(f"  Stopping Dist   : {risk.stopping_distance_m:.1f} m (Safety Ratio: {risk.safety_ratio:.2f})")
    print(f"  Calculated Risk : {risk.severity.value} (Score: {risk.risk_score:.2f})")
    print(f"  Safe Rec Speed  : {risk.recommended_speed_mps:.1f} m/s ({risk.recommended_speed_mps*3.6:.1f} km/h)")

    print("\n[SAFAR DECISION & CONTROL RECOMMENDATION]")
    print(f"  State           : {decision.state.value}")
    print(f"  Intervention    : {'ACTIVE (Control Override)' if decision.has_intervention else 'PASSIVE (Player Full Control)'}")
    print(f"  Action Reason   : {decision.reason}")
    print("=" * 65)


def main():
    if len(sys.argv) >= 6:
        # CLI arguments: speed distance width length depth [lateral]
        speed = float(sys.argv[1])
        dist = float(sys.argv[2])
        w = float(sys.argv[3])
        l = float(sys.argv[4])
        d = float(sys.argv[5])
        lat = float(sys.argv[6]) if len(sys.argv) > 6 else 0.0
        run_analysis(speed, dist, w, l, d, lat)
    else:
        # Default test scenario: Approaching medium pothole at 20 m/s from 35m
        run_analysis(
            vehicle_speed_mps=20.0,
            distance_forward_m=35.0,
            width_m=0.70,
            length_m=1.40,
            depth_m=0.06,
            lateral_offset_m=0.0
        )


if __name__ == "__main__":
    main()
