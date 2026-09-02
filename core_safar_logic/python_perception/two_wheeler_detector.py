"""Two-wheeler filtering starter component."""

from typing import Iterable, List

from .types import Detection


class TwoWheelerDetector:
    label = "two_wheeler"

    def detect(self, detections: Iterable[Detection]) -> List[Detection]:
        return [detection for detection in detections if detection.label == self.label]
