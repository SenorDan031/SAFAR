#pragma once

#include "SAFARCamera.hpp"
#include "SAFARIMU.hpp"
#include <memory>
#include <map>

namespace safar {

struct SensorBundle {
    uint64_t timestamp_us{0};
    uint32_t frame_id{0};
    IMUData imu;
    std::vector<Detection> detections;
    std::vector<GroundTruthObject> ground_truth; // Isolated for validation only
};

class SAFARSensorManager {
public:
    SAFARSensorManager() {
        cameras_[CameraID::FRONT] = std::make_shared<SAFARCamera>(CameraID::FRONT);
        cameras_[CameraID::LEFT]  = std::make_shared<SAFARCamera>(CameraID::LEFT);
        cameras_[CameraID::RIGHT] = std::make_shared<SAFARCamera>(CameraID::RIGHT);
    }

    SAFARIMU& getIMU() { return imu_; }
    const SAFARIMU& getIMU() const { return imu_; }

    std::shared_ptr<SAFARCamera> getCamera(CameraID id) {
        auto it = cameras_.find(id);
        if (it != cameras_.end()) return it->second;
        return nullptr;
    }

private:
    SAFARIMU imu_;
    std::map<CameraID, std::shared_ptr<SAFARCamera>> cameras_;
};

} // namespace safar
