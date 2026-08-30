#pragma once

#include "../Core/SAFARTypes.hpp"
#include <mutex>
#include <deque>

namespace safar {

class SAFARIMU {
public:
    SAFARIMU() = default;

    void update(const IMUData& data) {
        std::lock_guard<std::mutex> lock(mutex_);
        latest_imu_ = data;
        history_.push_back(data);
        if (history_.size() > 100) {
            history_.pop_front();
        }
    }

    IMUData getLatest() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return latest_imu_;
    }

private:
    mutable std::mutex mutex_;
    IMUData latest_imu_;
    std::deque<IMUData> history_;
};

} // namespace safar
