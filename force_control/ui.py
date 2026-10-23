"""PyQt5 page for UR10e force control.

The page owns the force controls, the sensor readout and the force history
chart. Mode state (active/inactive) and force-limit warnings use separate
labels so a safety warning cannot hide the fact that force mode is running.
"""

import math
import time

import pyqtgraph as pg
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .config import (
    FORCE_AXES,
    ForceConfig,
    build_limits,
)

MAX_PLOT_POINTS = 500


class ForceModePage(QWidget):
    """Force mode controls, sensor readout, safety state and history chart."""

    def __init__(self, force_controller, parent=None):
        super().__init__(parent)
        self.force_controller = force_controller
        self._connected = False
        self._mode_active = False
        self._chart_paused = False
        self._chart_t0 = None
        self._time_data = []
        self._fx_data = []
        self._fy_data = []
        self._fz_data = []

        self._build_ui()
        self.set_mode_state(False)
        self.set_connected(False)

    # ========================================
    # UI construction
    # ========================================

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        left_container = QWidget()
        left_container_layout = QVBoxLayout(left_container)
        left_container_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        left_panel = QWidget()
        self.left_layout = QVBoxLayout(left_panel)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        self.left_layout.setSpacing(10)

        self.left_layout.addWidget(self._create_control_group())
        self.left_layout.addWidget(self._create_parameter_group())
        self.left_layout.addWidget(self._create_direction_group())
        self.left_layout.addWidget(self._create_sensor_group())
        self.left_layout.addStretch()

        scroll_area.setWidget(left_panel)
        left_container_layout.addWidget(scroll_area)
        layout.addWidget(left_container, 2)
        layout.addWidget(self._create_chart_group(), 3)

    def add_left_widget(self, widget):
        """Append a widget (e.g. data recording) below the force controls."""
        self.left_layout.insertWidget(self.left_layout.count() - 1, widget)

    def _create_control_group(self) -> QGroupBox:
        group = QGroupBox("Force Mode Control")
        layout = QVBoxLayout()

        self.start_button = QPushButton("Start Force Mode")
        self.start_button.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 10px; }"
            "QPushButton:disabled { background-color: #bdbdbd; color: #757575; }"
        )
        self.start_button.clicked.connect(self._on_start_clicked)
        layout.addWidget(self.start_button)

        self.stop_button = QPushButton("Stop Force Mode")
        self.stop_button.setStyleSheet(
            "QPushButton { background-color: #f44336; color: white; font-weight: bold; padding: 10px; }"
            "QPushButton:disabled { background-color: #bdbdbd; color: #757575; }"
        )
        self.stop_button.clicked.connect(self._on_stop_clicked)
        layout.addWidget(self.stop_button)

        self.mode_status_label = QLabel("Status: Inactive")
        self.mode_status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.mode_status_label)

        group.setLayout(layout)
        return group

    def _create_parameter_group(self) -> QGroupBox:
        group = QGroupBox("Force Parameters")
        layout = QGridLayout()

        layout.addWidget(QLabel("Target Force (N):"), 0, 0)
        self.target_force_spin = QDoubleSpinBox()
        self.target_force_spin.setRange(ForceConfig.MIN_TARGET_FORCE, ForceConfig.MAX_TARGET_FORCE)
        self.target_force_spin.setValue(ForceConfig.DEFAULT_TARGET_FORCE)
        self.target_force_spin.setSingleStep(0.5)
        self.target_force_spin.setDecimals(2)
        layout.addWidget(self.target_force_spin, 0, 1)

        layout.addWidget(QLabel("Force Type:"), 1, 0)
        self.force_type_combo = QComboBox()
        for value, text in ForceConfig.FORCE_TYPES.items():
            self.force_type_combo.addItem(text, value)
        self.force_type_combo.setCurrentIndex(
            self.force_type_combo.findData(ForceConfig.DEFAULT_FORCE_TYPE)
        )
        layout.addWidget(self.force_type_combo, 1, 1)

        layout.addWidget(QLabel("Linear Speed (m/s):"), 2, 0)
        self.linear_speed_spin = QDoubleSpinBox()
        self.linear_speed_spin.setRange(0.01, ForceConfig.MAX_LINEAR_SPEED)
        self.linear_speed_spin.setValue(ForceConfig.DEFAULT_LINEAR_SPEED)
        self.linear_speed_spin.setSingleStep(0.01)
        self.linear_speed_spin.setDecimals(3)
        self.linear_speed_spin.setToolTip("Maximum speed on compliant linear axes.")
        layout.addWidget(self.linear_speed_spin, 2, 1)

        layout.addWidget(QLabel("Angular Speed (rad/s):"), 3, 0)
        self.angular_speed_spin = QDoubleSpinBox()
        self.angular_speed_spin.setRange(0.1, ForceConfig.MAX_ANGULAR_SPEED)
        self.angular_speed_spin.setValue(ForceConfig.DEFAULT_ANGULAR_SPEED)
        self.angular_speed_spin.setSingleStep(0.1)
        self.angular_speed_spin.setDecimals(2)
        self.angular_speed_spin.setToolTip("Maximum speed on compliant rotary axes.")
        layout.addWidget(self.angular_speed_spin, 3, 1)

        layout.addWidget(QLabel("Linear Deviation (mm):"), 4, 0)
        self.deviation_spin = QDoubleSpinBox()
        self.deviation_spin.setRange(0.1, ForceConfig.MAX_LINEAR_DEVIATION * 1000.0)
        self.deviation_spin.setValue(ForceConfig.DEFAULT_LINEAR_DEVIATION * 1000.0)
        self.deviation_spin.setSingleStep(1.0)
        self.deviation_spin.setDecimals(1)
        self.deviation_spin.setToolTip("Maximum X/Y deviation on non-compliant axes.")
        layout.addWidget(self.deviation_spin, 4, 1)

        layout.addWidget(QLabel("Rotation Deviation (deg):"), 5, 0)
        self.rotation_deviation_spin = QDoubleSpinBox()
        self.rotation_deviation_spin.setRange(
            0.1, math.degrees(ForceConfig.MAX_ANGULAR_DEVIATION)
        )
        self.rotation_deviation_spin.setValue(
            math.degrees(ForceConfig.DEFAULT_ANGULAR_DEVIATION)
        )
        self.rotation_deviation_spin.setSingleStep(0.1)
        self.rotation_deviation_spin.setDecimals(2)
        self.rotation_deviation_spin.setToolTip(
            "Maximum rotation deviation on non-compliant axes."
        )
        layout.addWidget(self.rotation_deviation_spin, 5, 1)

        layout.addWidget(QLabel("Auto-Release (s):"), 6, 0)
        self.timeout_spin = QDoubleSpinBox()
        self.timeout_spin.setRange(0.0, ForceConfig.MAX_TIMEOUT)
        self.timeout_spin.setValue(ForceConfig.DEFAULT_TIMEOUT)
        self.timeout_spin.setSingleStep(5.0)
        self.timeout_spin.setDecimals(1)
        self.timeout_spin.setToolTip("Force mode stops automatically after this time. 0 disables.")
        layout.addWidget(self.timeout_spin, 6, 1)

        group.setLayout(layout)
        return group

    def _create_direction_group(self) -> QGroupBox:
        group = QGroupBox("Compliant Axes")
        layout = QGridLayout()

        self.direction_checks = []
        for index, axis in enumerate(FORCE_AXES):
            check = QCheckBox(axis)
            check.setChecked(ForceConfig.DEFAULT_SELECTION[index] == 1)
            layout.addWidget(check, index // 3, index % 3)
            self.direction_checks.append(check)

        group.setLayout(layout)
        return group

    def _create_sensor_group(self) -> QGroupBox:
        group = QGroupBox("TCP Force (built-in estimate)")
        group.setToolTip(
            "UR controller's TCP force estimate read over RTDE; "
            "no external force/torque sensor is required."
        )
        layout = QGridLayout()

        self.sensor_labels = []
        for index, axis in enumerate(FORCE_AXES):
            unit = "N" if index < 3 else "Nm"
            layout.addWidget(QLabel(f"{axis} ({unit}):"), index // 3, (index % 3) * 2)
            value_label = QLabel("0.00")
            value_label.setStyleSheet(
                "QLabel { background-color: #f0f0f0; padding: 5px; font-family: monospace; }"
            )
            value_label.setMinimumWidth(100)
            layout.addWidget(value_label, index // 3, (index % 3) * 2 + 1)
            self.sensor_labels.append(value_label)

        self.sensor_safety_label = QLabel("● Force limits: OK")
        self.sensor_safety_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.sensor_safety_label, 2, 0, 1, 6)
        self.reset_safety()

        group.setLayout(layout)
        return group

    def _create_chart_group(self) -> QGroupBox:
        group = QGroupBox("Force Sensor History")
        layout = QVBoxLayout()

        controls = QHBoxLayout()
        self.pause_button = QPushButton("Pause Chart")
        self.pause_button.clicked.connect(self._toggle_pause)
        controls.addWidget(self.pause_button)

        clear_button = QPushButton("Clear Chart")
        clear_button.clicked.connect(self.clear_chart)
        controls.addWidget(clear_button)
        controls.addStretch()
        layout.addLayout(controls)

        self.plot_widget = pg.PlotWidget(title="Force (Fx, Fy, Fz)")
        self.plot_widget.setLabel("left", "Force", units="N")
        self.plot_widget.setLabel("bottom", "Time", units="s")
        self.plot_widget.addLegend()
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)

        self.fx_curve = self.plot_widget.plot(pen=pg.mkPen(color="r", width=2), name="Fx")
        self.fy_curve = self.plot_widget.plot(pen=pg.mkPen(color="g", width=2), name="Fy")
        self.fz_curve = self.plot_widget.plot(pen=pg.mkPen(color="b", width=2), name="Fz")
        layout.addWidget(self.plot_widget)

        group.setLayout(layout)
        return group

    # ========================================
    # Actions
    # ========================================

    def _on_start_clicked(self):
        selection = [1 if check.isChecked() else 0 for check in self.direction_checks]
        started = self.force_controller.start(
            target_force=self.target_force_spin.value(),
            selection_vector=selection,
            force_type=self.force_type_combo.currentData(),
            speed_limits=self._speed_limits(),
            timeout=self.timeout_spin.value(),
        )
        if started:
            return
        QMessageBox.warning(
            self,
            "Force Mode",
            self.force_controller.last_error or "Failed to start force mode",
        )

    def _on_stop_clicked(self):
        if not self.force_controller.stop():
            error = self.force_controller.last_error
            if error:
                QMessageBox.warning(self, "Force Mode", error)

    def _toggle_pause(self):
        self._chart_paused = not self._chart_paused
        self.pause_button.setText("Resume Chart" if self._chart_paused else "Pause Chart")

    # ========================================
    # External updates
    # ========================================

    def set_connected(self, connected: bool):
        self._connected = connected
        self.start_button.setEnabled(connected and not self._mode_active)
        self.stop_button.setEnabled(connected and self._mode_active)
        if not connected and not self._mode_active:
            self.mode_status_label.setText("Status: Not connected")

    def set_mode_state(self, active: bool, target_force: float = None):
        self._mode_active = active
        if active:
            target_text = f" ({target_force:.1f} N)" if target_force is not None else ""
            self.mode_status_label.setText(f"Status: Active{target_text}")
            self.mode_status_label.setStyleSheet("QLabel { color: #2E7D32; font-weight: bold; }")
        else:
            self.mode_status_label.setText("Status: Inactive")
            self.mode_status_label.setStyleSheet("QLabel { color: black; }")
        self.start_button.setEnabled(self._connected and not active)
        self.stop_button.setEnabled(self._connected and active)

    def on_mode_timeout(self, target_force: float, timeout: float):
        self.mode_status_label.setText(
            f"Status: Auto-released ({target_force:.1f} N, {timeout:.0f} s)"
        )
        self.mode_status_label.setStyleSheet("QLabel { color: #E65100; font-weight: bold; }")

    def on_force_data(self, forces: list):
        """Update the sensor readout and append a chart sample."""
        if forces and len(forces) >= 6:
            for label, value in zip(self.sensor_labels, forces):
                label.setText(f"{value:.2f}")
        self._append_chart_sample(forces)

    def show_force_warning(self, magnitude: float):
        self.sensor_safety_label.setText(f"⚠ Force limits: High ({magnitude:.1f})")
        self.sensor_safety_label.setStyleSheet(
            "QLabel { background-color: #FF9800; color: white; padding: 6px; "
            "font-weight: bold; border-radius: 4px; }"
        )

    def show_force_violation(self, magnitude: float):
        self.sensor_safety_label.setText(f"🚫 Force limits: EXCEEDED ({magnitude:.1f})")
        self.sensor_safety_label.setStyleSheet(
            "QLabel { background-color: #F44336; color: white; padding: 6px; "
            "font-weight: bold; border-radius: 4px; }"
        )

    def reset_safety(self):
        self.sensor_safety_label.setText("● Force limits: OK")
        self.sensor_safety_label.setStyleSheet(
            "QLabel { background-color: #4CAF50; color: white; padding: 6px; "
            "font-weight: bold; border-radius: 4px; }"
        )

    def clear_chart(self):
        self._time_data.clear()
        self._fx_data.clear()
        self._fy_data.clear()
        self._fz_data.clear()
        self._chart_t0 = None
        for curve in (self.fx_curve, self.fy_curve, self.fz_curve):
            curve.setData([], [])

    # ========================================
    # Internals
    # ========================================

    def _speed_limits(self):
        selection = [1 if check.isChecked() else 0 for check in self.direction_checks]
        return build_limits(
            selection,
            self.linear_speed_spin.value(),
            self.angular_speed_spin.value(),
            self.deviation_spin.value() / 1000.0,
            math.radians(self.rotation_deviation_spin.value()),
        )

    def _append_chart_sample(self, forces):
        if self._chart_paused or not forces or len(forces) < 3:
            return

        now = time.monotonic()
        if self._chart_t0 is None:
            self._chart_t0 = now

        self._time_data.append(now - self._chart_t0)
        self._fx_data.append(forces[0])
        self._fy_data.append(forces[1])
        self._fz_data.append(forces[2])

        if len(self._time_data) > MAX_PLOT_POINTS:
            for buffer in (self._time_data, self._fx_data, self._fy_data, self._fz_data):
                buffer.pop(0)

        self.fx_curve.setData(self._time_data, self._fx_data)
        self.fy_curve.setData(self._time_data, self._fy_data)
        self.fz_curve.setData(self._time_data, self._fz_data)
