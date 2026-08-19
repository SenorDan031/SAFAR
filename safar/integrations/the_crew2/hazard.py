"""Lead hazard selection and temporal confirmation state machine for The Crew 2."""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Sequence, Tuple

from safar.hazard.models import DecisionState, HazardDecision, HazardRiskAssessment, PerceptionObject
from safar.perception.ego_path import EgoPathModel, PathLevel, PathRelevance
from safar.perception.image_tracker import ImageTrack
from safar.perception.motion import ApparentMotion, TrafficState, apparent_motion, traffic_state
from .config import TheCrew2Config


class ConfirmationState(str, Enum):
    NONE = "NONE"
    CANDIDATE = "CANDIDATE"
    CONFIRMED = "CONFIRMED"
    HAZARD = "HAZARD"
    CLEARED = "CLEARED"


@dataclass(frozen=True)
class LeadHazardResult:
    """Standardized lead hazard output matching SAFAR specifications."""
    lead_track_id: Optional[str]
    lead_class: Optional[str]
    path_relevance: str
    traffic_state: str
    apparent_motion: str
    reason: str
    confirmation_state: ConfirmationState
    risk_level: str
    decision: str
    bbox: Optional[Tuple[int, int, int, int]] = None
    persistence_frames: int = 0
    distance_m: str = "UNKNOWN"
    closing_speed_kmh: str = "UNKNOWN"
    ttc_seconds: str = "UNKNOWN"


class LeadHazardSelector:
    """Select exactly one lead hazard based on path relevance, persistence, image-space proximity, and motion."""

    @staticmethod
    def _score_track(
        track: ImageTrack,
        relevance: PathRelevance,
        motion: ApparentMotion,
        frame_width: int,
        frame_height: int,
    ) -> float:
        # 1. Path score (0.0 to 1.0, weighted heavily)
        path_weight = 40.0 * (relevance.score if relevance.in_path else relevance.score * 0.2)

        # 2. Persistence / age (capped to avoid runaway)
        age_weight = min(15.0, track.age * 3.0)

        # 3. Image space visual proximity: bottom-y (closer to ego) and box area
        bbox = track.bbox
        bottom_y_ratio = bbox[3] / max(1, frame_height)  # 0.0 at top, 1.0 at bottom
        area_ratio = ((bbox[2] - bbox[0]) * (bbox[3] - bbox[1])) / max(1, frame_width * frame_height)
        proximity_weight = bottom_y_ratio * 30.0 + min(20.0, area_ratio * 200.0)

        # 4. Apparent approach bonus
        motion_weight = 15.0 if motion == ApparentMotion.APPROACHING else (5.0 if motion == ApparentMotion.STABLE else 0.0)

        return path_weight + age_weight + proximity_weight + motion_weight

    def select(
        self,
        tracks: Sequence[ImageTrack],
        relevance_map: Dict[str, PathRelevance],
        frame_width: int,
        frame_height: int,
    ) -> Optional[Tuple[ImageTrack, PathRelevance, ApparentMotion, TrafficState]]:
        """Identify candidate objects and select the primary lead hazard."""
        valid_candidates = []
        for track in tracks:
            if track.missed > 0:
                continue
            rel = relevance_map.get(track.track_id)
            if not rel:
                continue
            # Path-relevant objects: in_path or HIGH/MEDIUM relevance
            if rel.in_path or rel.level in (PathLevel.HIGH, PathLevel.MEDIUM):
                motion = apparent_motion(track)
                traffic = traffic_state(track)
                score = self._score_track(track, rel, motion, frame_width, frame_height)
                valid_candidates.append((score, track, rel, motion, traffic))

        if not valid_candidates:
            return None

        # Sort descending by composite hazard score
        valid_candidates.sort(key=lambda item: item[0], reverse=True)
        _, best_track, best_rel, best_motion, best_traffic = valid_candidates[0]
        return best_track, best_rel, best_motion, best_traffic


class TemporalConfirmationTracker:
    """Multi-frame confirmation state machine with hysteresis to prevent single-frame flickers."""

    def __init__(self, config: Optional[TheCrew2Config] = None):
        self.config = config or TheCrew2Config()
        self.state = ConfirmationState.NONE
        self.current_lead_id: Optional[str] = None
        self.consecutive_seen: int = 0
        self.consecutive_missed: int = 0

    def update(self, lead_track_id: Optional[str]) -> Tuple[ConfirmationState, int]:
        """Update confirmation state machine for the current sampled frame."""
        if lead_track_id is not None:
            if lead_track_id == self.current_lead_id:
                self.consecutive_seen += 1
                self.consecutive_missed = 0
            else:
                # Switched to a new lead target or first detection
                self.current_lead_id = lead_track_id
                self.consecutive_seen = 1
                self.consecutive_missed = 0

            if self.consecutive_seen >= self.config.hazard_frames:
                self.state = ConfirmationState.HAZARD
            elif self.consecutive_seen >= self.config.confirm_frames:
                self.state = ConfirmationState.CONFIRMED
            else:
                self.state = ConfirmationState.CANDIDATE
        else:
            # No lead hazard detected in current frame
            if self.current_lead_id is not None:
                self.consecutive_missed += 1
                if self.consecutive_missed <= self.config.missed_grace_frames:
                    # Hold state during brief occlusion/missed frames (hysteresis)
                    pass
                elif self.consecutive_missed == self.config.missed_grace_frames + 1:
                    self.state = ConfirmationState.CLEARED
                else:
                    self.state = ConfirmationState.NONE
                    self.current_lead_id = None
                    self.consecutive_seen = 0
            else:
                self.state = ConfirmationState.NONE
                self.consecutive_seen = 0
                self.consecutive_missed = 0

        return self.state, self.consecutive_seen


class TheCrew2HazardEngine:
    """Unified pipeline connecting Lead Selection, Temporal Confirmation, and SAFAR Decision states."""

    def __init__(self, config: Optional[TheCrew2Config] = None):
        self.config = config or TheCrew2Config()
        self.selector = LeadHazardSelector()
        self.temporal_tracker = TemporalConfirmationTracker(self.config)

    def evaluate_frame(
        self,
        tracks: Sequence[ImageTrack],
        relevance_map: Dict[str, PathRelevance],
        frame_width: int,
        frame_height: int,
    ) -> LeadHazardResult:
        """Run lead selection, temporal confirmation, and evaluate risk/decision."""
        lead_candidate = self.selector.select(tracks, relevance_map, frame_width, frame_height)

        if lead_candidate is not None:
            track, rel, motion, traffic = lead_candidate
            lead_id = track.track_id
            lead_class = track.detection.class_name
            bbox = track.bbox
            rel_level = rel.level.value
            traffic_str = traffic.value
            motion_str = motion.value
        else:
            lead_id = None
            lead_class = None
            bbox = None
            rel_level = "NONE"
            traffic_str = "UNKNOWN"
            motion_str = "UNKNOWN"
            rel = None
            track = None
            motion = ApparentMotion.UNKNOWN

        conf_state, persistence = self.temporal_tracker.update(lead_id)

        # Risk and Decision state evaluation
        if conf_state == ConfirmationState.NONE or conf_state == ConfirmationState.CLEARED:
            risk_level = "SAFE"
            decision = "CONTINUE"
            reason = "No persistent path hazard in ego corridor." if conf_state == ConfirmationState.NONE else "Path hazard has cleared."
        elif conf_state == ConfirmationState.CANDIDATE:
            risk_level = "LOW"
            decision = "CAUTION"
            reason = f"Candidate {lead_class} #{lead_id} in path; awaiting temporal confirmation."
        else:  # CONFIRMED or HAZARD
            # Inspect image-space metrics for escalation
            bbox_height = (bbox[3] - bbox[1]) if bbox else 0
            bbox_y2 = bbox[3] if bbox else 0
            y2_ratio = bbox_y2 / max(1, frame_height)
            h_ratio = bbox_height / max(1, frame_height)

            is_approaching = (motion == ApparentMotion.APPROACHING)
            is_imminent = (h_ratio > 0.40 or y2_ratio > 0.85) and (is_approaching or rel_level == "HIGH")
            is_close = (h_ratio > 0.22 or y2_ratio > 0.70) or is_approaching

            if is_imminent and conf_state == ConfirmationState.HAZARD:
                risk_level = "CRITICAL"
                decision = "EMERGENCY_BRAKE"
                reason = f"Imminent {lead_class} #{lead_id} rapidly closing directly in ego path."
            elif is_close or is_approaching:
                risk_level = "HIGH"
                decision = "SLOWDOWN"
                reason = f"Persistent {lead_class} #{lead_id} approaching within ego corridor."
            else:
                risk_level = "MEDIUM"
                decision = "WARN"
                reason = f"Persistent {lead_class} #{lead_id} detected ahead in path; maintain awareness."

        return LeadHazardResult(
            lead_track_id=lead_id,
            lead_class=lead_class,
            path_relevance=rel_level,
            traffic_state=traffic_str,
            apparent_motion=motion_str,
            reason=reason,
            confirmation_state=conf_state,
            risk_level=risk_level,
            decision=decision,
            bbox=bbox,
            persistence_frames=persistence,
            distance_m="UNKNOWN",
            closing_speed_kmh="UNKNOWN",
            ttc_seconds="UNKNOWN",
        )
