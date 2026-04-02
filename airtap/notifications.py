"""Desktop notifications for AirTap events."""

import threading


def _notify_thread(title: str, message: str):
    """Send notification in a background thread to avoid blocking."""
    try:
        from plyer import notification
        notification.notify(
            title=title,
            message=message,
            app_name="AirTap",
            timeout=2,
        )
    except Exception as e:
        print(f"[AirTap] Notification failed: {e}")


def notify(title: str, message: str):
    """Non-blocking desktop toast notification (auto-dismiss ~2s)."""
    t = threading.Thread(target=_notify_thread, args=(title, message), daemon=True)
    t.start()


def notify_mode_switch(old_mode, new_mode):
    notify("AirTap", f"Mode: {new_mode.value}")


def notify_enabled():
    notify("AirTap", "AirTap enabled")


def notify_disabled():
    notify("AirTap", "AirTap disabled")


def notify_screenshot(path: str):
    notify("AirTap Screenshot", f"Saved to {path}")


def notify_calibration_complete():
    notify("AirTap", "Calibration complete")


def notify_voice_command(command: str):
    notify("AirTap Voice", f"Heard: {command}")
