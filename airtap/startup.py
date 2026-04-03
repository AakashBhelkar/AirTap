"""System tray icon and Windows startup registration for AirTap."""

import os
import sys

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction
from PyQt6.QtCore import QSize

from mode_manager import Mode
from settings_ui import SettingsDialog
from profiles import list_profiles, save_profile, load_profile

# Registry path for Windows auto-start
_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_APP_NAME = "AirTap"


# Mode → tray icon color (RGB)
_MODE_ICON_COLORS = {
    Mode.DAILY: QColor(0, 200, 255),      # cyan
    Mode.PRESENTATION: QColor(0, 200, 0), # green
    Mode.MEDIA: QColor(200, 0, 200),      # purple
    Mode.DISABLED: QColor(220, 0, 0),     # red
}


def _make_tray_icon(mode: Mode = Mode.DAILY) -> QIcon:
    """Generate a colored icon reflecting the active mode."""
    size = 64
    color = _MODE_ICON_COLORS.get(mode, QColor(0, 200, 255))
    px = QPixmap(QSize(size, size))
    px.fill(QColor(0, 0, 0, 0))
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(color)
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

    def __init__(self, mode_mgr, on_calibrate, on_quit, on_toggle_overlay, on_tutorial=None):
        self._mode_mgr = mode_mgr
        self._on_calibrate = on_calibrate
        self._on_quit = on_quit
        self._on_toggle_overlay = on_toggle_overlay
        self._on_tutorial = on_tutorial

        self._settings_dialog: SettingsDialog | None = None

        self._tray = QSystemTrayIcon(_make_tray_icon(mode_mgr.get_mode()))
        self._tray.setToolTip("AirTap — Gesture Controller")
        self._build_menu()
        self._tray.show()

        # Update icon color when mode changes
        self._mode_mgr.on_mode_switch(self._on_mode_changed)

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

        # Tutorial
        if self._on_tutorial:
            tutorial_action = QAction("Gesture Tutorial...")
            tutorial_action.triggered.connect(self._on_tutorial)
            menu.addAction(tutorial_action)

        # Settings
        settings_action = QAction("Settings...")
        settings_action.triggered.connect(self._open_settings)
        menu.addAction(settings_action)

        # Profiles submenu
        self._profiles_menu = menu.addMenu("Profiles")
        self._rebuild_profiles_menu()

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

    def _rebuild_profiles_menu(self):
        """Rebuild the profiles submenu with current saved profiles."""
        self._profiles_menu.clear()

        # Save current
        save_act = QAction("Save Current as...")
        save_act.triggered.connect(self._save_profile_dialog)
        self._profiles_menu.addAction(save_act)
        self._profiles_menu.addSeparator()

        # List existing profiles
        names = list_profiles()
        if not names:
            empty = QAction("(no saved profiles)")
            empty.setEnabled(False)
            self._profiles_menu.addAction(empty)
        else:
            for name in sorted(names):
                act = QAction(name)
                act.triggered.connect(lambda checked, n=name: self._load_profile(n))
                self._profiles_menu.addAction(act)

    def _save_profile_dialog(self):
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(None, "Save Profile", "Profile name:")
        if ok and name.strip():
            save_profile(name.strip())
            self._rebuild_profiles_menu()

    def _load_profile(self, name: str):
        load_profile(name)

    def _on_mode_changed(self, old_mode, new_mode):
        """Update tray icon color when mode changes."""
        self._tray.setIcon(_make_tray_icon(new_mode))
        self._tray.setToolTip(f"AirTap — {new_mode.value}")

    def _open_settings(self):
        if self._settings_dialog is None or not self._settings_dialog.isVisible():
            self._settings_dialog = SettingsDialog()
            self._settings_dialog.show()

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
