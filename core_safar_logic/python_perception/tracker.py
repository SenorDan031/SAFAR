"""Minimal ID-based tracker for early perception integration."""

from typing import Dict, Iterable, List

from .types import Detection, TrackedObject


class Tracker:
    def __init__(self, max_missed_frames: int = 5):
        self.max_missed_frames = max_missed_frames
        self._tracks: Dict[str, TrackedObject] = {}

    def update(self, detections: Iterable[Detection]) -> List[TrackedObject]:
        observed = {detection.object_id: detection for detection in detections}
        updated = {}
        for object_id, detection in observed.items():
            previous = self._tracks.get(object_id)
            updated[object_id] = TrackedObject(object_id, detection, (previous.age_frames + 1 if previous else 1))
        for object_id, track in self._tracks.items():
            if object_id not in observed and track.missed_frames + 1 <= self.max_missed_frames:
                updated[object_id] = TrackedObject(track.track_id, track.detection, track.age_frames, track.missed_frames + 1)
        self._tracks = updated
        return list(self._tracks.values())

    def reset(self) -> None:
        self._tracks.clear()
