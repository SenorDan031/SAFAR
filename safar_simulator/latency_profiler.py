"""
SAFAR Simulator — End-to-End Latency Instrumentation & Profiler
Tracks high-precision hardware timestamps through each stage of the perception-reasoning-actuation pipeline:
Capture (T0) -> Perception (T1) -> Tracking/Prediction (T2) -> Threat/Decision (T3) -> Actuation (T4).
"""
import time
from dataclasses import dataclass
from typing import Dict, List, Optional
import collections

@dataclass
class FrameLatencyProfile:
    t_capture: float = 0.0
    t_perception: float = 0.0
    t_tracking: float = 0.0
    t_threat: float = 0.0
    t_actuation: float = 0.0

    @property
    def perception_ms(self) -> float:
        return max(0.0, (self.t_perception - self.t_capture) * 1000.0) if (self.t_perception > 0 and self.t_capture > 0) else 0.0

    @property
    def tracking_prediction_ms(self) -> float:
        return max(0.0, (self.t_tracking - self.t_perception) * 1000.0) if (self.t_tracking > 0 and self.t_perception > 0) else 0.0

    @property
    def threat_decision_ms(self) -> float:
        return max(0.0, (self.t_threat - self.t_tracking) * 1000.0) if (self.t_threat > 0 and self.t_tracking > 0) else 0.0

    @property
    def actuation_ms(self) -> float:
        return max(0.0, (self.t_actuation - self.t_threat) * 1000.0) if (self.t_actuation > 0 and self.t_threat > 0) else 0.0

    @property
    def total_end_to_end_ms(self) -> float:
        return max(0.0, (self.t_actuation - self.t_capture) * 1000.0) if (self.t_actuation > 0 and self.t_capture > 0) else 0.0


class LatencyProfiler:
    def __init__(self, window_size: int = 60):
        self.current_profile = FrameLatencyProfile()
        self.history: collections.deque = collections.deque(maxlen=window_size)

    def mark_capture(self) -> float:
        t = time.perf_counter()
        self.current_profile = FrameLatencyProfile(t_capture=t)
        return t

    def mark_perception(self) -> float:
        t = time.perf_counter()
        self.current_profile.t_perception = t
        return t

    def mark_tracking(self) -> float:
        t = time.perf_counter()
        self.current_profile.t_tracking = t
        return t

    def mark_threat_decision(self) -> float:
        t = time.perf_counter()
        self.current_profile.t_threat = t
        return t

    def mark_actuation(self) -> float:
        t = time.perf_counter()
        self.current_profile.t_actuation = t
        self.history.append(self.current_profile)
        return t

    def get_average_latency_ms(self) -> float:
        if not self.history:
            return 0.0
        return sum(p.total_end_to_end_ms for p in self.history) / len(self.history)

    def get_stats_summary(self) -> Dict[str, float]:
        if not self.history:
            return {
                "avg_perception_ms": 0.0,
                "avg_tracking_ms": 0.0,
                "avg_decision_ms": 0.0,
                "avg_actuation_ms": 0.0,
                "avg_total_ms": 0.0,
                "max_total_ms": 0.0
            }
        return {
            "avg_perception_ms": sum(p.perception_ms for p in self.history) / len(self.history),
            "avg_tracking_ms": sum(p.tracking_prediction_ms for p in self.history) / len(self.history),
            "avg_decision_ms": sum(p.threat_decision_ms for p in self.history) / len(self.history),
            "avg_actuation_ms": sum(p.actuation_ms for p in self.history) / len(self.history),
            "avg_total_ms": sum(p.total_end_to_end_ms for p in self.history) / len(self.history),
            "max_total_ms": max(p.total_end_to_end_ms for p in self.history)
        }
