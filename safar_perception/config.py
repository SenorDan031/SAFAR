"""
SAFAR Perception Configuration
"""
from dataclasses import dataclass, field
from typing import List

@dataclass
class PerceptionConfig:
    mode: str = "real"                # "real" (YOLO11) or "mock" (Synthetic)
    model_path: str = "yolo11n.pt"    # YOLO weights
    confidence_threshold: float = 0.28
    cpp_core_host: str = "127.0.0.1"
    cpp_core_port: int = 9002
    ue5_sensor_port: int = 9001
    target_fps: float = 30.0
    active_cameras: List[int] = field(default_factory=lambda: [0])  # 0=Front, 1=Left, 2=Right
