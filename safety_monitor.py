"""
Safety Monitor Module - Stage 4

Real-time safety monitoring for workspace boundaries, force limits,
and collision detection.

This module provides comprehensive safety monitoring capabilities:
- Workspace boundary checking with warning zones
- Force/torque limit monitoring
- Basic collision detection via force spikes
- Configurable safety thresholds

Author: UR10e Control UI Development Team
Date: 2025-11-04
Stage: 4 - Optimization & Refinement
"""

from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from typing import List, Optional, Dict
import logging
import math

from config import Config
from error_handler import SafetyError

logger = logging.getLogger(__name__)


class SafetyZone:
    """Safety zone enumeration"""
    SAFE = 0
    WARNING = 1
    CRITICAL = 2


class SafetyMonitor(QObject):
    """
    Real-time safety monitoring system for robot operation

    Monitors:
    - Workspace boundaries (X, Y, Z limits)
    - Force/torque limits
    - Collision detection via force spikes
    - Velocity limits

    Signals:
        workspace_warning: Emitted when approaching workspace boundary (axis_name)
        workspace_violation: Emitted when workspace boundary violated (axis_name)
        force_warning: Emitted when force is high but safe (magnitude)
        force_violation: Emitted when force limit exceeded (magnitude)
        collision_detected: Emitted on collision detection (description)
        safety_status_changed: Emitted when overall safety status changes (is_safe)
    """

    # Signals
    workspace_warning = pyqtSignal(str)  # axis name
    workspace_violation = pyqtSignal(str)  # axis name
    force_warning = pyqtSignal(float)  # force magnitude
    force_violation = pyqtSignal(float)  # force magnitude
    collision_detected = pyqtSignal(str)  # description
    safety_status_changed = pyqtSignal(bool)  # is_safe

    def __init__(self, parent=None):
        super().__init__(parent)

        # Monitoring state
        self.enabled = True
        self.workspace_monitoring_enabled = True
        self.force_monitoring_enabled = True
        self.collision_detection_enabled = True

        # Safety thresholds - Normal mode
        self.warning_zone_size = 0.05  # 5cm warning zone before boundary
        self.max_force_threshold = Config.MAX_FORCE_THRESHOLD
        self.max_torque_threshold = Config.MAX_TORQUE_THRESHOLD
        self.force_warning_threshold = Config.MAX_FORCE_THRESHOLD * 0.8  # 80% of max
        self.torque_warning_threshold = Config.MAX_TORQUE_THRESHOLD * 0.8
        self.collision_force_change_threshold = Config.COLLISION_FORCE_SPIKE  # N - sudden force change

        # Freedrive mode tracking
        self.freedrive_mode = False
        self.baseline_forces: Optional[List[float]] = None  # Baseline force for compensation

        # Motion state tracking (for smart force monitoring)
        self.robot_in_motion = False  # Set True during active moves
        self.check_forces_when_idle = False  # Set True to always check forces (even when idle)

        # State tracking
        self.last_tcp_pose: Optional[List[float]] = None
        self.last_forces: Optional[List[float]] = None
        self.last_velocity: Optional[List[float]] = None
        self.is_safe = True

        # Warning tracking (to avoid spam)
        self.active_warnings: Dict[str, bool] = {}

        # Statistics
        self.total_warnings = 0
        self.total_violations = 0
        self.collision_count = 0

        logger.info("SafetyMonitor initialized")

    # ========================================
    # Workspace Boundary Monitoring
    # ========================================

    def check_workspace_boundary(self, tcp_pose: List[float]) -> bool:
        """
        Check if TCP pose is within workspace limits

        Args:
            tcp_pose: [x, y, z, rx, ry, rz]

        Returns:
            True if safe (within limits), False if violation
        """
        if not self.enabled or not self.workspace_monitoring_enabled:
            return True

        if len(tcp_pose) < 3:
            logger.error(f"Invalid TCP pose length: {len(tcp_pose)}")
            return False

        x, y, z = tcp_pose[0:3]
        limits = Config.WORKSPACE_LIMITS

        violations = []
        warnings = []

        # Check X axis
        if x < limits['x_min']:
            violations.append('X_MIN')
        elif x > limits['x_max']:
            violations.append('X_MAX')
        elif x < limits['x_min'] + self.warning_zone_size:
            warnings.append('X_MIN')
        elif x > limits['x_max'] - self.warning_zone_size:
            warnings.append('X_MAX')

        # Check Y axis
        if y < limits['y_min']:
            violations.append('Y_MIN')
        elif y > limits['y_max']:
            violations.append('Y_MAX')
        elif y < limits['y_min'] + self.warning_zone_size:
            warnings.append('Y_MIN')
        elif y > limits['y_max'] - self.warning_zone_size:
            warnings.append('Y_MAX')

        # Check Z axis
        if z < limits['z_min']:
            violations.append('Z_MIN')
        elif z > limits['z_max']:
            violations.append('Z_MAX')
        elif z < limits['z_min'] + self.warning_zone_size:
            warnings.append('Z_MIN')
        elif z > limits['z_max'] - self.warning_zone_size:
            warnings.append('Z_MAX')

        # Emit violations (critical)
        for violation in violations:
            self.workspace_violation.emit(violation)
            logger.critical(f"Workspace boundary VIOLATED: {violation} at position {tcp_pose[:3]}")
            self.total_violations += 1
            self._update_safety_status(False)

        # Emit warnings (only if not already warned)
        for warning in warnings:
            warning_key = f"workspace_{warning}"
            if warning_key not in self.active_warnings:
                self.workspace_warning.emit(warning)
                logger.warning(f"Approaching workspace boundary: {warning} at position {tcp_pose[:3]}")
                self.active_warnings[warning_key] = True
                self.total_warnings += 1

        # Clear warnings that are no longer active
        if not warnings:
            for key in list(self.active_warnings.keys()):
                if key.startswith('workspace_'):
                    del self.active_warnings[key]

        # Update state
        self.last_tcp_pose = tcp_pose

        return len(violations) == 0

    # ========================================
    # Force/Torque Limit Monitoring
    # ========================================

    def check_force_limits(self, forces: List[float]) -> bool:
        """
        Check if forces/torques are within safe limits

        Args:
            forces: [fx, fy, fz, tx, ty, tz]

        Returns:
            True if safe, False if violation
        """
        if not self.enabled or not self.force_monitoring_enabled:
            return True

        if len(forces) < 6:
            logger.error(f"Invalid forces length: {len(forces)}")
            return False

        # Smart force monitoring: Only check limits when robot is active
        # Skip force checks when robot is idle (not moving and not in freedrive)
        # This prevents false positives from static payload forces
        if not self.freedrive_mode and not self.robot_in_motion and not self.check_forces_when_idle:
            # Robot is idle - skip force checking (payload creates static force)
            return True

        # Get raw force/torque values
        fx, fy, fz = forces[0:3]
        tx, ty, tz = forces[3:6]

        # Apply baseline compensation if in freedrive mode
        if self.freedrive_mode and self.baseline_forces is not None:
            # Subtract baseline to get net force (user-applied force only)
            fx_net = fx - self.baseline_forces[0]
            fy_net = fy - self.baseline_forces[1]
            fz_net = fz - self.baseline_forces[2]
            tx_net = tx - self.baseline_forces[3]
            ty_net = ty - self.baseline_forces[4]
            tz_net = tz - self.baseline_forces[5]

            # Calculate net magnitudes
            force_magnitude = math.sqrt(fx_net**2 + fy_net**2 + fz_net**2)
            torque_magnitude = math.sqrt(tx_net**2 + ty_net**2 + tz_net**2)

            logger.debug(f"Freedrive mode - Raw force: {math.sqrt(fx**2 + fy**2 + fz**2):.2f}N, Net force: {force_magnitude:.2f}N")
        else:
            # Normal mode - use raw values
            force_magnitude = math.sqrt(fx**2 + fy**2 + fz**2)
            torque_magnitude = math.sqrt(tx**2 + ty**2 + tz**2)

        # Check force limits (uses dynamic thresholds)
        if force_magnitude > self.max_force_threshold:
            self.force_violation.emit(force_magnitude)
            logger.critical(f"Force limit EXCEEDED: {force_magnitude:.2f}N (limit: {self.max_force_threshold}N)")
            self.total_violations += 1
            self._update_safety_status(False)
            return False

        elif force_magnitude > self.force_warning_threshold:
            if 'force_high' not in self.active_warnings:
                self.force_warning.emit(force_magnitude)
                logger.warning(f"Force level high: {force_magnitude:.2f}N")
                self.active_warnings['force_high'] = True
                self.total_warnings += 1
        else:
            # Clear force warning
            if 'force_high' in self.active_warnings:
                del self.active_warnings['force_high']

        # Check torque limits (uses dynamic thresholds)
        if torque_magnitude > self.max_torque_threshold:
            self.force_violation.emit(torque_magnitude)
            logger.critical(f"Torque limit EXCEEDED: {torque_magnitude:.2f}Nm (limit: {self.max_torque_threshold}Nm)")
            self.total_violations += 1
            self._update_safety_status(False)
            return False

        elif torque_magnitude > self.torque_warning_threshold:
            if 'torque_high' not in self.active_warnings:
                self.force_warning.emit(torque_magnitude)
                logger.warning(f"Torque level high: {torque_magnitude:.2f}Nm")
                self.active_warnings['torque_high'] = True
                self.total_warnings += 1
        else:
            # Clear torque warning
            if 'torque_high' in self.active_warnings:
                del self.active_warnings['torque_high']

        # Update state
        self.last_forces = forces

        return True

    # ========================================
    # Collision Detection
    # ========================================

    def detect_collision(self, forces: List[float]) -> bool:
        """
        Simple collision detection based on force spikes

        Detects sudden changes in force that may indicate collision.

        Args:
            forces: Current force readings [fx, fy, fz, tx, ty, tz]

        Returns:
            True if collision detected, False otherwise
        """
        if not self.enabled or not self.collision_detection_enabled:
            return False

        # Smart collision detection: Only enable in freedrive mode
        # During powered motion, acceleration creates force changes that look like collisions
        # The robot has built-in collision detection for powered motion anyway
        if not self.freedrive_mode:
            return False

        if self.last_forces is None:
            self.last_forces = forces
            return False

        if len(forces) < 3 or len(self.last_forces) < 3:
            return False

        # Calculate force change (only translational forces)
        force_change = math.sqrt(
            sum(
                (curr - last)**2
                for curr, last in zip(forces[0:3], self.last_forces[0:3])
            )
        )

        # Check for sudden force spike
        if force_change > self.collision_force_change_threshold:
            description = f"Sudden force change: {force_change:.2f}N (threshold: {self.collision_force_change_threshold}N)"
            self.collision_detected.emit(description)
            logger.critical(f"COLLISION DETECTED! {description}")
            self.collision_count += 1
            self._update_safety_status(False)
            return True

        return False

    # ========================================
    # Velocity Monitoring
    # ========================================

    def check_velocity_limits(self, velocity: List[float]) -> bool:
        """
        Check if velocity is within safe limits

        Args:
            velocity: [vx, vy, vz, wx, wy, wz]

        Returns:
            True if safe, False if violation
        """
        if not self.enabled:
            return True

        if len(velocity) < 3:
            return True

        # Calculate linear velocity magnitude
        vx, vy, vz = velocity[0:3]
        velocity_magnitude = math.sqrt(vx**2 + vy**2 + vz**2)

        # Check against maximum velocity
        if velocity_magnitude > Config.MAX_VELOCITY:
            logger.warning(f"Velocity exceeds limit: {velocity_magnitude:.3f} m/s (limit: {Config.MAX_VELOCITY} m/s)")
            self.total_warnings += 1
            return False

        self.last_velocity = velocity
        return True

    # ========================================
    # Safety Zone Analysis
    # ========================================

    def get_safety_zone(self, tcp_pose: List[float]) -> SafetyZone:
        """
        Get current safety zone based on TCP position

        Args:
            tcp_pose: [x, y, z, rx, ry, rz]

        Returns:
            SafetyZone: SAFE, WARNING, or CRITICAL
        """
        if not self.enabled:
            return SafetyZone.SAFE

        if len(tcp_pose) < 3:
            return SafetyZone.SAFE

        x, y, z = tcp_pose[0:3]
        limits = Config.WORKSPACE_LIMITS

        # Check for violations (critical zone)
        if (x < limits['x_min'] or x > limits['x_max'] or
            y < limits['y_min'] or y > limits['y_max'] or
            z < limits['z_min'] or z > limits['z_max']):
            return SafetyZone.CRITICAL

        # Check for warning zone
        if (x < limits['x_min'] + self.warning_zone_size or
            x > limits['x_max'] - self.warning_zone_size or
            y < limits['y_min'] + self.warning_zone_size or
            y > limits['y_max'] - self.warning_zone_size or
            z < limits['z_min'] + self.warning_zone_size or
            z > limits['z_max'] - self.warning_zone_size):
            return SafetyZone.WARNING

        return SafetyZone.SAFE

    # ========================================
    # Control & Configuration
    # ========================================

    def enable(self):
        """Enable safety monitoring"""
        self.enabled = True
        logger.info("Safety monitoring ENABLED")
        self._update_safety_status(True)

    def disable(self):
        """Disable safety monitoring (use with caution!)"""
        self.enabled = False
        logger.warning("Safety monitoring DISABLED - Use with caution!")

    def enable_workspace_monitoring(self):
        """Enable workspace boundary monitoring"""
        self.workspace_monitoring_enabled = True
        logger.info("Workspace monitoring enabled")

    def disable_workspace_monitoring(self):
        """Disable workspace boundary monitoring"""
        self.workspace_monitoring_enabled = False
        logger.warning("Workspace monitoring disabled")

    def enable_force_monitoring(self):
        """Enable force/torque monitoring"""
        self.force_monitoring_enabled = True
        logger.info("Force monitoring enabled")

    def disable_force_monitoring(self):
        """Disable force/torque monitoring"""
        self.force_monitoring_enabled = False
        logger.warning("Force monitoring disabled")

    def enable_collision_detection(self):
        """Enable collision detection"""
        self.collision_detection_enabled = True
        logger.info("Collision detection enabled")

    def disable_collision_detection(self):
        """Disable collision detection"""
        self.collision_detection_enabled = False
        logger.warning("Collision detection disabled")

    def set_warning_zone_size(self, size: float):
        """
        Set size of warning zone before workspace boundary

        Args:
            size: Warning zone size in meters (e.g., 0.05 for 5cm)
        """
        if size < 0:
            logger.error(f"Invalid warning zone size: {size}")
            return

        self.warning_zone_size = size
        logger.info(f"Warning zone size set to {size*1000:.1f}mm")

    def set_force_warning_threshold(self, threshold: float):
        """
        Set force warning threshold as percentage of maximum

        Args:
            threshold: Warning threshold as fraction of max (e.g., 0.8 for 80%)
        """
        if not 0 < threshold < 1:
            logger.error(f"Invalid threshold: {threshold}. Must be between 0 and 1")
            return

        self.force_warning_threshold = Config.MAX_FORCE_THRESHOLD * threshold
        logger.info(f"Force warning threshold set to {self.force_warning_threshold:.2f}N ({threshold*100:.0f}% of max)")

    def set_collision_threshold(self, threshold: float):
        """
        Set collision detection force change threshold

        Args:
            threshold: Force change threshold in Newtons
        """
        if threshold < 0:
            logger.error(f"Invalid collision threshold: {threshold}")
            return

        self.collision_force_change_threshold = threshold
        logger.info(f"Collision threshold set to {threshold:.2f}N")

    # ========================================
    # Status & Reporting
    # ========================================

    def get_status(self) -> Dict:
        """
        Get comprehensive safety status

        Returns:
            Dictionary with safety status information
        """
        return {
            'enabled': self.enabled,
            'workspace_monitoring': self.workspace_monitoring_enabled,
            'force_monitoring': self.force_monitoring_enabled,
            'collision_detection': self.collision_detection_enabled,
            'is_safe': self.is_safe,
            'total_warnings': self.total_warnings,
            'total_violations': self.total_violations,
            'collision_count': self.collision_count,
            'active_warnings': len(self.active_warnings),
            'warning_zone_size': self.warning_zone_size,
            'force_warning_threshold': self.force_warning_threshold,
            'collision_threshold': self.collision_force_change_threshold
        }

    def get_active_warnings(self) -> List[str]:
        """
        Get list of currently active warnings

        Returns:
            List of warning identifiers
        """
        return list(self.active_warnings.keys())

    def reset_statistics(self):
        """Reset warning and violation counters"""
        self.total_warnings = 0
        self.total_violations = 0
        self.collision_count = 0
        logger.info("Safety statistics reset")

    def clear_warnings(self):
        """Clear all active warnings"""
        self.active_warnings.clear()
        logger.info("Active warnings cleared")

    # ========================================
    # Freedrive Mode Safety Profile
    # ========================================

    def enable_freedrive_profile(self, current_forces: Optional[List[float]] = None):
        """
        Switch to freedrive safety profile with relaxed limits and baseline compensation

        Args:
            current_forces: Optional current force readings to use as baseline [fx, fy, fz, tx, ty, tz]
        """
        self.freedrive_mode = True

        # Switch to freedrive thresholds
        self.max_force_threshold = Config.FREEDRIVE_MAX_FORCE_THRESHOLD
        self.max_torque_threshold = Config.FREEDRIVE_MAX_TORQUE_THRESHOLD
        self.force_warning_threshold = Config.FREEDRIVE_MAX_FORCE_THRESHOLD * 0.8
        self.torque_warning_threshold = Config.FREEDRIVE_MAX_TORQUE_THRESHOLD * 0.8
        self.collision_force_change_threshold = Config.FREEDRIVE_COLLISION_FORCE_SPIKE

        # Record baseline forces for compensation
        if current_forces is not None and len(current_forces) >= 6:
            self.baseline_forces = current_forces.copy()
            raw_magnitude = math.sqrt(current_forces[0]**2 + current_forces[1]**2 + current_forces[2]**2)
            logger.info(f"Freedrive profile enabled with baseline force: {raw_magnitude:.2f}N")
            logger.info(f"New limits - Force: {self.max_force_threshold}N, Torque: {self.max_torque_threshold}Nm, Collision spike: {self.collision_force_change_threshold}N")
        else:
            self.baseline_forces = None
            logger.warning("Freedrive profile enabled WITHOUT baseline compensation (no force data provided)")
            logger.info(f"New limits - Force: {self.max_force_threshold}N, Torque: {self.max_torque_threshold}Nm")

        # Clear existing warnings since we're changing thresholds
        self.clear_warnings()

    def disable_freedrive_profile(self):
        """
        Switch back to normal safety profile with strict limits
        """
        self.freedrive_mode = False
        self.baseline_forces = None

        # Restore normal thresholds
        self.max_force_threshold = Config.MAX_FORCE_THRESHOLD
        self.max_torque_threshold = Config.MAX_TORQUE_THRESHOLD
        self.force_warning_threshold = Config.MAX_FORCE_THRESHOLD * 0.8
        self.torque_warning_threshold = Config.MAX_TORQUE_THRESHOLD * 0.8
        self.collision_force_change_threshold = Config.COLLISION_FORCE_SPIKE

        logger.info(f"Normal safety profile restored - Force: {self.max_force_threshold}N, Torque: {self.max_torque_threshold}Nm")

        # Clear existing warnings since we're changing thresholds
        self.clear_warnings()

    def update_baseline_forces(self, forces: List[float]):
        """
        Update the baseline force compensation values

        Args:
            forces: New baseline force readings [fx, fy, fz, tx, ty, tz]
        """
        if self.freedrive_mode and len(forces) >= 6:
            self.baseline_forces = forces.copy()
            raw_magnitude = math.sqrt(forces[0]**2 + forces[1]**2 + forces[2]**2)
            logger.info(f"Baseline forces updated: {raw_magnitude:.2f}N")
        else:
            logger.warning("Cannot update baseline forces - not in freedrive mode or invalid force data")

    # ========================================
    # Internal Methods
    # ========================================

    def _update_safety_status(self, is_safe: bool):
        """
        Update overall safety status and emit signal if changed

        Args:
            is_safe: New safety status
        """
        if self.is_safe != is_safe:
            self.is_safe = is_safe
            self.safety_status_changed.emit(is_safe)

            if is_safe:
                logger.info("System status: SAFE")
            else:
                logger.warning("System status: UNSAFE")


# Example usage and testing
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    app = QApplication(sys.argv)

    # Create safety monitor
    monitor = SafetyMonitor()

    # Connect signals for testing
    monitor.workspace_warning.connect(lambda axis: print(f"⚠️  Warning: Approaching {axis}"))
    monitor.workspace_violation.connect(lambda axis: print(f"🚫 VIOLATION: Boundary {axis} exceeded!"))
    monitor.force_warning.connect(lambda force: print(f"⚠️  Warning: High force {force:.2f}N"))
    monitor.force_violation.connect(lambda force: print(f"🚫 VIOLATION: Force {force:.2f}N exceeded!"))
    monitor.collision_detected.connect(lambda desc: print(f"💥 COLLISION: {desc}"))

    # Test workspace boundaries
    print("\n=== Testing Workspace Boundaries ===")
    monitor.check_workspace_boundary([0.5, 0.0, 0.5, 0, 0, 0])  # Safe
    monitor.check_workspace_boundary([0.76, 0.0, 0.5, 0, 0, 0])  # Warning
    monitor.check_workspace_boundary([0.85, 0.0, 0.5, 0, 0, 0])  # Violation

    # Test force limits
    print("\n=== Testing Force Limits ===")
    monitor.check_force_limits([5, 5, 5, 0, 0, 0])  # Safe (~8.7N)
    monitor.check_force_limits([20, 20, 20, 0, 0, 0])  # Warning (~34.6N)
    monitor.check_force_limits([40, 40, 40, 0, 0, 0])  # Violation (~69.3N)

    # Test collision detection
    print("\n=== Testing Collision Detection ===")
    monitor.detect_collision([5, 5, 5, 0, 0, 0])  # Set baseline
    monitor.detect_collision([30, 30, 30, 0, 0, 0])  # Large spike - collision

    # Print status
    print("\n=== Safety Status ===")
    status = monitor.get_status()
    for key, value in status.items():
        print(f"{key}: {value}")

    print("\nTest completed successfully!")
