#This file will allow the system to make decision based on CRITICALITY of threat level!

from .models import ActionType, Decision, RiskLevel

class DecisionEngine:
    def decide(self, assessment, current_speed_mps):
        if assessment.level == RiskLevel.CRITICAL:           #This allows system to provide immediate response based on the threat level critaclity
            return Decision(
                ActionType.EMERGENCY_BRAKE, 0.0, 1.0, 0.0,   #Applies break to avoid collision upon detecting on-road threat
                assessment.reason,
            )

        if assessment.level == RiskLevel.HIGH:        #This allows system to provide fast response based on the threat level criticality
            return Decision(
                ActionType.SLOWDOWN, current_speed_mps * 0.5, 0.5, 0.0,    #Lowers the vehicle speed giving driver more space to react 
                assessment.reason,     #IF car gets close to an on-road entity, threat level switches to CRITICAL and brakes are applied!!!
            )

        if assessment.level == RiskLevel.MEDIUM:   #This alerts the driver about possible entities in vehicle trajectory on-road.
            return Decision(
                ActionType.WARN, current_speed_mps * 0.8, 0.1, 0.2,   #Flashes warning/alert message to driver.
                assessment.reason,
            )

        return Decision(                              #The system becomes passive until a possible threat is detected on-road
            ActionType.NONE, current_speed_mps, 0.0, 0.45,    #System goes to passive state still scanning for possible on-road threats
            assessment.reason,
        )
