#define NOMINMAX
#include "safar/Bridge/UE5VehicleBridge.hpp"
#include <iostream>
#include <cstring>
#include <algorithm>
#include <cmath>

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#pragma comment(lib, "ws2_32.lib")
#else
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#endif

namespace safar {

UE5VehicleBridge::UE5VehicleBridge(const SAFARConfig& config, int port)
    : config_(config), port_(port) {
    tracker_ = std::make_unique<SAFARTracking>(config_);
    geometry_ = std::make_unique<SAFARGeometry>(config_);
    threat_engine_ = std::make_unique<SAFARThreatAssessment>(config_);
    decision_engine_ = std::make_unique<SAFARDecisionEngine>(config_);
    controller_ = std::make_unique<SAFARVehicleController>(config_);
}

UE5VehicleBridge::~UE5VehicleBridge() {
    stop();
}

bool UE5VehicleBridge::start() {
    if (running_) return true;
    running_ = true;
    server_thread_ = std::thread(&UE5VehicleBridge::runServerLoop, this);
    return true;
}

void UE5VehicleBridge::stop() {
    if (!running_) return;
    running_ = false;
    if (server_thread_.joinable()) {
        server_thread_.join();
    }
}

SAFARControlResponse UE5VehicleBridge::processTelemetry(
    const UE5VehicleSensorPacket& packet,
    const std::vector<UE5DetectionItem>& detections
) {
    std::lock_guard<std::mutex> lock(pipeline_mutex_);

    IMUData ego_imu;
    ego_imu.timestamp_us = 0;
    ego_imu.speed_mps = (std::max)(0.0f, packet.speed_mps);
    ego_imu.acceleration.x = packet.imu_ax;
    ego_imu.acceleration.y = packet.imu_ay;
    ego_imu.angular_velocity.z = packet.yaw_rate_rads;

    // 1. Ingest Detections & Compute Mathematical Stereo Depth: Z = (f * B) / d
    std::vector<Detection> raw_detections;
    std::vector<float> stereo_depths;

    for (const auto& det : detections) {
        float disparity = (std::max)(0.2f, det.disparity_px);
        float depth_z = (focal_length_px_ * stereo_baseline_m_) / disparity;
        stereo_depths.push_back(depth_z);

        Detection d;
        d.timestamp_us = 0;
        d.camera_id = CameraID::FRONT;
        d.confidence = det.confidence;
        
        switch (det.class_type) {
            case 0: d.class_name = "car"; break;
            case 1: d.class_name = "motorcycle"; break;
            case 2: d.class_name = "truck"; break;
            case 3: d.class_name = "bus"; break;
            case 4: d.class_name = "auto_rickshaw"; break;
            case 5: d.class_name = "pedestrian"; break;
            default: d.class_name = "vehicle"; break;
        }

        // Approximate screen coordinates
        float cx = 0.5f + (det.lateral_offset_m / 6.0f);
        float h = (std::max)(0.05f, 1.8f / (std::max)(1.0f, depth_z));
        d.bbox.xmin = cx - h * 0.5f;
        d.bbox.xmax = cx + h * 0.5f;
        d.bbox.ymin = 0.5f - h * 0.5f;
        d.bbox.ymax = 0.5f + h * 0.5f;
        d.center_x = cx;
        d.bottom_y = d.bbox.ymax;

        raw_detections.push_back(d);
    }

    // 2. Continuous 60Hz Kinematic Tracking
    auto tracks = tracker_->update(raw_detections, 0);

    // Apply stereo depth measurements to tracks
    for (size_t i = 0; i < tracks.size() && i < stereo_depths.size(); ++i) {
        tracks[i].estimated_distance_m = stereo_depths[i];
    }

    // 3. Trajectory & Ego-Path Corridor Geometry
    geometry_->evaluateSpatialMetrics(tracks, ego_imu, 0.016f);

    // 4. Predictive Threat Assessment & Stopping Distance
    auto threat = threat_engine_->assess(tracks, ego_imu);

    // 5. High-Frequency Decision Engine
    auto decision = decision_engine_->decide(threat, ego_imu);

    // 6. Actuator Overrides & Control Command Generation
    auto final_cmd = controller_->generateCommand(decision, threat, ego_imu, 0, 0, 0.05f);

    // 7. Format Fast Binary Control Response to UE5 Vehicle
    SAFARControlResponse response;
    std::memset(&response, 0, sizeof(response));

    float v_mps = ego_imu.speed_mps;
    float d_stop = (v_mps * 0.18f) + ((v_mps * v_mps) / (2.0f * 8.0f));

    bool is_emergency = (decision.action == DecisionAction::BRAKE && threat.state == ThreatState::CRITICAL);
    bool is_slowdown = (decision.action == DecisionAction::BRAKE || decision.action == DecisionAction::WARN);

    response.is_override_active = (is_emergency || is_slowdown) ? 1 : 0;
    response.throttle_override = is_emergency ? 0.0f : (is_slowdown ? (std::min)(packet.throttle_input, 0.25f) : packet.throttle_input);
    response.brake_override = is_emergency ? 1.0f : (is_slowdown ? 0.45f : packet.brake_input);
    response.handbrake_override = is_emergency ? 1 : 0;
    response.warning_led_active = (threat.state == ThreatState::CRITICAL || threat.state == ThreatState::HIGH || threat.state == ThreatState::MEDIUM) ? 1 : 0;
    response.calculated_d_stop_m = d_stop;
    response.current_ttc_s = threat.min_ttc_seconds;
    response.primary_hazard_id = threat.primary_hazard_id;

    return response;
}

void UE5VehicleBridge::runServerLoop() {
#ifdef _WIN32
    WSADATA wsa;
    WSAStartup(MAKEWORD(2, 2), &wsa);
#endif

    SOCKET sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (sock == INVALID_SOCKET) {
        return;
    }

    sockaddr_in server_addr;
    std::memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(static_cast<u_short>(port_));
    server_addr.sin_addr.s_addr = INADDR_ANY;

    if (bind(sock, (struct sockaddr*)&server_addr, sizeof(server_addr)) == SOCKET_ERROR) {
#ifdef _WIN32
        closesocket(sock);
#else
        close(sock);
#endif
        return;
    }

#ifdef _WIN32
    DWORD timeout_ms = 50;
    setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, (const char*)&timeout_ms, sizeof(timeout_ms));
#endif

    uint8_t buffer[4096];

    while (running_) {
        sockaddr_in client_addr;
        int client_len = sizeof(client_addr);

        int bytes_recv = recvfrom(
            sock,
            (char*)buffer,
            sizeof(buffer),
            0,
            (struct sockaddr*)&client_addr,
            &client_len
        );

        if (bytes_recv >= (int)sizeof(UE5VehicleSensorPacket)) {
            UE5VehicleSensorPacket packet;
            std::memcpy(&packet, buffer, sizeof(packet));

            std::vector<UE5DetectionItem> detections;
            size_t offset = sizeof(packet);
            size_t max_items = (bytes_recv - offset) / sizeof(UE5DetectionItem);
            uint32_t count = (std::min)(packet.detection_count, (uint32_t)max_items);

            for (uint32_t i = 0; i < count; ++i) {
                UE5DetectionItem item;
                std::memcpy(&item, buffer + offset + (i * sizeof(UE5DetectionItem)), sizeof(item));
                detections.push_back(item);
            }

            SAFARControlResponse response = processTelemetry(packet, detections);

            sendto(
                sock,
                (const char*)&response,
                sizeof(response),
                0,
                (struct sockaddr*)&client_addr,
                client_len
            );
        }
    }

#ifdef _WIN32
    closesocket(sock);
    WSACleanup();
#else
    close(sock);
#endif
}

} // namespace safar
