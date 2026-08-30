"""
SAFAR Simulator — Physics-Based Stopping-Distance Aware Predictive Threat Engine
Calculates dynamic stopping distance: d_stop = v * t_reaction + v^2 / (2 * a)
and forecasts short-horizon trajectory overlap to intervene well before physical collision limits.
"""
from dataclasses import dataclass
from typing import Tuple, Optional
import time
import math

from safar.perception.continuous_predictor import TrackedKinematicObject

@dataclass
class PredictiveAssessmentResult:
    threat_score: float        # 0.0 to 1.0
    threat_level: str          # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    decision_action: str       # "CONTINUE", "MONITOR", "WARN", "SLOWDOWN", "EMERGENCY_BRAKE"
    stopping_distance_m: float
    current_distance_m: float
    predicted_distance_m: float
    ttc_seconds: float
    safety_ratio: float
    is_in_path: bool
    reason: str


class PredictiveThreatEngine:
    def __init__(
        self,
        nominal_deceleration_mps2: float = 8.0,
        reaction_time_s: float = 0.20,
        lane_width_m: float = 3.5,
        min_hold_override_s: float = 0.40
    ):
        self.decel_mps2 = nominal_deceleration_mps2
        self.reaction_time_s = reaction_time_s
        self.half_lane_m = lane_width_m * 0.5
        self.min_hold_s = min_hold_override_s
        self.last_emergency_time_s = 0.0

    def compute_stopping_distance(self, ego_speed_kmh: float) -> float:
        """Computes stopping distance: d_stop = v * t_react + v^2 / (2 * a)"""
        v_mps = max(0.0, ego_speed_kmh / 3.6)
        d_reaction = v_mps * self.reaction_time_s
        d_braking = (v_mps * v_mps) / (2.0 * self.decel_mps2)
        return d_reaction + d_braking

    def evaluate_track(
        self,
        track: TrackedKinematicObject,
        ego_speed_kmh: float,
        lookahead_s: float = 1.2
    ) -> PredictiveAssessmentResult:
        now = time.perf_counter()
        d_stop = self.compute_stopping_distance(ego_speed_kmh)

        # 1. Kinematic Lookahead Prediction
        pred_dist, pred_lat = track.predict_future_position(lookahead_s)

        # 2. Path Relevance & Corridor Containment
        is_current_in_path = abs(track.lateral_offset_m) <= (self.half_lane_m + 0.3)
        is_pred_in_path = abs(pred_lat) <= (self.half_lane_m + 0.3)
        in_path = is_current_in_path or is_pred_in_path

        # 3. Calculate Time-to-Collision (TTC) with safety clamp
        closing_speed_mps = track.smoothed_vx_mps
        if closing_speed_mps > 0.5 and track.distance_m > 0:
            ttc_s = track.distance_m / closing_speed_mps
        else:
            ttc_s = 999.0

        # 4. Safety Margin Ratio = Current Distance / Stopping Distance
        safety_ratio = max(0.01, track.distance_m / max(3.0, d_stop))

        # Check if currently holding emergency brake hysteresis
        time_since_emergency = now - self.last_emergency_time_s
        is_holding_hysteresis = (time_since_emergency < self.min_hold_s and track.distance_m <= (1.35 * d_stop))

        # 5. Predictive Multi-Tier Decision Logic
        if not in_path and abs(track.lateral_offset_m) > (self.half_lane_m + 1.2):
            # Outside driving corridor (opposite lane or sidewalk)
            return PredictiveAssessmentResult(
                threat_score=0.00,
                threat_level="LOW",
                decision_action="CONTINUE",
                stopping_distance_m=d_stop,
                current_distance_m=track.distance_m,
                predicted_distance_m=pred_dist,
                ttc_seconds=ttc_s,
                safety_ratio=safety_ratio,
                is_in_path=False,
                reason=f"{track.class_name.upper()} #{track.track_id} outside ego path ({track.lateral_offset_m:+.1f}m lateral). Ignored."
            )

        # Imminent Critical Hazard Condition
        is_critical = in_path and (
            safety_ratio <= 1.15 or
            (ttc_s <= 2.2 and track.distance_m <= (1.40 * d_stop)) or
            track.distance_m <= 12.0 or
            is_holding_hysteresis
        )

        if is_critical:
            self.last_emergency_time_s = now
            score = min(1.0, 0.85 + max(0.0, 1.15 - safety_ratio) * 0.15)
            return PredictiveAssessmentResult(
                threat_score=score,
                threat_level="CRITICAL",
                decision_action="EMERGENCY_BRAKE",
                stopping_distance_m=d_stop,
                current_distance_m=track.distance_m,
                predicted_distance_m=pred_dist,
                ttc_seconds=ttc_s,
                safety_ratio=safety_ratio,
                is_in_path=True,
                reason=f"CRITICAL: {track.class_name.upper()} #{track.track_id} in path (Dist: {track.distance_m:.1f}m <= d_stop: {d_stop:.1f}m, TTC: {ttc_s:.1f}s). AEB engaged."
            )

        # High Threat / Active Slowdown Condition
        elif in_path and (safety_ratio <= 1.65 or ttc_s <= 4.0 or track.distance_m <= 28.0):
            return PredictiveAssessmentResult(
                threat_score=0.72,
                threat_level="HIGH",
                decision_action="SLOWDOWN",
                stopping_distance_m=d_stop,
                current_distance_m=track.distance_m,
                predicted_distance_m=pred_dist,
                ttc_seconds=ttc_s,
                safety_ratio=safety_ratio,
                is_in_path=True,
                reason=f"HIGH: {track.class_name.upper()} #{track.track_id} approaching in corridor (Dist: {track.distance_m:.1f}m, TTC: {ttc_s:.1f}s). Active slowdown."
            )

        # Medium Threat / Monitor Condition
        elif in_path or abs(track.lateral_offset_m) <= (self.half_lane_m + 0.8):
            return PredictiveAssessmentResult(
                threat_score=0.40,
                threat_level="MEDIUM",
                decision_action="WARN",
                stopping_distance_m=d_stop,
                current_distance_m=track.distance_m,
                predicted_distance_m=pred_dist,
                ttc_seconds=ttc_s,
                safety_ratio=safety_ratio,
                is_in_path=in_path,
                reason=f"MEDIUM: {track.class_name.upper()} #{track.track_id} nearby at {track.distance_m:.1f}m. Monitoring gap."
            )

        # Fallback Safe
        return PredictiveAssessmentResult(
            threat_score=0.00,
            threat_level="LOW",
            decision_action="CONTINUE",
            stopping_distance_m=d_stop,
            current_distance_m=track.distance_m,
            predicted_distance_m=pred_dist,
            ttc_seconds=ttc_s,
            safety_ratio=safety_ratio,
            is_in_path=False,
            reason="Road corridor is clear."
        )
