"""Full-screen calibration: user points at 4 corner dots to build a perspective transform."""

import json
import math
import os
import sys
import time

import cv2
import numpy as np

from config import CALIBRATION_FILE, CALIBRATION_HOLD_TIME, CALIBRATION_PADDING
from tracker import HandTracker


def _screen_size():
    """Return (width, height) of the primary monitor."""
    import pyautogui
    return pyautogui.size()


def calibrate(tracker: HandTracker) -> np.ndarray | None:
    """Run the 4-corner calibration and return the 3×3 perspective matrix.

    Returns None if the user aborts and no previous calibration exists.
    """
    sw, sh = _screen_size()

    # Target screen corners (with padding)
    pad = CALIBRATION_PADDING
    corners_screen = [
        (pad, pad),                  # top-left
        (sw - pad, pad),             # top-right
        (sw - pad, sh - pad),        # bottom-right
        (pad, sh - pad),             # bottom-left
    ]
    labels = ["Top-Left", "Top-Right", "Bottom-Right", "Bottom-Left"]

    window_name = "AirTap Calibration"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    collected_cam = []  # normalised camera coords for each corner

    for idx, (sx, sy) in enumerate(corners_screen):
        hold_start: float | None = None

        while True:
            frame = np.zeros((sh, sw, 3), dtype=np.uint8)

            # Draw target dot
            cv2.circle(frame, (sx, sy), 18, (0, 0, 255), -1)
            cv2.circle(frame, (sx, sy), 30, (0, 0, 180), 2)

            # Label
            cv2.putText(
                frame,
                f"Point at {labels[idx]} ({idx + 1}/4)",
                (sw // 2 - 200, sh // 2 - 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (255, 255, 255),
                2,
            )
            cv2.putText(
                frame,
                "Hold your index finger steady toward the red dot",
                (sw // 2 - 330, sh // 2 + 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (180, 180, 180),
                1,
            )

            state = tracker.get_hand_state()

            if state["detected"]:
                nx, ny = state["index_tip"]

                # Draw crosshair showing where the tracker sees the finger
                fx, fy = int(nx * sw), int(ny * sh)
                cv2.drawMarker(frame, (fx, fy), (255, 255, 0), cv2.MARKER_CROSS, 20, 2)
                cv2.putText(
                    frame,
                    f"({nx:.2f}, {ny:.2f})",
                    (fx + 15, fy - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 255, 0),
                    1,
                )

                # No proximity check — we can't map accurately before calibration.
                # Just require the hand to be detected and held steady.
                if hold_start is None:
                    hold_start = time.time()
                elapsed = time.time() - hold_start
                progress = min(elapsed / CALIBRATION_HOLD_TIME, 1.0)

                # Countdown ring around the target dot
                angle = int(360 * progress)
                cv2.ellipse(
                    frame,
                    (sx, sy),
                    (30, 30),
                    -90,
                    0,
                    angle,
                    (0, 255, 0),
                    3,
                )

                # Progress text
                remaining = max(0, CALIBRATION_HOLD_TIME - elapsed)
                cv2.putText(
                    frame,
                    f"{remaining:.1f}s",
                    (sx - 20, sy + 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2,
                )

                if elapsed >= CALIBRATION_HOLD_TIME:
                    collected_cam.append((nx, ny))
                    break
            else:
                hold_start = None
                # Show "no hand" status
                cv2.putText(
                    frame,
                    "No hand detected — show your hand to the camera",
                    (sw // 2 - 350, sh // 2 + 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 0, 255),
                    1,
                )

            cv2.imshow(window_name, frame)
            key = cv2.waitKey(30) & 0xFF
            if key in (27, ord("q")):  # ESC / Q to abort
                cv2.destroyWindow(window_name)
                # Try to load a previous calibration instead of exiting
                prev = load_calibration()
                if prev is not None:
                    print("[AirTap] Calibration cancelled — using previous calibration.")
                    return prev
                print("[AirTap] Calibration cancelled — no previous calibration found, retrying...")
                return calibrate(tracker)

    cv2.destroyWindow(window_name)

    # Build perspective transform: camera normalised → screen pixels
    src = np.array(collected_cam, dtype=np.float32)
    dst = np.array(corners_screen, dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(src, dst)

    # Validate — a degenerate matrix (e.g. collinear points) will have near-zero determinant
    det = np.linalg.det(matrix)
    if abs(det) < 1e-6 or not np.isfinite(matrix).all():
        print("[AirTap] WARNING: Calibration produced an invalid matrix. Please recalibrate.")
        print("[AirTap] Tip: point at each corner carefully and keep your hand steady.")
        return calibrate(tracker)  # retry automatically

    # Save to disk
    save_calibration(matrix, collected_cam, corners_screen)
    return matrix


def save_calibration(matrix: np.ndarray, cam_pts, screen_pts):
    data = {
        "matrix": matrix.tolist(),
        "camera_points": cam_pts,
        "screen_points": screen_pts,
    }
    with open(CALIBRATION_FILE, "w") as f:
        json.dump(data, f, indent=2)


def load_calibration() -> np.ndarray | None:
    """Load the perspective matrix from disk, or return None."""
    if not os.path.exists(CALIBRATION_FILE):
        return None
    with open(CALIBRATION_FILE) as f:
        data = json.load(f)
    return np.array(data["matrix"], dtype=np.float32)
