"""
SAFAR UE5 Receiver — Listens for C++ SAFAR Core Decision & Actuator Intervention Commands
"""
import socket
import json
import argparse
import time


class UE5Receiver:
    """
    Listens on UDP port 9003 for decisions and control commands from the C++ SAFAR Core,
    simulating the Unreal Engine Chaos Vehicle controller & HUD overlay.
    """
    def __init__(self, port: int = 9003):
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("0.0.0.0", self.port))
        self.running = False
        self.received_count = 0

    def start(self, max_packets: int = None, timeout_s: float = None):
        print("======================================================================")
        print(" SAFAR UE5 SIMULATION RECEIVER & VEHICLE HUD LISTENER")
        print("======================================================================")
        print(f" Listening on UDP port {self.port} for C++ SAFAR Core Decisions...")

        self.running = True
        self.received_count = 0
        if timeout_s:
            self.sock.settimeout(timeout_s)

        try:
            while self.running:
                try:
                    data, addr = self.sock.recvfrom(4096)
                except socket.timeout:
                    print("[UE5 RECEIVER] Socket listen timeout reached.")
                    break

                if not data:
                    continue

                json_str = data.decode("utf-8").strip()
                try:
                    payload = json.loads(json_str)
                except Exception:
                    continue

                self.received_count += 1
                hud_msg = payload.get("hud_message", "SAFAR: ACTIVE")
                threat = payload.get("threat_score", 0.0)
                decision = payload.get("decision", "CONTINUE")
                ctrl = payload.get("control", {})
                latency = payload.get("latency_ms", 0.0)

                # Simulated UE5 Vehicle HUD / Screen Overlay Output
                print(f"[UE5 HUD DISPLAY] {hud_msg}")
                print(f"       └── [VEHICLE ACTUATORS] Throttle: {ctrl.get('throttle', 1.0):.2f} | Brake: {ctrl.get('brake', 0.0):.2f} | Emergency Stop: {ctrl.get('emergency_stop', False)} | Core Latency: {latency:.2f}ms")

                if max_packets and self.received_count >= max_packets:
                    print(f"[UE5 RECEIVER] Reached target packet count ({max_packets}). Stopping.")
                    break

        except KeyboardInterrupt:
            print("\n[UE5 RECEIVER] Interrupted by user.")
        finally:
            self.close()

    def close(self):
        self.running = False
        self.sock.close()


def main():
    parser = argparse.ArgumentParser(description="SAFAR UE5 Receiver & HUD Listener")
    parser.add_argument("--port", type=int, default=9003, help="UDP port to listen on")
    parser.add_argument("--packets", type=int, default=None, help="Stop after N packets")
    args = parser.parse_args()

    receiver = UE5Receiver(port=args.port)
    receiver.start(max_packets=args.packets)


if __name__ == "__main__":
    main()
