"""Gesture test script — prints detected gestures and actions to console.
No cursor control, just real-time gesture label output for verification."""

import time
from collections import deque

from tracker import HandTracker
from mode_manager import ModeManager, Mode
from config import SWIPE_MIN_DISTANCE, SWIPE_TIME_WINDOW, GESTURE_HISTORY_SIZE


def detect_swipe(history):
    """Quick horizontal swipe check on the history buffer."""
    now = time.time()
    points = []
    for ts, st in history:
        if now - ts <= SWIPE_TIME_WINDOW and st["detected"]:
            points.append((ts, st["index_tip"][0], st["index_tip"][1]))

    result = []
    if len(points) >= 4:
        dx = points[-1][1] - points[0][1]
        dy = points[-1][2] - points[0][2]
        if abs(dx) >= SWIPE_MIN_DISTANCE:
            result.append(f"SWIPE {'RIGHT' if dx > 0 else 'LEFT'} (dx={dx:+.2f})")
        if abs(dy) >= SWIPE_MIN_DISTANCE:
            result.append(f"SWIPE {'DOWN' if dy > 0 else 'UP'} (dy={dy:+.2f})")
    return result


def main():
    print("[GestureTest] Starting tracker... (Ctrl+C to quit)")
    print("[GestureTest] Hotkeys: Ctrl+Shift+D/P/M/X to switch modes")
    print("-" * 60)

    tracker = HandTracker()
    tracker.start()
    mode_mgr = ModeManager()
    time.sleep(0.5)

    history: deque = deque(maxlen=GESTURE_HISTORY_SIZE)
    prev_gesture = ""
    prev_mode = None

    try:
        while True:
            state = tracker.get_hand_state()
            mode = mode_mgr.get_mode()
            now = time.time()

            if mode != prev_mode:
                print(f"\n>>> MODE: {mode.value}")
                prev_mode = mode

            if not state["detected"]:
                if prev_gesture != "":
                    print("  [no hand]")
                    prev_gesture = ""
                history.clear()
                time.sleep(0.03)
                continue

            history.append((now, state))
            gesture = state["gesture"]
            fingers = state["fingers_up"]
            nx, ny = state["index_tip"]
            finger_str = "".join("T I M R P"[i*2] if f else "." for i, f in enumerate(fingers))

            # Print gesture changes
            if gesture != prev_gesture:
                print(f"  Gesture: {gesture:12s}  Fingers: [{finger_str}]  Tip: ({nx:.2f}, {ny:.2f})")
                prev_gesture = gesture

            # Check swipes
            swipes = detect_swipe(history)
            for s in swipes:
                print(f"  >>> {s}")
                history.clear()

            time.sleep(0.03)

    except KeyboardInterrupt:
        pass
    finally:
        mode_mgr.cleanup()
        tracker.stop()
        print("\n[GestureTest] Done.")


if __name__ == "__main__":
    main()
