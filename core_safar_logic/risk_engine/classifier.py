"""Hazard relevance classification separate from perception backends."""

from .models import HazardCandidate, PerceptionObject
from safar.decision.policy import HazardPolicy


class HazardClassifier:
    """Decide whether a persistent, path-relevant observation is hazardous."""

    _RELEVANT_CATEGORIES = frozenset({
        "pedestrian", "vehicle", "two_wheeler", "wall", "barrier", "blockage", "dead_end", "road_hazard",
    })

    def __init__(self, policy: HazardPolicy) -> None:
        self.policy = policy

    def classify(self, observation: PerceptionObject, persistence_frames: int) -> HazardCandidate:
        """Classify an observation without guessing missing physical measurements."""
        if observation.category not in self._RELEVANT_CATEGORIES:
            return HazardCandidate(observation, persistence_frames, False, "Object category is not obstructive.")
        if observation.confidence < self.policy.minimum_confidence:
            return HazardCandidate(observation, persistence_frames, False, "Detection confidence is below policy threshold.")
        if not observation.in_path:
            return HazardCandidate(observation, persistence_frames, False, "Object is outside the predicted vehicle path.")

        imminent = (
            observation.distance_m is not None
            and observation.distance_m <= self.policy.critical_first_seen_distance_m
            and (observation.closing_speed_kmh or 0.0) >= self.policy.critical_first_seen_closing_kmh
        )
        if persistence_frames >= self.policy.persistence_frames or imminent:
            return HazardCandidate(observation, persistence_frames, True, "Persistent relevant object in vehicle path.")
        return HazardCandidate(observation, persistence_frames, False, "Awaiting temporal persistence.")
