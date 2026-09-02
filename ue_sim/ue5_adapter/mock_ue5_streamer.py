"""
SAFAR UE5 Mock Simulator — Virtual Camera Frame & Telemetry Streamer
Allows headless and interactive verification of the complete SAFAR pipeline without needing UE5 open.
"""
import time
import socket
import struct
import json
import argparse
import numpy as np
import cv2


class MockUE5Streamer:
    """
    Simulates an Unreal Engine 5 Chaos Vehicle with a front RGB RenderTarget virtual camera
    and an IMU telemetry publisher streaming to Python on TCP port 9001.
    """
    def __init__(self, host: str = "127.0.0.1", port: int = 9001, width: int = 640, height: int = 480):
        self.host = host
        self.port = port
        self.width = width
        self.height = height
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.is_connected = False
        self.frame_id = 0

    def connect(self, retries: int = 15, retry_delay_s: float = 0.5) -> bool:
        print(f"[UE5 SIMULATION] Connecting to Python Perception Sensor Interface at {self.host}:{self.port}...")
        for attempt in range(retries):
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((self.host, self.port))
                self.is_connected = True
                print("[UE5 SIMULATION] Successfully connected to Python Perception node.")
                return True
            except ConnectionRefusedError:
                time.sleep(retry_delay_s)
            except Exception as e:
                time.sleep(retry_delay_s)
        print("[UE5 SIMULATION] [ERROR] Could not connect to Python Perception node.")
        return False

    def generate_simulated_frame(self, obstacle_distance_factor: float = 0.6) -> np.ndarray:
        """
        Renders a synthetic road scene with perspective lane markings and a forward vehicle.
        obstacle_distance_factor: 1.0 (far), 0.5 (medium), 0.1 (very close)
        """
        img = np.zeros((self.height, self.width, 3), dtype=np.uint8)

        # Sky
        img[:int(self.height * 0.45), :] = [60, 45, 30]  # Slate blue

        # Road
        img[int(self.height * 0.45):, :] = [45, 45, 45]  # Dark asphalt

        # Road perspective lane lines
        horizon_y = int(self.height * 0.45)
        center_x = self.width // 2

        # Left lane boundary
        cv2.line(img, (center_x - 30, horizon_y), (int(self.width * 0.15), self.height), (255, 255, 255), 3)
        # Right lane boundary
        cv2.line(img, (center_x + 30, horizon_y), (int(self.width * 0.85), self.height), (255, 255, 255), 3)
        # Center dashed lane
        cv2.line(img, (center_x, horizon_y), (center_x, self.height), (0, 220, 255), 2)

        # Draw a forward vehicle directly in path
        # As distance decreases (smaller factor), vehicle appears larger and lower on screen
        y_pos = int(horizon_y + (self.height - horizon_y) * (1.0 - obstacle_distance_factor * 0.7))
        car_w = int(self.width * 0.12 * (1.0 + (1.0 - obstacle_distance_factor) * 2.0))
        car_h = int(car_w * 0.75)

        x1 = center_x - car_w // 2
        y1 = y_pos - car_h
        x2 = center_x + car_w // 2
        y2 = y_pos

        # Car body (Red)
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 210), -1)
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 100), 2)

        # Car roof / windows (Darker)
        roof_w = int(car_w * 0.7)
        roof_h = int(car_h * 0.45)
        rx1 = center_x - roof_w // 2
        ry1 = y1 - roof_h
        rx2 = center_x + roof_w // 2
        ry2 = y1
        cv2.rectangle(img, (rx1, ry1), (rx2, ry2), (20, 20, 20), -1)

        # Taillights (Bright Red)
        tl_w = max(4, int(car_w * 0.15))
        tl_h = max(3, int(car_h * 0.2))
        cv2.rectangle(img, (x1 + 4, y2 - tl_h - 4), (x1 + 4 + tl_w, y2 - 4), (0, 0, 255), -1)
        cv2.rectangle(img, (x2 - 4 - tl_w, y2 - tl_h - 4), (x2 - 4, y2 - 4), (0, 0, 255), -1)

        # License plate
        cv2.rectangle(img, (center_x - tl_w, y2 - tl_h), (center_x + tl_w, y2 - 2), (240, 240, 240), -1)

        return img

    def send_frame(self, img: np.ndarray, speed_mps: float = 15.0) -> bool:
        if not self.is_connected:
            return False

        self.frame_id += 1
        ret, jpeg_bytes = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not ret:
            return False

        raw_bytes = jpeg_bytes.tobytes()

        meta = {
            "timestamp_us": int(time.time() * 1e6),
            "frame_id": self.frame_id,
            "ego_speed_mps": round(speed_mps, 2),
            "ego_heading_deg": 0.0,
            "image_format": "jpeg",
            "image_bytes_len": len(raw_bytes)
        }

        meta_json = json.dumps(meta).encode("utf-8") + b"\0"
        payload = meta_json + raw_bytes

        # Header: Magic 4 bytes + Payload length 4 bytes
        header = struct.pack("!4sI", b"SFRM", len(payload))

        try:
            self.sock.sendall(header + payload)
            return True
        except Exception:
            self.is_connected = False
            return False

    def close(self):
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
        self.is_connected = False


def main():
    parser = argparse.ArgumentParser(description="Mock UE5 Vehicle & Sensor Streamer")
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9001)
    parser.add_argument("--frames", type=int, default=30)
    parser.add_argument("--fps", type=float, default=20.0)
    args = parser.parse_args()

    streamer = MockUE5Streamer(host=args.host, port=args.port)
    if not streamer.connect():
        return

    delay = 1.0 / args.fps
    print(f"[UE5 SIMULATION] Streaming {args.frames} frames at {args.fps} FPS...")

    for i in range(args.frames):
        # Progressively simulate vehicle approaching obstacle
        dist_factor = max(0.2, 0.8 - (i / args.frames) * 0.5)
        speed = 15.0 - (i / args.frames) * 3.0
        frame = streamer.generate_simulated_frame(obstacle_distance_factor=dist_factor)

        ok = streamer.send_frame(frame, speed_mps=speed)
        if not ok:
            print("[UE5 SIMULATION] Stream disconnected.")
            break

        print(f"[UE5 SIMULATION] Published Frame #{streamer.frame_id} (Speed: {speed:.1f} m/s, DistFactor: {dist_factor:.2f})")
        time.sleep(delay)

    streamer.close()
    print("[UE5 SIMULATION] Stream session complete.")


if __name__ == "__main__":
    main()
