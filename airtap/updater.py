"""Auto-updater — checks GitHub releases for new versions of AirTap."""

import threading
import webbrowser

# Current app version — bump this with each release
APP_VERSION = "1.0.0"

_GITHUB_REPO = "AakashBhelkar/AirTap"
_API_URL = f"https://api.github.com/repos/{_GITHUB_REPO}/releases/latest"


def _parse_version(v: str) -> tuple[int, ...]:
    """Parse 'v1.2.3' or '1.2.3' into (1, 2, 3)."""
    v = v.lstrip("vV").strip()
    parts = []
    for p in v.split("."):
        try:
            parts.append(int(p))
        except ValueError:
            break
    return tuple(parts) if parts else (0,)


def check_for_updates(callback=None):
    """Check GitHub for a newer release in a background thread.

    Args:
        callback: optional fn(has_update: bool, latest_version: str, download_url: str)
    """
    def _check():
        try:
            import requests
            resp = requests.get(_API_URL, timeout=10)
            if resp.status_code != 200:
                return

            data = resp.json()
            latest_tag = data.get("tag_name", "")
            latest_ver = _parse_version(latest_tag)
            current_ver = _parse_version(APP_VERSION)

            has_update = latest_ver > current_ver
            html_url = data.get("html_url", "")

            if has_update:
                print(f"[AirTap] Update available: {latest_tag} (current: v{APP_VERSION})")
                print(f"[AirTap] Download: {html_url}")
            else:
                print(f"[AirTap] Up to date (v{APP_VERSION})")

            if callback:
                callback(has_update, latest_tag, html_url)

        except Exception as e:
            print(f"[AirTap] Update check failed: {e}")

    threading.Thread(target=_check, daemon=True).start()


def open_release_page(url: str):
    """Open the GitHub release page in the default browser."""
    if url:
        webbrowser.open(url)
