"""The Crew 2 simulation adapter CLI for SAFAR."""
import argparse
import csv
import sys
import time
from pathlib import Path
from typing import Optional, Sequence

import cv2
import numpy as np

from safar.integrations.the_crew2 import (
    ConfirmationState,
    TheCrew2Capture,
    TheCrew2Config,
    TheCrew2Controller,
    TheCrew2EgoPathConfig,
    TheCrew2HazardEngine,
)
from safar.perception.ego_path import EgoPathModel
from safar.perception.image_tracker import ImageTracker
from safar.perception.motion import apparent_motion, traffic_state
from safar.perception.yolo_adapter import YOLOPerceptionAdapter
from safar.perception.yolo_detector import YOLODetector


def _draw_ego_corridor(frame: np.ndarray, ego_path: EgoPathModel) -> None:
    """Draw a visual overlay of the ego driving corridor."""
    h, w = frame.shape[:2]
    left_top, right_top = ego_path._bounds(ego_path.horizon_y)
    left_bot, right_bot = ego_path._bounds(1.0)

    pts = np.array([
        [int(left_bot * w), h],
        [int(left_top * w), int(ego_path.horizon_y * h)],
        [int(right_top * w), int(ego_path.horizon_y * h)],
        [int(right_bot * w), h],
    ], np.int32)

    overlay = frame.copy()
    cv2.fillPoly(overlay, [pts], (0, 180, 0))
    cv2.addWeighted(overlay, 0.15, frame, 0.85, 0, frame)
    cv2.polylines(frame, [pts], isClosed=True, color=(0, 255, 0), thickness=2)


def _draw_overlay(
    frame: np.ndarray,
    tracks: Sequence[object],
    relevance_map: dict,
    lead_result: object,
    ctrl_event: object,
    capture_fps: float,
    infer_fps: float,
    e2e_ms: float,
    is_control_enabled: bool,
) -> None:
    """Render comprehensive HUD on the preview frame."""
    h, w = frame.shape[:2]

    # Draw tracks
    for track in tracks:
        if track.missed > 0:
            continue
        bbox = track.bbox
        track_id = track.track_id
        is_lead = (lead_result.lead_track_id == track_id)

        rel = relevance_map.get(track_id)
        rel_str = rel.level.value if rel else "NONE"
        traffic_str = traffic_state(track).value
        motion_str = apparent_motion(track).value

        # Color: Red if lead hazard, Yellow if in path, Green if other
        if is_lead and lead_result.confirmation_state in (ConfirmationState.CONFIRMED, ConfirmationState.HAZARD):
            color = (0, 0, 255) if lead_result.risk_level in ("HIGH", "CRITICAL") else (0, 165, 255)
            thickness = 3
        elif rel and rel.in_path:
            color = (0, 220, 255)
            thickness = 2
        else:
            color = (0, 200, 0)
            thickness = 1

        cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, thickness)
        label = f"#{track_id} {track.detection.class_name} {track.detection.confidence:.2f}"
        cv2.putText(frame, label, (bbox[0], max(18, bbox[1] - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.50, color, 2)
        sub_label = f"P:{rel_str} | T:{traffic_str} | M:{motion_str}"
        cv2.putText(frame, sub_label, (bbox[0], min(h - 6, bbox[3] + 16)), cv2.FONT_HERSHEY_SIMPLEX, 0.40, color, 1)

    # Top-left HUD card
    hud_bg = frame[10:190, 10:480]
    dark_overlay = np.zeros_like(hud_bg)
    cv2.addWeighted(dark_overlay, 0.70, hud_bg, 0.30, 0, hud_bg)

    lead_text = f"LEAD: #{lead_result.lead_track_id or 'NONE'} {lead_result.lead_class or ''} [{lead_result.confirmation_state.value}]"
    path_text = f"PATH: {lead_result.path_relevance} | MOTION: {lead_result.apparent_motion}"
    risk_text = f"HZ: {'YES' if lead_result.lead_track_id else 'NO'} | RISK: {lead_result.risk_level} | DECISION: {lead_result.decision}"
    dist_text = f"DIST: {lead_result.distance_m} | CLOSING: {lead_result.closing_speed_kmh} | TTC: {lead_result.ttc_seconds}"
    ctrl_mode = "ACTIVE" if is_control_enabled else "DRY-RUN"
    ctrl_text = f"CTRL [{ctrl_mode}]: {ctrl_event.state.value} | BRAKE: {ctrl_event.brake_state.value}"
    perf_text = f"Cap FPS: {capture_fps:4.1f} | YOLO FPS: {infer_fps:4.1f} | Latency: {e2e_ms:4.1f}ms"

    # Color decision
    dec_color = (0, 255, 0)
    if lead_result.decision in ("SLOWDOWN", "EMERGENCY_BRAKE") or lead_result.risk_level in ("HIGH", "CRITICAL"):
        dec_color = (0, 0, 255)
    elif lead_result.decision in ("WARN", "CAUTION") or lead_result.risk_level == "MEDIUM":
        dec_color = (0, 220, 255)

    cv2.putText(frame, lead_text, (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 2)
    cv2.putText(frame, path_text, (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (200, 200, 200), 1)
    cv2.putText(frame, risk_text, (20, 88), cv2.FONT_HERSHEY_SIMPLEX, 0.52, dec_color, 2)
    cv2.putText(frame, dist_text, (20, 112), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)
    cv2.putText(frame, ctrl_text, (20, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 255, 255) if ctrl_event.is_overriding else (180, 255, 180), 2)
    cv2.putText(frame, perf_text, (20, 168), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (100, 255, 100), 1)

    # Top-right emergency banner if overriding
    if ctrl_event.is_overriding:
        cv2.rectangle(frame, (w - 320, 15), (w - 20, 65), (0, 0, 220), -1)
        cv2.putText(frame, "SAFAR OVERRIDE ACTIVE", (w - 305, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)


def main() -> None:
    parser = argparse.ArgumentParser(description="The Crew 2 simulation adapter for SAFAR")
    parser.add_argument("--window-title", default="The Crew 2", help="Window title of The Crew 2")
    parser.add_argument("--video", default=None, help="Optional video file for offline replay")
    parser.add_argument("--model", default="yolo11n.pt", help="YOLO model path")
    parser.add_argument("--confidence", type=float, default=0.28, help="YOLO confidence threshold")
    parser.add_argument("--sample-fps", type=float, default=30.0, help="Target processing FPS")
    parser.add_argument("--enable-control", action="store_true", help="Enable actual keyboard input simulation")
    parser.add_argument("--max-frames", type=int, default=0, help="Exit after N frames (0 for continuous)")
    parser.add_argument("--headless", action="store_true", help="Run without OpenCV GUI window")
    parser.add_argument("--output-csv", default="logs/the_crew2_safar_log.csv", help="CSV log path")
    parser.add_argument("--summary-interval", type=float, default=2.0, help="Console summary interval in seconds")
    parser.add_argument("--horizon-y", type=float, default=0.46, help="Ego path horizon ratio (0.0 to 1.0)")
    parser.add_argument("--bottom-width", type=float, default=0.70, help="Ego path bottom width ratio")
    parser.add_argument("--top-width", type=float, default=0.16, help="Ego path top width ratio")
    args = parser.parse_args()

    # Build configuration
    config = TheCrew2Config(
        window_titles=(args.window_title, "TheCrew2", "The Crew® 2"),
        model_path=args.model,
        confidence_threshold=args.confidence,
        target_fps=args.sample_fps,
        enabled=args.enable_control,
        ego_path=TheCrew2EgoPathConfig(
            horizon_y=args.horizon_y,
            bottom_width=args.bottom_width,
            top_width=args.top_width,
        ),
    )

    print("=" * 70)
    print("SAFAR × THE CREW 2 SIMULATION ADAPTER")
    print("=" * 70)
    print(f"Perception Model: {args.model} (conf: {args.confidence})")
    print(f"Input Source:     {'Video: ' + args.video if args.video else 'Screen Window: ' + args.window_title}")
    print(f"Control Mode:     {'ENABLED (Simulating Keystrokes)' if args.enable_control else 'DRY-RUN / SAFETY MODE (Inputs Disabled)'}")
    print(f"Ego Path Config:  horizon_y={args.horizon_y:.2f}, bottom_w={args.bottom_width:.2f}, top_w={args.top_width:.2f}")
    print("Emergency Key:    F8 (Manual Instant Release)")
    print("=" * 70)

    # Initialize components
    detector = YOLODetector(config.model_path, config.confidence_threshold)
    adapter = YOLOPerceptionAdapter()
    tracker = ImageTracker()
    ego_path = EgoPathModel(
        bottom_width=config.ego_path.bottom_width,
        top_width=config.ego_path.top_width,
        horizon_y=config.ego_path.horizon_y,
        center_offset=config.ego_path.center_offset,
    )
    hazard_engine = TheCrew2HazardEngine(config)

    # Video or screen capture
    video_cap = None
    capture = None
    if args.video:
        video_path = Path(args.video)
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")
        video_cap = cv2.VideoCapture(str(video_path))
        is_foreground_fn = lambda: True
    else:
        capture = TheCrew2Capture(config)
        capture.locate_window()
        capture.start_async()
        is_foreground_fn = capture.is_foreground

    controller = TheCrew2Controller(config, is_foreground_check=is_foreground_fn)

    # Logging setup
    csv_path = Path(args.output_csv)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    csv_file = csv_path.open("w", newline="", encoding="utf-8")
    csv_fields = [
        "timestamp_s", "frame_index", "lead_track_id", "lead_class",
        "path_relevance", "traffic_state", "apparent_motion", "hz_present",
        "confirmation_state", "risk_level", "decision", "control_state",
        "brake_state", "reason", "distance_m", "closing_speed_kmh", "ttc_seconds",
    ]
    csv_writer = csv.DictWriter(csv_file, fieldnames=csv_fields)
    csv_writer.writeheader()

    frame_index = 0
    start_time = time.perf_counter()
    last_summary = time.perf_counter()
    infer_times = []

    try:
        while True:
            t_frame_start = time.perf_counter()

            # Read frame
            if video_cap:
                ok, frame = video_cap.read()
                if not ok:
                    print("Video stream finished.")
                    break
                ts = time.perf_counter()
            else:
                ts, frame = capture.read()

            h, w = frame.shape[:2]

            # Run perception pipeline
            t_infer_start = time.perf_counter()
            raw_detections = detector.detect(frame)
            detections = adapter.adapt(raw_detections)
            tracks = tracker.update(detections)

            relevance_map = {
                track.track_id: ego_path.relevance_for_bbox(track.bbox, w, h)
                for track in tracks if not track.missed
            }

            # Lead hazard & temporal confirmation & risk/decision
            lead_result = hazard_engine.evaluate_frame(tracks, relevance_map, w, h)
            t_infer_end = time.perf_counter()
            infer_times.append(t_infer_end - t_infer_start)
            if len(infer_times) > 30:
                infer_times.pop(0)

            # Controller update
            ctrl_event = controller.update(lead_result)

            # Latency calculations
            e2e_ms = (time.perf_counter() - t_frame_start) * 1000.0
            avg_infer_fps = 1.0 / max(0.001, (sum(infer_times) / len(infer_times)))
            cap_fps = capture.fps if capture else 30.0

            # Log row
            csv_writer.writerow({
                "timestamp_s": f"{time.perf_counter() - start_time:.2f}",
                "frame_index": frame_index,
                "lead_track_id": lead_result.lead_track_id or "NONE",
                "lead_class": lead_result.lead_class or "NONE",
                "path_relevance": lead_result.path_relevance,
                "traffic_state": lead_result.traffic_state,
                "apparent_motion": lead_result.apparent_motion,
                "hz_present": "YES" if lead_result.lead_track_id else "NO",
                "confirmation_state": lead_result.confirmation_state.value,
                "risk_level": lead_result.risk_level,
                "decision": lead_result.decision,
                "control_state": ctrl_event.state.value,
                "brake_state": ctrl_event.brake_state.value,
                "reason": lead_result.reason,
                "distance_m": lead_result.distance_m,
                "closing_speed_kmh": lead_result.closing_speed_kmh,
                "ttc_seconds": lead_result.ttc_seconds,
            })

            # Visualization
            if not args.headless:
                _draw_ego_corridor(frame, ego_path)
                _draw_overlay(
                    frame, tracks, relevance_map, lead_result, ctrl_event,
                    cap_fps, avg_infer_fps, e2e_ms, args.enable_control,
                )
                cv2.imshow("SAFAR - The Crew 2 Adapter", frame)
                if cv2.waitKey(1) & 0xFF in (ord("q"), ord("Q")):
                    print("\nExit requested by user (Q).")
                    break

            frame_index += 1

            # Periodic console output matching Step 13
            now = time.perf_counter()
            if now - last_summary >= args.summary_interval:
                elapsed_s = now - start_time
                print(
                    f"{elapsed_s:6.2f}s | LEAD=#{lead_result.lead_track_id or 'NONE'} {lead_result.lead_class or 'NONE'} | "
                    f"CONF={lead_result.confirmation_state.value} | PATH={lead_result.path_relevance} | "
                    f"MOTION={lead_result.apparent_motion} | HZ={'YES' if lead_result.lead_track_id else 'NO'} | "
                    f"DIST={lead_result.distance_m} | CLOSING={lead_result.closing_speed_kmh} | TTC={lead_result.ttc_seconds} | "
                    f"RISK={lead_result.risk_level} | DECISION={lead_result.decision} | CTRL={ctrl_event.state.value}"
                )
                last_summary = now

            if args.max_frames > 0 and frame_index >= args.max_frames:
                print(f"\nReached max frames limit ({args.max_frames}).")
                break

    except KeyboardInterrupt:
        print("\nInterrupted by user (Ctrl+C).")
    finally:
        if capture:
            capture.release()
        if video_cap:
            video_cap.release()
        controller.release_all()
        csv_file.close()
        if not args.headless:
            cv2.destroyAllWindows()

    total_time = time.perf_counter() - start_time
    print("=" * 70)
    print(f"Session complete: {frame_index} frames in {total_time:.2f}s (Avg {frame_index / max(0.001, total_time):.1f} FPS)")
    print(f"Detailed perception log saved to: {csv_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
