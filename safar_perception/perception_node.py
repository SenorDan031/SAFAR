"""
SAFAR Perception Node — Main AI Inference & Perception Runner
"""
import time
import argparse
from typing import Optional

from .sensor_interface import BaseSensorSource, UE5SocketStreamSource, PhysicalCameraSource
from .detector import YoloDetector
from .ipc_sender import IpcSender


class PerceptionNode:
    """
    Orchestrates:
    1. Receiving sensor frame from SensorInterface (UE5 / Physical Camera)
    2. Running YOLO detection
    3. Sending canonical DetectionPayload to C++ SAFAR Core
    """
    def __init__(
        self,
        sensor_source: BaseSensorSource,
        detector: Optional[YoloDetector] = None,
        ipc_sender: Optional[IpcSender] = None,
        model_path: str = "yolo11n.pt",
        conf_threshold: float = 0.35,
        cpp_host: str = "127.0.0.1",
        cpp_port: int = 9002
    ):
        self.sensor = sensor_source
        self.detector = detector or YoloDetector(model_path=model_path, conf_threshold=conf_threshold)
        self.ipc = ipc_sender or IpcSender(host=cpp_host, port=cpp_port)
        self.running = False
        self.processed_frames = 0

    def start(self, max_frames: Optional[int] = None):
        print("======================================================================")
        print(" SAFAR PYTHON PERCEPTION NODE ACTIVE")
        print("======================================================================")
        print(f" Connecting to C++ SAFAR Core at {self.ipc.host}:{self.ipc.port}...")

        if not self.ipc.connect(retries=10, retry_delay_s=0.5):
            print("[WARN] Could not connect to C++ SAFAR Core immediately. Will retry during loop.")
        else:
            print("[INFO] Connected to C++ SAFAR Core.")

        self.running = True
        self.processed_frames = 0
        t_start = time.perf_counter()

        try:
            while self.running:
                frame = self.sensor.read_frame()
                if frame is None:
                    time.sleep(0.01)
                    continue

                t0 = time.perf_counter()

                # 1. Run YOLO detection
                payload = self.detector.detect(frame)

                # 2. Transmit to C++ Core
                sent = self.ipc.send_detections(payload)

                t_end = time.perf_counter()
                latency_ms = (t_end - t0) * 1000.0
                self.processed_frames += 1

                det_summary = f"{len(payload.detections)} objects"
                if payload.detections:
                    lead = payload.detections[0]
                    det_summary = f"{lead.class_name} (conf: {lead.confidence:.2f}, bbox: [{lead.bbox.xmin:.2f}, {lead.bbox.ymin:.2f}, {lead.bbox.xmax:.2f}, {lead.bbox.ymax:.2f}])"

                print(f"[PYTHON PERCEPTION] Frame #{frame.frame_id:04d} | Speed: {frame.ego_speed_mps:.1f} m/s | YOLO: {det_summary} | Latency: {latency_ms:.1f}ms | Sent to C++: {sent}")

                if max_frames and self.processed_frames >= max_frames:
                    print(f"[INFO] Reached max frames limit ({max_frames}). Stopping perception node.")
                    break

        except KeyboardInterrupt:
            print("\n[INFO] Perception Node interrupted by user.")
        finally:
            self.stop()
            elapsed = time.perf_counter() - t_start
            fps = self.processed_frames / elapsed if elapsed > 0 else 0
            print("======================================================================")
            print(f" Perception Node complete: {self.processed_frames} frames in {elapsed:.2f}s (Avg {fps:.1f} FPS)")
            print("======================================================================")

    def stop(self):
        self.running = False
        self.sensor.close()
        self.ipc.close()


def main():
    parser = argparse.ArgumentParser(description="SAFAR Python Perception Node")
    parser.add_argument("--mode", choices=["ue5", "camera"], default="ue5", help="Sensor source mode")
    parser.add_argument("--ue5-port", type=int, default=9001, help="Port to receive UE5 frames")
    parser.add_argument("--cpp-host", type=str, default="127.0.0.1", help="C++ Core host")
    parser.add_argument("--cpp-port", type=int, default=9002, help="C++ Core port")
    parser.add_argument("--conf", type=float, default=0.35, help="YOLO confidence threshold")
    parser.add_argument("--model", type=str, default="yolo11n.pt", help="YOLO model weights path")
    args = parser.parse_args()

    if args.mode == "ue5":
        sensor = UE5SocketStreamSource(port=args.ue5_port)
    else:
        sensor = PhysicalCameraSource(camera_index=0)

    node = PerceptionNode(
        sensor_source=sensor,
        model_path=args.model,
        conf_threshold=args.conf,
        cpp_host=args.cpp_host,
        cpp_port=args.cpp_port
    )
    node.start()


if __name__ == "__main__":
    main()
