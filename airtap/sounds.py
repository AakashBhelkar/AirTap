"""Optional sound feedback for AirTap actions using Windows built-in sounds."""

import threading
from config import get_value


def _beep(frequency: int, duration_ms: int):
    """Play a beep in a background thread to avoid blocking."""
    def _play():
        try:
            import winsound
            winsound.Beep(frequency, duration_ms)
        except Exception:
            pass
    threading.Thread(target=_play, daemon=True).start()


def sound_click():
    """Short high beep for left click."""
    if get_value("SOUND_ENABLED"):
        _beep(1200, 50)


def sound_right_click():
    """Two quick beeps for right click."""
    if get_value("SOUND_ENABLED"):
        _beep(800, 80)


def sound_mode_switch():
    """Rising tone for mode switch."""
    if get_value("SOUND_ENABLED"):
        _beep(600, 100)


def sound_scroll():
    """Soft tick for scroll."""
    if get_value("SOUND_ENABLED"):
        _beep(400, 30)


def sound_action():
    """Generic action confirmation."""
    if get_value("SOUND_ENABLED"):
        _beep(1000, 60)
