"""Unified SAFAR Risk Engine combining dynamic stopping distance, TTC, and multi-threat assessment."""

import math
from typing import Iterable, Optional, Tuple, Any

from safar.core.models import RiskAssessment, RiskLevel
from safar.decision.policy import HazardPolicy
from .models import DecisionState, HazardDecision, HazardRiskAssessment, PerceptionObject, VehicleSnapshot
from .tracker import HazardTracker
from .classifier import HazardClassifier
from .ttc import calculate_ttc_s
from .lead import select_lead


def calculate_stopping_distance_m(speed_mps: float, reaction_time_s: float = 1.0, max_decel_mps2: float = 6.5) -> float:
    """Calculate physics-based stopping distance d_stop = v * t_react + v^2 / (2 * a)."""
    v = max(0.0, speed_mps)
    return (v * reaction_time_s) + ((v * v) / (2.0 * max_decel_mps2))


class RiskEngine:
    """Core geometric and kinematic risk assessment."""

    def __init__(self, reaction_time_s: float = 1.0, nominal_decel_mps2: float = 6.5) -> None:
        self.reaction_time_s = reaction_time_s
        self.nominal_decel_mps2 = nominal_decel_mps2

    def calculate_stopping_distance(self, speed_mps: float) -> float:
        return calculate_stopping_distance_m(speed_mps, self.reaction_time_s, self.nominal_decel_mps2)

    def assess(self, vehicle, obstacle) -> RiskAssessment:
        if not getattr(obstacle, "in_path", False):
            return RiskAssessment(
                RiskLevel.SAFE, 0.0, "Obstacle is outside the ego lane."
            )

        rel_speed = getattr(obstacle, "relative_speed_mps", 0.0)
        dist = getattr(obstacle, "distance_m", 0.0)

        if rel_speed <= 0:
            return RiskAssessment(
                RiskLevel.SAFE, 0.0, "Obstacle is not closing."
            )

        ttc = dist / rel_speed if rel_speed > 0 else float("inf")

        if ttc <= 1.5 or dist <= 6.0:
            return RiskAssessment(
                RiskLevel.CRITICAL, 1.0, "Immediate collision risk."
            )

        if ttc <= 2.5:
            return RiskAssessment(
                RiskLevel.HIGH, 0.8, "High collision risk."
            )

        if ttc <= 4.0:
            return RiskAssessment(
                RiskLevel.MEDIUM, 0.5, "Developing forward hazard."
            )

        return RiskAssessment(
            RiskLevel.SAFE, 0.0, "Following distance is acceptable."
        )


class HazardRiskEngine:
    """Evaluate standardized multi-candidate observations into explainable decisions."""

    _RANK = {state: rank for rank, state in enumerate(DecisionState)}

    def __init__(self, policy: Optional[HazardPolicy] = None) -> None:
        self.policy = policy or HazardPolicy()
        self.tracker = HazardTracker()
        self.classifier = HazardClassifier(self.policy)
        self._state = DecisionState.NORMAL
        self._deescalation_count = 0

    def evaluate(self, vehicle: VehicleSnapshot, observations: Optional[Iterable[PerceptionObject]]):
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
