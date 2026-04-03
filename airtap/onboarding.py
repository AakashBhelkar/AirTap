"""First-run onboarding wizard — guides users through initial setup."""

import os

import cv2
import numpy as np

from config import CALIBRATION_FILE


_FIRST_RUN_FLAG = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), ".airtap_initialized"
)


def is_first_run() -> bool:
    """True if AirTap has never completed setup on this machine."""
    return not os.path.exists(_FIRST_RUN_FLAG) and not os.path.exists(CALIBRATION_FILE)


def mark_setup_complete():
    """Write a flag file so onboarding doesn't run again."""
    with open(_FIRST_RUN_FLAG, "w") as f:
        f.write("1")


def run_onboarding(tracker) -> bool:
    """Show a step-by-step onboarding sequence.

    Returns True if the user completed it, False if they skipped.
    """
    import pyautogui
    sw, sh = pyautogui.size()

    window = "AirTap Setup"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(window, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    steps = [
        {
            "title": "Welcome to AirTap!",
            "body": [
                "Control your computer with hand gestures using your webcam.",
                "",
                "This quick setup will help you get started.",
                "",
                "Press SPACE to continue, or ESC to skip.",
            ],
        },
        {
            "title": "Step 1: Camera Check",
            "body": [
                "Make sure your webcam can see your hand clearly.",
                "Hold your hand up in front of the camera.",
                "",
                "You should see a live preview with your hand detected.",
                "",
                "Press SPACE when you see the green skeleton on your hand.",
            ],
            "show_preview": True,
        },
        {
            "title": "Step 2: Gestures Overview",
            "body": [
                "AirTap recognizes these gestures:",
                "",
                "  POINT (index finger)  ->  Move cursor",
                "  TAP (flick down+up)   ->  Left click",
                "  PINCH (thumb+index)   ->  Right click / Laser / Play",
                "  OPEN PALM (all 5)     ->  Desktop / Fullscreen / Volume",
                "  TWO FINGERS           ->  Scroll up/down",
                "  SWIPE left/right      ->  Slides / Tracks",
                "",
                "Press SPACE to continue.",
            ],
        },
        {
            "title": "Step 3: Calibration Next",
            "body": [
                "Next you'll calibrate by pointing at 4 screen corners.",
                "",
                "  - Point your INDEX FINGER toward each red dot",
                "  - Hold steady for 1.5 seconds per corner",
                "  - A green ring fills up as you hold",
                "",
                "Press SPACE to start calibration.",
            ],
        },
    ]

    for step in steps:
        show_preview = step.get("show_preview", False)

        while True:
            frame = np.zeros((sh, sw, 3), dtype=np.uint8)
            frame[:] = (25, 25, 25)

            # Title
            cv2.putText(
                frame, step["title"],
                (sw // 2 - 250, 120),
                cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 200, 255), 2,
            )

            # Body text
            for i, line in enumerate(step["body"]):
                color = (200, 200, 200) if line else (100, 100, 100)
                cv2.putText(
                    frame, line,
                    (sw // 2 - 350, 200 + i * 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 1,
                )

            # Camera preview during step 1
            if show_preview and tracker is not None:
                cam_frame = tracker.get_frame()
                state = tracker.get_hand_state()
                if cam_frame is not None:
                    preview = cv2.resize(cam_frame, (320, 240))
                    # Draw skeleton if hand detected
                    if state.get("detected") and state.get("landmarks"):
                        lm = state["landmarks"]
                        h, w = preview.shape[:2]
                        connections = [
                            (0,1),(1,2),(2,3),(3,4),(0,5),(5,6),(6,7),(7,8),
                            (0,9),(9,10),(10,11),(11,12),(0,13),(13,14),(14,15),(15,16),
                            (0,17),(17,18),(18,19),(19,20),(5,9),(9,13),(13,17),
                        ]
                        for a, b in connections:
                            x1, y1 = int(lm[a][0]*w), int(lm[a][1]*h)
                            x2, y2 = int(lm[b][0]*w), int(lm[b][1]*h)
                            cv2.line(preview, (x1,y1), (x2,y2), (0,255,128), 2)

                    # Convert RGB to BGR for cv2.imshow
                    preview_bgr = cv2.cvtColor(preview, cv2.COLOR_RGB2BGR)
                    px = sw // 2 - 160
                    py = sh - 300
                    frame[py:py+240, px:px+320] = preview_bgr

                    # Detection status
                    if state.get("detected"):
                        cv2.putText(frame, "Hand detected!", (px, py - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    else:
                        cv2.putText(frame, "Show your hand...", (px, py - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 1)

            # Navigation hint
            cv2.putText(
                frame, "SPACE = Continue    ESC = Skip",
                (sw // 2 - 200, sh - 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 100), 1,
            )

            cv2.imshow(window, frame)
            key = cv2.waitKey(30) & 0xFF

            if key == 32:  # SPACE
                break
            if key == 27:  # ESC
                cv2.destroyWindow(window)
                return False

    cv2.destroyWindow(window)
    return True
