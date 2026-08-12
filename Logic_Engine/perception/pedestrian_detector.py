"""Pedestrian filtering starter component."""

from typing import Iterable, List

from .types import Detection


class PedestrianDetector:
    label = "pedestrian"

    def detect(self, detections: Iterable[Detection]) -> List[Detection]:
        return [detection for detection in detections if detection.label == self.label]
