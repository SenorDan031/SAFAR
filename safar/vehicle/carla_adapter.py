"""Translate SAFAR vehicle commands into CARLA controls."""


def to_carla_control(command, carla_module):
    """Create a CARLA VehicleControl while keeping CARLA out of unit tests."""
    return carla_module.VehicleControl(
        throttle=command.throttle,
        brake=command.brake,
        steer=command.steer,
        hand_brake=command.hand_brake,
        reverse=command.reverse,
        manual_gear_shift=command.manual_gear_shift,
        gear=command.gear,
    )
