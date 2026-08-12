"""CARLA-facing orchestration for Logic_Engine's Phase 2 perception starters."""

import time
from typing import Optional

from .actor_perception import ActorPerception
from .tracker import Tracker
from .types import PerceptionFrame


class CarlaPerception:
    def __init__(self, actor_perception: Optional[ActorPerception] = None, tracker: Optional[Tracker] = None):
        self.actor_perception = actor_perception or ActorPerception()
        self.tracker = tracker or Tracker()

    def perceive(self, world: object, ego_actor: object, timestamp_s: Optional[float] = None) -> PerceptionFrame:
        """Read world actors and return detections plus persistent tracks."""
        detections = tuple(self.actor_perception.detect(world.get_actors(), ego_actor))
        tracks = tuple(self.tracker.update(detections))
        return PerceptionFrame(timestamp_s if timestamp_s is not None else time.time(), detections, tracks)
