"""
SAFAR Temporal Pothole Tracking Engine
Maintains persistent track IDs across frames, smooths spatial coordinates, and tracks approach kinematics.
"""

import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from .classifier import PotholeObservation


@dataclass
class TrackedPothole:
    """
    State of a persistently tracked pothole across video/sensor frames.
    """
    track_id: int
    pothole_type: int
    pothole_name: str
    confidence: float
    distance_forward: float        # Smoothed longitudinal distance in meters
    distance_lateral: float        # Smoothed lateral offset in meters
    width: float
    length: float
    depth: float
    hit_streak: int = 1
    age_frames: int = 1
    missing_frames: int = 0
    is_confirmed: bool = False     # Confirmed after >= min_hits frames
    first_seen_timestamp: float = 0.0
    last_seen_timestamp: float = 0.0


class PotholeTemporalTracker:
    """
    Associates pothole detections across consecutive frames using spatial distance gating and moving average smoothing.
    """

    def __init__(
        self,
        min_hits_to_confirm: int = 2,
        max_missing_frames: int = 4,
        association_distance_threshold_m: float = 3.5,
        smoothing_alpha: float = 0.65
    ):
        self.min_hits_to_confirm = min_hits_to_confirm
        self.max_missing_frames = max_missing_frames
        self.association_threshold_m = association_distance_threshold_m
        self.smoothing_alpha = smoothing_alpha

        self.next_track_id = 1
        self.tracks: List[TrackedPothole] = []

    def reset(self):
        """Resets tracker state."""
        self.tracks.clear()
        self.next_track_id = 1

    def update(
        self,
        observations: List[PotholeObservation],
        vehicle_speed_mps: float = 0.0,
        delta_time_s: float = 0.033,
        current_timestamp: float = 0.0
    ) -> List[TrackedPothole]:
        """
        Updates active tracks with new frame observations.
        1. Predicts track positions forward using vehicle ego speed.
        2. Associates observations with existing tracks.
        3. Updates smoothed coordinates and confirms persistent hazards.
        4. Initializes new tracks and prunes dead tracks.
        """
        # 1. Kinematic Prediction Step (Pothole approaches vehicle at ego speed)
        for track in self.tracks:
            track.distance_forward -= (vehicle_speed_mps * delta_time_s)
            track.age_frames += 1

        # 2. Distance Matrix Calculation
        matched_track_indices = set()
        matched_obs_indices = set()

        matches = []
        for o_idx, obs in enumerate(observations):
            if not obs.is_valid:
                continue
            for t_idx, track in enumerate(self.tracks):
                if t_idx in matched_track_indices:
                    continue
                # Spatial distance between predicted track and new observation
                dist_error = math.sqrt(
                    (obs.distance_forward - track.distance_forward) ** 2 +
                    (obs.distance_lateral - track.distance_lateral) ** 2
                )
                if dist_error <= self.association_threshold_m:
                    matches.append((dist_error, o_idx, t_idx))

        # Sort matches by lowest spatial error (Greedy nearest-neighbor association)
        matches.sort(key=lambda m: m[0])

        for dist_err, o_idx, t_idx in matches:
            if o_idx in matched_obs_indices or t_idx in matched_track_indices:
                continue

            # Update matched track with exponential moving average
            obs = observations[o_idx]
            track = self.tracks[t_idx]
            alpha = self.smoothing_alpha

            track.distance_forward = alpha * obs.distance_forward + (1 - alpha) * track.distance_forward
            track.distance_lateral = alpha * obs.distance_lateral + (1 - alpha) * track.distance_lateral
            track.width = alpha * obs.width + (1 - alpha) * track.width
            track.length = alpha * obs.length + (1 - alpha) * track.length
            track.depth = alpha * obs.depth + (1 - alpha) * track.depth
            track.confidence = max(track.confidence, obs.confidence)
            track.pothole_type = obs.pothole_type
            track.pothole_name = obs.pothole_name
            track.hit_streak += 1
            track.missing_frames = 0
            track.last_seen_timestamp = current_timestamp

            if track.hit_streak >= self.min_hits_to_confirm:
                track.is_confirmed = True

            matched_obs_indices.add(o_idx)
            matched_track_indices.add(t_idx)

        # 3. Handle Unmatched Tracks
        for t_idx, track in enumerate(self.tracks):
            if t_idx not in matched_track_indices:
                track.missing_frames += 1
                track.hit_streak = max(0, track.hit_streak - 1)

        # 4. Handle Unmatched Observations -> Spawn New Tracks
        for o_idx, obs in enumerate(observations):
            if o_idx not in matched_obs_indices and obs.is_valid and obs.pothole_type > 0:
                new_track = TrackedPothole(
                    track_id=self.next_track_id,
                    pothole_type=obs.pothole_type,
                    pothole_name=obs.pothole_name,
                    confidence=obs.confidence,
                    distance_forward=obs.distance_forward,
                    distance_lateral=obs.distance_lateral,
                    width=obs.width,
                    length=obs.length,
                    depth=obs.depth,
                    hit_streak=1,
                    age_frames=1,
                    missing_frames=0,
                    is_confirmed=(self.min_hits_to_confirm <= 1),
                    first_seen_timestamp=current_timestamp,
                    last_seen_timestamp=current_timestamp
                )
                self.next_track_id += 1
                self.tracks.append(new_track)

        # 5. Prune Tracks (passed behind vehicle or missing too long)
        self.tracks = [
            t for t in self.tracks
            if t.distance_forward > -1.5 and t.missing_frames <= self.max_missing_frames
        ]

        return self.tracks
