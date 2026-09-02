"""Temporal persistence tracker for hazardous-object candidates."""

from typing import Dict, Iterable


class HazardTracker:
    """Counts consecutive appearances by stable perception-object identifier."""

    def __init__(self) -> None:
        self._frames: Dict[str, int] = {}

    def observe(self, object_id: str) -> int:
        """Record one visible tick and return its consecutive appearance count."""
        self._frames[object_id] = self._frames.get(object_id, 0) + 1
        return self._frames[object_id]

    def reset_missing(self, visible_ids: Iterable[str]) -> None:
        """Discard tracks that did not appear in the current complete perception tick."""
        visible = set(visible_ids)
        self._frames = {object_id: count for object_id, count in self._frames.items() if object_id in visible}
