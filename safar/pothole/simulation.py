"""
SAFAR Pothole Simulation and Multi-Hazard Aggregator
Handles multiple concurrent potholes and deterministic hazard prioritization.
"""

from typing import List, Dict, Any, Optional, Tuple
from .classifier import PotholeClassifier, PotholeObservation
from .physics import PotholePhysicsEngine
from .path import PotholePathGeometry
from .risk import PotholeRiskEngine, PotholeRiskAssessment, PotholeSeverity
from .decision import PotholeDecisionEngine, PotholeDecision, PotholeAction


class PotholeSafetyPipeline:
    """
    Complete end-to-end pothole safety reasoning pipeline.
    Combines Classifier -> Physics -> Path -> Risk Engine -> Decision Engine.
    """

    def __init__(
        self,
        classifier: Optional[PotholeClassifier] = None,
        risk_engine: Optional[PotholeRiskEngine] = None,
        decision_engine: Optional[PotholeDecisionEngine] = None
    ):
        self.classifier = classifier or PotholeClassifier()
        self.risk_engine = risk_engine or PotholeRiskEngine()
        self.decision_engine = decision_engine or PotholeDecisionEngine()

    def process_frame(
        self,
        raw_pothole_detections: List[Dict[str, Any]],
        vehicle_speed_mps: float,
        steering_angle_rad: float = 0.0,
        delta_time_s: float = 0.016
    ) -> Tuple[PotholeDecision, List[PotholeRiskAssessment]]:
        """
        Processes a list of raw detected pothole measurements for a single frame.
        Evaluates each pothole, prioritizes the primary threat, and makes a safety decision.
        """
        assessments: List[PotholeRiskAssessment] = []

        for idx, det in enumerate(raw_pothole_detections):
            obs = self.classifier.classify(
                width=det.get("width"),
                length=det.get("length"),
                depth=det.get("depth"),
                distance_forward=det.get("distance_forward", 20.0),
                distance_lateral=det.get("distance_lateral", 0.0),
                pothole_id=det.get("id", idx + 1),
                timestamp=det.get("timestamp", 0.0)
            )

            risk_eval = self.risk_engine.assess_risk(
                observation=obs,
                vehicle_speed_mps=vehicle_speed_mps,
                steering_angle_rad=steering_angle_rad
            )
            assessments.append(risk_eval)

        # Deterministic Priority Hazard Selection:
        # Highest risk score, then lowest distance, then highest severity
        severity_order = {
            PotholeSeverity.CRITICAL: 4,
            PotholeSeverity.HIGH: 3,
            PotholeSeverity.MEDIUM: 2,
            PotholeSeverity.LOW: 1,
            PotholeSeverity.SAFE: 0
        }

        valid_assessments = [a for a in assessments if a.is_valid]
        if valid_assessments:
            primary_hazard = max(
                valid_assessments,
                key=lambda a: (severity_order.get(a.severity, 0), a.risk_score, -a.distance_forward_m)
            )
        elif assessments:
            primary_hazard = assessments[0]
        else:
            # No potholes detected in this frame -> Clean road
            dummy_obs = self.classifier.classify(width=3.0, length=5.0, depth=0.002, distance_forward=50.0, distance_lateral=0.0)
            primary_hazard = self.risk_engine.assess_risk(dummy_obs, vehicle_speed_mps=vehicle_speed_mps)

        # Advance decision state machine with primary hazard
        decision = self.decision_engine.evaluate_decision(primary_hazard, delta_time_s=delta_time_s)

        return decision, assessments
