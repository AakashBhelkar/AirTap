# AirTap

Touchless hand-gesture controller for Windows using a webcam and MediaPipe hand tracking.

## Setup

```bash
cd airtap
pip install -r requirements.txt
```

The MediaPipe hand landmarker model (`hand_landmarker.task`) must be placed in the `airtap/` directory. It is downloaded automatically on first run or can be fetched from the [MediaPipe model page](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker#models).

## Usage

```bash
# First run — opens calibration screen, then starts controller
python main.py

# Force recalibration
python main.py --recalibrate

# Disable voice commands
python main.py --no-voice
```

## Gestures by Mode

### Daily Mode (default)

| Gesture        | Action                  |
|----------------|-------------------------|
| Pointing       | Move cursor             |
| Tap            | Left click              |
| Pinch (hold)   | Right click (0.8s hold) |
| Two fingers    | Scroll (move up/down)   |
| Open palm swipe up | Show desktop (Win+D) |

### Presentation Mode

| Gesture           | Action                        |
|-------------------|-------------------------------|
| Pointing / Palm   | Move cursor                   |
| Swipe right/left  | Next / Previous slide         |
| Open palm (hold)  | Toggle fullscreen (1s hold)   |
| Pinch (hold)      | Laser pointer (1.5s hold)     |

### Media Mode

| Gesture           | Action               |
|-------------------|----------------------|
| Swipe right/left  | Next / Previous track|
| Pinch (hold)      | Play / Pause (0.3s)  |
| Open palm + move  | Volume up/down       |

## Keyboard Shortcuts

| Shortcut         | Action             |
|------------------|--------------------|
| Ctrl+Shift+D     | Daily mode         |
| Ctrl+Shift+P     | Presentation mode  |
| Ctrl+Shift+M     | Media mode         |
| Ctrl+Shift+X     | Disable AirTap     |
| Ctrl+Shift+O     | Toggle overlay     |
| Q / ESC          | Quit               |

Hotkeys can be customized in `config.py` under `HOTKEY_*` settings.

## Voice Commands

Say any of the following (requires a microphone):

| Command                | Action               |
|------------------------|----------------------|
| "airtap on"            | Enable AirTap        |
| "airtap off"           | Disable AirTap       |
| "daily mode"           | Switch to Daily      |
| "presentation mode"    | Switch to Presentation|
| "media mode"           | Switch to Media      |
| "calibrate"            | Re-run calibration   |
| "take screenshot"      | Save screenshot      |

Voice recognition uses Google Web Speech API (online) with Vosk as an offline fallback. The Vosk model is downloaded automatically on first offline use.

## System Tray

AirTap adds an icon to the Windows system tray with a right-click menu for:

- Enable / Disable
- Switch mode (Daily, Presentation, Media)
- Toggle overlay
- Re-calibrate
- Launch on startup (adds to Windows registry)
- Quit

## Calibration

Point your index finger at each of the 4 red corner dots and hold for 1.5 seconds. Calibration is saved to `calibration.json` and reused on subsequent runs. Press ESC during calibration to use a previous calibration or restart.

## HUD Indicators

The small status window shows:

- **Mode** — current active mode with color coding
- **FPS** — processing frame rate
- **Gesture** — currently detected gesture
- **Action** — last triggered action
- **CAM** — green when camera is working, red if frames are dropping
- **MIC** — green when listening, red when processing, grey when disabled
- **OVR** — overlay on/off status

## Logging

Logs are written to `~/AirTap/logs/` with timestamped filenames. The last 5 log files are kept.

## Configuration

All tunable values are in `config.py`:

- Camera source and resolution
- Cursor smoothing and dead zone
- Click cooldown
- Gesture thresholds (tap velocity, pinch distance)
- Calibration timing and padding
- Swipe distance and timing
- Hold durations for each gesture
- Scroll and volume sensitivity
- Keyboard shortcuts
- Voice model settings
