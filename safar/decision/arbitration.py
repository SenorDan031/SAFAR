"""Multi-threat priority arbitration between dynamic obstacles and road surface hazards."""

from typing import List, Dict, Any, Optional, Union
from safar.core.models import RiskLevel, RiskAssessment, Decision, ActionType


class ThreatArbiter:
    """
    Arbitrates among dynamic obstacles (vehicles, pedestrians) and road hazards (craters, potholes)
    to produce a unified, authoritative vehicle control command.
    """

    PRIORITY = {
        RiskLevel.CRITICAL: 3,
        RiskLevel.HIGH: 2,
        RiskLevel.MEDIUM: 1,
        RiskLevel.SAFE: 0,
    }

    def arbitrate(self, assessments: List[RiskAssessment]) -> RiskAssessment:
        """Arbitrate between pure obstacle risk assessments."""
        if not assessments:
            return RiskAssessment(RiskLevel.SAFE, 0.0, "Corridor clear.")
        return max(assessments, key=lambda a: (self.PRIORITY.get(a.level, 0), a.score))

    def arbitrate_with_road_hazard(
        self,
        obstacle_decision: Decision,
        pothole_action_plan: Any
    ) -> Decision:
        """
        Unifies forward obstacle control decisions with road hazard action plans.
        Rule: Life safety (pedestrian/vehicle collision) takes precedence over road void.
              Severe craters trigger emergency stop/avoidance if obstacle path is clear.
        """
        if pothole_action_plan is None:
            return obstacle_decision

        hazard_class = getattr(pothole_action_plan, "hazard_class", 0)
        pothole_brake = getattr(pothole_action_plan, "brake_command", 0.0)
        pothole_msg = getattr(pothole_action_plan, "action", "")

        # 1. Forward collision emergency brake always dominates
        if obstacle_decision.action == ActionType.EMERGENCY_BRAKE:
            return obstacle_decision

        # 2. Severe crater triggers emergency braking
        if hazard_class == 3 and pothole_brake > 0.6:
            return Decision(
                action=ActionType.EMERGENCY_BRAKE,
                target_speed_mps=0.0,
                brake=max(obstacle_decision.brake, pothole_brake),
                throttle=0.0,
                reason=f"Pothole Hazard: {pothole_msg}"
            )

        # 3. Blended slowdown: Take highest brake demand
        effective_brake = max(obstacle_decision.brake, pothole_brake)
        effective_throttle = 0.0 if effective_brake > 0.15 else obstacle_decision.throttle

        if effective_brake > 0.0:
            chosen_reason = (
                f"Pothole Hazard: {pothole_msg}"
                if pothole_brake > obstacle_decision.brake
                else obstacle_decision.reason
            )
            return Decision(
                action=ActionType.SLOWDOWN,
                target_speed_mps=min(obstacle_decision.target_speed_mps, getattr(pothole_action_plan, "target_speed_mps", 99.0)),
                brake=effective_brake,
                throttle=effective_throttle,
                reason=chosen_reason
            )

        return obstacle_decision
