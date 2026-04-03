"""AirTap — touchless hand-gesture controller.  Phase 4 entry point."""

import argparse
import ctypes
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Enable DPI awareness so screen coordinates match physical pixels on high-DPI displays.
# Must be called before any GUI/screen-size operations.
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
except (AttributeError, OSError):
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except (AttributeError, OSError):
        pass

import cv2
import numpy as np
import pyautogui
import keyboard
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

import logging

from config import (
    HUD_WIDTH, HUD_HEIGHT, SCREENSHOT_DIR, LOG_DIR, MAX_LOG_FILES,
    HOTKEY_DAILY, HOTKEY_PRESENTATION, HOTKEY_MEDIA, HOTKEY_DISABLE, HOTKEY_OVERLAY,
)
from tracker import HandTracker
from calibration import load_calibration, calibrate
from cursor import CursorController
from mode_manager import ModeManager, Mode, MODE_COLORS
from gestures import GestureEngine
from overlay import Overlay
from voice_listener import VoiceListener, MicStatus
from notifications import (
    notify_mode_switch,
    notify_enabled,
    notify_disabled,
    notify_screenshot,
    notify_calibration_complete,
    notify_voice_command,
)
from startup import SystemTray


# Mic status colors (BGR for OpenCV HUD)
_MIC_COLORS = {
    MicStatus.LISTENING: (0, 255, 0),    # green
    MicStatus.PROCESSING: (0, 0, 255),   # red
    MicStatus.DISABLED: (128, 128, 128), # grey
    MicStatus.ERROR: (128, 128, 128),    # grey
}


def build_hud(
    fps: float,
    gesture: str,
    mode: Mode,
    action: str | None,
    click_ready: bool,
    laser: bool,
    overlay_on: bool,
    mic_status: MicStatus,
    cam_ok: bool = True,
) -> np.ndarray:
    """Render the small status HUD overlay."""
    hud = np.zeros((HUD_HEIGHT, HUD_WIDTH, 3), dtype=np.uint8)
    hud[:] = (30, 30, 30)

    cv2.putText(hud, "AirTap", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 1)

    mode_color = MODE_COLORS[mode]
    cv2.putText(hud, f"Mode: {mode.value}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, mode_color, 1)

    cv2.putText(hud, f"FPS: {fps:.0f}", (10, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    cv2.putText(hud, f"Gesture: {gesture}", (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

    action_text = action or ""
    cv2.putText(hud, f"Action: {action_text}", (10, 125), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 200), 1)

    # Status dots — right side
    x_right = HUD_WIDTH - 20

    # Click ready dot
    clr = (0, 255, 0) if click_ready else (0, 0, 255)
    cv2.circle(hud, (x_right, 20), 6, clr, -1)

    # Laser dot
    if laser:
        cv2.circle(hud, (x_right - 20, 20), 6, (0, 0, 255), -1)

    # Camera indicator
    cam_clr = (0, 255, 0) if cam_ok else (0, 0, 255)
    cv2.circle(hud, (x_right, 68), 5, cam_clr, -1)
    cv2.putText(hud, "CAM", (x_right - 35, 73), cv2.FONT_HERSHEY_SIMPLEX, 0.35, cam_clr, 1)

    # Mic indicator
    mic_clr = _MIC_COLORS[mic_status]
    cv2.circle(hud, (x_right, 90), 5, mic_clr, -1)
    cv2.putText(hud, "MIC", (x_right - 35, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.35, mic_clr, 1)

    # Overlay indicator
    ov_clr = (0, 255, 0) if overlay_on else (100, 100, 100)
    cv2.putText(hud, "OVR", (HUD_WIDTH - 55, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.4, ov_clr, 1)

    return hud


class AirTapApp:
    """Main application — ties all subsystems together."""

    def __init__(self, tracker, matrix, no_voice: bool = False):
        self._tracker = tracker
        self._matrix = matrix
        self._no_camera = tracker is None or matrix is None
        if not self._no_camera:
            self._cursor = CursorController(matrix)
            self._engine = GestureEngine(self._cursor)
        else:
            self._cursor = None
            self._engine = None
        self._mode_mgr = ModeManager()

        # Notifications on mode switch
        self._mode_mgr.on_mode_switch(notify_mode_switch)

        # Overlay
        self._overlay_visible = False
        self._overlay: Overlay | None = None
        keyboard.add_hotkey(HOTKEY_OVERLAY, self._toggle_overlay)

        # Voice listener
        if no_voice:
            self._voice = VoiceListener(disabled=True)
            print("[AirTap] Voice commands disabled via --no-voice")
        else:
            self._voice = VoiceListener()
            self._voice.on_command(self._handle_voice_command)
            self._voice.start()

        # System tray
        self._tray: SystemTray | None = None

        # HUD
        self._hud_window = "AirTap HUD"
        cv2.namedWindow(self._hud_window, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self._hud_window, HUD_WIDTH, HUD_HEIGHT)
        cv2.setWindowProperty(self._hud_window, cv2.WND_PROP_TOPMOST, 1)

        # State
        self._prev_time = time.time()
        self._fps = 0.0
        self._last_action: str | None = None
        self._action_expire = 0.0
        self._pending_calibrate = False

    def create_overlay(self):
        if self._no_camera:
            return
        self._overlay = Overlay(
            self._tracker, self._cursor, self._mode_mgr, self._engine
        )

    def create_tray(self):
        self._tray = SystemTray(
            self._mode_mgr,
            on_calibrate=self._request_calibrate,
            on_quit=self._quit,
            on_toggle_overlay=self._toggle_overlay,
        )

    # ------------------------------------------------------------------
    # Voice command handler
    # ------------------------------------------------------------------

    def _handle_voice_command(self, action_key: str):
        notify_voice_command(action_key.replace("_", " "))

        if action_key == "enable":
            self._mode_mgr.enable()
            notify_enabled()
        elif action_key == "disable":
            self._mode_mgr.disable()
            notify_disabled()
        elif action_key == "mode_presentation":
            self._mode_mgr.switch_mode(Mode.PRESENTATION)
        elif action_key == "mode_media":
            self._mode_mgr.switch_mode(Mode.MEDIA)
        elif action_key == "mode_daily":
            self._mode_mgr.switch_mode(Mode.DAILY)
        elif action_key == "calibrate":
            self._request_calibrate()
        elif action_key == "screenshot":
            self._take_screenshot()

    def _request_calibrate(self):
        """Flag calibration to run on next tick (must run on main thread)."""
        self._pending_calibrate = True

    def _run_calibrate(self):
        """Run calibration synchronously on the main thread."""
        if self._no_camera:
            print("[AirTap] Cannot calibrate — no camera available")
            return
        print("[AirTap] Re-calibrating...")
        if self._overlay_visible:
            self._overlay.hide()

        new_matrix = calibrate(self._tracker)
        if new_matrix is None:
            print("[AirTap] Calibration cancelled — keeping previous calibration.")
            if self._overlay_visible and self._overlay:
                self._overlay.show()
            return

        self._matrix = new_matrix
        self._cursor = CursorController(self._matrix)
        self._engine = GestureEngine(self._cursor)
        if self._overlay_visible and self._overlay:
            self._overlay.update_subsystems(self._cursor, self._engine)
            self._overlay.show()
        notify_calibration_complete()
        print("[AirTap] Calibration complete.")

    def _take_screenshot(self):
        screenshot_dir = Path(os.path.expanduser(SCREENSHOT_DIR))
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        filename = f"airtap_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        path = screenshot_dir / filename
        img = pyautogui.screenshot()
        img.save(str(path))
        notify_screenshot(str(path))
        print(f"[AirTap] Screenshot saved: {path}")

    # ------------------------------------------------------------------
    # Overlay
    # ------------------------------------------------------------------

    def _toggle_overlay(self):
        if self._overlay is None:
            return
        self._overlay_visible = not self._overlay_visible
        if self._overlay_visible:
            self._overlay.show()
            print("[AirTap] Overlay ON")
        else:
            self._overlay.hide()
            print("[AirTap] Overlay OFF")

    # ------------------------------------------------------------------
    # Main tick
    # ------------------------------------------------------------------

    def tick(self):
        # Pending calibration
        if self._pending_calibrate and not self._no_camera:
            self._pending_calibrate = False
            self._run_calibrate()
            return

        mode = self._mode_mgr.get_mode()

        gesture = "idle"
        action = None
        state = None

        if not self._no_camera:
            state = self._tracker.get_hand_state()
            gesture = state["gesture"]

            # Process gestures
            if mode != Mode.DISABLED:
                try:
                    action = self._engine.update(state, mode)
                except pyautogui.FailSafeException:
                    action = None

        # Track action
        now = time.time()
        if action:
            self._last_action = action
            self._action_expire = now + 2.0
        if now > self._action_expire:
            self._last_action = None

        # FPS
        dt = now - self._prev_time
        if dt > 0:
            self._fps = 0.8 * self._fps + 0.2 * (1.0 / dt)
        self._prev_time = now

        # Push to overlay
        if self._overlay_visible and self._overlay and state is not None:
            cursor_pos = pyautogui.position()
            self._overlay.push_state(state, cursor_pos, gesture, self._last_action)

        # HUD
        click_ready = self._cursor.click_ready if self._cursor else False
        laser_active = self._engine.laser_active if self._engine else False
        cam_ok = self._tracker.camera_ok if self._tracker else False

        hud = build_hud(
            self._fps, gesture, mode, self._last_action,
            click_ready, laser_active,
            self._overlay_visible, self._voice.status,
            cam_ok=cam_ok,
        )
        cv2.imshow(self._hud_window, hud)

        key = cv2.waitKey(1) & 0xFF
        if key in (27, ord("q")):
            self._quit()

    def _quit(self):
        QApplication.quit()

    def cleanup(self):
        self._voice.stop()
        if self._tray:
            self._tray.cleanup()
        self._mode_mgr.cleanup()
        if self._tracker:
            self._tracker.stop()
        cv2.destroyAllWindows()
        print("[AirTap] Stopped.")


def _setup_logging():
    """Configure logging to write to both console and a timestamped log file."""
    log_dir = Path(os.path.expanduser(LOG_DIR))
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f"airtap_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.FileHandler(str(log_file), encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )

    # Redirect print() output to the logger so existing print statements get logged
    class _PrintLogger:
        def __init__(self, logger, stream):
            self._logger = logger
            self._stream = stream

        def write(self, msg):
            msg = msg.rstrip()
            if msg:
                self._logger.info(msg)

        def flush(self):
            self._stream.flush()

    sys.stdout = _PrintLogger(logging.getLogger("airtap"), sys.__stdout__)

    # Clean up old log files
    log_files = sorted(log_dir.glob("airtap_*.log"), key=lambda p: p.stat().st_mtime)
    for old in log_files[:-MAX_LOG_FILES]:
        old.unlink(missing_ok=True)

    logging.info(f"Log file: {log_file}")


def main():
    parser = argparse.ArgumentParser(description="AirTap — touchless gesture controller")
    parser.add_argument("--recalibrate", action="store_true", help="Force recalibration")
    parser.add_argument("--no-voice", action="store_true", help="Disable voice commands")
    args = parser.parse_args()

    _setup_logging()

    # --- Hand tracker ---
    tracker = None
    try:
        tracker = HandTracker()
        tracker.start()
        time.sleep(0.5)
    except RuntimeError as e:
        print(f"[AirTap] {e}")
        print("[AirTap] Running in keyboard/voice-only mode (no hand tracking).")

    # --- Calibration ---
    matrix = None
    if tracker is not None:
        matrix = None if args.recalibrate else load_calibration()
        if matrix is None:
            print("[AirTap] Starting calibration...")
            matrix = calibrate(tracker)
            if matrix is None:
                print("[AirTap] Calibration failed — cannot continue without calibration.")
                tracker.stop()
                sys.exit(1)
            print("[AirTap] Calibration complete.")
        else:
            print("[AirTap] Loaded existing calibration.")

    # --- Qt application ---
    qt_app = QApplication(sys.argv)

    # --- Main app ---
    app = AirTapApp(tracker, matrix, no_voice=args.no_voice)
    app.create_overlay()
    app.create_tray()

    print("[AirTap] Running — Phase 4")
    print(f"  {HOTKEY_DAILY} = Daily mode")
    print(f"  {HOTKEY_PRESENTATION} = Presentation mode")
    print(f"  {HOTKEY_MEDIA} = Media mode")
    print(f"  {HOTKEY_DISABLE} = Disable")
    print(f"  {HOTKEY_OVERLAY} = Toggle overlay")
    print("  Voice: 'airtap on/off', 'daily/presentation/media mode',")
    print("         'calibrate', 'take screenshot'")
    print("  Q / ESC = Quit")

    # Main loop via QTimer
    timer = QTimer()
    timer.timeout.connect(app.tick)
    timer.start(15)

    try:
        qt_app.exec()
    except KeyboardInterrupt:
        pass
    finally:
        app.cleanup()


if __name__ == "__main__":
    main()
