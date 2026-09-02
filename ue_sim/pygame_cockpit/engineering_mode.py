"""
SAFAR Simulator — Clean Gameplay & Toggleable Engineering Mode
Ensures normal gameplay is 100% clean (no HUD clutter, no debug text, no bounding boxes),
while providing a comprehensive diagnostic overlay on demand via developer toggle (F3).
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
import time

@dataclass
class CleanCockpitState:
    speed_kmh: float = 0.0
    gear: int = 1
    engine_rpm: float = 2400.0
    is_aeb_braking: bool = False
    warning_chime_active: bool = False
    engineering_mode_active: bool = False


class EngineeringModeController:
    """Manages clean automotive presentation vs developer diagnostic overlay."""

    def __init__(self):
        self.is_engineering_mode_enabled = False

    def toggle_engineering_mode(self) -> bool:
        self.is_engineering_mode_enabled = not self.is_engineering_mode_enabled
        return self.is_engineering_mode_enabled

    @staticmethod
    def render_clean_cockpit_display(state: CleanCockpitState) -> str:
        """Clean automotive dashboard — NO giant HUD, NO AI debug spam."""
        if state.is_aeb_braking:
            alert = " ⚡ [SAFAR AEB ENGAGED] ⚡ "
        elif state.warning_chime_active:
            alert = " ⚠ [FORWARD HAZARD WARN] ⚠ "
        else:
            alert = " [SAFAR ACTIVE] "

        # Clean, discrete automotive instrument line
        return f"🚗 SPEED: {state.speed_kmh:3.0f} km/h | GEAR: {state.gear} | RPM: {state.engine_rpm:4.0f} |{alert}"

    @staticmethod
    def render_engineering_overlay(
        state: CleanCockpitState,
        stereo_detections: List[Any],
        threat_assessment: Any,
        latency_stats: Dict[str, float]
    ) -> str:
        """Full developer diagnostic view shown ONLY when Engineering Mode (F3) is toggled."""
        lines = [
            "\n" + "=" * 80,
            " 🛠️  SAFAR ENGINEERING DIAGNOSTICS OVERLAY [TOGGLE: F3] 🛠️",
            "=" * 80,
            f" [VEHICLE TELEMETRY] Speed: {state.speed_kmh:.1f} km/h | Gear: {state.gear} | Brake Override: {'LOCKED (AEB)' if state.is_aeb_braking else 'STANDBY'}",
            f" [SENSOR RIG]        Stereo Baseline B: 0.25m | Focal Length: 650px | Front Pair: ONLINE | Flank Cameras: ONLINE",
            f" [LATENCY PROFILE]   Total: {latency_stats.get('avg_total_ms', 0):.2f}ms | Perception: {latency_stats.get('avg_perception_ms', 0):.1f}ms | Decision: {latency_stats.get('avg_decision_ms', 0):.2f}ms",
            "-" * 80,
            f" [TRACKED STEREO OBJECTS: {len(stereo_detections)}]"
        ]

        for det in stereo_detections[:5]:
            lines.append(
                f"   • {det.class_name.upper():<12} #{det.track_id:<6} | Disparity: {det.disparity_px:5.1f}px | Stereo Depth Z: {det.estimated_depth_m:4.1f}m | Lat: {det.lateral_offset_m:+4.1f}m"
            )

        if threat_assessment:
            lines.extend([
                "-" * 80,
                f" [THREAT ASSESSMENT] Level: {threat_assessment.threat_level:<8} (Score: {threat_assessment.threat_score:.2f}) | Action: {threat_assessment.decision_action}",
                f" [SAFETY RATIO]      Current Dist: {threat_assessment.current_distance_m:.1f}m / Stopping Dist: {threat_assessment.stopping_distance_m:.1f}m (Ratio: {threat_assessment.safety_ratio:.2f})",
                f" [EXPLAINABILITY]    {threat_assessment.reason}"
            ])

        lines.append("=" * 80)
        return "\n".join(lines)
