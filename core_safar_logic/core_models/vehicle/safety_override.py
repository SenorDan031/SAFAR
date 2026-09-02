"""Apply SAFAR decisions to driver input without changing the risk engines."""

from dataclasses import dataclass

from safar.core.models import ActionType

from .manual_controller import ManualControl


@dataclass(frozen=True)
class OverrideResult:
    control: ManualControl
    active: bool


class SafetyOverride:
    """Constrain manual input only when SAFAR's decision requires it."""

    def apply(self, manual_control, decision):
        if decision.action == ActionType.EMERGENCY_BRAKE:
            # KeyboardController only marks reverse after the ego has stopped.
            # Let a stopped driver back away; forward acceleration remains blocked.
            if manual_control.reverse:
                return OverrideResult(manual_control, active=False)
            return OverrideResult(
                ManualControl(
                    throttle=0.0,
                    brake=1.0,
                    steer=manual_control.steer,
                    hand_brake=manual_control.hand_brake,
                    reverse=False,
                    manual_gear_shift=False,
                    gear=1,
                ),
                active=True,
            )
        if decision.action == ActionType.SLOWDOWN:
            return OverrideResult(
                ManualControl(
                    throttle=min(manual_control.throttle, 0.2),
                    brake=max(manual_control.brake, 0.25),
                    steer=manual_control.steer,
                    hand_brake=manual_control.hand_brake,
                    reverse=manual_control.reverse,
                    manual_gear_shift=manual_control.manual_gear_shift,
                    gear=manual_control.gear,
                ),
                active=True,
            )
        return OverrideResult(manual_control, active=False)
