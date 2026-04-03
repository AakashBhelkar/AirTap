"""Gesture tutorial — interactive practice mode with live feedback."""

import time
import cv2
import numpy as np


_GESTURES = [
    {
        "name": "Pointing",
        "key": "pointing",
        "desc": "Extend ONLY your index finger (keep others folded)",
        "action": "This moves the cursor in Daily & Presentation modes",
    },
    {
        "name": "Tap",
        "key": "tap",
        "desc": "Point with index finger, then quickly flick DOWN and UP",
        "action": "This performs a left-click in Daily mode",
    },
    {
        "name": "Pinch",
        "key": "pinch",
        "desc": "Touch your thumb tip to your index finger tip",
        "action": "Right-click (Daily), Laser pointer (Presentation), Play/Pause (Media)",
    },
    {
        "name": "Open Palm",
        "key": "open_palm",
        "desc": "Spread ALL 5 fingers wide open",
        "action": "Show Desktop (Daily), Fullscreen (Presentation), Volume (Media)",
    },
    {
        "name": "Two Fingers",
        "key": "two_fingers",
        "desc": "Raise index + middle fingers (keep ring & pinky down)",
        "action": "This activates scroll mode in Daily mode",
    },
]


def run_tutorial(tracker) -> None:
    """Run the interactive gesture tutorial. Blocks until complete or ESC."""
    import pyautogui
    sw, sh = pyautogui.size()

    window = "AirTap Tutorial"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(window, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    for idx, gesture_info in enumerate(_GESTURES):
        target = gesture_info["key"]
        detected_time = 0.0
        hold_required = 1.5  # hold gesture for 1.5s to pass
        completed = False

        while not completed:
            frame = np.zeros((sh, sw, 3), dtype=np.uint8)
            frame[:] = (25, 25, 25)

            state = tracker.get_hand_state()
            current_gesture = state.get("gesture", "idle")

            # Title
            cv2.putText(
                frame,
                f"Tutorial: {gesture_info['name']} ({idx + 1}/{len(_GESTURES)})",
                (sw // 2 - 300, 80),
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 200, 255), 2,
            )

            # Instructions
            cv2.putText(
                frame, gesture_info["desc"],
                (sw // 2 - 350, 150),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 1,
            )
            cv2.putText(
                frame, gesture_info["action"],
                (sw // 2 - 350, 190),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (150, 150, 150), 1,
            )

            # Current detection status
            if current_gesture == target:
                if detected_time == 0.0:
                    detected_time = time.time()

                elapsed = time.time() - detected_time
                progress = min(elapsed / hold_required, 1.0)

                # Progress bar
                bar_x = sw // 2 - 200
                bar_y = sh // 2
                bar_w = 400
                bar_h = 40
                cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (60, 60, 60), -1)
                fill_w = int(bar_w * progress)
                cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h), (0, 255, 100), -1)
                cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (100, 100, 100), 2)

                cv2.putText(
                    frame, f"Hold it... {progress * 100:.0f}%",
                    (sw // 2 - 80, bar_y - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 100), 2,
                )

                if progress >= 1.0:
                    completed = True
                    # Show success flash
                    success_frame = frame.copy()
                    cv2.putText(
                        success_frame, "Great!",
                        (sw // 2 - 80, bar_y + 100),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3,
                    )
                    cv2.imshow(window, success_frame)
                    cv2.waitKey(800)
                    continue
            else:
                detected_time = 0.0

                status_color = (0, 0, 255) if not state.get("detected") else (0, 180, 255)
                if not state.get("detected"):
                    status_text = "Show your hand to the camera"
                else:
                    status_text = f"Detected: {current_gesture} (need: {gesture_info['name']})"

                cv2.putText(
                    frame, status_text,
                    (sw // 2 - 250, sh // 2 + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 1,
                )

            # Camera preview (small, bottom-right)
            cam_frame = tracker.get_frame()
            if cam_frame is not None:
                preview = cv2.resize(cam_frame, (240, 180))
                preview_bgr = cv2.cvtColor(preview, cv2.COLOR_RGB2BGR)
                px, py = sw - 260, sh - 200
                frame[py:py + 180, px:px + 240] = preview_bgr

            # Navigation
            cv2.putText(
                frame, "ESC = Exit Tutorial    SPACE = Skip Gesture",
                (sw // 2 - 250, sh - 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1,
            )

            cv2.imshow(window, frame)
            key = cv2.waitKey(30) & 0xFF
            if key == 27:  # ESC
                cv2.destroyWindow(window)
                return
            if key == 32:  # SPACE to skip
                break

    # All done
    frame = np.zeros((sh, sw, 3), dtype=np.uint8)
    frame[:] = (25, 25, 25)
    cv2.putText(
        frame, "Tutorial Complete!",
        (sw // 2 - 220, sh // 2 - 20),
        cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 100), 3,
    )
    cv2.putText(
        frame, "You're ready to use AirTap. Press any key to continue.",
        (sw // 2 - 320, sh // 2 + 40),
        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 1,
    )
    cv2.imshow(window, frame)
    cv2.waitKey(0)
    cv2.destroyWindow(window)
