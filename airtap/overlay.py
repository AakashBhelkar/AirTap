"""Full-screen translucent overlay with webcam preview, cursor dot, and gesture labels."""

import time

import cv2
import numpy as np
from PyQt6.QtCore import Qt, QTimer, QRect
from PyQt6.QtGui import QImage, QPainter, QColor, QFont, QPen, QBrush, QPainterPath, QRegion
from PyQt6.QtWidgets import QWidget, QApplication

from mode_manager import Mode, MODE_COLORS

# MediaPipe hand connections for skeleton drawing
_HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),       # thumb
    (0, 5), (5, 6), (6, 7), (7, 8),       # index
    (0, 9), (9, 10), (10, 11), (11, 12),   # middle
    (0, 13), (13, 14), (14, 15), (15, 16), # ring
    (0, 17), (17, 18), (18, 19), (19, 20), # pinky
    (5, 9), (9, 13), (13, 17),             # palm
]

# Webcam preview size
_PREVIEW_W = 320
_PREVIEW_H = 240
_PREVIEW_MARGIN = 20
_PREVIEW_RADIUS = 16


class Overlay(QWidget):
    """Transparent always-on-top overlay that is click-through."""

    def __init__(self, tracker, cursor_ctrl, mode_mgr, gesture_engine):
        super().__init__()
        self._tracker = tracker
        self._cursor = cursor_ctrl
        self._mode_mgr = mode_mgr
        self._engine = gesture_engine

        # State for rendering
        self._hand_state: dict = {}
        self._cursor_pos = (0, 0)
        self._gesture = "idle"
        self._action: str | None = None
        self._action_expire = 0.0
        self._tap_flash_until = 0.0
        self._rclick_flash_until = 0.0

        screen = QApplication.primaryScreen().geometry()
        self._sw = screen.width()
        self._sh = screen.height()

        # Window flags: frameless, always-on-top, transparent, tool window (no taskbar)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput  # click-through
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setGeometry(0, 0, self._sw, self._sh)

        # Refresh timer — 40ms = 25fps
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(40)

    # ------------------------------------------------------------------
    # Public API — called from main loop to push state
    # ------------------------------------------------------------------

    def update_subsystems(self, cursor_ctrl, gesture_engine):
        """Update internal references after re-calibration."""
        self._cursor = cursor_ctrl
        self._engine = gesture_engine

    def push_state(self, hand_state: dict, cursor_pos: tuple, gesture: str, action: str | None):
        self._hand_state = hand_state
        self._cursor_pos = cursor_pos
        self._gesture = gesture
        now = time.time()
        if action:
            self._action = action
            self._action_expire = now + 2.0
            if action == "Left Click":
                self._tap_flash_until = now + 0.2
            elif action == "Right Click":
                self._rclick_flash_until = now + 0.2
        if now > self._action_expire:
            self._action = None

    def _tick(self):
        self.update()  # triggers paintEvent

    # ------------------------------------------------------------------
    # Paint
    # ------------------------------------------------------------------

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1. Dark tint over entire screen (15% opacity)
        p.fillRect(0, 0, self._sw, self._sh, QColor(0, 0, 0, 38))

        # 2. Mode badge — top right
        self._draw_mode_badge(p)

        # 3. Cursor indicator dot
        self._draw_cursor_dot(p)

        # 4. Gesture label pill below cursor
        self._draw_gesture_label(p)

        # 5. Webcam preview — bottom right with skeleton
        self._draw_webcam_preview(p)

        # 6. Action flash text — center of screen
        if self._action:
            self._draw_action_toast(p)

        p.end()

    # ------------------------------------------------------------------
    # Drawing helpers
    # ------------------------------------------------------------------

    def _draw_mode_badge(self, p: QPainter):
        mode = self._mode_mgr.get_mode()
        # Convert BGR color from mode_manager to RGB
        bgr = MODE_COLORS[mode]
        color = QColor(bgr[2], bgr[1], bgr[0])

        text = mode.value
        font = QFont("Segoe UI", 14, QFont.Weight.Bold)
        p.setFont(font)
        fm = p.fontMetrics()
        tw = fm.horizontalAdvance(text)
        th = fm.height()

        pad_x, pad_y = 16, 8
        rx = self._sw - tw - pad_x * 2 - 20
        ry = 20
        rw = tw + pad_x * 2
        rh = th + pad_y * 2

        # Background pill
        path = QPainterPath()
        path.addRoundedRect(float(rx), float(ry), float(rw), float(rh), 12, 12)
        p.fillPath(path, QColor(0, 0, 0, 160))
        p.setPen(QPen(color, 2))
        p.drawPath(path)

        # Text
        p.setPen(color)
        p.drawText(rx + pad_x, ry + pad_y + fm.ascent(), text)

    def _draw_cursor_dot(self, p: QPainter):
        cx, cy = self._cursor_pos
        now = time.time()

        # Color based on state
        if now < self._tap_flash_until:
            color = QColor(0, 255, 100)   # green flash — tap
        elif now < self._rclick_flash_until:
            color = QColor(255, 60, 60)   # red flash — right click
        elif self._gesture == "pointing":
            color = QColor(60, 140, 255)  # blue — moving
        elif self._gesture == "two_fingers":
            color = QColor(200, 120, 255) # purple — scroll
        else:
            color = QColor(220, 220, 220) # white — idle

        # Outer glow
        glow = QColor(color)
        glow.setAlpha(60)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(glow))
        p.drawEllipse(int(cx) - 16, int(cy) - 16, 32, 32)

        # Inner dot
        p.setBrush(QBrush(color))
        p.drawEllipse(int(cx) - 10, int(cy) - 10, 20, 20)

    def _draw_gesture_label(self, p: QPainter):
        cx, cy = self._cursor_pos
        text = self._gesture
        if not text:
            return

        font = QFont("Segoe UI", 10)
        p.setFont(font)
        fm = p.fontMetrics()
        tw = fm.horizontalAdvance(text)
        th = fm.height()

        pad_x, pad_y = 10, 4
        lx = int(cx) - tw // 2 - pad_x
        ly = int(cy) + 22
        lw = tw + pad_x * 2
        lh = th + pad_y * 2

        # Pill background
        path = QPainterPath()
        path.addRoundedRect(float(lx), float(ly), float(lw), float(lh), 10, 10)
        p.fillPath(path, QColor(0, 0, 0, 140))

        # Text
        p.setPen(QColor(230, 230, 230))
        p.drawText(lx + pad_x, ly + pad_y + fm.ascent(), text)

    def _draw_webcam_preview(self, p: QPainter):
        frame = self._tracker.get_frame()
        if frame is None:
            return

        # Resize to preview dimensions
        preview = cv2.resize(frame, (_PREVIEW_W, _PREVIEW_H), interpolation=cv2.INTER_LINEAR)

        # Draw hand skeleton on the preview
        state = self._hand_state
        if state.get("detected") and state.get("landmarks"):
            lm = state["landmarks"]
            h, w = preview.shape[:2]
            # Draw connections
            for i, j in _HAND_CONNECTIONS:
                x1, y1 = int(lm[i][0] * w), int(lm[i][1] * h)
                x2, y2 = int(lm[j][0] * w), int(lm[j][1] * h)
                cv2.line(preview, (x1, y1), (x2, y2), (0, 255, 128), 2)
            # Draw landmark dots
            for pt in lm:
                x, y = int(pt[0] * w), int(pt[1] * h)
                cv2.circle(preview, (x, y), 3, (255, 100, 100), -1)

        # Convert RGB numpy → QImage
        h, w, ch = preview.shape
        bytes_per_line = ch * w
        qimg = QImage(preview.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)

        # Position: bottom-right with margin
        px = self._sw - _PREVIEW_W - _PREVIEW_MARGIN
        py = self._sh - _PREVIEW_H - _PREVIEW_MARGIN

        # Clip to rounded rect
        clip_path = QPainterPath()
        clip_path.addRoundedRect(
            float(px), float(py), float(_PREVIEW_W), float(_PREVIEW_H),
            _PREVIEW_RADIUS, _PREVIEW_RADIUS,
        )
        p.save()
        p.setClipPath(clip_path)
        p.setOpacity(0.80)
        p.drawImage(px, py, qimg)
        p.setOpacity(1.0)
        p.restore()

        # Border
        p.setPen(QPen(QColor(255, 255, 255, 80), 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(px, py, _PREVIEW_W, _PREVIEW_H, _PREVIEW_RADIUS, _PREVIEW_RADIUS)

    def _draw_action_toast(self, p: QPainter):
        text = self._action or ""
        font = QFont("Segoe UI", 18, QFont.Weight.Bold)
        p.setFont(font)
        fm = p.fontMetrics()
        tw = fm.horizontalAdvance(text)
        th = fm.height()

        pad_x, pad_y = 24, 12
        tx = self._sw // 2 - tw // 2 - pad_x
        ty = self._sh - 120
        bw = tw + pad_x * 2
        bh = th + pad_y * 2

        path = QPainterPath()
        path.addRoundedRect(float(tx), float(ty), float(bw), float(bh), 14, 14)
        p.fillPath(path, QColor(0, 0, 0, 180))

        p.setPen(QColor(0, 255, 200))
        p.drawText(tx + pad_x, ty + pad_y + fm.ascent(), text)
