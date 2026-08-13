from .models import RiskAssessment, RiskLevel


class RiskEngine:
    def assess(self, vehicle, obstacle):
        if not obstacle.in_path:
            return RiskAssessment(
                RiskLevel.SAFE, 0.0, "Obstacle is outside the ego lane."
            )

        if obstacle.relative_speed_mps <= 0:
            return RiskAssessment(
                RiskLevel.SAFE, 0.0, "Obstacle is not closing."
            )

        ttc = obstacle.distance_m / obstacle.relative_speed_mps

        if ttc <= 1.5 or obstacle.distance_m <= 6.0:
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
        )& "C:\Users\shrey\SAFAR\SAFAR\.venv-carla37\Scripts\python.exe" -m pytest safar\tests -q