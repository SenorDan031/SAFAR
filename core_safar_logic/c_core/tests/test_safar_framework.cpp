#include "safar/Core/SAFARManager.hpp"
#include "safar/Core/SAFARTypes.hpp"
#include "safar/Core/SAFARConfig.hpp"
#include "safar/Tracking/SAFARTracking.hpp"
#include "safar/Geometry/SAFARGeometry.hpp"
#include "safar/Threat/SAFARThreatAssessment.hpp"
#include "safar/Decision/SAFARDecisionEngine.hpp"
#include "safar/Control/SAFARVehicleController.hpp"

#include <iostream>
#include <cassert>
#include <cmath>
#include <thread>
#include <chrono>

void testTracking() {
    safar::SAFARConfig cfg;
    cfg.max_missed_frames = 3;
    safar::SAFARTracking tracker(cfg);

    // Frame 1: 1 detection
    safar::Detection d1;
    d1.class_name = "car";
    d1.confidence = 0.92f;
    d1.bbox = {0.45f, 0.50f, 0.55f, 0.65f};
    auto tracks1 = tracker.update({d1}, 1000000);
    assert(tracks1.size() == 1);
    int id1 = tracks1[0].tracking_id;
    assert(tracks1[0].age_frames == 1);

    // Frame 2: Slightly shifted detection -> Must keep same tracking_id
    safar::Detection d2;
    d2.class_name = "car";
    d2.confidence = 0.95f;
    d2.bbox = {0.44f, 0.52f, 0.56f, 0.67f};
    auto tracks2 = tracker.update({d2}, 1033000);
    assert(tracks2.size() == 1);
    assert(tracks2[0].tracking_id == id1);
    assert(tracks2[0].age_frames == 2);
    assert(tracks2[0].missed_frames == 0);

    // Missed 4 frames -> Track must expire
    tracker.update({}, 1066000);
    tracker.update({}, 1099000);
    tracker.update({}, 1132000);
    auto tracks_final = tracker.update({}, 1165000);
    assert(tracks_final.empty());

    std::cout << "[PASS] Multi-Object Tracking & Persistence Test Passed.\n";
}

void testGeometryAndGroundTruth() {
    safar::SAFARConfig cfg;
    safar::SAFARGeometry geom(cfg);

    // Centered box in ego corridor
    safar::BoundingBox2D box_in = {0.40f, 0.55f, 0.60f, 0.85f};
    float lateral_offset = 0.0f;
    bool in_path = geom.isBoxInEgoCorridor(box_in, lateral_offset);
    assert(in_path == true);
    assert(std::abs(lateral_offset) < 0.1f);

    // Distance estimation
    float dist = geom.estimateDistanceMeters(box_in, "car");
    assert(dist > 5.0f && dist < 40.0f);

    // TTC calculation: 20m closing at 10 m/s -> TTC = 2.0s
    float ttc = geom.computeTTC(20.0f, 10.0f);
    assert(std::abs(ttc - 2.0f) < 0.001f);

    // Ground truth comparator
    safar::TrackedObject trk;
    trk.estimated_distance_m = 21.1f;
    trk.ttc_seconds = 1.74f;

    safar::GroundTruthObject gt;
    gt.actual_distance_m = 20.4f;
    gt.actual_ttc_seconds = 1.63f;

    auto metrics = geom.compareWithGroundTruth(trk, gt);
    assert(metrics.detection_matched == true);
    assert(std::abs(metrics.distance_error_m - 0.7f) < 0.05f);

    std::cout << "[PASS] Geometry, TTC & Ground Truth Comparison Test Passed.\n";
}

void testThreatAssessmentAndDecision() {
    safar::SAFARConfig cfg;
    safar::SAFARThreatAssessment threat_engine(cfg);
    safar::SAFARDecisionEngine decision_engine(cfg);

    safar::IMUData ego_imu;
    ego_imu.speed_mps = 15.0f;

    // 1. Clear track
    auto threat_clear = threat_engine.assess({}, ego_imu);
    assert(threat_clear.state == safar::ThreatState::LOW);
    assert(threat_clear.threat_score == 0.0f);
    assert(decision_engine.decide(threat_clear, ego_imu).action == safar::DecisionAction::CONTINUE);

    // 2. High hazard (Imminent forward vehicle)
    safar::TrackedObject hazard;
    hazard.tracking_id = 10;
    hazard.class_name = "car";
    hazard.confidence = 0.96f;
    hazard.in_ego_path = true;
    hazard.lateral_offset = 0.0f;
    hazard.estimated_distance_m = 8.0f;
    hazard.relative_velocity_mps = 12.0f;
    hazard.ttc_seconds = 0.67f; // Very critical TTC < 1.2s

    auto threat_crit = threat_engine.assess({hazard}, ego_imu);
    assert(threat_crit.state == safar::ThreatState::CRITICAL);
    assert(threat_crit.threat_score >= cfg.threat_critical_threshold);

    auto dec_crit = decision_engine.decide(threat_crit, ego_imu);
    assert(dec_crit.action == safar::DecisionAction::BRAKE);
    assert(dec_crit.emergency_stop == true);
    assert(dec_crit.recommended_brake == 1.0f);
    assert(dec_crit.recommended_throttle == 0.0f);

    std::cout << "[PASS] Threat Assessment & Configurable Decision Engine Test Passed.\n";
}

void testFailsafeWatchdog() {
    safar::SAFARConfig cfg;
    cfg.watchdog_timeout_ms = 100; // 100ms timeout for test
    safar::SAFARManager manager(cfg);

    safar::IMUData imu;
    imu.speed_mps = 15.0f;

    // Normal detection -> triggers warning/brake
    safar::Detection d;
    d.class_name = "truck";
    d.confidence = 0.95f;
    d.bbox = {0.35f, 0.60f, 0.65f, 0.95f};

    uint64_t now = safar::SAFARManager::getCurrentTimeUs();
    auto cmd = manager.evaluateStep({d}, imu, now);
    assert(cmd.failsafe_active == false);
    assert(cmd.brake > 0.0f);

    // Simulate perception failure (wait 150ms > watchdog_timeout_ms 100ms)
    std::this_thread::sleep_for(std::chrono::milliseconds(150));

    // Watchdog check must trigger failsafe release!
    auto failsafe_cmd = manager.checkWatchdogAndStep();
    assert(failsafe_cmd.failsafe_active == true);
    assert(failsafe_cmd.brake == 0.0f);
    assert(failsafe_cmd.throttle == 1.0f);
    assert(failsafe_cmd.emergency_brake == false);
    assert(failsafe_cmd.hud_status.find("FAILSAFE") != std::string::npos);

    std::cout << "[PASS] Failsafe Watchdog Protection Test Passed.\n";
}

int main() {
    std::cout << "===============================================================\n";
    std::cout << " RUNNING SAFAR FULL FRAMEWORK MODULAR UNIT TESTS\n";
    std::cout << "===============================================================\n";

    testTracking();
    testGeometryAndGroundTruth();
    testThreatAssessmentAndDecision();
    testFailsafeWatchdog();

    std::cout << "===============================================================\n";
    std::cout << " ALL SAFAR FRAMEWORK TESTS PASSED (100% SUCCESS)\n";
    std::cout << "===============================================================\n";
    return 0;
}
