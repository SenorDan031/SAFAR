#pragma once

#include "safar/Core/SAFARConfig.hpp"
#include "safar/Sensors/SAFARSensorManager.hpp"
#include "safar/Tracking/SAFARTracking.hpp"
#include "safar/Geometry/SAFARGeometry.hpp"
#include "safar/Threat/SAFARThreatAssessment.hpp"
#include "safar/Decision/SAFARDecisionEngine.hpp"
#include "safar/Control/SAFARVehicleController.hpp"

#include <string>
#include <vector>
#include <memory>
#include <atomic>
#include <thread>
#include <mutex>

namespace safar {

#pragma pack(push, 1)
struct UE5VehicleSensorPacket {
    float speed_mps;
    float steering_input;
    float throttle_input;
    float brake_input;
    float yaw_rate_rads;
    float imu_ax;
    float imu_ay;
    uint32_t detection_count;
};

struct UE5DetectionItem {
    int32_t actor_id;
    int32_t class_type; // 0: Car, 1: Motorcycle, 2: Truck, 3: Bus, 4: AutoRickshaw, 5: Pedestrian
    float disparity_px; // Optical disparity from stereo camera pair
    float lateral_offset_m;
    float relative_vx_mps;
    float confidence;
};

struct SAFARControlResponse {
    uint8_t is_override_active;  // 1 if SAFAR is overriding controls, 0 otherwise
    float throttle_override;     // 0.0 (cut) or normal
    float brake_override;        // 1.0 (AEB lock), 0.4 (slowdown), 0.0 (free)
    uint8_t handbrake_override;  // 1 if handbrake locked
    uint8_t warning_led_active;  // 1 if dash warning light on
    float calculated_d_stop_m;   // Dynamic stopping distance for dashboard
    float current_ttc_s;         // Time to collision
    int32_t primary_hazard_id;
};
#pragma pack(pop)

class UE5VehicleBridge {
public:
    UE5VehicleBridge(const SAFARConfig& config, int port = 8888);
    ~UE5VehicleBridge();

    bool start();
    void stop();

    SAFARControlResponse processTelemetry(
        const UE5VehicleSensorPacket& packet,
        const std::vector<UE5DetectionItem>& detections
    );

private:
    SAFARConfig config_;
    int port_;
    std::atomic<bool> running_{false};
    std::thread server_thread_;

    std::unique_ptr<SAFARTracking> tracker_;
    std::unique_ptr<SAFARGeometry> geometry_;
    std::unique_ptr<SAFARThreatAssessment> threat_engine_;
    std::unique_ptr<SAFARDecisionEngine> decision_engine_;
    std::unique_ptr<SAFARVehicleController> controller_;

    std::mutex pipeline_mutex_;
    float focal_length_px_ = 650.0f;
    float stereo_baseline_m_ = 0.25f;

    void runServerLoop();
};

} // namespace safar
