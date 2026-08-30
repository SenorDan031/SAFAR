#include "safar/types.hpp"
#include "safar/geometry.hpp"
#include "safar/threat_engine.hpp"
#include "safar/decision_engine.hpp"
#include "safar/vehicle_control.hpp"
#include "safar/json_helper.hpp"

#include <iostream>
#include <cassert>
#include <cmath>

void testGeometry() {
    safar::EgoPathGeometry geom;
    float offset = 0.0f;

    // Centered object near bottom (x=0.5, y=0.8) -> Must be in path
    assert(geom.isPointInPath(0.5f, 0.8f, offset) == true);
    assert(std::abs(offset) < 0.05f);

    // Object far to the left (x=0.1, y=0.8) -> Outside corridor
    assert(geom.isPointInPath(0.1f, 0.8f, offset) == false);

    // Object above horizon (y=0.2 < horizon_y=0.45) -> Ignored / outside path
    assert(geom.isPointInPath(0.5f, 0.2f, offset) == false);

    std::cout << "[PASS] Geometry & Corridor Test Passed.\n";
}

void testThreatAndDecision() {
    safar::EgoPathGeometry geom;
    safar::ThreatEngine threat_engine(geom);
    safar::DecisionEngine decision_engine;
    safar::VehicleControl control;

    // 1. Clear frame (no detections)
    safar::DetectionFrame clear_frame;
    clear_frame.frame_id = 1;
    clear_frame.ego_speed_mps = 15.0f;

    auto threat_clear = threat_engine.assess(clear_frame);
    assert(threat_clear.in_path == false);
    assert(threat_clear.threat_score == 0.0f);
    assert(decision_engine.decide(threat_clear) == safar::DecisionAction::CONTINUE);

    // 2. Off-path obstacle on side of road
    safar::DetectionFrame side_frame;
    side_frame.frame_id = 2;
    side_frame.ego_speed_mps = 15.0f;
    safar::Detection side_det;
    side_det.track_id = 1;
    side_det.class_name = "car";
    side_det.confidence = 0.90f;
    side_det.bbox = {0.05f, 0.60f, 0.18f, 0.80f};
    side_det.center_x = 0.115f;
    side_det.bottom_y = 0.80f;
    side_frame.detections.push_back(side_det);

    auto threat_side = threat_engine.assess(side_frame);
    assert(threat_side.in_path == false);
    assert(decision_engine.decide(threat_side) == safar::DecisionAction::CONTINUE);

    // 3. Forward vehicle in path (Moderate distance) -> Expect WARN
    safar::DetectionFrame warn_frame;
    warn_frame.frame_id = 3;
    warn_frame.ego_speed_mps = 15.0f;
    safar::Detection lead_det;
    lead_det.track_id = 2;
    lead_det.class_name = "car";
    lead_det.confidence = 0.95f;
    lead_det.bbox = {0.42f, 0.50f, 0.58f, 0.68f};
    lead_det.center_x = 0.50f;
    lead_det.bottom_y = 0.68f;
    warn_frame.detections.push_back(lead_det);

    auto threat_warn = threat_engine.assess(warn_frame);
    assert(threat_warn.in_path == true);
    assert(threat_warn.threat_score >= 0.40f);
    assert(decision_engine.decide(threat_warn) == safar::DecisionAction::WARN ||
           decision_engine.decide(threat_warn) == safar::DecisionAction::SLOWDOWN);

    // 4. Imminent vehicle in path (Large & close to bottom) -> Expect EMERGENCY_BRAKE
    safar::DetectionFrame crit_frame;
    crit_frame.frame_id = 4;
    crit_frame.ego_speed_mps = 20.0f;
    safar::Detection crit_det;
    crit_det.track_id = 3;
    crit_det.class_name = "truck";
    crit_det.confidence = 0.98f;
    crit_det.bbox = {0.30f, 0.55f, 0.70f, 0.95f};
    crit_det.center_x = 0.50f;
    crit_det.bottom_y = 0.95f;
    crit_frame.detections.push_back(crit_det);

    auto threat_crit = threat_engine.assess(crit_frame);
    assert(threat_crit.in_path == true);
    assert(threat_crit.threat_score >= 0.85f);
    assert(decision_engine.decide(threat_crit) == safar::DecisionAction::EMERGENCY_BRAKE);

    auto cmd = control.generateCommand(crit_frame, threat_crit, safar::DecisionAction::EMERGENCY_BRAKE, 1.2f);
    assert(cmd.control.brake == 1.0f);
    assert(cmd.control.throttle == 0.0f);
    assert(cmd.control.emergency_stop == true);

    std::cout << "[PASS] Threat Assessment & Decision Engine Test Passed.\n";
}

void testJsonHelper() {
    std::string sample_json = "{\"timestamp_us\":1787118000123456,\"frame_id\":1042,\"ego_speed_mps\":14.5,\"detections\":[{\"track_id\":1,\"class_name\":\"car\",\"confidence\":0.94,\"bbox_normalized\":[0.42,0.35,0.58,0.68],\"center_x\":0.50,\"bottom_y\":0.68}]}";
    
    safar::DetectionFrame frame;
    bool ok = safar::JsonHelper::parseDetectionFrame(sample_json, frame);
    assert(ok == true);
    assert(frame.frame_id == 1042);
    assert(frame.ego_speed_mps > 14.0f);
    assert(frame.detections.size() == 1);
    assert(frame.detections[0].class_name == "car");
    assert(frame.detections[0].track_id == 1);

    safar::ControlResponse resp;
    resp.timestamp_us = 1787118000128910ULL;
    resp.frame_id = 1042;
    resp.threat_score = 0.72f;
    resp.decision = safar::DecisionAction::WARN;
    resp.control.throttle = 0.50f;
    resp.control.brake = 0.0f;
    resp.hud_message = "SAFAR: VEHICLE DETECTED | THREAT: 0.72 | ACTION: WARN";
    resp.latency_ms = 4.5f;

    std::string out_json = safar::JsonHelper::serializeControlResponse(resp);
    assert(out_json.find("\"decision\":\"WARN\"") != std::string::npos);
    assert(out_json.find("\"threat_score\":0.7200") != std::string::npos);

    std::cout << "[PASS] JSON Helper Parsing & Serialization Test Passed.\n";
}

int main() {
    std::cout << "==================================================\n";
    std::cout << " RUNNING SAFAR C++ CORE LOGIC UNIT TESTS\n";
    std::cout << "==================================================\n";

    testGeometry();
    testThreatAndDecision();
    testJsonHelper();

    std::cout << "==================================================\n";
    std::cout << " ALL C++ UNIT TESTS PASSED SUCCESSFULLY (100%)\n";
    std::cout << "==================================================\n";
    return 0;
}
