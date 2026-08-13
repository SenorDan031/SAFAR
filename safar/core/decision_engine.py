from .models import ActionType, Decision, RiskLevel


class DecisionEngine:
    def decide(self, assessment, current_speed_mps):
        if assessment.level == RiskLevel.CRITICAL:
            return Decision(
                ActionType.EMERGENCY_BRAKE, 0.0, 1.0, 0.0,
                assessment.reason,
            )

        if assessment.level == RiskLevel.HIGH:
            return Decision(
                ActionType.SLOWDOWN, current_speed_mps * 0.5, 0.5, 0.0,
                assessment.reason,
            )

        if assessment.level == RiskLevel.MEDIUM:
            return Decision(
                ActionType.WARN, current_speed_mps * 0.8, 0.1, 0.2,
                assessment.reason,
            )

        return Decision(
            ActionType.NONE, current_speed_mps, 0.0, 0.45,
            assessment.reason,
        )