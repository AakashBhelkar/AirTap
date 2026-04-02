"""Cursor control — maps normalised hand coordinates to screen via perspective transform."""

import time

import cv2
import numpy as np
import pyautogui

from config import SMOOTHING_ALPHA, CLICK_COOLDOWN, SCROLL_SENSITIVITY, CURSOR_DEAD_ZONE

# Disable pyautogui's built-in pause and fail-safe for responsiveness
pyautogui.PAUSE = 0
pyautogui.FAILSAFE = True  # move mouse to corner to kill


class CursorController:
    def __init__(self, matrix: np.ndarray):
        self._matrix = matrix
        self._smooth_x: float | None = None
        self._smooth_y: float | None = None
        self._last_click = 0.0
        self._sw, self._sh = pyautogui.size()
        self._scroll_accum: float = 0.0

    def move_cursor(self, norm_x: float, norm_y: float):
        """Transform normalised camera coords → screen coords and move the cursor."""
        # Apply perspective transform
        pt = np.array([[[norm_x, norm_y]]], dtype=np.float32)
        transformed = cv2.perspectiveTransform(pt, self._matrix)
        sx, sy = transformed[0][0]

        # Clamp to screen bounds (keep 5px margin to avoid pyautogui failsafe)
        sx = max(5, min(sx, self._sw - 6))
        sy = max(5, min(sy, self._sh - 6))

        # Exponential moving average for smoothing
        if self._smooth_x is None:
            self._smooth_x, self._smooth_y = sx, sy
        else:
            self._smooth_x += SMOOTHING_ALPHA * (sx - self._smooth_x)
            self._smooth_y += SMOOTHING_ALPHA * (sy - self._smooth_y)

        # Dead zone — skip tiny jittery movements
        cur_x, cur_y = pyautogui.position()
        dx = abs(int(self._smooth_x) - cur_x)
        dy = abs(int(self._smooth_y) - cur_y)
        if dx < CURSOR_DEAD_ZONE and dy < CURSOR_DEAD_ZONE:
            return

        pyautogui.moveTo(int(self._smooth_x), int(self._smooth_y), _pause=False)

    def do_click(self) -> bool:
        """Perform a left click if cooldown has elapsed. Returns True if clicked."""
        now = time.time()
        if now - self._last_click < CLICK_COOLDOWN:
            return False
        self._last_click = now
        pyautogui.click(_pause=False)
        return True

    def do_right_click(self) -> bool:
        """Perform a right click if cooldown has elapsed."""
        now = time.time()
        if now - self._last_click < CLICK_COOLDOWN:
            return False
        self._last_click = now
        pyautogui.rightClick(_pause=False)
        return True

    def do_scroll(self, delta_y: float):
        """Scroll by a normalized vertical delta (negative = up, positive = down)."""
        self._scroll_accum += -delta_y * SCROLL_SENSITIVITY
        clicks = int(self._scroll_accum)
        if clicks != 0:
            pyautogui.scroll(clicks, _pause=False)
            self._scroll_accum -= clicks  # keep the fractional remainder

    @property
    def click_ready(self) -> bool:
        return time.time() - self._last_click >= CLICK_COOLDOWN
