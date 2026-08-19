"""The Crew 2 simulation adapter package for SAFAR."""

from .config import TheCrew2Config, TheCrew2EgoPathConfig
from .capture import TheCrew2Capture, find_game_window
from .hazard import (
    ConfirmationState,
    LeadHazardResult,
    LeadHazardSelector,
    TemporalConfirmationTracker,
    TheCrew2HazardEngine,
)
from .controller import (
    BrakeState,
    ControlEvent,
    ControlState,
    TheCrew2Controller,
)

__all__ = [
    "TheCrew2Config",
    "TheCrew2EgoPathConfig",
    "TheCrew2Capture",
    "find_game_window",
    "ConfirmationState",
    "LeadHazardResult",
    "LeadHazardSelector",
    "TemporalConfirmationTracker",
    "TheCrew2HazardEngine",
    "BrakeState",
    "ControlEvent",
    "ControlState",
    "TheCrew2Controller",
]
