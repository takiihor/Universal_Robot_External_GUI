# Stage 4 Quick Start Guide

## What Has Been Completed

### ✅ Error Handling System (FULLY IMPLEMENTED)

**New File Created:** `error_handler.py`
- Comprehensive error classification and handling
- Auto-recovery mechanisms
- Error history tracking
- User-friendly error dialogs

**Enhanced File:** `robot_controller.py`
- Automatic reconnection on connection loss (up to 5 attempts every 5 seconds)
- Connection loss detection via consecutive error counting
- Graceful error handling in all methods
- All log messages converted to English

### How to Use the New Error Handling

#### 1. Basic Error Handling
```python
from error_handler import ErrorHandler, ConnectionError

# Create error handler
error_handler = ErrorHandler(parent=main_window)

# Handle an error
try:
    robot.connect(ip, port)
except Exception as e:
    error_handler.handle_error(
        e,
        context="Robot connection",
        show_dialog=True,
        attempt_recovery=True
    )
```

#### 2. Auto-Reconnection
```python
# In robot_controller.py - already implemented!
# Auto-reconnection is enabled by default

# To disable:
controller = RobotController(enable_auto_reconnect=False)

# Configure reconnection parameters:
controller.max_reconnect_attempts = 10  # Default: 5
controller.reconnect_interval = 3000    # ms, Default: 5000
```

#### 3. Listen to Reconnection Events
```python
# In your UI code:
self.robot_controller.reconnection_attempted.connect(
    self.on_reconnection_status
)

def on_reconnection_status(self, success: bool, message: str):
    if success:
        print(f"Reconnection successful: {message}")
    else:
        print(f"Reconnection failed: {message}")
```

---

## What to Implement Next

### Priority 1: Safety Features

**Estimated Time:** 2-3 hours

#### Step 1: Create SafetyMonitor Class

Create `safety_monitor.py`:

```python
"""
Safety Monitor Module - Stage 4

Real-time safety monitoring for workspace boundaries, force limits,
and collision detection.
"""

from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from typing import List
import logging

from config import Config
from error_handler import SafetyError

logger = logging.getLogger(__name__)


class SafetyMonitor(QObject):
    """Real-time safety monitoring system"""

    # Signals
    workspace_warning = pyqtSignal(str)  # axis name
    workspace_violation = pyqtSignal(str)  # axis name
    force_warning = pyqtSignal(float)  # force magnitude
    force_violation = pyqtSignal(float)  # force magnitude
    collision_detected = pyqtSignal(str)  # description

    def __init__(self, parent=None):
        super().__init__(parent)
        self.enabled = True
        self.warning_zone = 0.05  # 5cm warning zone
        self.last_tcp_pose = None
        self.last_forces = None

    def check_workspace_boundary(self, tcp_pose: List[float]) -> bool:
        """
        Check if TCP pose is within workspace limits

        Args:
            tcp_pose: [x, y, z, rx, ry, rz]

        Returns:
            True if safe, False if violation
        """
        if not self.enabled:
            return True

        x, y, z = tcp_pose[0:3]
        limits = Config.WORKSPACE_LIMITS

        # Check each axis
        violations = []

        # X axis
        if x < limits['x_min']:
            violations.append('X_MIN')
        elif x > limits['x_max']:
            violations.append('X_MAX')
        elif x < limits['x_min'] + self.warning_zone:
            self.workspace_warning.emit('X_MIN')
        elif x > limits['x_max'] - self.warning_zone:
            self.workspace_warning.emit('X_MAX')

        # Y axis
        if y < limits['y_min']:
            violations.append('Y_MIN')
        elif y > limits['y_max']:
            violations.append('Y_MAX')
        elif y < limits['y_min'] + self.warning_zone:
            self.workspace_warning.emit('Y_MIN')
        elif y > limits['y_max'] - self.warning_zone:
            self.workspace_warning.emit('Y_MAX')

        # Z axis
        if z < limits['z_min']:
            violations.append('Z_MIN')
        elif z > limits['z_max']:
            violations.append('Z_MAX')
        elif z < limits['z_min'] + self.warning_zone:
            self.workspace_warning.emit('Z_MIN')
        elif z > limits['z_max'] - self.warning_zone:
            self.workspace_warning.emit('Z_MAX')

        # Emit violations
        for violation in violations:
            self.workspace_violation.emit(violation)
            logger.warning(f"Workspace violation: {violation}")

        self.last_tcp_pose = tcp_pose
        return len(violations) == 0

    def check_force_limits(self, forces: List[float]) -> bool:
        """
        Check if forces are within safe limits

        Args:
            forces: [fx, fy, fz, tx, ty, tz]

        Returns:
            True if safe, False if violation
        """
        if not self.enabled:
            return True

        # Calculate force magnitude
        fx, fy, fz = forces[0:3]
        force_magnitude = (fx**2 + fy**2 + fz**2)**0.5

        # Calculate torque magnitude
        tx, ty, tz = forces[3:6]
        torque_magnitude = (tx**2 + ty**2 + tz**2)**0.5

        # Check force limits
        if force_magnitude > Config.MAX_FORCE_THRESHOLD:
            self.force_violation.emit(force_magnitude)
            logger.critical(f"Force limit exceeded: {force_magnitude:.2f}N")
            return False
        elif force_magnitude > Config.MAX_FORCE_THRESHOLD * 0.8:
            self.force_warning.emit(force_magnitude)

        # Check torque limits
        if torque_magnitude > Config.MAX_TORQUE_THRESHOLD:
            self.force_violation.emit(torque_magnitude)
            logger.critical(f"Torque limit exceeded: {torque_magnitude:.2f}Nm")
            return False

        self.last_forces = forces
        return True

    def detect_collision(self, forces: List[float]) -> bool:
        """
        Simple collision detection based on force spikes

        Args:
            forces: Current force readings

        Returns:
            True if collision detected
        """
        if not self.enabled or self.last_forces is None:
            return False

        # Calculate force change
        force_change = sum(
            abs(curr - last)
            for curr, last in zip(forces[0:3], self.last_forces[0:3])
        )

        # Threshold for collision (sudden force change)
        collision_threshold = 20.0  # N

        if force_change > collision_threshold:
            self.collision_detected.emit(f"Sudden force change: {force_change:.2f}N")
            logger.critical(f"Collision detected! Force change: {force_change:.2f}N")
            return True

        return False

    def enable(self):
        """Enable safety monitoring"""
        self.enabled = True
        logger.info("Safety monitoring enabled")

    def disable(self):
        """Disable safety monitoring (use with caution!)"""
        self.enabled = False
        logger.warning("Safety monitoring DISABLED")
```

#### Step 2: Integrate SafetyMonitor into RobotController

In `robot_controller.py`, add to `__init__`:

```python
# Safety monitoring
from safety_monitor import SafetyMonitor
self.safety_monitor = SafetyMonitor(parent=parent)
self.safety_monitor.workspace_violation.connect(self._on_workspace_violation)
self.safety_monitor.force_violation.connect(self._on_force_violation)
self.safety_monitor.collision_detected.connect(self._on_collision_detected)
```

Add handler methods:

```python
def _on_workspace_violation(self, axis: str):
    """Handle workspace violation"""
    error = SafetyError(f"Workspace boundary violated: {axis}")
    self.error_handler.handle_error(error, context="Safety monitoring")
    self.emergency_stop()

def _on_force_violation(self, magnitude: float):
    """Handle force limit violation"""
    error = SafetyError(f"Force limit exceeded: {magnitude:.2f}N")
    self.error_handler.handle_error(error, context="Force monitoring")
    self.emergency_stop()

def _on_collision_detected(self, description: str):
    """Handle collision detection"""
    error = SafetyError(f"Collision detected: {description}")
    self.error_handler.handle_error(error, context="Collision detection")
    self.emergency_stop()
```

In `_on_tcp_pose_updated`, add safety check:

```python
def _on_tcp_pose_updated(self, pose: List[float]):
    """TCP pose updated"""
    with QMutexLocker(self.mutex):
        self._current_tcp_pose = pose

    # Safety check
    self.safety_monitor.check_workspace_boundary(pose)

    self.tcp_pose_updated.emit(pose)
```

In `_on_force_data_updated`, add safety check:

```python
def _on_force_data_updated(self, force: List[float]):
    """Force data updated"""
    with QMutexLocker(self.mutex):
        self._current_tcp_force = force

    # Safety checks
    self.safety_monitor.check_force_limits(force)
    self.safety_monitor.detect_collision(force)

    self.force_data_updated.emit(force)
```

#### Step 3: Add Visual Safety Indicators to UI

In `ui_mainwindow.py`, add safety status panel:

```python
def create_safety_status_panel(self) -> QGroupBox:
    """Create safety monitoring status panel"""
    group = QGroupBox("Safety Status")
    layout = QVBoxLayout()

    # Workspace status
    self.workspace_status_label = QLabel("Workspace: OK")
    self.workspace_status_label.setStyleSheet(
        "QLabel { background-color: #4CAF50; color: white; padding: 5px; }"
    )
    layout.addWidget(self.workspace_status_label)

    # Force status
    self.force_status_label = QLabel("Forces: OK")
    self.force_status_label.setStyleSheet(
        "QLabel { background-color: #4CAF50; color: white; padding: 5px; }"
    )
    layout.addWidget(self.force_status_label)

    # Collision status
    self.collision_status_label = QLabel("Collision: None")
    self.collision_status_label.setStyleSheet(
        "QLabel { background-color: #4CAF50; color: white; padding: 5px; }"
    )
    layout.addWidget(self.collision_status_label)

    group.setLayout(layout)
    return group
```

Connect safety signals:

```python
# In connect_signals()
self.robot_controller.safety_monitor.workspace_warning.connect(
    self.on_workspace_warning
)
self.robot_controller.safety_monitor.force_warning.connect(
    self.on_force_warning
)
```

---

### Priority 2: User Experience - Tooltips

**Estimated Time:** 1 hour

Add tooltips to all major UI elements in `ui_mainwindow.py`:

```python
# Connection section
self.connect_button.setToolTip(
    "<b>Connect to Robot</b><br>"
    "Establish RTDE connection with robot controller.<br>"
    "<i>Shortcut: Ctrl+Shift+C</i>"
)

self.disconnect_button.setToolTip(
    "<b>Disconnect from Robot</b><br>"
    "Safely disconnect from robot.<br>"
    "<i>Shortcut: Ctrl+Shift+D</i>"
)

# Emergency stop
self.emergency_stop_button.setToolTip(
    "<b>EMERGENCY STOP</b><br>"
    "Immediately stops all robot motion.<br>"
    "<font color='red'><b>Use only in emergency!</b></font><br>"
    "<i>Shortcut: Space</i>"
)

# Data logging
self.start_recording_btn.setToolTip(
    "<b>Start Recording</b><br>"
    "Begin logging robot state data.<br>"
    "Format: CSV or HDF5<br>"
    "<i>Shortcut: Ctrl+R</i>"
)

# TCP control
self.tcp_x_plus.setToolTip(
    "<b>Move TCP +X</b><br>"
    f"Step size: {Config.TCP_STEP_SIZES[self.current_tcp_step_index]*1000:.1f}mm<br>"
    "Positive X direction"
)
```

---

### Priority 3: Settings Management

**Estimated Time:** 1-2 hours

Add to `ui_mainwindow.py`:

```python
from PyQt5.QtCore import QSettings

def save_window_state(self):
    """Save window geometry and state"""
    settings = QSettings('UR10e', 'ControlUI')

    # Window geometry
    settings.setValue('geometry', self.saveGeometry())
    settings.setValue('windowState', self.saveState())

    # Splitter positions
    settings.setValue('mainSplitter', self.main_splitter.saveState())

    # Last connection
    settings.setValue('lastIP', self.ip_input.text())
    settings.setValue('lastPort', self.port_input.text())

    # Control parameters
    settings.setValue('tcpSpeed', self.tcp_speed_spin.value())
    settings.setValue('tcpAccel', self.tcp_accel_spin.value())
    settings.setValue('jointSpeed', self.joint_speed_spin.value())
    settings.setValue('jointAccel', self.joint_accel_spin.value())

    logger.info("Window state saved")

def restore_window_state(self):
    """Restore window geometry and state"""
    settings = QSettings('UR10e', 'ControlUI')

    # Window geometry
    geometry = settings.value('geometry')
    if geometry:
        self.restoreGeometry(geometry)

    window_state = settings.value('windowState')
    if window_state:
        self.restoreState(window_state)

    # Splitter positions
    splitter_state = settings.value('mainSplitter')
    if splitter_state:
        self.main_splitter.restoreState(splitter_state)

    # Last connection
    last_ip = settings.value('lastIP')
    if last_ip:
        self.ip_input.setText(last_ip)

    last_port = settings.value('lastPort')
    if last_port:
        self.port_input.setText(last_port)

    # Control parameters
    tcp_speed = settings.value('tcpSpeed')
    if tcp_speed:
        self.tcp_speed_spin.setValue(float(tcp_speed))

    logger.info("Window state restored")

# Call in __init__:
def __init__(self):
    super().__init__()
    # ... existing init code ...
    self.restore_window_state()

# Call in closeEvent:
def closeEvent(self, event):
    # ... existing close code ...
    self.save_window_state()
    # ... rest of close code ...
```

---

## Testing Your Changes

### Test Error Handling
```bash
# Run the application
python main.py

# Test scenarios:
1. Try connecting to invalid IP (192.168.1.999)
   - Should show error dialog
   - Should not crash

2. Connect to robot, then disconnect network
   - Should detect connection loss
   - Should attempt auto-reconnection
   - Should show reconnection attempts

3. After 5 failed reconnections
   - Should stop trying
   - Should show failure message
```

### Test Safety Features (after implementation)
```bash
# In simulation or with real robot:
1. Move TCP close to workspace boundary
   - Should show warning
   - Should prevent movement beyond boundary

2. Apply excessive force
   - Should trigger force warning
   - Should execute emergency stop if exceeded
```

---

## File Structure After Stage 4

```
ur10e_control_ui/
├── main.py
├── robot_controller.py       ✅ UPDATED (Stage 4)
├── ui_mainwindow.py          🔄 TO UPDATE
├── data_logger.py            ✅ COMPLETE (Stage 3)
├── config.py                 🔄 TO UPDATE
├── utils.py                  🔄 TO UPDATE
├── error_handler.py          ✅ NEW (Stage 4)
├── safety_monitor.py         📝 TO CREATE (Stage 4)
├── STAGE4_PROGRESS_REPORT.md ✅ NEW
├── STAGE4_QUICKSTART.md      ✅ NEW (this file)
├── STAGE3_COMPLETION_REPORT.md
└── logs/
    └── (log files)
```

---

## Common Issues & Solutions

### Issue: Import Error for error_handler
**Solution:** Make sure `error_handler.py` is in the same directory as `robot_controller.py`

### Issue: Auto-reconnection Not Working
**Solution:** Check that `enable_auto_reconnect=True` (default)

### Issue: Too Many Reconnection Attempts
**Solution:** Adjust parameters:
```python
controller.max_reconnect_attempts = 10
controller.reconnect_interval = 3000  # 3 seconds
```

---

## Contact & Support

For questions or issues with Stage 4 implementation:
1. Check `STAGE4_PROGRESS_REPORT.md` for detailed information
2. Review error logs in `logs/` directory
3. Check Python console for error messages

---

*Quick Start Guide - Stage 4*
*Last Updated: 2025-11-04*
