"""AirTap configuration — all tunable values in one place."""

# Webcam
# Set to a specific source (integer index or DroidCam URL) to skip auto-detection,
# or leave as None to automatically find the first available camera.
WEBCAM_SOURCE = None
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

# Cursor smoothing (exponential moving average, lower = smoother/slower)
SMOOTHING_ALPHA = 0.2
CURSOR_DEAD_ZONE = 4  # pixels — ignore movement smaller than this

# Click cooldown in seconds
CLICK_COOLDOWN = 1.0

# Gesture detection
TAP_VELOCITY_THRESHOLD = 0.18  # normalized y-velocity spike (higher = harder to trigger)
PINCH_DISTANCE_THRESHOLD = 0.05  # normalized distance between thumb & index tips

# Calibration
CALIBRATION_FILE = "calibration.json"
CALIBRATION_HOLD_TIME = 1.5  # seconds to hold at each corner
CALIBRATION_PADDING = 60  # pixels from screen edge

# HUD
HUD_WIDTH = 240
HUD_HEIGHT = 150

# Phase 2: Gesture actions
SWIPE_MIN_DISTANCE = 0.30  # normalized x-distance to trigger swipe
SWIPE_TIME_WINDOW = 0.5  # seconds — swipe must complete within this
GESTURE_HISTORY_SIZE = 30  # frames of hand state history

# Hold durations (seconds)
HOLD_OPEN_PALM_FULLSCREEN = 1.0  # presentation: toggle fullscreen
HOLD_PINCH_LASER = 1.5  # presentation: laser pointer
HOLD_PINCH_RIGHT_CLICK = 0.8  # daily: right click

# Scroll
SCROLL_SENSITIVITY = 1200  # pyautogui scroll clicks per normalized-unit of hand movement
VOLUME_SENSITIVITY = 5  # volume key presses per normalized-unit of hand movement

# Voice
VOSK_MODEL_NAME = "vosk-model-small-en-us-0.15"
VOSK_MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
VOSK_MODEL_DIR = "vosk_models"
SCREENSHOT_DIR = "~/AirTap/screenshots"
