from .models import (
    VehicleState,
    Hazard,
    DriverState,
    Decision,
    Action,
    RiskAssessment,
)


class DecisionEngine:

    def decide(
        self,
        vehicle: VehicleState,
        hazard: Hazard,
        driver: DriverState,
        risk: RiskAssessment,
    ) -> Decision:

        current_speed = vehicle.speed_kmh

        if not hazard.in_path:
            return Decision(
                action=Action.NONE,
                target_speed_kmh=current_speed,
                brake=0.0,
                throttle=0.0,
                reason="Hazard not in vehicle path."
            )

        # Critical collision
        if risk.critical:

            return Decision(
                action=Action.EMERGENCY_BRAKE,
                target_speed_kmh=0.0,
                brake=1.0,
                throttle=0.0,
                reason="Critical collision risk."
            )

        # High risk
        if risk.score >= 0.65:

            target_speed = max(
                10.0,
                current_speed * 0.5
            )

            return Decision(
                action=Action.BRAKE,
                target_speed_kmh=target_speed,
                brake=0.45,
                throttle=0.0,
                reason="High collision risk."
            )

        # Moderate risk
        if risk.score >= 0.4:

            target_speed = max(
                20.0,
                current_speed * 0.75
            )

            return Decision(
                action=Action.SLOW_DOWN,
                target_speed_kmh=target_speed,
                brake=0.2,
                throttle=0.0,
                reason="Moderate hazard detected."
            )

        return Decision(
            action=Action.WARN,
            target_speed_kmh=current_speed,
            brake=0.0,
            throttle=0.0,
            reason="Hazard detected but intervention not required."
        )