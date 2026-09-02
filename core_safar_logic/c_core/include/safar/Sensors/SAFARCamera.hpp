#pragma once

#include "../Core/SAFARTypes.hpp"
#include <string>
#include <vector>

namespace safar {

struct CameraFrameMetadata {
    uint64_t timestamp_us{0};
    uint32_t frame_id{0};
    CameraID camera_id{CameraID::FRONT};
    uint32_t width{640};
    uint32_t height{480};
    float fov_degrees{90.0f};
    Vector3D relative_position; // Position relative to vehicle center
    Rotator3D relative_rotation;
};

class SAFARCamera {
public:
    explicit SAFARCamera(CameraID id = CameraID::FRONT, uint32_t width = 640, uint32_t height = 480)
        : id_(id), width_(width), height_(height) {}

    CameraID getID() const { return id_; }
    uint32_t getWidth() const { return width_; }
    uint32_t getHeight() const { return height_; }

    CameraFrameMetadata createMetadata(uint64_t timestamp_us, uint32_t frame_id) const {
        CameraFrameMetadata meta;
        meta.timestamp_us = timestamp_us;
        meta.frame_id = frame_id;
        meta.camera_id = id_;
        meta.width = width_;
        meta.height = height_;
        return meta;
    }

private:
    CameraID id_;
    uint32_t width_;
    uint32_t height_;
};

} // namespace safar
