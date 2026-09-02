from ..core.models import Decision


class VehicleController:

    def convert(self, decision: Decision) -> dict:

        return {
            "throttle": decision.throttle,
            "brake": decision.brake,
            "target_speed_kmh": decision.target_speed_kmh,
            "action": decision.action.value,
        }