"""Hand tracking via MediaPipe Tasks API — extracts landmarks, finger states, and gestures."""

import os
import time
import threading
from collections import deque

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

from config import (
    WEBCAM_SOURCE,
    CAMERA_WIDTH,
    CAMERA_HEIGHT,
    TAP_VELOCITY_THRESHOLD,
    PINCH_DISTANCE_THRESHOLD,
)

# Path to the hand landmarker model (sits next to this file)
_MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hand_landmarker.task")

# MediaPipe hand landmark indices
WRIST = 0
THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP = 1, 2, 3, 4
INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP = 5, 6, 7, 8
MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP = 9, 10, 11, 12
RING_MCP, RING_PIP, RING_DIP, RING_TIP = 13, 14, 15, 16
PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP = 17, 18, 19, 20


class HandTracker:
    """Captures webcam frames and produces hand-state dicts."""

    def __init__(self):
        self.cap = self._open_camera()
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

        # New MediaPipe Tasks API — VIDEO mode for sequential frame processing
        base_options = mp_python.BaseOptions(model_asset_path=_MODEL_PATH)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_hands=1,
            min_hand_detection_confidence=0.7,
            min_tracking_confidence=0.6,
        )
        self._landmarker = vision.HandLandmarker.create_from_options(options)

        self._lock = threading.Lock()
        self._state = self._empty_state()
        self._last_frame: np.ndarray | None = None  # latest mirrored RGB frame
        self._running = False
        self._frame_timestamp_ms = 0

        # Camera health tracking
        self._consecutive_failures = 0
        self._camera_ok = True
        self._FAILURE_THRESHOLD = 30  # ~1 second at 30fps before flagging

        # For tap detection: keep recent index-tip y positions with timestamps
        self._y_history: deque = deque(maxlen=10)
        self._tap_cooldown = 0.0

    @staticmethod
    def _open_camera() -> cv2.VideoCapture:
        """Open a camera: use WEBCAM_SOURCE if set, otherwise auto-detect."""
        if WEBCAM_SOURCE is not None:
            cap = cv2.VideoCapture(WEBCAM_SOURCE)
            if cap.isOpened():
                print(f"[AirTap] Opened configured camera: {WEBCAM_SOURCE!r}")
                return cap
            cap.release()
            print(f"[AirTap] Configured source {WEBCAM_SOURCE!r} unavailable, scanning...")

        # Auto-detect: try indices 0–4
        for idx in range(5):
            cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    print(f"[AirTap] Auto-detected camera at index {idx}")
                    return cap
            cap.release()

        raise RuntimeError(
            "No camera found. Connect a camera or set WEBCAM_SOURCE in config.py."
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self):
        """Begin capturing in a background thread."""
        self._running = True
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()

    def stop(self):
        self._running = False
        self.cap.release()
        self._landmarker.close()

    def get_hand_state(self) -> dict:
        with self._lock:
            return self._state.copy()

    def get_frame(self) -> np.ndarray | None:
        """Return the latest mirrored RGB frame, or None."""
        with self._lock:
            return self._last_frame.copy() if self._last_frame is not None else None

    @property
    def camera_ok(self) -> bool:
        """False if the camera has been failing to deliver frames."""
        with self._lock:
            return self._camera_ok

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _empty_state() -> dict:
        return {
            "landmarks": [],
            "index_tip": (0.0, 0.0),
            "fingers_up": [False, False, False, False, False],
            "gesture": "idle",
            "detected": False,
        }

    def _loop(self):
        while self._running:
            ok, frame = self.cap.read()
            if not ok:
                self._consecutive_failures += 1
                if self._consecutive_failures >= self._FAILURE_THRESHOLD:
                    with self._lock:
                        if self._camera_ok:
                            self._camera_ok = False
                            print("[AirTap] WARNING: Camera stopped delivering frames")
                continue

            # Camera recovered or still healthy
            if not self._camera_ok:
                with self._lock:
                    self._camera_ok = True
                print("[AirTap] Camera recovered")
            self._consecutive_failures = 0

            frame = cv2.flip(frame, 1)  # mirror
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Convert to MediaPipe Image
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

            # Monotonically increasing timestamp required by VIDEO mode
            self._frame_timestamp_ms += 33  # ~30 fps
            result = self._landmarker.detect_for_video(mp_image, self._frame_timestamp_ms)

            if result.hand_landmarks:
                hand = result.hand_landmarks[0]
                lm = [(p.x, p.y, p.z) for p in hand]
                index_tip = (lm[INDEX_TIP][0], lm[INDEX_TIP][1])
                fingers = self._fingers_up(lm)
                gesture = self._classify_gesture(lm, fingers)

                state = {
                    "landmarks": lm,
                    "index_tip": index_tip,
                    "fingers_up": fingers,
                    "gesture": gesture,
                    "detected": True,
                }
            else:
                state = self._empty_state()
                self._y_history.clear()

            with self._lock:
                self._state = state
                self._last_frame = rgb

    # ------------------------------------------------------------------
    # Finger detection
    # ------------------------------------------------------------------

    def _fingers_up(self, lm) -> list[bool]:
        """Return [thumb, index, middle, ring, pinky] booleans."""
        # Thumb: compare tip.x vs ip.x (works for right hand in mirrored view)
        thumb = lm[THUMB_TIP][0] < lm[THUMB_IP][0]

        # Other fingers: tip above pip (lower y = higher on screen)
        index = lm[INDEX_TIP][1] < lm[INDEX_PIP][1]
        middle = lm[MIDDLE_TIP][1] < lm[MIDDLE_PIP][1]
        ring = lm[RING_TIP][1] < lm[RING_PIP][1]
        pinky = lm[PINKY_TIP][1] < lm[PINKY_PIP][1]

        return [thumb, index, middle, ring, pinky]

    # ------------------------------------------------------------------
    # Gesture classification
    # ------------------------------------------------------------------

    def _classify_gesture(self, lm, fingers: list[bool]) -> str:
        now = time.time()

        # Pinch: thumb tip ↔ index tip distance
        dist = np.hypot(
            lm[THUMB_TIP][0] - lm[INDEX_TIP][0],
            lm[THUMB_TIP][1] - lm[INDEX_TIP][1],
        )
        if dist < PINCH_DISTANCE_THRESHOLD:
            return "pinch"

        # Tap: rapid downward then upward motion of index tip
        # Only track tap when index finger is up
        if fingers[1]:
            self._y_history.append((now, lm[INDEX_TIP][1]))
        else:
            self._y_history.clear()
        if len(self._y_history) >= 4 and now - self._tap_cooldown > 0.8:
            velocities = []
            items = list(self._y_history)
            for i in range(1, len(items)):
                dt = items[i][0] - items[i - 1][0]
                if dt > 0:
                    velocities.append((items[i][1] - items[i - 1][1]) / dt)
            if len(velocities) >= 2:
                # Look for a positive spike (down) followed by negative (up)
                max_v = max(velocities)
                min_v = min(velocities)
                if max_v > TAP_VELOCITY_THRESHOLD and min_v < -TAP_VELOCITY_THRESHOLD:
                    self._tap_cooldown = now
                    self._y_history.clear()
                    return "tap"

        # Open palm: all 5 fingers up
        if all(fingers):
            return "open_palm"

        # Two fingers: index + middle up, ring + pinky down (thumb ignored — unreliable)
        if fingers[1] and fingers[2] and not fingers[3] and not fingers[4]:
            return "two_fingers"

        # Pointing: only index up (thumb ignored)
        if fingers[1] and not fingers[2] and not fingers[3] and not fingers[4]:
            return "pointing"

        return "idle"
