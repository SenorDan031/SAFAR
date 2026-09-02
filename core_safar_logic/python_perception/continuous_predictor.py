"""
SAFAR — Continuous Object Kinematic Predictor & Inter-Frame Tracker
Maintains high-frequency (60 Hz) dead-reckoning state estimation between perception frames (15 Hz)
with short-horizon trajectory forecasting and robust velocity smoothing.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import time
import math

@dataclass
class TrackedKinematicObject:
    track_id: str
    class_name: str
    distance_m: float
    lateral_offset_m: float
    relative_speed_kmh: float
    confidence: float
    timestamp_s: float
    last_update_s: float
    smoothed_vx_mps: float = 0.0
    smoothed_vy_mps: float = 0.0
    age_frames: int = 1
    missed_frames: int = 0
    bbox: Optional[Tuple[int, int, int, int]] = None

    def predict_future_position(self, lookahead_s: float) -> Tuple[float, float]:
        """Predicts (distance_m, lateral_offset_m) after lookahead_s seconds."""
        pred_dist = self.distance_m - (self.smoothed_vx_mps * lookahead_s)
        pred_lat = self.lateral_offset_m + (self.smoothed_vy_mps * lookahead_s)
        return pred_dist, pred_lat


class ContinuousKinematicPredictor:
    """High-frequency 60Hz kinematic predictor decoupling tracking from perception frame rate."""

    def __init__(self, max_missed_frames: int = 5, velocity_alpha: float = 0.35):
        self.tracks: Dict[str, TrackedKinematicObject] = {}
        self.max_missed_frames = max_missed_frames
        self.velocity_alpha = velocity_alpha
        self.last_step_time = time.perf_counter()

    def update_from_perception(
        self,
        detections: List[Dict[str, Any]],
        current_time_s: Optional[float] = None
    ) -> List[TrackedKinematicObject]:
        """Updates tracks with fresh visual perception detections."""
        now = current_time_s or time.perf_counter()
        seen_ids = set()

        for det in detections:
            t_id = str(det.get("track_id", det.get("id", "0")))
            seen_ids.add(t_id)

            dist_m = float(det.get("distance_m", 25.0))
            lat_m = float(det.get("lateral_offset_m", 0.0))
            rel_speed = float(det.get("relative_speed_kmh", 15.0))
            conf = float(det.get("confidence", 0.90))
            cls_name = str(det.get("class_name", "car"))
            bbox = det.get("bbox", None)

            if t_id in self.tracks:
                trk = self.tracks[t_id]
                dt = max(0.001, now - trk.last_update_s)

                # Estimate raw closing speed (positive = closing in)
                raw_vx = (trk.distance_m - dist_m) / dt
                raw_vy = (lat_m - trk.lateral_offset_m) / dt

                # Exponential Moving Average velocity smoothing
                trk.smoothed_vx_mps = (1.0 - self.velocity_alpha) * trk.smoothed_vx_mps + self.velocity_alpha * raw_vx
                trk.smoothed_vy_mps = (1.0 - self.velocity_alpha) * trk.smoothed_vy_mps + self.velocity_alpha * raw_vy

                trk.distance_m = dist_m
                trk.lateral_offset_m = lat_m
                trk.relative_speed_kmh = trk.smoothed_vx_mps * 3.6
                trk.confidence = conf
                trk.last_update_s = now
                trk.timestamp_s = now
                trk.age_frames += 1
                trk.missed_frames = 0
                trk.bbox = bbox
            else:
                vx_init = (rel_speed / 3.6)
                self.tracks[t_id] = TrackedKinematicObject(
                    track_id=t_id,
                    class_name=cls_name,
                    distance_m=dist_m,
                    lateral_offset_m=lat_m,
                    relative_speed_kmh=rel_speed,
                    confidence=conf,
                    timestamp_s=now,
                    last_update_s=now,
                    smoothed_vx_mps=vx_init,
                    smoothed_vy_mps=0.0,
                    age_frames=1,
                    missed_frames=0,
                    bbox=bbox
                )

        # Increment missed frames for unseen tracks
        for t_id, trk in list(self.tracks.items()):
            if t_id not in seen_ids:
                trk.missed_frames += 1
                if trk.missed_frames > self.max_missed_frames:
                    del self.tracks[t_id]

        return list(self.tracks.values())

    def step_dead_reckoning(self, dt: float) -> List[TrackedKinematicObject]:
        """High-frequency 60Hz step that advances positions forward between perception frames."""
        for trk in self.tracks.values():
            trk.distance_m = max(0.0, trk.distance_m - (trk.smoothed_vx_mps * dt))
            trk.lateral_offset_m += trk.smoothed_vy_mps * dt

        return list(self.tracks.values())

    def get_all_tracks(self) -> List[TrackedKinematicObject]:
        return list(self.tracks.values())
