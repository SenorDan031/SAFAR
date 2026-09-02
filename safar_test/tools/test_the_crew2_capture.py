"""Standalone screen-capture test tool for The Crew 2."""
import argparse
import sys
import time

import cv2

from safar.integrations.the_crew2 import TheCrew2Capture, TheCrew2Config


def main() -> None:
    parser = argparse.ArgumentParser(description="Test screen capture for The Crew 2")
    parser.add_argument("--window-title", default="The Crew 2", help="Window title to capture")
    parser.add_argument("--width", type=int, default=1280, help="Target capture width")
    parser.add_argument("--height", type=int, default=720, help="Target capture height")
    parser.add_argument("--fps", type=float, default=30.0, help="Target capture FPS")
    parser.add_argument("--max-frames", type=int, default=0, help="Exit after N frames (0 for infinite)")
    parser.add_argument("--headless", action="store_true", help="Run without cv2.imshow GUI")
    args = parser.parse_args()

    config = TheCrew2Config(
        window_titles=(args.window_title, "TheCrew2", "The Crew® 2"),
        capture_width=args.width,
        capture_height=args.height,
        target_fps=args.fps,
    )

    print("=" * 60)
    print("SAFAR × THE CREW 2 SCREEN CAPTURE TEST")
    print("=" * 60)
    print(f"Target window title: {args.window_title}")
    print(f"Target resolution:   {args.width}x{args.height}")
    print(f"Target FPS:          {args.fps}")

    capture = TheCrew2Capture(config)
    found = capture.locate_window()
    if found:
        print(f"[OK] Located target window: '{capture.window_name}' (HWND: {capture.hwnd})")
    else:
        print("[INFO] Target window not found. Running in synthetic/mock frame mode.")

    capture.start_async()
    frame_count = 0
    start_time = time.perf_counter()
    last_print = time.perf_counter()

    try:
        while True:
            ts, frame = capture.read()
            frame_count += 1
            h, w = frame.shape[:2]

            # Overlay info
            if not args.headless:
                cv2.putText(
                    frame,
                    f"The Crew 2 Capture | {w}x{h} | FPS: {capture.fps:.1f}",
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 0),
                    2,
                )
                cv2.putText(
                    frame,
                    f"Window: {capture.window_name} | Press Q to exit",
                    (20, 75),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 255),
                    1,
                )
                cv2.imshow("The Crew 2 Capture Test", frame)
                if cv2.waitKey(1) & 0xFF in (ord("q"), ord("Q")):
                    print("\nExit requested by user (Q pressed).")
                    break

            now = time.perf_counter()
            if now - last_print >= 1.0:
                elapsed = now - start_time
                avg_fps = frame_count / elapsed if elapsed > 0 else 0
                print(f"[{elapsed:6.1f}s] Captured {frame_count} frames | Instant FPS: {capture.fps:5.1f} | Avg FPS: {avg_fps:5.1f} | Dim: {w}x{h}")
                last_print = now

            if args.max_frames > 0 and frame_count >= args.max_frames:
                print(f"\nReached max frames limit ({args.max_frames}).")
                break

    except KeyboardInterrupt:
        print("\nInterrupted by Ctrl+C.")
    finally:
        capture.release()
        if not args.headless:
            cv2.destroyAllWindows()

    total_time = time.perf_counter() - start_time
    avg_fps = frame_count / total_time if total_time > 0 else 0
    print("=" * 60)
    print(f"CAPTURE TEST SUMMARY: {frame_count} frames in {total_time:.2f}s ({avg_fps:.1f} FPS)")
    print("=" * 60)


if __name__ == "__main__":
    main()
