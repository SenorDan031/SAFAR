"""Deterministic HZ risk and decision state engine with no CARLA/YOLO imports."""

import math
from typing import Iterable, Optional

from .classifier import HazardClassifier
from .models import DecisionState, HazardDecision, HazardRiskAssessment, PerceptionObject, VehicleSnapshot
from .policy import HazardPolicy
from .tracker import HazardTracker


class HazardRiskEngine:
    """Evaluate standardized observations into explainable, non-actuating decisions."""

    _RANK = {state: rank for rank, state in enumerate(DecisionState)}

    def __init__(self, policy: Optional[HazardPolicy] = None) -> None:
        self.policy = policy or HazardPolicy()
        self.tracker = HazardTracker()
        self.classifier = HazardClassifier(self.policy)
        self._state = DecisionState.NORMAL
        self._deescalation_count = 0

    def evaluate(self, vehicle: VehicleSnapshot, observations: Optional[Iterable[PerceptionObject]]):
        """Return candidates, risk assessment, and a safe response command.

        ``None`` means perception is unavailable (FAULT); an empty iterable means
        perception is available but observed no objects (NORMAL after hysteresis).
        """
        if not math.isfinite(vehicle.speed_kmh) or vehicle.speed_kmh < 0.0:
            return (), self._fault("Vehicle speed is invalid.")
        if observations is None:
            return (), self._fault("Perception is unavailable.")

        try:
            observations = tuple(observations)
        except TypeError:
            return (), self._fault("Perception input is malformed.")
        if any(not isinstance(item, PerceptionObject) for item in observations):
            return (), self._fault("Perception input is malformed.")
        self.tracker.reset_missing(item.object_id for item in observations)
        candidates = tuple(self.classifier.classify(item, self.tracker.observe(item.object_id)) for item in observations)
        hazards = [candidate for candidate in candidates if candidate.is_hazard]
        assessment = self._assess(vehicle, hazards)
        stabilized = self._stabilize(assessment)
        return candidates, (stabilized, self._decision(stabilized))

    def evaluate_without_vehicle_state(self, observations: Optional[Iterable[PerceptionObject]]):
        """Evaluate image-only perception without inventing speed or distance.

        A persistent relevant HZ can be reported as CAUTION, but no physical
        slowdown or emergency conclusion is made without valid vehicle state.
        """
        if observations is None:
            return (), self._fault("Perception is unavailable.")
        try:
            observations = tuple(observations)
        except TypeError:
            return (), self._fault("Perception input is malformed.")
        if any(not isinstance(item, PerceptionObject) for item in observations):
            return (), self._fault("Perception input is malformed.")
        self.tracker.reset_missing(item.object_id for item in observations)
        candidates = tuple(self.classifier.classify(item, self.tracker.observe(item.object_id)) for item in observations)
        hazards = [candidate for candidate in candidates if candidate.is_hazard]
        if hazards:
            item = hazards[0].perception
            assessment = HazardRiskAssessment(
                DecisionState.CAUTION, item.object_id,
                "Persistent HZ in vehicle path; speed and distance are UNKNOWN.",
                None, None, hazards[0].persistence_frames,
            )
        else:
            assessment = HazardRiskAssessment(DecisionState.NORMAL, None, "No persistent relevant hazard.", None, None, 0)
        stabilized = self._stabilize(assessment)
        decision = self._decision(stabilized)
        if hazards:
            # A single camera view provides qualitative HZ evidence but not the
            # physical measurements needed to label a collision risk LOW/HIGH.
            decision = HazardDecision(
                stabilized.state,
                "WARN",
                stabilized.reason,
                "UNKNOWN",
            )
        return candidates, (stabilized, decision)

    def _fault(self, reason: str):
        assessment = HazardRiskAssessment(DecisionState.FAULT, None, reason, None, None, 0)
        return assessment, self._decision(assessment)

    def _assess(self, vehicle: VehicleSnapshot, hazards) -> HazardRiskAssessment:
        if not hazards:
            return HazardRiskAssessment(DecisionState.NORMAL, None, "No persistent relevant hazard.", None, None, 0)
        assessments = [self._assess_one(vehicle, candidate) for candidate in hazards]
        return max(assessments, key=lambda result: self._RANK[result.state])

    def _assess_one(self, vehicle: VehicleSnapshot, candidate) -> HazardRiskAssessment:
        item = candidate.perception
        distance = item.distance_m
        closing = item.closing_speed_kmh
        if distance is None:
            return HazardRiskAssessment(
                DecisionState.CAUTION, item.object_id,
                "Persistent HZ in vehicle path; metric distance is UNKNOWN.", None, closing,
                candidate.persistence_frames,
            )

        closing_mps = (closing or 0.0) / 3.6
        ttc_s = distance / closing_mps if closing_mps > 0.1 else None
        if ttc_s is not None and ttc_s <= self.policy.emergency_ttc_s:
            state = DecisionState.EMERGENCY_BRAKE
            reason = "Persistent HZ in path has imminent time-to-collision."
        elif vehicle.speed_kmh >= 20.0 and distance <= self.policy.awareness_distance_m(vehicle.speed_kmh) and closing_mps > 0.1:
            state = DecisionState.SLOWDOWN
            reason = "Relevant HZ is approaching within the gradual reduction range."
        elif distance <= self.policy.slowdown_distance_m(vehicle.speed_kmh) and closing_mps > 0.1:
            state = DecisionState.SLOWDOWN
            reason = "Persistent HZ in vehicle path within slowdown threshold."
        elif distance <= self.policy.awareness_distance_m(vehicle.speed_kmh):
            state = DecisionState.WARNING
            reason = "Persistent HZ in vehicle path within awareness threshold."
        else:
            state = DecisionState.CAUTION
            reason = "Persistent HZ is relevant but outside the current awareness threshold."
        return HazardRiskAssessment(state, item.object_id, reason, distance, closing, candidate.persistence_frames)

    def _stabilize(self, assessment: HazardRiskAssessment) -> HazardRiskAssessment:
        if assessment.state == DecisionState.FAULT:
            self._state = DecisionState.FAULT
            self._deescalation_count = 0
            return assessment
        if self._RANK[assessment.state] >= self._RANK[self._state]:
            self._state = assessment.state
            self._deescalation_count = 0
            return assessment
        self._deescalation_count += 1
        if self._deescalation_count < self.policy.deescalation_frames:
            return HazardRiskAssessment(self._state, assessment.hazard_id, "State held by de-escalation hysteresis.", assessment.distance_m, assessment.closing_speed_kmh, assessment.persistence_frames)
        self._state = assessment.state
        self._deescalation_count = 0
        return assessment

    @staticmethod
    def _decision(assessment: HazardRiskAssessment) -> HazardDecision:
        actions = {
            DecisionState.NORMAL: "CONTINUE", DecisionState.CAUTION: "CONTINUE",
            DecisionState.WARNING: "WARN", DecisionState.SLOWDOWN: "REDUCE_SPEED",
            DecisionState.EMERGENCY_BRAKE: "EMERGENCY_STOP", DecisionState.FAULT: "STOP",
        }
        risk_levels = {
            DecisionState.NORMAL: "SAFE", DecisionState.CAUTION: "LOW", DecisionState.WARNING: "MEDIUM",
            DecisionState.SLOWDOWN: "HIGH", DecisionState.EMERGENCY_BRAKE: "CRITICAL", DecisionState.FAULT: "FAULT",
        }
        return HazardDecision(assessment.state, actions[assessment.state], assessment.reason, risk_levels[assessment.state])
