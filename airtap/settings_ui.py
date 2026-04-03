"""Settings dialog — allows users to tune AirTap parameters at runtime."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QPushButton,
    QGroupBox, QFormLayout,
)
from PyQt6.QtCore import Qt

import config


class _SliderRow:
    """Helper: label + slider + value display, mapped to a config attribute."""

    def __init__(self, label: str, attr: str, min_val: float, max_val: float, step: float):
        self.attr = attr
        self.step = step
        self.min_val = min_val

        self.label = QLabel(label)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(int((max_val - min_val) / step))
        self.slider.setValue(int((getattr(config, attr) - min_val) / step))
        self.value_label = QLabel(f"{getattr(config, attr):.2f}")
        self.value_label.setMinimumWidth(50)

        self.slider.valueChanged.connect(self._on_change)

    def _on_change(self, pos):
        val = self.min_val + pos * self.step
        self.value_label.setText(f"{val:.2f}")

    def apply(self):
        val = self.min_val + self.slider.value() * self.step
        setattr(config, self.attr, val)


class SettingsDialog(QDialog):
    """Modal dialog for tuning AirTap settings at runtime."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AirTap Settings")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)

        # --- Cursor group ---
        cursor_group = QGroupBox("Cursor")
        cursor_form = QFormLayout()
        self._rows = []

        self._add_row(cursor_form, "Smoothing", "SMOOTHING_ALPHA", 0.05, 0.80, 0.05)
        self._add_row(cursor_form, "Dead Zone (px)", "CURSOR_DEAD_ZONE", 0, 20, 1)
        self._add_row(cursor_form, "Click Cooldown (s)", "CLICK_COOLDOWN", 0.2, 3.0, 0.1)

        cursor_group.setLayout(cursor_form)
        layout.addWidget(cursor_group)

        # --- Gesture group ---
        gesture_group = QGroupBox("Gesture Detection")
        gesture_form = QFormLayout()

        self._add_row(gesture_form, "Tap Velocity", "TAP_VELOCITY_THRESHOLD", 0.05, 0.50, 0.01)
        self._add_row(gesture_form, "Pinch Distance", "PINCH_DISTANCE_THRESHOLD", 0.02, 0.15, 0.01)
        self._add_row(gesture_form, "Swipe Distance", "SWIPE_MIN_DISTANCE", 0.10, 0.60, 0.05)

        gesture_group.setLayout(gesture_form)
        layout.addWidget(gesture_group)

        # --- Scroll / Volume group ---
        scroll_group = QGroupBox("Scroll & Volume")
        scroll_form = QFormLayout()

        self._add_row(scroll_form, "Scroll Sensitivity", "SCROLL_SENSITIVITY", 200, 3000, 100)
        self._add_row(scroll_form, "Volume Sensitivity", "VOLUME_SENSITIVITY", 1, 20, 1)
        self._add_row(scroll_form, "Max Volume Presses", "MAX_VOLUME_PRESSES", 1, 15, 1)

        scroll_group.setLayout(scroll_form)
        layout.addWidget(scroll_group)

        # --- Hold durations group ---
        hold_group = QGroupBox("Hold Durations (seconds)")
        hold_form = QFormLayout()

        self._add_row(hold_form, "Right Click", "HOLD_PINCH_RIGHT_CLICK", 0.3, 3.0, 0.1)
        self._add_row(hold_form, "Fullscreen", "HOLD_OPEN_PALM_FULLSCREEN", 0.3, 3.0, 0.1)
        self._add_row(hold_form, "Laser Pointer", "HOLD_PINCH_LASER", 0.5, 5.0, 0.1)

        hold_group.setLayout(hold_form)
        layout.addWidget(hold_group)

        # --- Buttons ---
        btn_layout = QHBoxLayout()
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self._apply)
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self._reset)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)

        btn_layout.addWidget(reset_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(apply_btn)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _add_row(self, form: QFormLayout, label: str, attr: str,
                 min_val: float, max_val: float, step: float):
        row = _SliderRow(label, attr, min_val, max_val, step)
        self._rows.append(row)
        h = QHBoxLayout()
        h.addWidget(row.slider)
        h.addWidget(row.value_label)
        form.addRow(row.label, h)

    def _apply(self):
        for row in self._rows:
            row.apply()
        print("[AirTap] Settings applied")

    def _reset(self):
        """Reset sliders to built-in defaults."""
        defaults = {
            "SMOOTHING_ALPHA": 0.2,
            "CURSOR_DEAD_ZONE": 4,
            "CLICK_COOLDOWN": 1.0,
            "TAP_VELOCITY_THRESHOLD": 0.18,
            "PINCH_DISTANCE_THRESHOLD": 0.05,
            "SWIPE_MIN_DISTANCE": 0.30,
            "SCROLL_SENSITIVITY": 1200,
            "VOLUME_SENSITIVITY": 5,
            "MAX_VOLUME_PRESSES": 5,
            "HOLD_PINCH_RIGHT_CLICK": 0.8,
            "HOLD_OPEN_PALM_FULLSCREEN": 1.0,
            "HOLD_PINCH_LASER": 1.5,
        }
        for row in self._rows:
            if row.attr in defaults:
                val = defaults[row.attr]
                setattr(config, row.attr, val)
                pos = int((val - row.min_val) / row.step)
                row.slider.setValue(pos)
                row.value_label.setText(f"{val:.2f}")
        print("[AirTap] Settings reset to defaults")
