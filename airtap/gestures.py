"""Gesture Action Engine — maps hand gestures to system actions per mode."""

import time
from collections import deque

import pyautogui

from config import (
    GESTURE_HISTORY_SIZE,
    SWIPE_TIME_WINDOW,
    get_value,
)
from mode_manager import Mode
from cursor import CursorController
from sounds import sound_click, sound_right_click, sound_scroll, sound_action


def _get_gesture_map(mode: Mode) -> dict:
    """Return the gesture-to-action map for the given mode."""
    if mode == Mode.DAILY:
        return get_value("GESTURE_MAP_DAILY")
    elif mode == Mode.PRESENTATION:
        return get_value("GESTURE_MAP_PRESENTATION")
    elif mode == Mode.MEDIA:
        return get_value("GESTURE_MAP_MEDIA")
    return {}


class GestureEngine:
    """Consumes hand-state frames and fires actions based on the active mode."""

    def __init__(self, cursor: CursorController):
        self._cursor = cursor
        # Ring buffer of (timestamp, hand_state) for swipe / motion detection
        self._history: deque = deque(maxlen=GESTURE_HISTORY_SIZE)

        # Hold timers — track when a gesture started being held
        self._hold_gesture: str | None = None
        self._hold_start: float = 0.0

        # Swipe cooldown to avoid double-fire
        self._last_swipe_time: float = 0.0

        # Scroll tracking
        self._last_scroll_y: float | None = None

        # Volume tracking
        self._last_vol_y: float | None = None

        # Laser pointer state
        self.laser_active = False

        # Gesture debounce — must see same gesture for N frames before acting
        self._stable_gesture: str = "idle"
        self._gesture_count: int = 0
        self._DEBOUNCE_FRAMES = 3

        # Cursor freeze — after a tap, freeze cursor briefly so it doesn't drift
        self._cursor_frozen_until: float = 0.0

        # Second-hand modifier (shift/ctrl/alt or None)
        self._modifier: str | None = None

    # ------------------------------------------------------------------
    # Main entry — call once per frame
    # ------------------------------------------------------------------

    def update(self, state: dict, mode: Mode) -> str | None:
        """Process one frame. Returns a human-readable action label or None."""
        now = time.time()
        self._history.append((now, state))

        # Track modifier from second hand
        self._modifier = state.get("modifier")

        if not state["detected"]:
            self._reset_holds()
            self._last_scroll_y = None
            self._last_vol_y = None
            self.laser_active = False
            self._stable_gesture = "idle"
            self._gesture_count = 0
            return None

        raw_gesture = state["gesture"]
        nx, ny = state["index_tip"]

        # Debounce: require the same gesture for N consecutive frames
        # Exception: "tap" is instantaneous — only accept if we were pointing
        if raw_gesture == "tap":
            gesture = "tap" if self._stable_gesture == "pointing" else self._stable_gesture
        elif raw_gesture == self._stable_gesture:
            self._gesture_count += 1
            gesture = raw_gesture if self._gesture_count >= self._DEBOUNCE_FRAMES else self._stable_gesture
        else:
            self._gesture_count = 1
            self._stable_gesture = raw_gesture
            gesture = raw_gesture if self._DEBOUNCE_FRAMES <= 1 else "idle"

        if mode == Mode.DAILY:
            return self._daily(state, gesture, nx, ny, now)
        elif mode == Mode.PRESENTATION:
            return self._presentation(state, gesture, nx, ny, now)
        elif mode == Mode.MEDIA:
            return self._media(state, gesture, nx, ny, now)
        return None

    # ------------------------------------------------------------------
    # DAILY mode
    # ------------------------------------------------------------------

    def _daily(self, state, gesture, nx, ny, now) -> str | None:
        gmap = _get_gesture_map(Mode.DAILY)
        cursor_frozen = now < self._cursor_frozen_until

        # Pointing → move cursor (skip if frozen after a tap)
        if gesture in ("pointing", "idle") and not cursor_frozen:
            if gmap.get("pointing") == "move_cursor":
                self._cursor.move_cursor(nx, ny)
            self._last_scroll_y = None

        # Tap → left click (only from pointing, cursor freezes to avoid drift)
        if gesture == "tap" and gmap.get("tap"):
            if self._modifier:
                # Hold modifier key during click (e.g., shift+click, ctrl+click)
                import pyautogui as _pag
                _pag.keyDown(self._modifier)
                clicked = self._cursor.do_click()
                _pag.keyUp(self._modifier)
                if clicked:
                    self._cursor_frozen_until = now + 0.4
                    sound_click()
                    return f"{self._modifier.capitalize()}+Click"
            elif self._cursor.do_click():
                self._cursor_frozen_until = now + 0.4
                sound_click()
                return "Left Click"

        # Pinch held → right click
        if gesture == "pinch" and gmap.get("pinch"):
            action = self._check_hold("pinch", get_value("HOLD_PINCH_RIGHT_CLICK"), now)
            if action:
                if self._cursor.do_right_click():
                    sound_right_click()
                    return "Right Click"
        else:
            if self._hold_gesture == "pinch":
                self._reset_holds()

        # Two fingers → scroll
        if gesture == "two_fingers" and gmap.get("two_fingers"):
            if self._last_scroll_y is not None:
                delta = ny - self._last_scroll_y
                if abs(delta) > 0.008:
                    self._cursor.do_scroll(delta)
                    self._last_scroll_y = ny
            else:
                self._last_scroll_y = ny
            return "Scroll"
        else:
            self._last_scroll_y = None
            self._cursor._scroll_accum = 0.0

        # Open palm swipe up → show desktop
        if gesture == "open_palm" and gmap.get("open_palm"):
            swipe = self._detect_swipe_vertical()
            if swipe == "up":
                pyautogui.hotkey("win", "d", _pause=False)
                return "Show Desktop"

        return None

    # ------------------------------------------------------------------
    # PRESENTATION mode
    # ------------------------------------------------------------------

    def _presentation(self, state, gesture, nx, ny, now) -> str | None:
        gmap = _get_gesture_map(Mode.PRESENTATION)

        # Always move cursor when hand detected (for laser pointer)
        if gesture in ("pointing", "idle", "open_palm"):
            if gmap.get("pointing") == "move_cursor":
                self._cursor.move_cursor(nx, ny)

        # Swipe → slides
        swipe = self._detect_swipe_horizontal()
        if swipe == "right" and gmap.get("swipe_right"):
            pyautogui.press("right", _pause=False)
            return "Next Slide"
        if swipe == "left" and gmap.get("swipe_left"):
            pyautogui.press("left", _pause=False)
            return "Prev Slide"

        # Open palm held → fullscreen
        if gesture == "open_palm" and gmap.get("open_palm"):
            action = self._check_hold("open_palm", get_value("HOLD_OPEN_PALM_FULLSCREEN"), now)
            if action:
                pyautogui.press("f5", _pause=False)
                return "Toggle Fullscreen"
        else:
            if self._hold_gesture == "open_palm":
                self._reset_holds()

        # Pinch held → laser pointer
        if gesture == "pinch" and gmap.get("pinch"):
            self._cursor.move_cursor(nx, ny)
            action = self._check_hold("pinch", get_value("HOLD_PINCH_LASER"), now)
            if action:
                self.laser_active = True
                return "Laser ON"
            return None
        else:
            if self.laser_active:
                self.laser_active = False
                return "Laser OFF"
            if self._hold_gesture == "pinch":
                self._reset_holds()

        return None

    # ------------------------------------------------------------------
    # MEDIA mode
    # ------------------------------------------------------------------

    def _media(self, state, gesture, nx, ny, now) -> str | None:
        gmap = _get_gesture_map(Mode.MEDIA)

        # Swipe → tracks
        swipe = self._detect_swipe_horizontal()
        if swipe == "right" and gmap.get("swipe_right"):
            pyautogui.press("nexttrack", _pause=False)
            return "Next Track"
        if swipe == "left" and gmap.get("swipe_left"):
            pyautogui.press("prevtrack", _pause=False)
            return "Prev Track"

        # Pinch → play/pause
        if gesture == "pinch" and gmap.get("pinch"):
            action = self._check_hold("pinch_media", 0.3, now)
            if action:
                pyautogui.press("playpause", _pause=False)
                return "Play/Pause"
        else:
            if self._hold_gesture == "pinch_media":
                self._reset_holds()

        # Open palm + vertical motion → volume
        if gesture == "open_palm" and gmap.get("open_palm"):
            if self._last_vol_y is not None:
                delta = ny - self._last_vol_y
                if abs(delta) > 0.02:
                    presses = int(abs(delta) * get_value("VOLUME_SENSITIVITY"))
                    presses = max(1, min(presses, get_value("MAX_VOLUME_PRESSES")))
                    if delta < 0:
                        for _ in range(presses):
                            pyautogui.press("volumeup", _pause=False)
                        self._last_vol_y = ny
                        return "Volume Up"
                    else:
                        for _ in range(presses):
                            pyautogui.press("volumedown", _pause=False)
                        self._last_vol_y = ny
                        return "Volume Down"
            self._last_vol_y = ny
        else:
            self._last_vol_y = None

        return None

    # ------------------------------------------------------------------
    # Swipe detection
    # ------------------------------------------------------------------

    def _detect_swipe_horizontal(self) -> str | None:
        """Check recent history for a horizontal swipe. Returns 'left', 'right', or None."""
        now = time.time()
        if now - self._last_swipe_time < 0.6:
            return None

        if len(self._history) < 5:
            return None

        # Collect x positions within the swipe time window
        points = []
        for ts, st in self._history:
            if now - ts <= SWIPE_TIME_WINDOW and st["detected"]:
                points.append((ts, st["index_tip"][0]))

        if len(points) < 4:
            return None

        x_start = points[0][1]
        x_end = points[-1][1]
        dx = x_end - x_start

        if abs(dx) >= get_value("SWIPE_MIN_DISTANCE"):
            self._last_swipe_time = now
            self._history.clear()
            return "right" if dx > 0 else "left"

        return None

    def _detect_swipe_vertical(self) -> str | None:
        """Check recent history for a vertical swipe. Returns 'up', 'down', or None."""
        now = time.time()
        if now - self._last_swipe_time < 0.6:
            return None

        if len(self._history) < 5:
            return None

        points = []
        for ts, st in self._history:
            if now - ts <= SWIPE_TIME_WINDOW and st["detected"]:
                points.append((ts, st["index_tip"][1]))

        if len(points) < 4:
            return None

        y_start = points[0][1]
        y_end = points[-1][1]
        dy = y_end - y_start

        if abs(dy) >= get_value("SWIPE_MIN_DISTANCE"):
            self._last_swipe_time = now
            self._history.clear()
            return "down" if dy > 0 else "up"

        return None

    # ------------------------------------------------------------------
    # Hold detection
    # ------------------------------------------------------------------

    def _check_hold(self, gesture_key: str, duration: float, now: float) -> bool:
        """Returns True once when a gesture has been held for `duration` seconds."""
        if self._hold_gesture != gesture_key:
            self._hold_gesture = gesture_key
            self._hold_start = now
            return False

        if now - self._hold_start >= duration:
            self._reset_holds()
            return True

        return False

    def _reset_holds(self):
        self._hold_gesture = None
        self._hold_start = 0.0
