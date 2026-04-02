# AirTap

Touchless hand-gesture controller for your computer using a webcam.

## Setup

```bash
cd airtap
pip install -r requirements.txt
```

## Usage

```bash
# First run — opens calibration screen, then starts controller
python main.py

# Force recalibration
python main.py --recalibrate
```

## Gestures

| Gesture    | Action          |
|------------|-----------------|
| Pointing   | Move cursor     |
| Tap        | Left click      |
| Open palm  | Move cursor     |
| Pinch      | (reserved)      |

## Calibration

Point your index finger at each of the 4 red corner dots and hold for 1.5 seconds.
Calibration is saved to `calibration.json` and reused on subsequent runs.
