"""
SAFAR 12-Scenario Deterministic Validation Benchmark
Tests the exact passive driver + emergency intervention pipeline:
1. Empty Road -> PASSIVE (Brake = 0.0)
2. Wall beside road -> NO INTERVENTION (Brake = 0.0)
3. Vehicle in other lane -> NO INTERVENTION (Brake = 0.0)
4. Vehicle moving away -> NO INTERVENTION (Brake = 0.0)
5. Vehicle ahead at safe distance -> NO INTERVENTION (Brake = 0.0)
6. Vehicle ahead suddenly brakes -> EMERGENCY BRAKE (Brake = 1.0)
7. Vehicle cuts into ego path -> EMERGENCY BRAKE (Brake = 1.0)
8. Static wall directly ahead in ego path -> EMERGENCY BRAKE (Brake = 1.0)
9. Dead end -> EMERGENCY BRAKE (Brake = 1.0)
10. False / invalid sensor data (NaN, is_valid = False) -> NO INTERVENTION (Brake = 0.0)
11. Python disconnected / empty data -> NO RANDOM BRAKING (Brake = 0.0, PASSIVE)
12. Threat clears -> CLEAN RELEASE TO PASSIVE (Hold timer expires -> Brake = 0.0)
"""
import math
import time

class MockSAFARPipeline:
    def __init__(self):
        self.corridor_half_width = 1.85
        self.t_react = 0.18
        self.a_brake = 8.0
        self.threat_confirmation_frames = 2
        self.min_hold_duration = 0.35
        self.min_closing_speed = 0.5
        self.active_hold_timer = 0.0
        self.state = "PASSIVE"
        self.action = "CONTINUE"
        self.tracked_objects = {}

    def calculate_stopping_distance(self, speed_mps: float) -> float:
        v = max(0.0, speed_mps)
        return (v * self.t_react) + ((v * v) / (2.0 * self.a_brake))

    def evaluate_step(self, ego_speed_mps: float, ego_initialized: bool, detections: list, dt: float = 0.016):
        if self.active_hold_timer > 0.0:
            self.active_hold_timer -= dt

        if not ego_initialized or ego_speed_mps < 0.2:
            self.state = "PASSIVE"
            self.action = "CONTINUE"
            self.active_hold_timer = 0.0
            return {
                "state": "PASSIVE",
                "has_intervention": False,
                "action": "CONTINUE",
                "throttle_override": 1.0,
                "brake_override": 0.0,
                "threat_level": "LOW"
            }

        d_stop = self.calculate_stopping_distance(ego_speed_mps)

        # 1. Update Tracks
        seen_ids = set()
        for det in detections:
            if not det.get("is_valid", True):
                continue
            actor_id = det["id"]
            seen_ids.add(actor_id)
            dist_x = det["dist_x"]
            lat_y = det["lat_y"]
            rel_vx = det["rel_vx"]
            rel_vy = det.get("rel_vy", 0.0)
            is_static = det.get("is_static", False)

            if math.isnan(dist_x) or dist_x <= 0.5:
                continue

            if actor_id not in self.tracked_objects:
                self.tracked_objects[actor_id] = {
                    "dist_x": dist_x,
                    "lat_y": lat_y,
                    "rel_vx": rel_vx,
                    "rel_vy": rel_vy,
                    "is_static": is_static,
                    "consecutive_threat_frames": 0,
                    "last_seen": time.time()
                }
            else:
                track = self.tracked_objects[actor_id]
                track["dist_x"] = dist_x
                track["lat_y"] = lat_y
                track["rel_vx"] = rel_vx
                track["rel_vy"] = rel_vy
                track["is_static"] = is_static
                track["last_seen"] = time.time()

        # Prune missing tracks
        for tid in list(self.tracked_objects.keys()):
            if tid not in seen_ids:
                del self.tracked_objects[tid]

        # 2. Prediction & Threat Evaluation
        min_ttc = 999.0
        min_safety_ratio = 99.0
        candidate_level = "LOW"
        primary_hazard = None

        for tid, track in self.tracked_objects.items():
            dist_x = track["dist_x"]
            lat_y = track["lat_y"]

            if track["is_static"]:
                closing_speed = ego_speed_mps
                in_path = abs(lat_y) <= self.corridor_half_width
            else:
                closing_speed = -track["rel_vx"]
                future_lat_y = abs(lat_y + (track["rel_vy"] * 1.2))
                in_path = (abs(lat_y) <= self.corridor_half_width) or (future_lat_y <= self.corridor_half_width)

            is_closing = closing_speed > self.min_closing_speed

            if in_path and is_closing and closing_speed > 0.01:
                ttc = dist_x / closing_speed
                safety_ratio = dist_x / d_stop if d_stop > 0.5 else 99.0

                track_threat = "LOW"
                if ttc <= 1.8 and safety_ratio <= 1.25:
                    track_threat = "CRITICAL"
                elif ttc <= 2.8 and safety_ratio <= 1.75:
                    track_threat = "HIGH"
                elif ttc <= 4.5:
                    track_threat = "MONITOR"

                if track_threat != "LOW":
                    track["consecutive_threat_frames"] += 1
                    if track["consecutive_threat_frames"] >= self.threat_confirmation_frames:
                        if ttc < min_ttc or safety_ratio < min_safety_ratio:
                            min_ttc = ttc
                            min_safety_ratio = safety_ratio
                            candidate_level = track_threat
                            primary_hazard = track
                else:
                    track["consecutive_threat_frames"] = 0
            else:
                track["consecutive_threat_frames"] = 0

        # 3. State Machine Transitions (PASSIVE / ASSESSING / THREAT_CONFIRMED / INTERVENTION / THREAT_CLEARED)
        if primary_hazard and candidate_level == "CRITICAL":
            self.state = "INTERVENTION"
            self.action = "EMERGENCY_BRAKE"
            self.active_hold_timer = self.min_hold_duration
        elif primary_hazard and candidate_level == "HIGH":
            if self.action != "EMERGENCY_BRAKE" or self.active_hold_timer <= 0.0:
                self.state = "INTERVENTION"
                self.action = "BRAKE"
                self.active_hold_timer = self.min_hold_duration
        elif primary_hazard and candidate_level == "MONITOR":
            if self.active_hold_timer <= 0.0:
                self.state = "ASSESSING"
                self.action = "CAUTION"
        else:
            if self.active_hold_timer <= 0.0:
                self.state = "PASSIVE"
                self.action = "CONTINUE"

        has_intervention = (self.state == "INTERVENTION")
        brake_cmd = 0.0
        if has_intervention:
            brake_cmd = 1.0 if self.action == "EMERGENCY_BRAKE" else 0.40

        return {
            "state": self.state,
            "has_intervention": has_intervention,
            "action": self.action,
            "throttle_override": 0.0 if has_intervention else 1.0,
            "brake_override": brake_cmd,
            "threat_level": candidate_level
        }


def run_all_tests():
    print("=" * 75)
    print(" SAFAR 12-SCENARIO PASSIVE DRIVER + EMERGENCY INTERVENTION BENCHMARK")
    print("=" * 75)

    passed = 0

    # TEST 1: Empty Road
    pipeline = MockSAFARPipeline()
    res = pipeline.evaluate_step(ego_speed_mps=15.0, ego_initialized=True, detections=[])
    assert not res["has_intervention"] and res["brake_override"] == 0.0, f"Test 1 Failed: {res}"
    print("[PASS] TEST 1:  Empty Road                       -> PASSIVE (Brake: 0.0, HasIntervention: False)")
    passed += 1

    # TEST 2: Wall Beside Road (Lat = 4.0m)
    pipeline = MockSAFARPipeline()
    det = [{"id": 100, "dist_x": 15.0, "lat_y": 4.0, "rel_vx": -15.0, "is_static": True}]
    for _ in range(5):
        res = pipeline.evaluate_step(ego_speed_mps=15.0, ego_initialized=True, detections=det)
    assert not res["has_intervention"] and res["brake_override"] == 0.0, f"Test 2 Failed: {res}"
    print("[PASS] TEST 2:  Wall Beside Road                 -> NO INTERVENTION (Brake: 0.0, Out of corridor)")
    passed += 1

    # TEST 3: Vehicle in Other Lane (Lat = 3.5m)
    pipeline = MockSAFARPipeline()
    det = [{"id": 101, "dist_x": 12.0, "lat_y": 3.5, "rel_vx": -5.0, "rel_vy": 0.0}]
    for _ in range(5):
        res = pipeline.evaluate_step(ego_speed_mps=15.0, ego_initialized=True, detections=det)
    assert not res["has_intervention"] and res["brake_override"] == 0.0, f"Test 3 Failed: {res}"
    print("[PASS] TEST 3:  Vehicle in Other Lane            -> NO INTERVENTION (Brake: 0.0, In other lane)")
    passed += 1

    # TEST 4: Vehicle Moving Away (V_rel = +5 m/s)
    pipeline = MockSAFARPipeline()
    det = [{"id": 102, "dist_x": 20.0, "lat_y": 0.0, "rel_vx": 5.0, "rel_vy": 0.0}]
    for _ in range(5):
        res = pipeline.evaluate_step(ego_speed_mps=15.0, ego_initialized=True, detections=det)
    assert not res["has_intervention"] and res["brake_override"] == 0.0, f"Test 4 Failed: {res}"
    print("[PASS] TEST 4:  Vehicle Moving Away              -> NO INTERVENTION (Brake: 0.0, Separating)")
    passed += 1

    # TEST 5: Vehicle Ahead at Safe Distance (Dist = 50m)
    pipeline = MockSAFARPipeline()
    det = [{"id": 103, "dist_x": 50.0, "lat_y": 0.0, "rel_vx": -2.0, "rel_vy": 0.0}]
    for _ in range(5):
        res = pipeline.evaluate_step(ego_speed_mps=15.0, ego_initialized=True, detections=det)
    assert not res["has_intervention"] and res["brake_override"] == 0.0, f"Test 5 Failed: {res}"
    print("[PASS] TEST 5:  Vehicle Ahead Safe Distance      -> NO INTERVENTION (Brake: 0.0, Safe buffer)")
    passed += 1

    # TEST 6: Vehicle Ahead Suddenly Brakes (Dist = 10m, V_rel = -12 m/s)
    pipeline = MockSAFARPipeline()
    det = [{"id": 104, "dist_x": 10.0, "lat_y": 0.0, "rel_vx": -12.0, "rel_vy": 0.0}]
    for _ in range(3):
        res = pipeline.evaluate_step(ego_speed_mps=15.0, ego_initialized=True, detections=det)
    assert res["has_intervention"] and res["brake_override"] == 1.0, f"Test 6 Failed: {res}"
    print("[PASS] TEST 6:  Vehicle Ahead Sudden Brake       -> EMERGENCY BRAKE (Brake: 1.0, Intervening)")
    passed += 1

    # TEST 7: Vehicle Cuts Into Ego Path (Lat 2.5m -> 0m, V_rel_y = -2 m/s, Dist = 8m)
    pipeline = MockSAFARPipeline()
    det = [{"id": 105, "dist_x": 8.0, "lat_y": 2.5, "rel_vx": -10.0, "rel_vy": -2.0}]
    for _ in range(3):
        res = pipeline.evaluate_step(ego_speed_mps=15.0, ego_initialized=True, detections=det)
    assert res["has_intervention"] and res["brake_override"] == 1.0, f"Test 7 Failed: {res}"
    print("[PASS] TEST 7:  Vehicle Path Cut-in              -> EMERGENCY BRAKE (Brake: 1.0, Trajectory cut-in)")
    passed += 1

    # TEST 8: Static Wall Directly Ahead in Ego Path (Dist = 12m, EgoSpeed = 15m/s)
    pipeline = MockSAFARPipeline()
    det = [{"id": 999, "dist_x": 12.0, "lat_y": 0.0, "rel_vx": -15.0, "is_static": True}]
    for _ in range(3):
        res = pipeline.evaluate_step(ego_speed_mps=15.0, ego_initialized=True, detections=det)
    assert res["has_intervention"] and res["brake_override"] == 1.0, f"Test 8 Failed: {res}"
    print("[PASS] TEST 8:  Static Wall Directly Ahead       -> EMERGENCY BRAKE (Brake: 1.0, Static wall in path)")
    passed += 1

    # TEST 9: Dead End / Road Blocked (Dist = 10m, EgoSpeed = 15m/s)
    pipeline = MockSAFARPipeline()
    det = [{"id": 999, "dist_x": 10.0, "lat_y": 0.0, "rel_vx": -15.0, "is_static": True}]
    for _ in range(3):
        res = pipeline.evaluate_step(ego_speed_mps=15.0, ego_initialized=True, detections=det)
    assert res["has_intervention"] and res["brake_override"] == 1.0, f"Test 9 Failed: {res}"
    print("[PASS] TEST 9:  Dead End / Road Blocked          -> EMERGENCY BRAKE (Brake: 1.0, Dead-end stop)")
    passed += 1

    # TEST 10: False / Invalid Sensor Data (NaN distance, is_valid = False)
    pipeline = MockSAFARPipeline()
    det = [{"id": 106, "dist_x": float("nan"), "lat_y": 0.0, "rel_vx": -20.0, "is_valid": False}]
    for _ in range(5):
        res = pipeline.evaluate_step(ego_speed_mps=15.0, ego_initialized=True, detections=det)
    assert not res["has_intervention"] and res["brake_override"] == 0.0, f"Test 10 Failed: {res}"
    print("[PASS] TEST 10: False / Invalid Data             -> NO INTERVENTION (Brake: 0.0, Filtered)")
    passed += 1

    # TEST 11: Python Disconnected / Empty Observation Data
    pipeline = MockSAFARPipeline()
    for _ in range(5):
        res = pipeline.evaluate_step(ego_speed_mps=15.0, ego_initialized=True, detections=[])
    assert not res["has_intervention"] and res["brake_override"] == 0.0, f"Test 11 Failed: {res}"
    print("[PASS] TEST 11: Python Disconnected / No Data   -> NO RANDOM BRAKING (Brake: 0.0, PASSIVE)")
    passed += 1

    # TEST 12: Threat Clears -> Clean Release to PASSIVE
    pipeline = MockSAFARPipeline()
    det_hazard = [{"id": 107, "dist_x": 10.0, "lat_y": 0.0, "rel_vx": -12.0, "rel_vy": 0.0}]
    for _ in range(3):
        pipeline.evaluate_step(ego_speed_mps=15.0, ego_initialized=True, detections=det_hazard)
    # Hazard resolves / vehicle swerves away:
    for _ in range(30): # 30 * 0.016s = 0.48s > hold duration (0.35s)
        res = pipeline.evaluate_step(ego_speed_mps=15.0, ego_initialized=True, detections=[], dt=0.016)
    assert not res["has_intervention"] and res["state"] == "PASSIVE" and res["brake_override"] == 0.0, f"Test 12 Failed: {res}"
    print("[PASS] TEST 12: Threat Clears                   -> CLEAN RELEASE TO PASSIVE (Hold expired -> Brake: 0.0)")
    passed += 1

    print("=" * 75)
    print(f" ALL {passed}/12 SCENARIOS PASSED WITH 100% SUCCESS")
    print("=" * 75)


if __name__ == "__main__":
    run_all_tests()
