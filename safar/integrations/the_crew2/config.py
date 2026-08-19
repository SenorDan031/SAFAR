"""Configuration for The Crew 2 simulation adapter."""
from dataclasses import dataclass, field
from typing import Sequence, Tuple


@dataclass
class TheCrew2EgoPathConfig:
    """Ego-path calibration specific to The Crew 2 camera framing."""
    bottom_width: float = 0.70
    top_width: float = 0.16
    horizon_y: float = 0.46
    center_offset: float = 0.0


@dataclass
class TheCrew2Config:
    """Master configuration for The Crew 2 capture, perception, and control."""
    # Window capture
    window_titles: Sequence[str] = field(default_factory=lambda: ("The Crew 2", "TheCrew2", "The Crew® 2"))
    target_fps: float = 30.0
    capture_width: int = 1280
    capture_height: int = 720
    drop_stale_frames: bool = True

    # Camera & Ego path
    ego_path: TheCrew2EgoPathConfig = field(default_factory=TheCrew2EgoPathConfig)

    # YOLO Detector
    model_path: str = "yolo11n.pt"
    confidence_threshold: float = 0.28

    # Temporal Confirmation
    candidate_frames: int = 1
    confirm_frames: int = 2
    hazard_frames: int = 3
    missed_grace_frames: int = 2

    # Controller Safety & Scancodes (DirectInput)
    throttle_scancode: int = 0x11   # 'W'
    brake_scancode: int = 0x1F      # 'S'
    handbrake_scancode: int = 0x39  # Space
    max_override_duration_s: float = 3.0
    emergency_release_vk: int = 0x77  # VK_F8 (0x77)
    require_foreground_window: bool = True
    enabled: bool = False           # Defaults to dry-run / safety mode
