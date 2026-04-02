"""System tray icon and Windows startup registration for AirTap."""

import os
import sys

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction
from PyQt6.QtCore import QSize

from mode_manager import Mode

# Registry path for Windows auto-start
_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_APP_NAME = "AirTap"


def _make_tray_icon() -> QIcon:
    """Generate a simple colored icon (no external file needed)."""
    size = 64
    px = QPixmap(QSize(size, size))
    px.fill(QColor(0, 0, 0, 0))
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor(0, 200, 255))
    p.setPen(QColor(255, 255, 255))
    p.drawEllipse(4, 4, size - 8, size - 8)
    p.setPen(QColor(0, 0, 0))
    from PyQt6.QtGui import QFont
    font = QFont("Segoe UI", 22, QFont.Weight.Bold)
    p.setFont(font)
    p.drawText(px.rect(), 0x0084, "AT")  # AlignCenter
    p.end()
    return QIcon(px)


class SystemTray:
    """System tray icon with menu for AirTap control."""

    def __init__(self, mode_mgr, on_calibrate, on_quit, on_toggle_overlay):
        self._mode_mgr = mode_mgr
        self._on_calibrate = on_calibrate
        self._on_quit = on_quit
        self._on_toggle_overlay = on_toggle_overlay

        self._tray = QSystemTrayIcon(_make_tray_icon())
        self._tray.setToolTip("AirTap — Gesture Controller")
        self._build_menu()
        self._tray.show()

    def _build_menu(self):
        menu = QMenu()

        # Enable / Disable
        self._enable_action = QAction("Enable AirTap")
        self._enable_action.triggered.connect(lambda: self._mode_mgr.enable())
        menu.addAction(self._enable_action)

        self._disable_action = QAction("Disable AirTap")
        self._disable_action.triggered.connect(lambda: self._mode_mgr.disable())
        menu.addAction(self._disable_action)

        menu.addSeparator()

        # Mode submenu
        mode_menu = menu.addMenu("Mode")
        for mode in (Mode.DAILY, Mode.PRESENTATION, Mode.MEDIA):
            act = QAction(mode.value.capitalize())
            act.triggered.connect(lambda checked, m=mode: self._mode_mgr.switch_mode(m))
            mode_menu.addAction(act)

        menu.addSeparator()

        # Overlay toggle
        overlay_action = QAction("Toggle Overlay")
        overlay_action.triggered.connect(self._on_toggle_overlay)
        menu.addAction(overlay_action)

        # Calibrate
        cal_action = QAction("Calibrate")
        cal_action.triggered.connect(self._on_calibrate)
        menu.addAction(cal_action)

        menu.addSeparator()

        # Auto-start
        self._startup_action = QAction("Launch on Startup")
        self._startup_action.setCheckable(True)
        self._startup_action.setChecked(_is_startup_enabled())
        self._startup_action.triggered.connect(self._toggle_startup)
        menu.addAction(self._startup_action)

        menu.addSeparator()

        # Quit
        quit_action = QAction("Quit")
        quit_action.triggered.connect(self._on_quit)
        menu.addAction(quit_action)

        self._tray.setContextMenu(menu)

    def _toggle_startup(self):
        if self._startup_action.isChecked():
            _enable_startup()
            print("[AirTap] Added to Windows startup")
        else:
            _disable_startup()
            print("[AirTap] Removed from Windows startup")

    def show_message(self, title: str, message: str):
        self._tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 2000)

    def cleanup(self):
        self._tray.hide()


# ------------------------------------------------------------------
# Windows startup registry helpers
# ------------------------------------------------------------------

def _get_exe_path() -> str:
    """Return the command to launch AirTap."""
    python = sys.executable
    main_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
    return f'"{python}" "{main_py}"'


def _is_startup_enabled() -> bool:
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_READ)
        try:
            winreg.QueryValueEx(key, _APP_NAME)
            return True
        except FileNotFoundError:
            return False
        finally:
            winreg.CloseKey(key)
    except Exception:
        return False


def _enable_startup():
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, _APP_NAME, 0, winreg.REG_SZ, _get_exe_path())
        winreg.CloseKey(key)
    except Exception as e:
        print(f"[AirTap] Failed to set startup: {e}")


def _disable_startup():
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE)
        try:
            winreg.DeleteValue(key, _APP_NAME)
        except FileNotFoundError:
            pass
        winreg.CloseKey(key)
    except Exception as e:
        print(f"[AirTap] Failed to remove startup: {e}")
