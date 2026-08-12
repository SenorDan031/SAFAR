from safar.core.models import ActionType, Decision
from safar.vehicle.manual_controller import ManualControl
from safar.vehicle.safety_override import SafetyOverride


def decision(action):
    return Decision(action, 0.0, 1.0, 0.0, "test")


def test_manual_control_has_valid_values():
    control = ManualControl(throttle=0.7, brake=0.0, steer=-0.5)
    assert 0.0 <= control.throttle <= 1.0
    assert 0.0 <= control.brake <= 1.0
    assert -1.0 <= control.steer <= 1.0


def test_safe_keeps_manual_control():
    manual = ManualControl(throttle=0.7, steer=0.5)
    result = SafetyOverride().apply(manual, decision(ActionType.NONE))
    assert result.control == manual
    assert not result.active


def test_medium_does_not_emergency_brake():
    manual = ManualControl(throttle=0.7)
    result = SafetyOverride().apply(manual, decision(ActionType.WARN))
    assert result.control == manual
    assert result.control.brake == 0.0


def test_high_slows_driver_command():
    result = SafetyOverride().apply(ManualControl(throttle=0.7, steer=-0.5), decision(ActionType.SLOWDOWN))
    assert result.active
    assert result.control.throttle == 0.2
    assert result.control.brake == 0.25
    assert result.control.steer == -0.5


def test_critical_overrides_acceleration():
    result = SafetyOverride().apply(ManualControl(throttle=0.7, steer=0.5), decision(ActionType.EMERGENCY_BRAKE))
    assert result.active
    assert result.control.throttle == 0.0
    assert result.control.brake == 1.0
    assert result.control.steer == 0.5


def test_control_returns_after_critical_clears():
    safety = SafetyOverride()
    manual = ManualControl(throttle=0.7)
    assert safety.apply(manual, decision(ActionType.EMERGENCY_BRAKE)).active
    restored = safety.apply(manual, decision(ActionType.NONE))
    assert restored.control == manual
    assert not restored.active
