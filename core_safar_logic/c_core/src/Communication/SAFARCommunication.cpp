#include "safar/Communication/SAFARCommunication.hpp"
#include <iostream>
#include <sstream>
#include <iomanip>
#include <regex>

namespace safar {

SAFARCommunication::SAFARCommunication(int perception_port, int ue5_port)
    : perception_port_(perception_port), ue5_port_(ue5_port) {
#ifdef _WIN32
    WSADATA wsaData;
    WSAStartup(MAKEWORD(2, 2), &wsaData);
#endif
    ue5_fd_ = socket(AF_INET, SOCK_DGRAM, 0);
}

SAFARCommunication::~SAFARCommunication() {
    stopServer();
    if (ue5_fd_ != INVALID_SOCKET) {
        closesocket(ue5_fd_);
    }
#ifdef _WIN32
    WSACleanup();
#endif
}

bool SAFARCommunication::startServer(DetectionCallback callback) {
    callback_ = callback;
    running_ = true;

    server_fd_ = socket(AF_INET, SOCK_STREAM, 0);
    if (server_fd_ == INVALID_SOCKET) {
        return false;
    }

    int opt = 1;
#ifdef _WIN32
    setsockopt(server_fd_, SOL_SOCKET, SO_REUSEADDR, (const char*)&opt, sizeof(opt));
#else
    setsockopt(server_fd_, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
#endif

    sockaddr_in address{};
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY;
    address.sin_port = htons(perception_port_);

    if (bind(server_fd_, (struct sockaddr*)&address, sizeof(address)) == SOCKET_ERROR) {
        closesocket(server_fd_);
        return false;
    }

    if (listen(server_fd_, 5) == SOCKET_ERROR) {
        closesocket(server_fd_);
        return false;
    }

    std::cout << "[SAFAR CORE] [COMMUNICATION] Listening for Perception Stream on TCP Port " << perception_port_ << std::endl;
    listen_thread_ = std::thread(&SAFARCommunication::listenLoop, this);
    return true;
}

void SAFARCommunication::stopServer() {
    if (!running_) return;
    running_ = false;

    if (server_fd_ != INVALID_SOCKET) {
        closesocket(server_fd_);
        server_fd_ = INVALID_SOCKET;
    }

    if (listen_thread_.joinable()) {
        listen_thread_.join();
    }
}

void SAFARCommunication::listenLoop() {
    while (running_) {
        sockaddr_in client_addr{};
        int addr_len = sizeof(client_addr);

        SOCKET client_fd = accept(server_fd_, (struct sockaddr*)&client_addr, &addr_len);
        if (client_fd == INVALID_SOCKET) {
            if (running_) {
                std::this_thread::sleep_for(std::chrono::milliseconds(50));
            }
            continue;
        }

        std::cout << "[SAFAR CORE] [COMMUNICATION] Python Perception service connected." << std::endl;

        char buffer[8192];
        std::string accumulated;

        while (running_) {
            int bytes_read = recv(client_fd, buffer, sizeof(buffer) - 1, 0);
            if (bytes_read <= 0) break;

            buffer[bytes_read] = '\0';
            accumulated += buffer;

            size_t pos = 0;
            while ((pos = accumulated.find('\n')) != std::string::npos) {
                std::string line = accumulated.substr(0, pos);
                accumulated.erase(0, pos + 1);

                if (!line.empty()) {
                    std::vector<Detection> detections;
                    uint64_t timestamp_us = 0;
                    if (parseDetections(line, detections, timestamp_us)) {
                        if (callback_) {
                            callback_(detections, timestamp_us);
                        }
                    }
                }
            }
        }

        closesocket(client_fd);
        std::cout << "[SAFAR CORE] [COMMUNICATION] Perception client disconnected." << std::endl;
    }
}

bool SAFARCommunication::sendControlCommand(const ControlCommand& cmd, const std::string& host) {
    if (ue5_fd_ == INVALID_SOCKET) return false;

    std::string payload = serializeControlCommand(cmd);

    sockaddr_in dest_addr{};
    dest_addr.sin_family = AF_INET;
    dest_addr.sin_port = htons(ue5_port_);
    inet_pton(AF_INET, host.c_str(), &dest_addr.sin_addr);

    int sent = sendto(ue5_fd_, payload.c_str(), static_cast<int>(payload.length()),
                      0, (struct sockaddr*)&dest_addr, sizeof(dest_addr));

    return (sent != SOCKET_ERROR);
}

std::string SAFARCommunication::serializeControlCommand(const ControlCommand& cmd) {
    std::ostringstream ss;
    ss << "{"
       << "\"timestamp_us\":" << cmd.timestamp_us << ","
       << "\"frame_id\":" << cmd.frame_id << ","
       << "\"decision\":\"" << toString(cmd.decision) << "\","
       << "\"throttle\":" << std::fixed << std::setprecision(3) << cmd.throttle << ","
       << "\"brake\":" << std::fixed << std::setprecision(3) << cmd.brake << ","
       << "\"steering\":" << std::fixed << std::setprecision(3) << cmd.steering << ","
       << "\"emergency_brake\":" << (cmd.emergency_brake ? "true" : "false") << ","
       << "\"hud_status\":\"" << cmd.hud_status << "\","
       << "\"latency_ms\":" << std::fixed << std::setprecision(2) << cmd.latency_ms << ","
       << "\"failsafe_active\":" << (cmd.failsafe_active ? "true" : "false")
       << "}\n";
    return ss.str();
}

bool SAFARCommunication::parseDetections(const std::string& json_str, std::vector<Detection>& out_detections, uint64_t& out_timestamp_us) {
    out_detections.clear();

    std::smatch match;
    std::regex ts_regex("\"timestamp_us\"\\s*:\\s*([0-9]+)");
    if (std::regex_search(json_str, match, ts_regex) && match.size() > 1) {
        out_timestamp_us = std::stoull(match[1].str());
    }

    std::regex det_regex("\"camera_id\"\\s*:\\s*([0-9]+).*?\"class_name\"\\s*:\\s*\"([^\"]+)\".*?\"confidence\"\\s*:\\s*([0-9]*\\.?[0-9]+).*?\"bbox_normalized\"\\s*:\\s*\\[\\s*([0-9]*\\.?[0-9]+)\\s*,\\s*([0-9]*\\.?[0-9]+)\\s*,\\s*([0-9]*\\.?[0-9]+)\\s*,\\s*([0-9]*\\.?[0-9]+)\\s*\\]");

    auto words_begin = std::sregex_iterator(json_str.begin(), json_str.end(), det_regex);
    auto words_end = std::sregex_iterator();

    for (std::sregex_iterator i = words_begin; i != words_end; ++i) {
        std::smatch m = *i;
        if (m.size() >= 8) {
            Detection det;
            det.timestamp_us = out_timestamp_us;
            det.camera_id = static_cast<CameraID>(std::stoi(m[1].str()));
            det.class_name = m[2].str();
            det.confidence = std::stof(m[3].str());
            det.bbox.xmin = std::stof(m[4].str());
            det.bbox.ymin = std::stof(m[5].str());
            det.bbox.xmax = std::stof(m[6].str());
            det.bbox.ymax = std::stof(m[7].str());
            det.center_x = det.bbox.centerX();
            det.bottom_y = det.bbox.bottomY();
            out_detections.push_back(det);
        }
    }

    return true;
}

} // namespace safar
