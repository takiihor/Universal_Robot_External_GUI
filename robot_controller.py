"""
UR10e Robot Controller Core Module - Stage 4 Enhanced

This module handles RTDE communication, motion control, and status monitoring.
Uses QThread for background data reception with signal-based UI updates.

Features (Stage 4):
- Enhanced error handling with automatic recovery
- Network disconnection auto-reconnection
- Comprehensive error logging in English
- Safety validation with detailed feedback

Author: UR10e Control UI Development Team
Date: 2025-11-04
Stage: 4 - Optimization & Refinement
"""

import logging
import time
import socket
from typing import List, Optional, Dict, Any
from PyQt5.QtCore import QObject, QThread, pyqtSignal, QMutex, QMutexLocker, QTimer

try:
    from rtde_control import RTDEControlInterface
    from rtde_receive import RTDEReceiveInterface
    RTDE_AVAILABLE = True
except ImportError:
    RTDE_AVAILABLE = False
    logging.warning("ur_rtde module not installed. Some features will be unavailable.")

from config import Config
from preset_manager import PresetManager
from utils import check_pose_in_workspace, check_joint_limits
from error_handler import (
    ErrorHandler, ConnectionError as RobotConnectionError,
    CommunicationError, MotionControlError, SafetyError,
    safe_execute
)
from safety_monitor import SafetyMonitor

# Setup logger
logger = logging.getLogger(__name__)


class DataReceiverThread(QThread):
    """Background data receiver thread for robot state"""

    # Define signals
    tcp_pose_updated = pyqtSignal(list)  # TCP pose update
    joint_positions_updated = pyqtSignal(list)  # Joint angles update
    force_data_updated = pyqtSignal(list)  # Force sensor data update
    robot_mode_changed = pyqtSignal(int)  # Robot mode change
    safety_status_changed = pyqtSignal(int)  # Safety status change
    error_occurred = pyqtSignal(str)  # Error occurred
    connection_lost = pyqtSignal()  # Connection lost

    def __init__(self, rtde_receive: 'RTDEReceiveInterface', parent=None):
        super().__init__(parent)
        self.rtde_receive = rtde_receive
        self.running = False
        self.update_rate = Config.STATUS_UPDATE_RATE  # Hz
        self.error_count = 0
        self.max_consecutive_errors = 10

    def run(self):
        """Thread main loop"""
        self.running = True
        self.error_count = 0
        logger.info("Data receiver thread started")

        while self.running:
            try:
                if self.rtde_receive is None:
                    logger.error("RTDE Receive interface is None")
                    self.error_occurred.emit("RTDE Receive interface not initialized")
                    break

                # Read TCP pose
                tcp_pose = self.rtde_receive.getActualTCPPose()
                if tcp_pose:
                    self.tcp_pose_updated.emit(list(tcp_pose))

                # Read joint angles
                joint_positions = self.rtde_receive.getActualQ()
                if joint_positions:
                    self.joint_positions_updated.emit(list(joint_positions))

                # Read force sensor data
                tcp_force = self.rtde_receive.getActualTCPForce()
                if tcp_force:
                    self.force_data_updated.emit(list(tcp_force))

                # Read robot mode
                robot_mode = self.rtde_receive.getRobotMode()
                if robot_mode is not None:
                    self.robot_mode_changed.emit(robot_mode)

                # Read safety status
                safety_mode = self.rtde_receive.getSafetyMode()
                if safety_mode is not None:
                    self.safety_status_changed.emit(safety_mode)

                # Reset error count on successful read
                self.error_count = 0

                # Control update rate
                time.sleep(1.0 / self.update_rate)

            except Exception as e:
                self.error_count += 1
                logger.error(f"Data receiver thread error: {e} (count: {self.error_count})")
                self.error_occurred.emit(f"Data reception error: {str(e)}")

                # Check for connection loss
                if self.error_count >= self.max_consecutive_errors:
                    logger.critical("Too many consecutive errors - connection likely lost")
                    self.connection_lost.emit()
                    break

                time.sleep(0.1)

        logger.info("Data receiver thread stopped")

    def stop(self):
        """Stop thread"""
        self.running = False
        self.wait(5000)  # Wait up to 5 seconds for thread to finish
        if self.isRunning():
            logger.warning("Data receiver thread did not stop gracefully, terminating")
            self.terminate()
            self.wait()


class RobotController(QObject):
    """Robot controller class with enhanced error handling and auto-reconnection"""

    # Define signals
    tcp_pose_updated = pyqtSignal(list)
    joint_positions_updated = pyqtSignal(list)
    force_data_updated = pyqtSignal(list)
    robot_mode_changed = pyqtSignal(int)
    safety_status_changed = pyqtSignal(int)
    connection_status_changed = pyqtSignal(bool)
    error_occurred = pyqtSignal(str)
    info_message = pyqtSignal(str)
    reconnection_attempted = pyqtSignal(bool, str)  # success, message

    # Trajectory replay signals
    trajectory_replay_started = pyqtSignal(int)  # total_points
    trajectory_replay_progress = pyqtSignal(int, int)  # current_point, total_points
    trajectory_replay_completed = pyqtSignal(bool)  # success
    trajectory_replay_paused = pyqtSignal(int, int)  # current_point, total_points

    def __init__(self, parent=None, enable_auto_reconnect: bool = True):
        super().__init__(parent)

        # RTDE interfaces
        self.rtde_control: Optional[RTDEControlInterface] = None
        self.rtde_receive: Optional[RTDEReceiveInterface] = None

        # Data receiver thread
        self.data_receiver: Optional[DataReceiverThread] = None

        # Connection state
        self._connected = False
        self._ip = ""
        self._port = 0

        # Thread lock
        self.mutex = QMutex()

        # Current state cache
        self._current_tcp_pose: List[float] = [0] * 6
        self._current_joint_positions: List[float] = [0] * 6
        self._current_tcp_force: List[float] = [0] * 6
        self._robot_mode: int = 0
        self._safety_mode: int = 0

        # Error handling
        self.error_handler = ErrorHandler(parent=parent)

        # Safety monitoring
        self.safety_monitor = SafetyMonitor(parent=parent)
        self.safety_monitor.workspace_violation.connect(self._on_workspace_violation)
        self.safety_monitor.force_violation.connect(self._on_force_violation)
        self.safety_monitor.collision_detected.connect(self._on_collision_detected)
        self.safety_monitor.workspace_warning.connect(self._on_workspace_warning)
        self.safety_monitor.force_warning.connect(self._on_force_warning)

        # Auto-reconnection settings
        self.enable_auto_reconnect = enable_auto_reconnect
        self.reconnect_timer = QTimer()
        self.reconnect_timer.timeout.connect(self._attempt_reconnect)
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_interval = 5000  # ms

        # Trajectory replay pause/resume state
        self._trajectory_paused = False
        self._trajectory_pause_point = 0

        # Preset management
        self.preset_manager = PresetManager()
        self._trajectory_data_cache = []
        self._trajectory_speed_cache = None
        self._trajectory_accel_cache = None
        self._trajectory_use_joint_space = True

        # Check RTDE availability
        if not RTDE_AVAILABLE:
            error_msg = "ur_rtde module not installed. Please run: pip install ur-rtde"
            logger.error(error_msg)
            self.error_handler.handle_error(
                RobotConnectionError(error_msg),
                context="Module initialization",
                show_dialog=False
            )

        logger.info("RobotController initialized with auto-reconnect: %s, safety monitoring: enabled", enable_auto_reconnect)

    # ========================================
    # Connection Management
    # ========================================

    def connect(self, ip: str, port: int = 30004) -> bool:
        """
        Connect to robot with enhanced error handling

        Args:
            ip: Robot IP address
            port: RTDE port (default 30004)

        Returns:
            bool: True if connection successful
        """
        if not RTDE_AVAILABLE:
            error = RobotConnectionError("ur_rtde module not installed")
            self.error_handler.handle_error(error, context="Connection attempt")
            self.error_occurred.emit(str(error))
            return False

        if self._connected:
            logger.warning("Already connected to robot, disconnecting first")
            self.disconnect()

        # Store connection info before attempting (needed for reconnection even if this attempt fails)
        self._ip = ip
        self._port = port

        try:
            logger.info(f"Connecting to robot: {ip}:{port}")
            self.info_message.emit(f"Connecting to {ip}:{port}...")

            # Create RTDE Control interface
            self.rtde_control = RTDEControlInterface(ip)
            logger.info("RTDE Control interface established")

            # Create RTDE Receive interface
            self.rtde_receive = RTDEReceiveInterface(ip)
            logger.info("RTDE Receive interface established")

            # Mark as connected
            self._connected = True

            # Reset reconnection counter
            self.reconnect_attempts = 0

            # Start data streaming thread
            self.start_data_streaming()

            # Emit connection status
            self.connection_status_changed.emit(True)
            self.info_message.emit(f"Successfully connected to {ip}")

            logger.info(f"Successfully connected to robot: {ip}:{port}")
            return True

        except Exception as e:
            error_msg = f"Connection failed: {str(e)}"
            logger.error(error_msg)

            # Create detailed error
            error = RobotConnectionError(
                error_msg,
                ip=ip,
                port=port
            )
            self.error_handler.handle_error(error, context="Robot connection", show_dialog=True)

            self.error_occurred.emit(error_msg)
            self._connected = False
            self.connection_status_changed.emit(False)

            # Start auto-reconnection if enabled
            if self.enable_auto_reconnect:
                self._start_reconnection_timer()

            return False

    def disconnect(self) -> bool:
        """
        Disconnect from robot

        Returns:
            bool: True if disconnection successful
        """
        try:
            # Stop reconnection timer if running
            if self.reconnect_timer.isActive():
                self.reconnect_timer.stop()
                logger.info("Reconnection timer stopped")

            # Stop data receiver thread
            self.stop_data_streaming()

            # Stop any running motion
            if self.rtde_control is not None:
                try:
                    self.rtde_control.stopScript()
                except Exception as e:
                    logger.warning(f"Failed to stop script during disconnect: {e}")

            # Close RTDE interfaces
            if self.rtde_control is not None:
                try:
                    self.rtde_control.disconnect()
                except Exception as e:
                    logger.warning(f"Failed to disconnect control interface: {e}")
                finally:
                    self.rtde_control = None

            if self.rtde_receive is not None:
                try:
                    self.rtde_receive.disconnect()
                except Exception as e:
                    logger.warning(f"Failed to disconnect receive interface: {e}")
                finally:
                    self.rtde_receive = None

            self._connected = False
            self.connection_status_changed.emit(False)
            self.info_message.emit("Disconnected from robot")

            logger.info("Disconnected from robot")
            return True

        except Exception as e:
            error_msg = f"Error during disconnection: {str(e)}"
            logger.error(error_msg)

            error = CommunicationError(error_msg)
            self.error_handler.handle_error(error, context="Robot disconnection", show_dialog=False)

            self.error_occurred.emit(error_msg)
            return False

    def reconnect(self) -> bool:
        """
        Reconnect to robot (manual reconnection)

        Returns:
            bool: True if reconnection successful
        """
        if not self._ip:
            error_msg = "Cannot reconnect: No previous connection information"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False

        logger.info("Manual reconnection initiated...")
        self.info_message.emit("Reconnecting...")

        self.disconnect()
        time.sleep(1)

        return self.connect(self._ip, self._port)

    def _start_reconnection_timer(self):
        """Start automatic reconnection timer"""
        if not self.enable_auto_reconnect:
            return

        if not self.reconnect_timer.isActive():
            self.reconnect_attempts = 0
            self.reconnect_timer.start(self.reconnect_interval)
            logger.info(f"Auto-reconnection timer started (interval: {self.reconnect_interval}ms)")
            self.info_message.emit(f"Will attempt automatic reconnection every {self.reconnect_interval/1000}s")

    def _attempt_reconnect(self):
        """Attempt automatic reconnection (called by timer)"""
        if self._connected:
            self.reconnect_timer.stop()
            return

        self.reconnect_attempts += 1
        logger.info(f"Auto-reconnection attempt {self.reconnect_attempts}/{self.max_reconnect_attempts}")
        self.info_message.emit(f"Reconnection attempt {self.reconnect_attempts}/{self.max_reconnect_attempts}...")

        success = self.connect(self._ip, self._port)

        if success:
            self.reconnect_timer.stop()
            self.reconnection_attempted.emit(True, "Reconnection successful")
            logger.info("Auto-reconnection successful")
        elif self.reconnect_attempts >= self.max_reconnect_attempts:
            self.reconnect_timer.stop()
            error_msg = f"Failed to reconnect after {self.max_reconnect_attempts} attempts"
            logger.error(error_msg)
            self.reconnection_attempted.emit(False, error_msg)
            self.error_occurred.emit(error_msg)

    def _on_connection_lost(self):
        """Handle connection lost event from data receiver thread"""
        logger.warning("Connection lost detected by data receiver")
        self.info_message.emit("Connection lost - attempting to reconnect...")

        self._connected = False
        self.connection_status_changed.emit(False)

        if self.enable_auto_reconnect:
            self._start_reconnection_timer()

    def is_connected(self) -> bool:
        """
        檢查是否已連線

        Returns:
            bool: 連線狀態
        """
        return self._connected

    # ========================================
    # 狀態讀取
    # ========================================

    def get_tcp_pose(self) -> Optional[List[float]]:
        """
        獲取當前 TCP 位姿

        Returns:
            Optional[List[float]]: [x, y, z, rx, ry, rz] 或 None
        """
        with QMutexLocker(self.mutex):
            return self._current_tcp_pose.copy() if self._current_tcp_pose else None

    def get_joint_positions(self) -> Optional[List[float]]:
        """
        獲取當前關節角度

        Returns:
            Optional[List[float]]: [j1, j2, j3, j4, j5, j6] 或 None
        """
        with QMutexLocker(self.mutex):
            return self._current_joint_positions.copy() if self._current_joint_positions else None

    def get_tcp_force(self) -> Optional[List[float]]:
        """
        獲取當前 TCP 力/力矩

        Returns:
            Optional[List[float]]: [fx, fy, fz, tx, ty, tz] 或 None
        """
        with QMutexLocker(self.mutex):
            return self._current_tcp_force.copy() if self._current_tcp_force else None

    def get_robot_mode(self) -> int:
        """
        獲取機器人模式

        Returns:
            int: 機器人模式代碼
        """
        return self._robot_mode

    def get_safety_status(self) -> int:
        """
        獲取安全狀態

        Returns:
            int: 安全狀態代碼
        """
        return self._safety_mode

    # ========================================
    # 運動控制
    # ========================================

    def move_tcp(self, x: float = 0, y: float = 0, z: float = 0,
                 rx: float = 0, ry: float = 0, rz: float = 0,
                 speed: float = None, accel: float = None,
                 relative: bool = True) -> bool:
        """
        移動 TCP (笛卡爾空間)

        Args:
            x, y, z: 位置增量或絕對位置 (m)
            rx, ry, rz: 姿態增量或絕對姿態 (rad)
            speed: 速度 (m/s)
            accel: 加速度 (m/s²)
            relative: True 為相對移動，False 為絕對移動

        Returns:
            bool: 是否成功執行
        """
        if not self._connected or self.rtde_control is None:
            self.error_occurred.emit("Not connected to robot")
            return False

        try:
            # Use default values
            if speed is None:
                speed = Config.DEFAULT_TCP_SPEED
            if accel is None:
                accel = Config.DEFAULT_TCP_ACCEL

            # Calculate target pose
            if relative:
                current_pose = self.rtde_receive.getActualTCPPose()
                target_pose = [
                    current_pose[0] + x,
                    current_pose[1] + y,
                    current_pose[2] + z,
                    current_pose[3] + rx,
                    current_pose[4] + ry,
                    current_pose[5] + rz
                ]
            else:
                target_pose = [x, y, z, rx, ry, rz]

            # Safety check
            if not check_pose_in_workspace(target_pose, Config.WORKSPACE_LIMITS):
                self.error_occurred.emit("Target position exceeds workspace limits")
                return False

            # Execute movement
            logger.info(f"Moving TCP to: {target_pose}")
            result = self.rtde_control.moveL(target_pose, speed, accel, asynchronous=False)

            if result:
                self.info_message.emit("TCP movement completed")
                logger.info("TCP movement completed successfully")
                return True
            else:
                self.error_occurred.emit("TCP movement failed - robot did not execute command")
                logger.error("TCP movement failed - moveL returned False")
                return False

        except Exception as e:
            logger.error(f"TCP movement failed: {e}")
            self.error_occurred.emit(f"TCP movement failed: {str(e)}")
            return False

    def start_tcp_velocity_mode(self, vx: float = 0, vy: float = 0, vz: float = 0,
                                vrx: float = 0, vry: float = 0, vrz: float = 0,
                                accel: float = None) -> bool:
        """
        Start smooth continuous TCP velocity control

        Args:
            vx, vy, vz: Linear velocities in m/s
            vrx, vry, vrz: Angular velocities in rad/s
            accel: Acceleration (m/s²)

        Returns:
            bool: Success status
        """
        if not self._connected or self.rtde_control is None:
            self.error_occurred.emit("Not connected to robot")
            return False

        try:
            if accel is None:
                accel = Config.DEFAULT_TCP_ACCEL

            velocity_vector = [vx, vy, vz, vrx, vry, vrz]

            # Start velocity control (speedL moves at constant velocity until stopped)
            self.rtde_control.speedL(velocity_vector, accel, 0.5)  # 0.5s time step for smooth control
            logger.debug(f"TCP velocity mode started: {velocity_vector}")
            return True

        except Exception as e:
            logger.error(f"Failed to start TCP velocity mode: {e}")
            self.error_occurred.emit(f"Velocity control failed: {str(e)}")
            return False

    def stop_tcp_velocity_mode(self, accel: float = None) -> bool:
        """
        Stop TCP velocity control smoothly

        Args:
            accel: Deceleration (m/s²)

        Returns:
            bool: Success status
        """
        if not self._connected or self.rtde_control is None:
            return False

        try:
            if accel is None:
                accel = Config.DEFAULT_TCP_ACCEL

            # Stop by sending zero velocity
            self.rtde_control.speedStop(accel)
            logger.debug("TCP velocity mode stopped")
            return True

        except Exception as e:
            logger.error(f"Failed to stop TCP velocity mode: {e}")
            return False

    def start_joint_velocity_mode(self, qd1: float = 0, qd2: float = 0, qd3: float = 0,
                                  qd4: float = 0, qd5: float = 0, qd6: float = 0,
                                  accel: float = None) -> bool:
        """
        Start smooth continuous joint velocity control

        Args:
            qd1-qd6: Joint velocities in rad/s
            accel: Acceleration (rad/s²)

        Returns:
            bool: Success status
        """
        if not self._connected or self.rtde_control is None:
            self.error_occurred.emit("Not connected to robot")
            return False

        try:
            if accel is None:
                accel = Config.DEFAULT_JOINT_ACCEL

            velocity_vector = [qd1, qd2, qd3, qd4, qd5, qd6]

            # Start velocity control (speedJ moves at constant velocity until stopped)
            self.rtde_control.speedJ(velocity_vector, accel, 0.5)  # 0.5s time step for smooth control
            logger.debug(f"Joint velocity mode started: {velocity_vector}")
            return True

        except Exception as e:
            logger.error(f"Failed to start joint velocity mode: {e}")
            self.error_occurred.emit(f"Joint velocity control failed: {str(e)}")
            return False

    def stop_joint_velocity_mode(self, accel: float = None) -> bool:
        """
        Stop joint velocity control smoothly

        Args:
            accel: Deceleration (rad/s²)

        Returns:
            bool: Success status
        """
        if not self._connected or self.rtde_control is None:
            return False

        try:
            if accel is None:
                accel = Config.DEFAULT_JOINT_ACCEL

            # Stop by sending zero velocity
            self.rtde_control.speedStop(accel)
            logger.debug("Joint velocity mode stopped")
            return True

        except Exception as e:
            logger.error(f"Failed to stop joint velocity mode: {e}")
            return False

    def move_joint(self, q1: float = 0, q2: float = 0, q3: float = 0,
                   q4: float = 0, q5: float = 0, q6: float = 0,
                   speed: float = None, accel: float = None,
                   relative: bool = True) -> bool:
        """
        移動關節 (關節空間)

        Args:
            q1-q6: 關節角度增量或絕對角度 (rad)
            speed: 速度 (rad/s)
            accel: 加速度 (rad/s²)
            relative: True 為相對移動，False 為絕對移動

        Returns:
            bool: 是否成功執行
        """
        if not self._connected or self.rtde_control is None:
            self.error_occurred.emit("Not connected to robot")
            return False

        try:
            # Use default values
            if speed is None:
                speed = Config.DEFAULT_JOINT_SPEED
            if accel is None:
                accel = Config.DEFAULT_JOINT_ACCEL

            # Calculate target joint angles
            if relative:
                current_joints = self.rtde_receive.getActualQ()
                target_joints = [
                    current_joints[0] + q1,
                    current_joints[1] + q2,
                    current_joints[2] + q3,
                    current_joints[3] + q4,
                    current_joints[4] + q5,
                    current_joints[5] + q6
                ]
            else:
                target_joints = [q1, q2, q3, q4, q5, q6]

            # Safety check
            if not check_joint_limits(target_joints):
                self.error_occurred.emit("Target joint angles exceed limits")
                return False

            # Execute movement
            logger.info(f"Moving joints to: {target_joints}")
            result = self.rtde_control.moveJ(target_joints, speed, accel, asynchronous=False)

            if result:
                self.info_message.emit("Joint movement completed")
                logger.info("Joint movement completed successfully")
                return True
            else:
                self.error_occurred.emit("Joint movement failed - robot did not execute command")
                logger.error("Joint movement failed - moveJ returned False")
                return False

        except Exception as e:
            logger.error(f"Joint movement failed: {e}")
            self.error_occurred.emit(f"Joint movement failed: {str(e)}")
            return False

    def move_to_preset_position(self, position_name: str,
                                speed: float = None, accel: float = None) -> bool:
        """
        移動到預設位置

        Args:
            position_name: 位置名稱
            speed: 速度 (rad/s)
            accel: 加速度 (rad/s²)

        Returns:
            bool: 是否成功執行
        """
        joints = None
        if hasattr(self, 'preset_manager') and self.preset_manager:
            joints = self.preset_manager.get_preset_joints(position_name)
        if joints is None:
            # Fallback to legacy Config presets for compatibility
            joints = Config.get_preset_position(position_name)

        if joints is None:
            self.error_occurred.emit(f"預設位置不存在: {position_name}")
            return False

        return self.move_joint(*joints, speed=speed, accel=accel, relative=False)

    def replay_trajectory(self, trajectory_data: list, speed: float = None,
                         accel: float = None, use_joint_space: bool = True) -> bool:
        """
        Replay a recorded trajectory

        Args:
            trajectory_data: List of DataPoint objects from data_logger
            speed: Movement speed (rad/s for joints, m/s for TCP)
            accel: Movement acceleration (rad/s² for joints, m/s² for TCP)
            use_joint_space: True to use joint positions, False to use TCP positions

        Returns:
            bool: True if replay completed successfully
        """
        if not self._connected or self.rtde_control is None:
            self.error_occurred.emit("Not connected to robot")
            return False

        if not trajectory_data or len(trajectory_data) == 0:
            self.error_occurred.emit("No trajectory data to replay")
            return False

        try:
            # Use default speeds if not provided
            if use_joint_space:
                if speed is None:
                    speed = Config.DEFAULT_JOINT_SPEED
                if accel is None:
                    accel = Config.DEFAULT_JOINT_ACCEL
            else:
                if speed is None:
                    speed = Config.DEFAULT_TCP_SPEED
                if accel is None:
                    accel = Config.DEFAULT_TCP_ACCEL

            total_points = len(trajectory_data)
            logger.info(f"Starting trajectory replay: {total_points} points")

            # Reset pause state at start
            self._trajectory_paused = False
            self._trajectory_pause_point = 0

            self.trajectory_replay_started.emit(total_points)
            self.info_message.emit(f"Replaying trajectory: {total_points} points")

            # Cache trajectory data for resume capability
            self._trajectory_data_cache = trajectory_data
            self._trajectory_speed_cache = speed
            self._trajectory_accel_cache = accel
            self._trajectory_use_joint_space = use_joint_space

            # Execute each point in the trajectory
            for i, data_point in enumerate(trajectory_data):
                # Check if we should pause
                if self._trajectory_paused:
                    # Stop robot motion first
                    self.stop_motion()
                    # Save pause point for resume
                    self._trajectory_pause_point = i
                    logger.info(f"Trajectory replay paused at point {i}/{total_points}")
                    self.trajectory_replay_paused.emit(i, total_points)
                    self.info_message.emit(f"Trajectory replay paused at point {i}/{total_points}")
                    return False

                # Check if we should stop
                if not self._connected:
                    logger.warning("Connection lost during trajectory replay")
                    self.trajectory_replay_completed.emit(False)
                    return False

                # Move to position
                if use_joint_space:
                    # Use joint positions for more accurate replay
                    success = self.move_joint(
                        *data_point.joint_pos,
                        speed=speed,
                        accel=accel,
                        relative=False
                    )
                else:
                    # Use TCP positions
                    success = self.move_tcp(
                        *data_point.tcp_pose,
                        speed=speed,
                        accel=accel,
                        relative=False
                    )

                if not success:
                    logger.error(f"Trajectory replay failed at point {i+1}/{total_points}")
                    self.error_occurred.emit(f"Replay failed at point {i+1}")
                    self.trajectory_replay_completed.emit(False)
                    return False

                # Emit progress
                self.trajectory_replay_progress.emit(i + 1, total_points)

                # Small delay to allow UI updates
                time.sleep(0.01)

            logger.info("Trajectory replay completed successfully")
            self.info_message.emit("Trajectory replay completed")

            # Clear cached data on successful completion
            self._trajectory_data_cache = []
            self._trajectory_pause_point = 0
            self._trajectory_paused = False

            self.trajectory_replay_completed.emit(True)
            return True

        except Exception as e:
            logger.error(f"Trajectory replay failed: {e}")
            self.error_occurred.emit(f"Trajectory replay failed: {str(e)}")
            self.trajectory_replay_completed.emit(False)
            return False

    def pause_trajectory_replay(self) -> bool:
        """
        Pause ongoing trajectory replay

        Returns:
            bool: True if pause flag was set successfully
        """
        if not self._trajectory_paused:
            self._trajectory_paused = True
            logger.info("Trajectory replay pause requested")
            return True
        else:
            logger.warning("Trajectory replay is already paused or not running")
            return False

    def resume_trajectory_replay(self) -> bool:
        """
        Resume paused trajectory replay from pause point

        Returns:
            bool: True if resume completed successfully
        """
        if not self._trajectory_paused:
            logger.warning("Cannot resume: trajectory replay is not paused")
            self.error_occurred.emit("No paused trajectory to resume")
            return False

        if not self._trajectory_data_cache or len(self._trajectory_data_cache) == 0:
            logger.error("Cannot resume: no cached trajectory data")
            self.error_occurred.emit("No trajectory data available for resume")
            self._trajectory_paused = False
            return False

        try:
            # Clear pause flag
            self._trajectory_paused = False

            # Get remaining trajectory data from pause point
            remaining_trajectory = self._trajectory_data_cache[self._trajectory_pause_point:]
            total_points = len(self._trajectory_data_cache)

            logger.info(f"Resuming trajectory replay from point {self._trajectory_pause_point}/{total_points}")
            self.info_message.emit(f"Resuming trajectory replay from point {self._trajectory_pause_point}/{total_points}")

            # Execute remaining points
            for i, data_point in enumerate(remaining_trajectory):
                # Check if we should pause again
                if self._trajectory_paused:
                    # Stop robot motion first
                    self.stop_motion()
                    # Update pause point
                    self._trajectory_pause_point = self._trajectory_pause_point + i
                    logger.info(f"Trajectory replay paused again at point {self._trajectory_pause_point}/{total_points}")
                    self.trajectory_replay_paused.emit(self._trajectory_pause_point, total_points)
                    self.info_message.emit(f"Trajectory replay paused at point {self._trajectory_pause_point}/{total_points}")
                    return False

                # Check if we should stop
                if not self._connected:
                    logger.warning("Connection lost during trajectory replay resume")
                    self.trajectory_replay_completed.emit(False)
                    return False

                # Move to position
                if self._trajectory_use_joint_space:
                    success = self.move_joint(
                        *data_point.joint_pos,
                        speed=self._trajectory_speed_cache,
                        accel=self._trajectory_accel_cache,
                        relative=False
                    )
                else:
                    success = self.move_tcp(
                        *data_point.tcp_pose,
                        speed=self._trajectory_speed_cache,
                        accel=self._trajectory_accel_cache,
                        relative=False
                    )

                if not success:
                    current_point = self._trajectory_pause_point + i + 1
                    logger.error(f"Trajectory replay resume failed at point {current_point}/{total_points}")
                    self.error_occurred.emit(f"Replay failed at point {current_point}")
                    self.trajectory_replay_completed.emit(False)
                    return False

                # Emit progress (offset by pause point)
                current_point = self._trajectory_pause_point + i + 1
                self.trajectory_replay_progress.emit(current_point, total_points)

                # Small delay to allow UI updates
                time.sleep(0.01)

            logger.info("Trajectory replay resumed and completed successfully")
            self.info_message.emit("Trajectory replay completed")
            self.trajectory_replay_completed.emit(True)

            # Clear cached data
            self._trajectory_data_cache = []
            self._trajectory_pause_point = 0

            return True

        except Exception as e:
            logger.error(f"Trajectory replay resume failed: {e}")
            self.error_occurred.emit(f"Trajectory replay resume failed: {str(e)}")
            self.trajectory_replay_completed.emit(False)
            self._trajectory_paused = False
            return False

    def stop_motion(self, deceleration: float = 2.0) -> bool:
        """
        停止機器人運動

        Args:
            deceleration: 減速度 (m/s²)

        Returns:
            bool: 是否成功執行
        """
        if not self._connected or self.rtde_control is None:
            return False

        try:
            self.rtde_control.stopL(deceleration)
            self.info_message.emit("已停止運動")
            logger.info("已停止機器人運動")
            return True
        except Exception as e:
            logger.error(f"停止運動失敗: {e}")
            self.error_occurred.emit(f"停止失敗: {str(e)}")
            return False

    # ========================================
    # 自由驅動模式
    # ========================================

    def enable_freedrive(self, free_axes: List[int] = [1, 1, 1, 1, 1, 1]) -> bool:
        """
        啟動自由驅動模式

        Args:
            free_axes: 自由軸設定 [Fx, Fy, Fz, Rx, Ry, Rz]，1 為自由，0 為鎖定

        Returns:
            bool: 是否成功啟動
        """
        if not self._connected or self.rtde_control is None:
            self.error_occurred.emit("Not connected to robot")
            return False

        try:
            # Zero force/torque sensor to remove payload offset
            # This makes the robot feel much lighter to move
            logger.info("Zeroing force/torque sensor for lighter movement...")
            self.rtde_control.zeroFtSensor()

            # Wait a moment for sensor to stabilize
            import time
            time.sleep(0.1)

            # Switch safety monitor to freedrive profile with baseline compensation
            # Use current TCP force as baseline to compensate for payload
            self.safety_monitor.enable_freedrive_profile(self._current_tcp_force)

            # Enable teach mode (low damping, easy to move)
            # teachMode() provides much lighter resistance than freedriveMode()
            self.rtde_control.teachMode()
            self.info_message.emit("Freedrive mode enabled - Force sensor zeroed for easy movement")
            logger.info("Teach mode enabled with zeroed force sensor - Movement should feel very light")
            return True
        except Exception as e:
            logger.error(f"Enable freedrive failed: {e}")
            self.error_occurred.emit(f"Freedrive failed: {str(e)}")
            # Restore normal safety profile if freedrive failed
            self.safety_monitor.disable_freedrive_profile()
            return False

    def disable_freedrive(self) -> bool:
        """
        停止自由驅動模式

        Returns:
            bool: 是否成功停止
        """
        if not self._connected or self.rtde_control is None:
            return False

        try:
            # End teach/freedrive mode on robot
            self.rtde_control.endTeachMode()

            # Restore normal safety profile
            self.safety_monitor.disable_freedrive_profile()

            self.info_message.emit("Freedrive mode disabled - Normal safety limits restored")
            logger.info("Teach mode disabled - Normal safety limits restored")
            return True
        except Exception as e:
            logger.error(f"Disable freedrive failed: {e}")
            self.error_occurred.emit(f"Stop freedrive failed: {str(e)}")
            # Always restore normal safety profile even if disable failed
            self.safety_monitor.disable_freedrive_profile()
            return False

    # ========================================
    # Force Control Functions
    # ========================================

    def start_force_mode(self, task_frame: List[float] = None,
                        selection_vector: List[int] = None,
                        wrench: List[float] = None,
                        force_type: int = 2,
                        limits: List[float] = None) -> bool:
        """
        Start force mode with compliant behavior

        Args:
            task_frame: Task frame pose [x, y, z, rx, ry, rz]
            selection_vector: Selection vector [Fx, Fy, Fz, Tx, Ty, Tz] (1=active, 0=inactive)
            wrench: Target wrench [fx, fy, fz, tx, ty, tz] (negative values push down/backward)
            force_type: Force type (1=no transform, 2=base frame, 3=tool frame)
            limits: Speed limits [vx, vy, vz, wx, wy, wz] (m/s and rad/s)

        Returns:
            bool: Success status
        """
        if not self._connected or self.rtde_control is None:
            self.error_occurred.emit("Not connected to robot")
            return False

        try:
            # Use default values if not provided
            if task_frame is None:
                current_pose = self.rtde_receive.getActualTCPPose()
                task_frame = list(current_pose) if current_pose else [0, 0, 0, 0, 0, 0]

            if selection_vector is None:
                selection_vector = Config.DEFAULT_FORCE_DIRECTION

            if wrench is None:
                # Default: apply downward force in Z
                wrench = [0, 0, -Config.DEFAULT_TARGET_FORCE, 0, 0, 0]

            if limits is None:
                # Use speed limits from config for compliant behavior
                # Linear velocities (m/s), Angular velocities (rad/s)
                limits = Config.FORCE_MODE_SPEED_LIMITS

            # Start force mode
            self.rtde_control.forceMode(task_frame, selection_vector, wrench,
                                       force_type, limits)

            self.info_message.emit("Force mode started - robot will comply with external forces")
            logger.info(f"Force mode started with wrench: {wrench}, selection: {selection_vector}")
            logger.info(f"Task frame: {task_frame}, limits: {limits}")
            return True

        except Exception as e:
            logger.error(f"Failed to start force mode: {e}")
            self.error_occurred.emit(f"Force mode failed: {str(e)}")
            return False

    def stop_force_mode(self) -> bool:
        """
        Stop force mode

        Returns:
            bool: Success status
        """
        if not self._connected or self.rtde_control is None:
            return False

        try:
            self.rtde_control.forceModeStop()
            self.info_message.emit("Force mode stopped")
            logger.info("Force mode stopped")
            return True
        except Exception as e:
            logger.error(f"Failed to stop force mode: {e}")
            self.error_occurred.emit(f"Stop force mode failed: {str(e)}")
            return False

    def update_force_params(self, target_force: float = None,
                           gain: float = None, max_disp: float = None) -> bool:
        """
        Update force control parameters (requires restarting force mode)

        Args:
            target_force: Target force in N
            gain: Force control gain
            max_disp: Maximum displacement in m

        Returns:
            bool: Success status
        """
        # Note: RTDE doesn't support runtime parameter updates
        # This would require stopping and restarting force mode with new parameters
        self.info_message.emit("Force parameter update requires restarting force mode")
        logger.warning("Force parameters cannot be updated at runtime with RTDE")
        return False

    # ========================================
    # Script Execution Functions
    # ========================================

    def execute_script(self, script_path: str) -> bool:
        """
        Execute a URScript file

        Args:
            script_path: Path to the .script file

        Returns:
            bool: Success status
        """
        if not self._connected or self.rtde_control is None:
            self.error_occurred.emit("Not connected to robot")
            return False

        try:
            # Read script file
            from utils import read_script_file
            script_code = read_script_file(script_path)

            if script_code is None:
                self.error_occurred.emit(f"Failed to read script: {script_path}")
                return False

            # Execute script
            return self.execute_urscript_code(script_code)

        except Exception as e:
            logger.error(f"Script execution failed: {e}")
            self.error_occurred.emit(f"Script execution failed: {str(e)}")
            return False

    def execute_urscript_code(self, code_string: str) -> bool:
        """
        Execute URScript code directly

        Args:
            code_string: URScript code as string

        Returns:
            bool: Success status
        """
        if not self._connected or self.rtde_control is None:
            self.error_occurred.emit("Not connected to robot")
            return False

        try:
            # Send script to robot
            self.rtde_control.sendCustomScriptFunction(code_string)

            self.info_message.emit("Script executed")
            logger.info(f"Executed URScript code: {code_string[:50]}...")
            return True

        except Exception as e:
            logger.error(f"URScript execution failed: {e}")
            self.error_occurred.emit(f"URScript failed: {str(e)}")
            return False

    def stop_script(self) -> bool:
        """
        Stop currently executing script

        Returns:
            bool: Success status
        """
        if not self._connected or self.rtde_control is None:
            return False

        try:
            self.rtde_control.stopScript()
            self.info_message.emit("Script stopped")
            logger.info("Script execution stopped")
            return True
        except Exception as e:
            logger.error(f"Failed to stop script: {e}")
            self.error_occurred.emit(f"Stop script failed: {str(e)}")
            return False

    # ========================================
    # I/O Control Functions
    # ========================================

    def set_digital_out(self, pin: int, value: bool) -> bool:
        """
        Set digital output pin

        Args:
            pin: Pin number (0-7 for standard digital outputs)
            value: True for HIGH, False for LOW

        Returns:
            bool: Success status
        """
        if not self._connected or self.rtde_control is None:
            self.error_occurred.emit("Not connected to robot")
            return False

        try:
            self.rtde_control.setStandardDigitalOut(pin, value)
            state = "HIGH" if value else "LOW"
            self.info_message.emit(f"Digital output {pin} set to {state}")
            logger.info(f"Set digital output {pin} to {state}")
            return True
        except Exception as e:
            logger.error(f"Failed to set digital output: {e}")
            self.error_occurred.emit(f"Digital output failed: {str(e)}")
            return False

    def get_digital_in(self, pin: int) -> Optional[bool]:
        """
        Get digital input pin state

        Args:
            pin: Pin number (0-7 for standard digital inputs)

        Returns:
            Optional[bool]: Pin state (True=HIGH, False=LOW) or None if failed
        """
        if not self._connected or self.rtde_receive is None:
            return None

        try:
            # Get all digital inputs
            digital_inputs = self.rtde_receive.getActualDigitalInputBits()

            # Extract specific pin (check bit at position)
            if 0 <= pin < 16:  # UR robots typically have 16 digital inputs
                value = bool((digital_inputs >> pin) & 1)
                logger.debug(f"Digital input {pin} is {'HIGH' if value else 'LOW'}")
                return value
            else:
                logger.error(f"Invalid digital input pin: {pin}")
                return None

        except Exception as e:
            logger.error(f"Failed to read digital input: {e}")
            return None

    def set_analog_out(self, pin: int, value: float) -> bool:
        """
        Set analog output pin

        Args:
            pin: Pin number (0-1 for standard analog outputs)
            value: Output value (0.0 to 1.0 for current mode, voltage depends on mode)

        Returns:
            bool: Success status
        """
        if not self._connected or self.rtde_control is None:
            self.error_occurred.emit("Not connected to robot")
            return False

        try:
            self.rtde_control.setStandardAnalogOut(pin, value)
            self.info_message.emit(f"Analog output {pin} set to {value:.3f}")
            logger.info(f"Set analog output {pin} to {value:.3f}")
            return True
        except Exception as e:
            logger.error(f"Failed to set analog output: {e}")
            self.error_occurred.emit(f"Analog output failed: {str(e)}")
            return False

    def get_analog_in(self, pin: int) -> Optional[float]:
        """
        Get analog input pin value

        Args:
            pin: Pin number (0-1 for standard analog inputs)

        Returns:
            Optional[float]: Analog value or None if failed
        """
        if not self._connected or self.rtde_receive is None:
            return None

        try:
            if pin == 0:
                value = self.rtde_receive.getStandardAnalogInput0()
            elif pin == 1:
                value = self.rtde_receive.getStandardAnalogInput1()
            else:
                logger.error(f"Invalid analog input pin: {pin}")
                return None

            logger.debug(f"Analog input {pin} value: {value:.3f}")
            return value

        except Exception as e:
            logger.error(f"Failed to read analog input: {e}")
            return None

    # ========================================
    # Safety Functions
    # ========================================

    def emergency_stop(self) -> bool:
        """
        Software emergency stop

        Returns:
            bool: Success status
        """
        if not self._connected or self.rtde_control is None:
            return False

        try:
            self.rtde_control.stopScript()
            self.info_message.emit("Emergency stop executed - Click 'Unlock Robot' to resume")
            logger.warning("Software emergency stop executed")
            return True
        except Exception as e:
            logger.error(f"Emergency stop failed: {e}")
            self.error_occurred.emit(f"Emergency stop failed: {str(e)}")
            return False

    def unlock_protective_stop(self) -> bool:
        """
        Unlock robot from protective stop state

        Simple 2-step unlock:
        1. Unlock protective stop
        2. Close safety popup

        Note: Does NOT restart safety system (which would break RTDE connection).
        For force errors or protective stops, unlocking is sufficient.

        Returns:
            bool: Success status
        """
        if not self._connected or not self._ip:
            self.error_occurred.emit("Not connected to robot")
            return False

        dashboard_socket = None
        try:
            logger.info(f"Connecting to Dashboard server at {self._ip}:29999...")

            # Connect to Dashboard server
            dashboard_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            dashboard_socket.settimeout(5.0)
            dashboard_socket.connect((self._ip, 29999))

            # Read initial connection message
            welcome = dashboard_socket.recv(1024).decode('utf-8')
            logger.info(f"Dashboard connected: {welcome.strip()}")

            # Step 1: Unlock protective stop
            logger.info("Unlocking protective stop...")
            dashboard_socket.sendall(b"unlock protective stop\n")
            response1 = dashboard_socket.recv(1024).decode('utf-8').strip()
            logger.info(f"Unlock response: {response1}")
            time.sleep(0.3)

            # Step 2: Close safety popup
            logger.info("Closing safety popup...")
            dashboard_socket.sendall(b"close safety popup\n")
            response2 = dashboard_socket.recv(1024).decode('utf-8').strip()
            logger.info(f"Close popup response: {response2}")

            # Close Dashboard connection
            dashboard_socket.sendall(b"quit\n")
            dashboard_socket.close()
            dashboard_socket = None

            # Brief wait for robot to update state
            time.sleep(0.5)

            # Restart RTDE control script (required after stopScript/E-stop)
            if self.rtde_control is not None:
                try:
                    logger.info("Restarting RTDE control script...")
                    self.rtde_control.reuploadScript()
                    logger.info("RTDE control script restarted")
                    time.sleep(0.5)  # Wait for script to be ready
                except Exception as e:
                    logger.error(f"Failed to restart control script: {e}")
                    # Continue anyway - freedrive will still work

            self.info_message.emit("Robot unlocked - ready to move")
            logger.info("Robot unlocked successfully")
            return True

        except socket.timeout:
            error_msg = "Dashboard connection timeout"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False
        except Exception as e:
            logger.error(f"Unlock failed: {e}")
            self.error_occurred.emit(f"Unlock failed: {str(e)}")
            return False
        finally:
            if dashboard_socket:
                try:
                    dashboard_socket.close()
                except:
                    pass

    # ========================================
    # Data Stream Management
    # ========================================

    def start_data_streaming(self):
        """Start background data receiver thread"""
        if self.data_receiver is not None:
            logger.warning("Data receiver thread already running")
            return

        if self.rtde_receive is None:
            logger.error("RTDE Receive interface not initialized")
            return

        # Create and start thread
        self.data_receiver = DataReceiverThread(self.rtde_receive)

        # Connect signals
        self.data_receiver.tcp_pose_updated.connect(self._on_tcp_pose_updated)
        self.data_receiver.joint_positions_updated.connect(self._on_joint_positions_updated)
        self.data_receiver.force_data_updated.connect(self._on_force_data_updated)
        self.data_receiver.robot_mode_changed.connect(self._on_robot_mode_changed)
        self.data_receiver.safety_status_changed.connect(self._on_safety_status_changed)
        self.data_receiver.error_occurred.connect(self.error_occurred)
        self.data_receiver.connection_lost.connect(self._on_connection_lost)  # NEW: Handle connection loss

        self.data_receiver.start()
        logger.info("Data receiver thread started")

    def stop_data_streaming(self):
        """Stop background data receiver thread"""
        if self.data_receiver is not None:
            logger.info("Stopping data receiver thread...")
            self.data_receiver.stop()
            self.data_receiver = None
            logger.info("Data receiver thread stopped")

    # ========================================
    # 內部槽函數（處理執行緒信號）
    # ========================================

    def _on_tcp_pose_updated(self, pose: List[float]):
        """TCP pose updated"""
        with QMutexLocker(self.mutex):
            self._current_tcp_pose = pose

        # Safety check: workspace boundaries
        if not self.safety_monitor.check_workspace_boundary(pose):
            logger.warning("Workspace boundary check failed")

        self.tcp_pose_updated.emit(pose)

    def _on_joint_positions_updated(self, joints: List[float]):
        """關節角度更新"""
        with QMutexLocker(self.mutex):
            self._current_joint_positions = joints
        self.joint_positions_updated.emit(joints)

    def _on_force_data_updated(self, force: List[float]):
        """Force sensor data updated"""
        with QMutexLocker(self.mutex):
            self._current_tcp_force = force

        # Safety checks: force limits and collision detection
        if not self.safety_monitor.check_force_limits(force):
            logger.warning("Force limit check failed")

        if self.safety_monitor.detect_collision(force):
            logger.critical("Collision detected by safety monitor")

        self.force_data_updated.emit(force)

    def _on_robot_mode_changed(self, mode: int):
        """機器人模式變更"""
        self._robot_mode = mode
        self.robot_mode_changed.emit(mode)

    def _on_safety_status_changed(self, status: int):
        """Safety status changed"""
        self._safety_mode = status
        self.safety_status_changed.emit(status)

    # ========================================
    # Safety Signal Handlers
    # ========================================

    def _on_workspace_violation(self, axis: str):
        """
        Handle workspace boundary violation

        Triggers emergency stop and notifies user.

        Args:
            axis: Violated axis identifier (e.g., 'X_MIN', 'Z_MAX')
        """
        error = SafetyError(
            f"Workspace boundary violated: {axis}",
            axis=axis
        )
        self.error_handler.handle_error(
            error,
            context="Safety monitoring - workspace boundary",
            show_dialog=True,
            attempt_recovery=False
        )

        self.error_occurred.emit(f"SAFETY: Workspace boundary {axis} violated!")

        # Execute emergency stop
        logger.critical(f"Executing emergency stop due to workspace violation: {axis}")
        self.emergency_stop()

    def _on_force_violation(self, magnitude: float):
        """
        Handle force/torque limit violation

        Triggers emergency stop and notifies user.

        Args:
            magnitude: Force or torque magnitude that exceeded limit
        """
        error = SafetyError(
            f"Force/torque limit exceeded: {magnitude:.2f}",
            magnitude=magnitude
        )
        self.error_handler.handle_error(
            error,
            context="Safety monitoring - force limit",
            show_dialog=True,
            attempt_recovery=False
        )

        self.error_occurred.emit(f"SAFETY: Force/torque limit exceeded: {magnitude:.2f}!")

        # Execute emergency stop
        logger.critical(f"Executing emergency stop due to force violation: {magnitude:.2f}")
        self.emergency_stop()

    def _on_collision_detected(self, description: str):
        """
        Handle collision detection

        Triggers emergency stop and notifies user.

        Args:
            description: Collision description from safety monitor
        """
        error = SafetyError(
            f"Collision detected: {description}",
            description=description
        )
        self.error_handler.handle_error(
            error,
            context="Safety monitoring - collision detection",
            show_dialog=True,
            attempt_recovery=False
        )

        self.error_occurred.emit(f"SAFETY: Collision detected! {description}")

        # Execute emergency stop
        logger.critical(f"Executing emergency stop due to collision: {description}")
        self.emergency_stop()

    def _on_workspace_warning(self, axis: str):
        """
        Handle workspace boundary warning

        Args:
            axis: Axis approaching boundary (e.g., 'X_MIN', 'Z_MAX')
        """
        warning_msg = f"Approaching workspace boundary: {axis}"
        logger.warning(warning_msg)
        self.info_message.emit(warning_msg)

    def _on_force_warning(self, magnitude: float):
        """
        Handle force/torque warning

        Args:
            magnitude: Force or torque magnitude approaching limit
        """
        warning_msg = f"Force/torque level high: {magnitude:.2f}"
        logger.warning(warning_msg)
        self.info_message.emit(warning_msg)

    # ========================================
    # Cleanup
    # ========================================

    def __del__(self):
        """Destructor"""
        self.disconnect()
