"""Profile system — save and load named configuration profiles."""

import json
import os
from pathlib import Path

from config import get_value, set_value


_PROFILES_DIR = os.path.join(
    os.path.expanduser("~/AirTap"), "profiles"
)

# Config keys that are saved/restored in profiles
_PROFILE_KEYS = [
    "SMOOTHING_ALPHA", "CURSOR_DEAD_ZONE", "CLICK_COOLDOWN",
    "TAP_VELOCITY_THRESHOLD", "PINCH_DISTANCE_THRESHOLD",
    "SWIPE_MIN_DISTANCE", "SWIPE_TIME_WINDOW",
    "HOLD_OPEN_PALM_FULLSCREEN", "HOLD_PINCH_LASER", "HOLD_PINCH_RIGHT_CLICK",
    "SCROLL_SENSITIVITY", "VOLUME_SENSITIVITY", "MAX_VOLUME_PRESSES",
    "SOUND_ENABLED",
    "GESTURE_MAP_DAILY", "GESTURE_MAP_PRESENTATION", "GESTURE_MAP_MEDIA",
]


def _ensure_dir():
    os.makedirs(_PROFILES_DIR, exist_ok=True)


def list_profiles() -> list[str]:
    """Return names of all saved profiles."""
    _ensure_dir()
    return [
        f.stem for f in Path(_PROFILES_DIR).glob("*.json")
    ]


def save_profile(name: str):
    """Save current config values to a named profile."""
    _ensure_dir()
    data = {}
    for key in _PROFILE_KEYS:
        data[key] = get_value(key)

    path = os.path.join(_PROFILES_DIR, f"{name}.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"[AirTap] Profile saved: {name}")


def load_profile(name: str) -> bool:
    """Load a named profile into the running config. Returns True on success."""
    path = os.path.join(_PROFILES_DIR, f"{name}.json")
    if not os.path.exists(path):
        print(f"[AirTap] Profile not found: {name}")
        return False

    with open(path) as f:
        data = json.load(f)

    for key in _PROFILE_KEYS:
        if key in data:
            set_value(key, data[key])

    print(f"[AirTap] Profile loaded: {name}")
    return True


def delete_profile(name: str) -> bool:
    """Delete a named profile. Returns True on success."""
    path = os.path.join(_PROFILES_DIR, f"{name}.json")
    if os.path.exists(path):
        os.remove(path)
        print(f"[AirTap] Profile deleted: {name}")
        return True
    return False
