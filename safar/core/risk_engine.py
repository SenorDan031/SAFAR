#This code file allows the system to assess the risk and return the type of risk detcted

from .models import RiskAssessment, RiskLevel


class RiskEngine:   
    def assess(self, vehicle, obstacle):   #After retrieving the essential parameters, risk analysis becomes active
        if not obstacle.in_path:
            return RiskAssessment(
                RiskLevel.SAFE, 0.0, "Obstacle is outside the ego lane."    #Threat level and the cause of the level
            )

        if obstacle.relative_speed_mps <= 0:
            return RiskAssessment(
                RiskLevel.SAFE, 0.0, "Obstacle is not closing."
            )

        ttc = obstacle.distance_m / obstacle.relative_speed_mps

        if ttc <= 1.5 or obstacle.distance_m <= 6.0:
            return RiskAssessment(
                RiskLevel.CRITICAL, 1.0, "Immediate collision risk."      #Cause of Critical threat levels.
            )

        if ttc <= 2.5:
            return RiskAssessment(
                RiskLevel.HIGH, 0.8, "High collision risk."    #Cause of High Threat levels.
            )

        if ttc <= 4.0:
            return RiskAssessment(
                RiskLevel.MEDIUM, 0.5, "Developing forward hazard."  #Cause of Medium threat levels.
            )

        return RiskAssessment(
            RiskLevel.SAFE, 0.0, "Following distance is acceptable."     
        )& "C:\Users\shrey\SAFAR\SAFAR\.venv-carla37\Scripts\python.exe" -m pytest safar\tests -q
