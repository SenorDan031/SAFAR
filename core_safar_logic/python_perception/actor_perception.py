"""Translate CARLA actors into framework-neutral detections."""

from typing import Iterable, List, Optional

from .types import Detection, as_point3d


def classify_actor(type_id: str) -> Optional[str]:
    """Map CARLA actor identifiers to the labels used by SAFAR."""
    value = (type_id or "").lower()
    if value.startswith("walker.pedestrian"):
        return "pedestrian"
    if value.startswith("vehicle"):
        if any(word in value for word in ("motorcycle", "scooter", "bicycle", "bike")):
            return "two_wheeler"
        return "vehicle"
    if value.startswith("static") or value.startswith("prop"):
        return "road_hazard"
    return None


class ActorPerception:
    """Starter adapter for CARLA's actor API; no sensor model is assumed yet."""

    def detect(self, actors: Iterable[object], ego_actor: Optional[object] = None) -> List[Detection]:
        ego_location = ego_actor.get_location() if ego_actor is not None else None
        detections = []
        for actor in actors:
            if ego_actor is not None and getattr(actor, "id", None) == getattr(ego_actor, "id", None):
                continue
            label = classify_actor(getattr(actor, "type_id", ""))
            if label is None or not hasattr(actor, "get_location"):
                continue
            location = actor.get_location()
            if ego_location is not None:
                position = (location.x - ego_location.x, location.y - ego_location.y, location.z - ego_location.z)
            else:
                position = as_point3d(location)
            velocity = as_point3d(actor.get_velocity()) if hasattr(actor, "get_velocity") else (0.0, 0.0, 0.0)
            detections.append(Detection(str(actor.id), label, position, velocity, metadata={"type_id": getattr(actor, "type_id", "")}))
        return detections
