#pragma once

#include "types.hpp"
#include "json_helper.hpp"
#include "logger.hpp"

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#pragma comment(lib, "ws2_32.lib")
#else
#include <sys/socket.h>
#include <netinet/in.h>
#include <unistd.h>
#define SOCKET int
#define INVALID_SOCKET -1
#define SOCKET_ERROR -1
#define closesocket close
#endif

#include <string>
#include <functional>
#include <thread>
#include <atomic>
#include <iostream>

namespace safar {

class IpcReceiver {
public:
    using FrameCallback = std::function<void(const DetectionFrame&)>;

    explicit IpcReceiver(int port = 9002)
        : port_(port), running_(false), server_fd_(INVALID_SOCKET) {}

    ~IpcReceiver() {
        stop();
    }

    bool start(FrameCallback callback) {
        callback_ = callback;
        running_ = true;

#ifdef _WIN32
        WSADATA wsaData;
        if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
            Logger::logInfo("IPC_RECEIVER", "Failed to initialize WinSock2.");
            return false;
        }
#endif

        server_fd_ = socket(AF_INET, SOCK_STREAM, 0);
        if (server_fd_ == INVALID_SOCKET) {
            Logger::logInfo("IPC_RECEIVER", "Failed to create socket.");
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
        address.sin_port = htons(port_);

        if (bind(server_fd_, (struct sockaddr*)&address, sizeof(address)) == SOCKET_ERROR) {
            Logger::logInfo("IPC_RECEIVER", "Bind failed on port " + std::to_string(port_));
            closesocket(server_fd_);
            return false;
        }

        if (listen(server_fd_, 5) == SOCKET_ERROR) {
            Logger::logInfo("IPC_RECEIVER", "Listen failed on port " + std::to_string(port_));
            closesocket(server_fd_);
            return false;
        }

        Logger::logInfo("IPC_RECEIVER", "Listening for Python Detections on TCP port " + std::to_string(port_));

        worker_thread_ = std::thread(&IpcReceiver::listenLoop, this);
        return true;
    }

    void stop() {
        if (!running_) return;
        running_ = false;

        if (server_fd_ != INVALID_SOCKET) {
            closesocket(server_fd_);
            server_fd_ = INVALID_SOCKET;
        }

        if (worker_thread_.joinable()) {
            worker_thread_.join();
        }

#ifdef _WIN32
        WSACleanup();
#endif
    }

private:
    void listenLoop() {
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

            Logger::logInfo("IPC_RECEIVER", "Python Perception client connected.");

            char buffer[8192];
            std::string accumulated;

            while (running_) {
                int bytes_read = recv(client_fd, buffer, sizeof(buffer) - 1, 0);
                if (bytes_read <= 0) {
                    break;
                }

                buffer[bytes_read] = '\0';
                accumulated += buffer;

                // Process newline-delimited JSON packets
                size_t pos = 0;
                while ((pos = accumulated.find('\n')) != std::string::npos) {
                    std::string line = accumulated.substr(0, pos);
                    accumulated.erase(0, pos + 1);

                    if (!line.empty()) {
                        DetectionFrame frame;
                        if (JsonHelper::parseDetectionFrame(line, frame)) {
                            if (callback_) {
                                callback_(frame);
                            }
                        }
                    }
                }
            }

            closesocket(client_fd);
            Logger::logInfo("IPC_RECEIVER", "Python Perception client disconnected.");
        }
    }

    int port_;
    std::atomic<bool> running_;
    SOCKET server_fd_;
    FrameCallback callback_;
    std::thread worker_thread_;
};

} // namespace safar
