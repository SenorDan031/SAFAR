"""
SAFAR Perception Service — Multi-Mode Standalone Daemon
Supports:
- Real Perception Mode (YOLO11)
- Mock Perception Mode (Synthetic obstacles)
"""
import time
import socket
import argparse
import sys

from .config import PerceptionConfig
from .protocol import PerceptionProtocol
from .mock_detector import MockDetector
from .yolo_detector import YoloPerceptionDetector

class PerceptionService:
    def __init__(self, config: PerceptionConfig):
        self.config = config
        self.mock_detector = MockDetector(scenario="approaching_vehicle") if config.mode == "mock" else None
        self.yolo_detector = YoloPerceptionDetector(config.model_path, config.confidence_threshold) if config.mode == "real" else None
        self.sock = None
        self.running = False
        self.frame_counter = 0

    def connect_to_cpp_core(self, retries: int = 10, delay_s: float = 0.5) -> bool:
        print(f"[SAFAR PERCEPTION] Connecting to C++ SAFAR Core at {self.config.cpp_core_host}:{self.config.cpp_core_port}...")
        for attempt in range(retries):
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((self.config.cpp_core_host, self.config.cpp_core_port))
                print("[SAFAR PERCEPTION] Successfully connected to C++ SAFAR Core.")
                return True
            except ConnectionRefusedError:
                time.sleep(delay_s)
            except Exception:
                time.sleep(delay_s)
        print("[SAFAR PERCEPTION] [ERROR] Could not connect to C++ SAFAR Core.")
        return False

    def run_mock_loop(self, max_frames: int = None):
        delay = 1.0 / self.config.target_fps
        self.running = True

        print(f"[SAFAR PERCEPTION] Running MOCK perception service at {self.config.target_fps} FPS...")
        try:
            while self.running:
                t0 = time.perf_counter()
                ts_us = int(time.time() * 1e6)
                self.frame_counter += 1

                # Generate mock detections
                detections = self.mock_detector.generate_detections(ts_us)

                # Format wire message
                msg = PerceptionProtocol.format_detection_message(detections, ts_us, self.frame_counter)

                # Transmit to C++ Core
                try:
                    self.sock.sendall(msg.encode("utf-8"))
                except Exception:
                    print("[SAFAR PERCEPTION] Connection lost to C++ Core. Reconnecting...")
                    if not self.connect_to_cpp_core(retries=3):
                        break

                t_end = time.perf_counter()
                time.sleep(max(0.001, delay - (t_end - t0)))

                if max_frames and self.frame_counter >= max_frames:
                    break

        except KeyboardInterrupt:
            print("\n[SAFAR PERCEPTION] Service stopped by user.")
        finally:
            self.close()

    def close(self):
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass

def main():
    parser = argparse.ArgumentParser(description="SAFAR Standalone Perception Service")
    parser.add_argument("--mode", choices=["real", "mock"], default="real", help="Perception mode: real (YOLO) or mock (Synthetic)")
    parser.add_argument("--scenario", type=str, default="approaching_vehicle", help="Mock scenario")
    parser.add_argument("--fps", type=float, default=30.0, help="Target FPS")
    parser.add_argument("--port", type=int, default=9002, help="C++ Core Port")
    args = parser.parse_args()

    cfg = PerceptionConfig(mode=args.mode, target_fps=args.fps, cpp_core_port=args.port)
    service = PerceptionService(cfg)
    if args.mode == "mock":
        service.mock_detector.scenario = args.scenario

    if service.connect_to_cpp_core():
        if args.mode == "mock":
            service.run_mock_loop()
        else:
            print("[SAFAR PERCEPTION] Real YOLO mode requires live sensor stream. Use main.py --mode ue5 or test_ue5_safar.")

if __name__ == "__main__":
    main()
