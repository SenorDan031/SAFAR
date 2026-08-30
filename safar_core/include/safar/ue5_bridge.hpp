#pragma once

#include "types.hpp"
#include "json_helper.hpp"
#include "logger.hpp"

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#else
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#define SOCKET int
#define INVALID_SOCKET -1
#define SOCKET_ERROR -1
#define closesocket close
#endif

#include <string>

namespace safar {

class UE5Bridge {
public:
    explicit UE5Bridge(const std::string& host = "127.0.0.1", int port = 9003)
        : host_(host), port_(port), socket_fd_(INVALID_SOCKET) {
        initSocket();
    }

    ~UE5Bridge() {
        if (socket_fd_ != INVALID_SOCKET) {
            closesocket(socket_fd_);
        }
    }

    // Sends the evaluated decision and actuator commands to UE5
    bool sendControl(const ControlResponse& resp) {
        if (socket_fd_ == INVALID_SOCKET) {
            if (!initSocket()) return false;
        }

        std::string json_payload = JsonHelper::serializeControlResponse(resp);

        sockaddr_in dest_addr{};
        dest_addr.sin_family = AF_INET;
        dest_addr.sin_port = htons(port_);
        inet_pton(AF_INET, host_.c_str(), &dest_addr.sin_addr);

        int sent = sendto(socket_fd_, json_payload.c_str(), static_cast<int>(json_payload.length()),
                          0, (struct sockaddr*)&dest_addr, sizeof(dest_addr));

        if (sent == SOCKET_ERROR) {
            return false;
        }

        Logger::logBoundary("C++ SAFAR CORE", "UE5 SIMULATION",
                            "Frame #" + std::to_string(resp.frame_id) + " -> Decision: " +
                            toString(resp.decision) + " (Threat: " + std::to_string(resp.threat_score) + ")");
        return true;
    }

private:
    bool initSocket() {
        socket_fd_ = socket(AF_INET, SOCK_DGRAM, 0);
        if (socket_fd_ == INVALID_SOCKET) {
            Logger::logInfo("UE5_BRIDGE", "Failed to create UDP socket for UE5 bridge.");
            return false;
        }
        return true;
    }

    std::string host_;
    int port_;
    SOCKET socket_fd_;
};

} // namespace safar
