"""
SAFAR Pothole Decision Engine
State machine with temporal stabilization, hysteresis, and control arbitration recommendation.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, List
from .config import (
    THREAT_CONFIRMATION_FRAMES,
    ACTIVATION_THRESHOLD,
    RELEASE_THRESHOLD,
    MIN_HOLD_DURATION_S
)
from .risk import PotholeRiskAssessment, PotholeSeverity


class PotholeAction(Enum):
    MAINTAIN = "MAINTAIN"
    MONITOR = "MONITOR"
    SLOW = "SLOW"
    BRAKE = "BRAKE"
    EMERGENCY_BRAKE = "EMERGENCY_BRAKE"
    AVOID = "AVOID"


@dataclass
class PotholeDecision:
    """
    Final decision output recommended by SAFAR for pothole mitigation.
    """
    state: PotholeAction
    has_intervention: bool         # True if SAFAR recommends active braking/speed intervention
    recommended_action: PotholeAction
    target_pothole_id: int
    target_pothole_name: str
    risk_score: float
    recommended_speed_mps: float
    time_to_pothole_s: float
    distance_forward_m: float
    confidence: float
    hold_timer_active: bool
    reason: str


class PotholeDecisionEngine:
    """
    Decides appropriate vehicular mitigation strategy based on risk assessment.
    Prevents single-frame jitter through temporal confirmation and hysteresis.
    """

    def __init__(
        self,
        confirmation_frames: int = THREAT_CONFIRMATION_FRAMES,
        activation_threshold: float = ACTIVATION_THRESHOLD,
        release_threshold: float = RELEASE_THRESHOLD,
        min_hold_duration_s: float = MIN_HOLD_DURATION_S
    ):
        self.confirmation_frames = confirmation_frames
        self.activation_threshold = activation_threshold
        self.release_threshold = release_threshold
        self.min_hold_duration_s = min_hold_duration_s

        self.current_state = PotholeAction.MAINTAIN
        self.consecutive_threat_frames = 0
        self.active_hold_timer_s = 0.0
        self.last_target_id = -1

    def reset(self):
        """Resets state machine."""
        self.current_state = PotholeAction.MAINTAIN
        self.consecutive_threat_frames = 0
        self.active_hold_timer_s = 0.0
        self.last_target_id = -1

    def evaluate_decision(
        self,
        assessment: PotholeRiskAssessment,
        delta_time_s: float = 0.016
    ) -> PotholeDecision:
        """
        Processes risk assessment and advances the decision state machine.
        """
        if self.active_hold_timer_s > 0.0:
            self.active_hold_timer_s -= delta_time_s

        # 1. Invalid or Inactive Risk Guardrail
        if not assessment.is_valid or assessment.severity == PotholeSeverity.SAFE or assessment.risk_score <= 0.05:
            # Threat gone or clear: Check if minimum hold timer has expired
            if self.active_hold_timer_s <= 0.0:
                self.current_state = PotholeAction.MAINTAIN
                self.consecutive_threat_frames = 0
                self.last_target_id = -1

            has_intervention = (self.current_state in [PotholeAction.BRAKE, PotholeAction.EMERGENCY_BRAKE])
            return PotholeDecision(
                state=self.current_state,
                has_intervention=has_intervention,
                recommended_action=self.current_state,
                target_pothole_id=assessment.pothole_id,
                target_pothole_name=assessment.pothole_name,
                risk_score=assessment.risk_score,
                recommended_speed_mps=assessment.recommended_speed_mps,
                time_to_pothole_s=assessment.time_to_pothole_s,
                distance_forward_m=assessment.distance_forward_m,
                confidence=assessment.confidence,
                hold_timer_active=self.active_hold_timer_s > 0.0,
                reason="Road surface clear or vehicle stationary. Maintaining player control."
            )

        # 2. Temporal Threat Confirmation
        is_candidate_threat = (assessment.severity in [PotholeSeverity.HIGH, PotholeSeverity.CRITICAL])
        if is_candidate_threat:
            self.consecutive_threat_frames += 1
        else:
            self.consecutive_threat_frames = 0

        is_confirmed = (self.consecutive_threat_frames >= self.confirmation_frames)

        # 3. State Machine Transitions with Hysteresis
        if assessment.severity == PotholeSeverity.CRITICAL and is_confirmed:
            self.current_state = PotholeAction.EMERGENCY_BRAKE
            self.active_hold_timer_s = self.min_hold_duration_s
            self.last_target_id = assessment.pothole_id

        elif assessment.severity == PotholeSeverity.HIGH and is_confirmed:
            if self.current_state != PotholeAction.EMERGENCY_BRAKE or self.active_hold_timer_s <= 0.0:
                self.current_state = PotholeAction.BRAKE
                self.active_hold_timer_s = self.min_hold_duration_s
                self.last_target_id = assessment.pothole_id

        elif assessment.severity == PotholeSeverity.MEDIUM:
            if self.active_hold_timer_s <= 0.0:
                self.current_state = PotholeAction.SLOW
                self.last_target_id = assessment.pothole_id

        elif assessment.severity == PotholeSeverity.LOW:
            if self.active_hold_timer_s <= 0.0:
                self.current_state = PotholeAction.MONITOR
                self.last_target_id = assessment.pothole_id

        else: # Score < Release Threshold
            if self.active_hold_timer_s <= 0.0:
                self.current_state = PotholeAction.MAINTAIN
                self.last_target_id = -1

        has_intervention = (self.current_state in [PotholeAction.BRAKE, PotholeAction.EMERGENCY_BRAKE])

        return PotholeDecision(
            state=self.current_state,
            has_intervention=has_intervention,
            recommended_action=self.current_state,
            target_pothole_id=assessment.pothole_id,
            target_pothole_name=assessment.pothole_name,
            risk_score=assessment.risk_score,
            recommended_speed_mps=assessment.recommended_speed_mps,
            time_to_pothole_s=assessment.time_to_pothole_s,
            distance_forward_m=assessment.distance_forward_m,
            confidence=assessment.confidence,
            hold_timer_active=self.active_hold_timer_s > 0.0,
            reason=assessment.reason
        )
