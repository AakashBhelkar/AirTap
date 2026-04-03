# AirTap Documentation

> Touchless hand-gesture controller for Windows using webcam and MediaPipe hand tracking.

**Version:** 1.0.0  
**Platform:** Windows 10/11  
**Python:** 3.10+

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Installation](#installation)
4. [Quick Start](#quick-start)
5. [Features](#features)
6. [Gestures Reference](#gestures-reference)
7. [Modes](#modes)
8. [Keyboard Shortcuts](#keyboard-shortcuts)
9. [Voice Commands](#voice-commands)
10. [System Tray](#system-tray)
11. [Settings UI](#settings-ui)
12. [Profiles](#profiles)
13. [Multi-Hand Support](#multi-hand-support)
14. [Calibration](#calibration)
15. [HUD Indicators](#hud-indicators)
16. [Overlay](#overlay)
17. [Sound Feedback](#sound-feedback)
18. [Logging](#logging)
19. [Configuration Reference](#configuration-reference)
20. [Building Standalone .exe](#building-standalone-exe)
21. [Auto-Updater](#auto-updater)
22. [File Structure](#file-structure)
23. [Future Plans](#future-plans)

---

## Overview

AirTap lets you control your Windows computer with hand gestures captured by a webcam. Point to move the cursor, tap to click, pinch for right-click, swipe for slides, and more. It supports three operational modes (Daily, Presentation, Media), voice commands, a full-screen overlay, and a system tray with settings UI.

## Architecture

```
main.py          ─── Entry point, QTimer main loop, HUD
  tracker.py     ─── Webcam capture + MediaPipe hand detection (background thread)
  calibration.py ─── 4-corner perspective calibration
  cursor.py      ─── Perspective transform → screen coords, mouse control
  gestures.py    ─── Gesture-to-action engine (per-mode mapping)
  mode_manager.py─── Mode state machine + global hotkeys
  overlay.py     ─── Full-screen translucent Qt overlay
  voice_listener.py ─ Background speech recognition (Google + Vosk)
  notifications.py  ─ Desktop toast notifications
  startup.py     ─── System tray icon + Windows startup registry
  settings_ui.py ─── Qt settings dialog with sliders
  profiles.py    ─── Save/load named config profiles
  sounds.py      ─── Optional audio feedback via winsound
  onboarding.py  ─── First-run setup wizard
  tutorial.py    ─── Interactive gesture practice mode
  updater.py     ─── GitHub release auto-updater
  config.py      ─── All tunable values + thread-safe accessors
```

## Installation

### From source

```bash
cd airtap
pip install -r requirements.txt
```

**Dependencies** (11 packages):
- mediapipe (hand tracking)
- opencv-python (computer vision)
- pyautogui (mouse/keyboard control)
- numpy (math)
- keyboard (global hotkeys)
- PyQt6 (GUI, overlay, tray)
- SpeechRecognition (voice — online)
- vosk (voice — offline fallback)
- plyer (desktop notifications)
- pywin32 (Windows registry)
- requests (Vosk model download, update checker)

### MediaPipe model

The `hand_landmarker.task` model (~7.6 MB) must be in the `airtap/` directory. Download from [MediaPipe models](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker#models).

### Building as .exe

```bash
# From project root:
build.bat
# Output: airtap/dist/AirTap/AirTap.exe
```

Requires `pyinstaller` (installed automatically by the build script).

## Quick Start

```bash
# First run — onboarding wizard + calibration
python main.py

# Force recalibration
python main.py --recalibrate

# Disable voice commands
python main.py --no-voice
```

On first run:
1. Onboarding wizard explains gestures and checks camera
2. Calibration asks you to point at 4 screen corners
3. App starts in Daily mode with HUD window

## Features

### Current Features (v1.0.0)

| Category | Feature | Status |
|----------|---------|--------|
| **Core** | Real-time hand tracking via MediaPipe | Done |
| **Core** | Auto-detect any available camera (built-in, USB, DroidCam) | Done |
| **Core** | 4-corner perspective calibration | Done |
| **Core** | Cursor movement with exponential smoothing + dead zone | Done |
| **Gestures** | Pointing (move cursor) | Done |
| **Gestures** | Tap (left click with cursor freeze) | Done |
| **Gestures** | Pinch hold (right-click / laser / play-pause) | Done |
| **Gestures** | Two-finger scroll | Done |
| **Gestures** | Open palm (show desktop / fullscreen / volume) | Done |
| **Gestures** | Horizontal swipe (slides / tracks) | Done |
| **Gestures** | Vertical swipe (show desktop) | Done |
| **Gestures** | Custom gesture-to-action mapping per mode | Done |
| **Modes** | Daily mode (cursor, click, scroll, desktop) | Done |
| **Modes** | Presentation mode (cursor, slides, fullscreen, laser pointer) | Done |
| **Modes** | Media mode (play/pause, tracks, volume) | Done |
| **Modes** | Disabled mode | Done |
| **Multi-Hand** | Two-hand tracking (second hand = modifier) | Done |
| **Multi-Hand** | Open palm modifier = Shift | Done |
| **Multi-Hand** | Fist modifier = Ctrl | Done |
| **Multi-Hand** | Pointing modifier = Alt | Done |
| **Voice** | Google Web Speech API (online) | Done |
| **Voice** | Vosk offline fallback (auto-downloads model) | Done |
| **Voice** | Commands: on/off, mode switch, calibrate, screenshot | Done |
| **Voice** | Feedback for unrecognized speech | Done |
| **UI** | OpenCV HUD with FPS, gesture, action, status indicators | Done |
| **UI** | Full-screen translucent overlay with webcam preview | Done |
| **UI** | Cursor dot with color-coded gesture state | Done |
| **UI** | Action toast notifications on overlay | Done |
| **UI** | Hand skeleton drawn on webcam preview | Done |
| **Tray** | System tray icon with right-click menu | Done |
| **Tray** | Icon color changes with active mode | Done |
| **Tray** | Pointing-finger icon design | Done |
| **Tray** | Enable/Disable, Mode switch, Overlay toggle | Done |
| **Tray** | Calibrate, Tutorial, Settings, Profiles | Done |
| **Tray** | Launch on Startup (Windows registry) | Done |
| **Tray** | Check for Updates (GitHub releases) | Done |
| **Settings** | Runtime settings dialog with sliders | Done |
| **Settings** | Cursor smoothing, dead zone, click cooldown | Done |
| **Settings** | Tap velocity, pinch distance, swipe thresholds | Done |
| **Settings** | Scroll/volume sensitivity, hold durations | Done |
| **Settings** | Reset to defaults | Done |
| **Profiles** | Save/load named config profiles (JSON) | Done |
| **Profiles** | Tray submenu with save dialog | Done |
| **Sound** | Optional beep sounds on click, right-click, mode switch | Done |
| **Sound** | Toggle via SOUND_ENABLED config | Done |
| **Onboarding** | First-run wizard with camera check | Done |
| **Onboarding** | Gesture overview and calibration guidance | Done |
| **Tutorial** | Interactive gesture practice with progress bars | Done |
| **Tutorial** | Live camera feed with detection feedback | Done |
| **Stability** | DPI scaling awareness (high-DPI displays) | Done |
| **Stability** | Multi-monitor cursor clamping (virtual screen bounds) | Done |
| **Stability** | Camera failure detection + auto-recovery | Done |
| **Stability** | Calibration matrix validation (retry on degenerate) | Done |
| **Stability** | ESC during calibration uses previous or retries | Done |
| **Stability** | Perspective transform NaN/Inf guard | Done |
| **Stability** | Thread-safe config access (get_value/set_value) | Done |
| **Stability** | Graceful degradation without camera (keyboard/voice only) | Done |
| **Stability** | Volume press cap per frame | Done |
| **Logging** | Timestamped log files in ~/AirTap/logs/ | Done |
| **Logging** | Auto-cleanup (keeps last 5 logs) | Done |
| **Logging** | All print() output redirected to logger | Done |
| **Config** | All thresholds in config.py | Done |
| **Config** | Configurable keyboard shortcuts (HOTKEY_*) | Done |
| **Config** | Auto-detect camera or explicit WEBCAM_SOURCE | Done |
| **Build** | PyInstaller .spec file for standalone .exe | Done |
| **Build** | build.bat one-click build script | Done |
| **Updates** | GitHub release version checker | Done |

## Gestures Reference

### Recognized Gestures

| Gesture | Hand Shape | Detection |
|---------|-----------|-----------|
| **Pointing** | Index finger extended, others closed | Finger-up analysis |
| **Tap** | Quick flick down+up of index finger | Velocity spike detection |
| **Pinch** | Thumb tip touches index tip | Distance threshold |
| **Open Palm** | All 5 fingers spread open | All fingers up |
| **Two Fingers** | Index + middle up, ring + pinky down | Finger pattern |
| **Swipe** | Quick horizontal/vertical hand movement | Position delta over time |

### Gesture Debouncing

Gestures require 3 consecutive frames of the same detection to activate (prevents flickering). Tap is special: it fires instantly but only from a pointing state.

## Modes

### Daily Mode (default)

| Gesture | Action |
|---------|--------|
| Pointing | Move cursor |
| Tap | Left click (with 400ms cursor freeze) |
| Pinch (hold 0.8s) | Right click |
| Two fingers + move | Scroll up/down |
| Open palm + swipe up | Show Desktop (Win+D) |

### Presentation Mode

| Gesture | Action |
|---------|--------|
| Pointing / Open palm | Move cursor |
| Swipe right | Next slide (Right arrow) |
| Swipe left | Previous slide (Left arrow) |
| Open palm (hold 1.0s) | Toggle fullscreen (F5) |
| Pinch (hold 1.5s) | Laser pointer mode |

### Media Mode

| Gesture | Action |
|---------|--------|
| Swipe right | Next track |
| Swipe left | Previous track |
| Pinch (hold 0.3s) | Play / Pause |
| Open palm + move up | Volume up |
| Open palm + move down | Volume down |

## Keyboard Shortcuts

Default shortcuts (configurable in `config.py`):

| Shortcut | Action |
|----------|--------|
| Ctrl+Shift+D | Daily mode |
| Ctrl+Shift+P | Presentation mode |
| Ctrl+Shift+M | Media mode |
| Ctrl+Shift+X | Disable AirTap |
| Ctrl+Shift+O | Toggle overlay |
| Q / ESC | Quit (in HUD window) |

## Voice Commands

Requires a microphone. Uses Google Web Speech API (online) with Vosk as offline fallback.

| Say this | Action |
|----------|--------|
| "airtap on" / "air tap on" | Enable AirTap |
| "airtap off" / "air tap off" | Disable AirTap |
| "daily mode" | Switch to Daily |
| "presentation mode" | Switch to Presentation |
| "media mode" | Switch to Media |
| "calibrate" | Re-run calibration |
| "take screenshot" / "take a screenshot" | Save screenshot |

Unrecognized speech is logged so you can tell the mic is working.

## System Tray

Right-click the tray icon for:

- **Enable / Disable** AirTap
- **Mode** submenu (Daily, Presentation, Media)
- **Toggle Overlay**
- **Calibrate** — re-run 4-corner calibration
- **Gesture Tutorial** — practice each gesture interactively
- **Settings** — runtime slider dialog
- **Profiles** — save/load named config profiles
- **Launch on Startup** — add/remove from Windows autostart
- **Check for Updates** — query GitHub for new releases
- **Quit**

The tray icon color reflects the current mode.

## Settings UI

Open via tray menu "Settings...". Provides sliders for:

- **Cursor:** Smoothing alpha, dead zone, click cooldown
- **Gestures:** Tap velocity threshold, pinch distance, swipe distance
- **Scroll & Volume:** Scroll sensitivity, volume sensitivity, max volume presses
- **Hold Durations:** Right click, fullscreen, laser pointer

Changes apply immediately. "Reset to Defaults" restores built-in values.

## Profiles

Save your tuned settings as named profiles:

1. Tray > Profiles > "Save Current as..."
2. Enter a name (e.g., "Work", "Gaming", "Presentation")
3. Load anytime from Tray > Profiles > [name]

Profiles are stored as JSON in `~/AirTap/profiles/`.

## Multi-Hand Support

AirTap tracks up to 2 hands simultaneously:

- **Primary hand** (first detected): controls gestures as normal
- **Secondary hand** (second detected): acts as a keyboard modifier

| Second Hand Gesture | Modifier Key |
|---------------------|-------------|
| Open palm | Shift |
| Fist (all fingers closed) | Ctrl |
| Pointing (index only) | Alt |

This enables **Shift+Click**, **Ctrl+Click**, etc. through two-handed gestures.

## Calibration

Point your index finger at 4 red corner dots on screen. Hold steady for 1.5 seconds each. A green ring shows progress. The resulting perspective matrix maps camera coordinates to screen pixels.

- Saved to `calibration.json`, reused on next run
- ESC during calibration: falls back to previous calibration or restarts
- Invalid/degenerate matrices are auto-detected and retried
- Re-calibrate anytime via tray menu or voice command

## HUD Indicators

The small always-on-top status window shows:

| Indicator | Meaning |
|-----------|---------|
| Mode + color | Current active mode |
| FPS | Processing frame rate |
| Gesture | Currently detected gesture |
| Action | Last triggered action (fades after 2s) |
| Green/red dot (top-right) | Click ready / on cooldown |
| CAM | Camera health (green = OK, red = failing) |
| MIC | Mic status (green = listening, red = processing, grey = off) |
| OVR | Overlay on/off |

## Overlay

Toggle with Ctrl+Shift+O. Full-screen translucent overlay showing:

- Mode badge (top-right, color-coded)
- Cursor dot with glow (color changes by gesture)
- Gesture label pill below cursor
- Webcam preview with hand skeleton (bottom-right)
- Action toast (center-bottom, fades after 2s)

Click-through — does not block mouse input.

## Sound Feedback

Optional audio beeps using Windows `winsound`:

| Event | Sound |
|-------|-------|
| Left click | Short high beep (1200 Hz) |
| Right click | Medium beep (800 Hz) |
| Mode switch | Rising tone (600 Hz) |

Enable in `config.py`: `SOUND_ENABLED = True`

## Logging

All output is logged to `~/AirTap/logs/airtap_YYYYMMDD_HHMMSS.log`. The last 5 log files are kept; older ones are auto-deleted.

## Configuration Reference

All values in `config.py`. Runtime-changeable values use `get_value()`/`set_value()` for thread safety.

| Setting | Default | Description |
|---------|---------|-------------|
| WEBCAM_SOURCE | None | Camera source (None = auto-detect, int = index, str = URL) |
| CAMERA_WIDTH | 640 | Capture width |
| CAMERA_HEIGHT | 480 | Capture height |
| SMOOTHING_ALPHA | 0.2 | Cursor smoothing (lower = smoother) |
| CURSOR_DEAD_ZONE | 4 | Pixels — ignore jitter below this |
| CLICK_COOLDOWN | 1.0 | Seconds between clicks |
| TAP_VELOCITY_THRESHOLD | 0.18 | Tap detection sensitivity |
| PINCH_DISTANCE_THRESHOLD | 0.05 | Pinch detection distance |
| CALIBRATION_HOLD_TIME | 1.5 | Seconds to hold per corner |
| CALIBRATION_PADDING | 60 | Pixels from screen edge |
| SWIPE_MIN_DISTANCE | 0.30 | Minimum swipe distance |
| SWIPE_TIME_WINDOW | 0.5 | Seconds for swipe completion |
| HOLD_OPEN_PALM_FULLSCREEN | 1.0 | Hold duration for fullscreen |
| HOLD_PINCH_LASER | 1.5 | Hold duration for laser |
| HOLD_PINCH_RIGHT_CLICK | 0.8 | Hold duration for right-click |
| SCROLL_SENSITIVITY | 1200 | Scroll speed multiplier |
| VOLUME_SENSITIVITY | 5 | Volume key presses per unit |
| MAX_VOLUME_PRESSES | 5 | Cap per frame |
| SOUND_ENABLED | False | Enable audio feedback |
| HOTKEY_DAILY | ctrl+shift+d | Daily mode shortcut |
| HOTKEY_PRESENTATION | ctrl+shift+p | Presentation mode shortcut |
| HOTKEY_MEDIA | ctrl+shift+m | Media mode shortcut |
| HOTKEY_DISABLE | ctrl+shift+x | Disable shortcut |
| HOTKEY_OVERLAY | ctrl+shift+o | Overlay toggle shortcut |
| GESTURE_MAP_DAILY | {...} | Gesture-to-action map for Daily |
| GESTURE_MAP_PRESENTATION | {...} | Gesture-to-action map for Presentation |
| GESTURE_MAP_MEDIA | {...} | Gesture-to-action map for Media |

## Building Standalone .exe

```bash
# Windows:
build.bat

# Or manually:
cd airtap
pip install pyinstaller
pyinstaller airtap.spec --noconfirm
```

Output: `airtap/dist/AirTap/AirTap.exe` (directory mode, includes all DLLs and models).

## Auto-Updater

On startup, AirTap checks `https://api.github.com/repos/AakashBhelkar/AirTap/releases/latest` for a newer version. If found:

- Console prints the available version
- Tray menu item updates to show "Update Available: vX.Y.Z"
- Tray notification popup appears

Manual check: Tray > "Check for Updates".

## File Structure

```
AirTap-master/
  .gitignore
  build.bat              # One-click .exe build script
  DOCS.md                # This file
  airtap/
    main.py              # Entry point + HUD + main loop
    config.py            # All configuration values
    tracker.py           # Webcam + MediaPipe hand tracking
    calibration.py       # 4-corner perspective calibration
    cursor.py            # Cursor movement + click/scroll
    gestures.py          # Gesture-to-action engine
    mode_manager.py      # Mode state machine + hotkeys
    overlay.py           # Full-screen Qt overlay
    voice_listener.py    # Speech recognition (Google + Vosk)
    notifications.py     # Desktop toast notifications
    startup.py           # System tray + Windows autostart
    settings_ui.py       # Runtime settings dialog
    profiles.py          # Config profile save/load
    sounds.py            # Audio feedback
    onboarding.py        # First-run wizard
    tutorial.py          # Gesture practice mode
    updater.py           # GitHub release checker
    gestures_test.py     # Standalone gesture testing utility
    hand_landmarker.task # MediaPipe model (not in git)
    airtap.spec          # PyInstaller build spec
    requirements.txt     # Python dependencies
    README.md            # Quick-start README
```

---

## Future Plans

### Near-Term (v1.1)

- [ ] **Drag & drop gesture** — pinch to grab, move hand, release to drop
- [ ] **Double-tap** — two quick taps for double-click
- [ ] **Gesture recording** — let users define custom gestures with ML training
- [ ] **Webcam preview window** — toggle a standalone camera view with landmarks for debugging
- [ ] **Per-application profiles** — auto-switch profiles based on active window (e.g., PowerPoint = Presentation)
- [ ] **Improved calibration** — proximity validation, visual distance feedback for each corner

### Mid-Term (v1.2)

- [ ] **Cross-platform support** — Linux/macOS compatibility (replace winsound, winreg, DShow)
- [ ] **Plugin system** — user-authored Python plugins for custom gesture actions
- [ ] **Gesture chaining** — combine sequential gestures (e.g., pinch then swipe = copy)
- [ ] **Eye tracking integration** — combine hand gestures with eye gaze for precision
- [ ] **Multi-language voice** — configurable Vosk model for other languages
- [ ] **Accessibility mode** — simplified gestures with longer hold times for users with motor challenges

### Long-Term (v2.0)

- [ ] **Neural gesture recognition** — train a custom ML model for higher accuracy and more gestures
- [ ] **Mobile companion app** — use phone camera as a secondary tracker
- [ ] **Web interface** — browser-based settings dashboard
- [ ] **Smart home integration** — control IoT devices with hand gestures
- [ ] **Gaming mode** — map gestures to game controller inputs (WASD, joystick)
- [ ] **Collaborative mode** — multiple users controlling the same screen (classroom/meeting)
- [ ] **Hand pose estimation** — full 3D hand model for depth-aware gestures
- [ ] **Sign language recognition** — extend gesture vocabulary to ASL/BSL alphabets

---

*Built with MediaPipe, OpenCV, PyQt6, and Python.*
