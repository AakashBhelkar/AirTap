"""Mode manager — tracks active mode and registers global hotkeys."""

from enum import Enum
import keyboard

from config import HOTKEY_DAILY, HOTKEY_PRESENTATION, HOTKEY_MEDIA, HOTKEY_DISABLE
from sounds import sound_mode_switch


class Mode(Enum):
    DAILY = "DAILY"
    PRESENTATION = "PRESENTATION"
    MEDIA = "MEDIA"
    DISABLED = "DISABLED"


# BGR colors for HUD display
MODE_COLORS = {
    Mode.DAILY: (255, 180, 0),       # blue
    Mode.PRESENTATION: (0, 200, 0),   # green
    Mode.MEDIA: (200, 0, 200),        # purple
    Mode.DISABLED: (0, 0, 220),       # red
}


class ModeManager:
    def __init__(self):
        self._mode = Mode.DAILY
        self._last_active_mode = Mode.DAILY  # for "airtap on" restore
        self._on_switch: list = []  # callbacks: fn(old_mode, new_mode)
        self._register_hotkeys()

    def _register_hotkeys(self):
        keyboard.add_hotkey(HOTKEY_DAILY, lambda: self.switch_mode(Mode.DAILY))
        keyboard.add_hotkey(HOTKEY_PRESENTATION, lambda: self.switch_mode(Mode.PRESENTATION))
        keyboard.add_hotkey(HOTKEY_MEDIA, lambda: self.switch_mode(Mode.MEDIA))
        keyboard.add_hotkey(HOTKEY_DISABLE, lambda: self.switch_mode(Mode.DISABLED))

    def on_mode_switch(self, callback):
        """Register a callback fn(old_mode, new_mode) for mode changes."""
        self._on_switch.append(callback)

    def switch_mode(self, mode: Mode):
        if self._mode != mode:
            old = self._mode
            if old != Mode.DISABLED:
                self._last_active_mode = old
            self._mode = mode
            print(f"[AirTap] Mode → {mode.value}")
            sound_mode_switch()
            for cb in self._on_switch:
                try:
                    cb(old, mode)
                except Exception:
                    pass

    def enable(self):
        """Re-enable AirTap with the last active mode."""
        self.switch_mode(self._last_active_mode)

    def disable(self):
        self.switch_mode(Mode.DISABLED)

    def get_mode(self) -> Mode:
        return self._mode

    def cleanup(self):
        keyboard.unhook_all()
