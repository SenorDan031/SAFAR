"""Display a live local phone IP-camera stream using OpenCV."""

import argparse

import cv2

from safar.perception.camera import CameraStreamError, PhoneCamera


def main() -> None:
    """Connect to the configured stream and show frames until Q is pressed."""
    parser = argparse.ArgumentParser(description="SAFAR phone camera test")
    parser.add_argument("--url", required=True, help="Local HTTP/MJPEG or RTSP URL, e.g. rtsp://PHONE_IP:8554/path")
    args = parser.parse_args()
    print("=== SAFAR Phone Camera Test ===")
    print(f"Stream: {args.url}")
    print("Connecting...")
    camera = PhoneCamera(args.url)
    try:
        camera.connect()
        print("Camera stream connected. Press Q in the video window to exit.")
        while True:
            try:
                frame = camera.read()
            except CameraStreamError as error:
                print(f"ERROR: {error}")
                break
            cv2.imshow("SAFAR Phone Camera", frame)
            if cv2.waitKey(1) & 0xFF in (ord("q"), ord("Q")):
                break
    except CameraStreamError as error:
        print(f"ERROR: {error}")
    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
