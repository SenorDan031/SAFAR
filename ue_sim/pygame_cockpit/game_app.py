"""
SAFAR Simulator — Realistic Playable Driving Simulation Game
Integrates physical virtual stereo vision (Z = fB/d), realistic urban traffic & pedestrians (Left-Hand Traffic),
clean cockpit dashboard presentation, and invisible 60Hz predictive safety interventions.
"""
import time
import sys
import os
import math
import subprocess
import threading
from typing import List, Dict, Tuple, Optional, Any

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from .urban_traffic_manager import UrbanTrafficManager, UrbanActor, TrafficArchetype
from .engineering_mode import EngineeringModeController, CleanCockpitState
from .latency_profiler import LatencyProfiler
from .predictive_threat import PredictiveThreatEngine, PredictiveAssessmentResult

from safar.perception.stereo_depth import StereoDepthEngine, StereoDetection
from safar.perception.continuous_predictor import ContinuousKinematicPredictor, TrackedKinematicObject
from safar.integrations.the_crew2.config import TheCrew2Config
from safar.integrations.the_crew2.controller import TheCrew2Controller
from safar.perception.yolo_detector import YOLODetector
from safar.perception.ego_path import EgoPathModel
from safar.integrations.ue5.runner import AsyncUE5CaptureWorker


class SAFARSimulatorApp:
    def __init__(self):
        self.perception_mode = "real"
        self.traffic_density = "MEDIUM"
        self.target_window = "SAFAR_Sim"
        self.cpp_proc = None
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.eng_controller = EngineeringModeController()

    def start_cpp_core(self):
        cpp_exe = os.path.join(self.root_dir, "safar_core", "build", "Release", "safar_core.exe")
        if os.path.exists(cpp_exe) and self.cpp_proc is None:
            self.cpp_proc = subprocess.Popen(
                [cpp_exe],
                cwd=self.root_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            time.sleep(0.3)

    def stop_cpp_core(self):
        if self.cpp_proc:
            self.cpp_proc.terminate()
            try:
                self.cpp_proc.wait(timeout=1.0)
            except Exception:
                self.cpp_proc.kill()
            self.cpp_proc = None

    def run(self):
        self.start_cpp_core()

        try:
            print("\n======================================================================")
            print(" [SAFAR SIMULATOR] -- REALISTIC URBAN DRIVING SIMULATION")
            print("======================================================================")
            print(" * Environment: Realistic Urban City Corridor (Left-Hand Traffic)")
            print(" * Vehicle: BP_VehicleAdvSportsCar (Chaos Physics + Driver Cockpit)")
            print(" * Sensors: Virtual Stereo Camera Pair (Baseline B = 0.25m | Z = fB/d)")
            print(" * Traffic: Ambient Cars, Auto-Rickshaws, Bikes, Buses & Pedestrians")
            print(" * HUD Mode: 100% CLEAN DRIVING (Zero on-screen clutter | F3 for Eng Mode)")
            print("======================================================================\n")

            self.play_simulation()

        except KeyboardInterrupt:
            pass
        finally:
            self.stop_cpp_core()

    def play_simulation(self):
        # 1. Initialize Subsystems
        traffic_mgr = UrbanTrafficManager(target_actor_count=22, hazard_frequency_s=9.0)
        stereo_engine = StereoDepthEngine(baseline_m=0.25, focal_length_px=650.0)
        predictor = ContinuousKinematicPredictor()
        threat_engine = PredictiveThreatEngine(nominal_deceleration_mps2=8.0, reaction_time_s=0.18)
        profiler = LatencyProfiler()

        config = TheCrew2Config(
            enabled=True,
            require_foreground_window=False,
            candidate_frames=1,
            confirm_frames=1,
            hazard_frames=1
        )
        capture = AsyncUE5CaptureWorker(target_title=self.target_window, target_fps=30.0)
        capture.start()

        detector = YOLODetector(confidence_threshold=0.32) if self.perception_mode == "real" else None
        controller = TheCrew2Controller(config)
        ego_path = EgoPathModel()

        cockpit_state = CleanCockpitState()

        # Thread synchronization flags
        running = True
        latest_stereo_dets: List[StereoDetection] = []
        det_lock = threading.Lock()

        # 2. Background Stereo Perception Thread (~20 Hz)
        def stereo_perception_worker():
            nonlocal latest_stereo_dets
            while running:
                t0 = profiler.mark_capture()
                frame_img = capture.get_latest_frame(timeout_s=0.04)
                w, h = (1280, 720) if frame_img is None else (frame_img.shape[1], frame_img.shape[0])

                raw_dets = []
                if self.perception_mode == "real" and frame_img is not None:
                    yolo_dets = detector.detect(frame_img)
                    profiler.mark_perception()
                    for idx, d in enumerate(yolo_dets):
                        raw_dets.append({
                            "track_id": f"cam-{idx}",
                            "class_name": d.class_name,
                            "bbox": d.bbox,
                            "confidence": d.confidence
                        })
                else:
                    profiler.mark_perception()

                # Process mathematical stereo depth
                stereo_dets = stereo_engine.process_stereo_pair(raw_dets, current_time_s=t0)
                with det_lock:
                    latest_stereo_dets = stereo_dets
                time.sleep(0.045)

        percep_thread = threading.Thread(target=stereo_perception_worker, daemon=True)
        percep_thread.start()

        # 3. Master 60Hz Predictive ADAS & Actuation Loop
        t_prev = time.perf_counter()
        frame_idx = 0
        ego_speed_kmh = 45.0
        prev_decision = "CONTINUE"

        print(" [SAFAR ACTIVE] Drive normally in Unreal Engine 5. Experience SAFAR safety invisibly.\n")

        try:
            while True:
                t_now = time.perf_counter()
                dt = max(0.001, t_now - t_prev)
                t_prev = t_now
                frame_idx += 1

                # 1. Update Ambient Urban Traffic & Pedestrians
                urban_actors = traffic_mgr.update(ego_speed_kmh=ego_speed_kmh, dt=dt)

                with det_lock:
                    current_stereo = list(latest_stereo_dets)

                # Feed urban actors into stereo perception input
                ingest_dets = []
                if current_stereo:
                    for s in current_stereo:
                        ingest_dets.append({
                            "track_id": s.track_id,
                            "class_name": s.class_name,
                            "distance_m": s.estimated_depth_m,
                            "lateral_offset_m": s.lateral_offset_m,
                            "relative_speed_kmh": 20.0,
                            "confidence": s.confidence
                        })
                else:
                    # Sensor simulation from physical traffic actors within camera FOV
                    for act in urban_actors:
                        if 0.0 < act.distance_m < 85.0:
                            # Verify within Front Camera FOV (78 degrees)
                            angle_deg = math.degrees(math.atan2(act.lateral_offset_m, act.distance_m))
                            if abs(angle_deg) <= 39.0: # Half FOV
                                # Estimate depth via stereo formula with noise
                                disp = stereo_engine.compute_disparity_from_depth(act.distance_m)
                                est_z = stereo_engine.compute_depth_from_disparity(disp)
                                ingest_dets.append({
                                    "track_id": str(act.id),
                                    "class_name": act.archetype.value,
                                    "distance_m": est_z,
                                    "lateral_offset_m": act.lateral_offset_m,
                                    "relative_speed_kmh": ego_speed_kmh - act.speed_kmh,
                                    "confidence": 0.95
                                })

                # 2. Continuous 60Hz Kinematic Tracking & Dead Reckoning
                profiler.mark_tracking()
                predictor.update_from_perception(ingest_dets, current_time_s=t_now)
                tracks = predictor.step_dead_reckoning(dt)

                # 3. Predictive Threat Assessment (Stopping Distance Aware)
                primary_assessment: Optional[PredictiveAssessmentResult] = None
                worst_track: Optional[TrackedKinematicObject] = None
                max_score = 0.0

                for trk in tracks:
                    assessment = threat_engine.evaluate_track(trk, ego_speed_kmh=ego_speed_kmh, lookahead_s=1.2)
                    if assessment.threat_score > max_score:
                        max_score = assessment.threat_score
                        primary_assessment = assessment
                        worst_track = trk

                profiler.mark_threat_decision()

                # 4. Low-Latency Actuator Fast-Path
                if primary_assessment is not None and primary_assessment.decision_action == "EMERGENCY_BRAKE":
                    controller.apply_strong_brake()
                    is_override = True
                elif primary_assessment is not None and primary_assessment.decision_action == "SLOWDOWN":
                    controller.apply_light_brake()
                    is_override = True
                else:
                    if controller.is_overriding:
                        controller.release_all()
                    is_override = False

                profiler.mark_actuation()

                # Physical speed integration
                if is_override:
                    ego_speed_kmh = max(0.0, ego_speed_kmh - 28.0 * dt)
                else:
                    ego_speed_kmh = min(55.0, ego_speed_kmh + 10.0 * dt)

                # 5. Clean Automotive Presentation (No Debug Clutter)
                cockpit_state.speed_kmh = ego_speed_kmh
                cockpit_state.gear = 1 if ego_speed_kmh < 20 else (2 if ego_speed_kmh < 40 else 3)
                cockpit_state.engine_rpm = 1000.0 + (ego_speed_kmh * 45.0)
                cockpit_state.is_aeb_braking = is_override
                cockpit_state.warning_chime_active = (primary_assessment.decision_action == "SLOWDOWN") if primary_assessment else False

                current_action = primary_assessment.decision_action if primary_assessment else "CONTINUE"
                if current_action != prev_decision and current_action in ["SLOWDOWN", "EMERGENCY_BRAKE"]:
                    print(f"\n[SAFAR ADAS] [!ALERT] {primary_assessment.reason}")

                prev_decision = current_action

                # In normal mode, print only clean single-line vehicle cluster
                if not self.eng_controller.is_engineering_mode_enabled:
                    if frame_idx % 25 == 0:
                        sys.stdout.write("\r" + EngineeringModeController.render_clean_cockpit_display(cockpit_state))
                        sys.stdout.flush()
                else:
                    if frame_idx % 30 == 0:
                        stats = profiler.get_stats_summary()
                        print(EngineeringModeController.render_engineering_overlay(
                            cockpit_state, current_stereo, primary_assessment, stats
                        ))

                time.sleep(0.016) # ~60 Hz loop

        except KeyboardInterrupt:
            print("\n\n[SIMULATION] Drive concluded by player.")
        finally:
            running = False
            controller.release_all()
            capture.stop()


def main():
    app = SAFARSimulatorApp()
    app.run()


if __name__ == "__main__":
    main()
