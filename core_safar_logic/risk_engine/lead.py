"""Explainable lead-object selection for image or simulator standardized objects."""

from typing import Iterable, Optional, Any


def select_lead(candidates: Iterable[Any]) -> Optional[Any]:
    """Select the primary lead hazard candidate using proximity, persistence, and bbox area."""
    hazards = [c for c in candidates if getattr(c, "is_hazard", False)]
    if not hazards:
        return None

    def score(c):
        p = getattr(c, "perception", None)
        if p is None:
            return (0, 0, 0, 0, 0)
        area = 0
        if getattr(p, "bbox", None) and len(p.bbox) >= 4:
            area = (p.bbox[2] - p.bbox[0]) * (p.bbox[3] - p.bbox[1])
        dist = getattr(p, "distance_m", None)
        conf = getattr(p, "confidence", 0.0)
        persist = getattr(c, "persistence_frames", 0)
        return (0 if dist is None else 1, -(dist or 0), persist, area, conf)

    return max(hazards, key=score)
