"""Small IoU tracker for image detections; replaceable by a production tracker later."""
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Sequence, Tuple


def _iou(a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    left, top, right, bottom = max(ax1, bx1), max(ay1, by1), min(ax2, bx2), min(ay2, by2)
    inter = max(0, right - left) * max(0, bottom - top)
    union = max(1, (ax2 - ax1) * (ay2 - ay1) + (bx2 - bx1) * (by2 - by1) - inter)
    return inter / union


@dataclass
class ImageTrack:
    track_id: str
    detection: object
    age: int = 1
    missed: int = 0
    history: List[object] = field(default_factory=list)

    @property
    def bbox(self) -> Tuple[int, int, int, int]:
        return self.detection.bbox


class ImageTracker:
    def __init__(self, min_iou: float = 0.3, max_missed: int = 5, max_history: int = 10):
        self.min_iou = min_iou
        self.max_missed = max_missed
        self.max_history = max_history
        self._next = 1
        self._tracks: Dict[str, ImageTrack] = {}

    def update(self, detections: Iterable[object]) -> List[ImageTrack]:
        remaining = list(detections)
        updated: Dict[str, ImageTrack] = {}
        for track in self._tracks.values():
            matches = [
                d for d in remaining
                if getattr(d, "class_name", None) == getattr(track.detection, "class_name", None)
                and _iou(track.bbox, d.bbox) >= self.min_iou
            ]
            if matches:
                best = max(matches, key=lambda d: _iou(track.bbox, d.bbox))
                remaining.remove(best)
                new_history = (track.history[-self.max_history + 1:] if track.history else [track.detection]) + [best]
                updated[track.track_id] = ImageTrack(
                    track_id=track.track_id,
                    detection=best,
                    age=track.age + 1,
                    missed=0,
                    history=new_history,
                )
            elif track.missed + 1 <= self.max_missed:
                updated[track.track_id] = ImageTrack(
                    track_id=track.track_id,
                    detection=track.detection,
                    age=track.age,
                    missed=track.missed + 1,
                    history=list(track.history),
                )
        for detection in remaining:
            identifier = f"image-{self._next}"
            self._next += 1
            updated[identifier] = ImageTrack(
                track_id=identifier,
                detection=detection,
                age=1,
                missed=0,
                history=[detection],
            )
        self._tracks = updated
        return list(updated.values())
