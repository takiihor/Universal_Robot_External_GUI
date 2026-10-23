"""
Data Logger Module for UR10e Control UI

This module provides real-time data logging capabilities for robot state,
TCP pose, force sensor data, and joint positions. Supports CSV and HDF5 formats.

Author: UR10e Control UI Development Team
Date: 2025-11-04
Stage: 3 - Data Logging & Visualization
"""

import csv
import os
import time
from datetime import datetime
from typing import List, Optional, Dict, Any
from collections import deque
import logging

# Optional dependency for HDF5 import/export
try:
    import h5py
    HDF5_AVAILABLE = True
except ImportError:
    HDF5_AVAILABLE = False

from PyQt5.QtCore import QObject, pyqtSignal, QMutex, QMutexLocker

from config import Config

# Setup logger
logger = logging.getLogger(__name__)


class DataPoint:
    """
    Single data point structure containing all robot state information
    """
    def __init__(self, timestamp: float, tcp_pose: List[float],
                 joint_pos: List[float], forces: List[float]):
        """
        Initialize a data point

        Args:
            timestamp: Unix timestamp in seconds
            tcp_pose: TCP pose [x, y, z, rx, ry, rz] in meters and radians
            joint_pos: Joint positions [j1, j2, j3, j4, j5, j6] in radians
            forces: Force/torque [fx, fy, fz, tx, ty, tz] in N and Nm
        """
        self.timestamp = timestamp
        self.tcp_pose = tcp_pose if tcp_pose else [0.0] * 6
        self.joint_pos = joint_pos if joint_pos else [0.0] * 6
        self.forces = forces if forces else [0.0] * 6

    def to_dict(self) -> Dict[str, Any]:
        """Convert data point to dictionary"""
        return {
            'timestamp': self.timestamp,
            'tcp_x': self.tcp_pose[0],
            'tcp_y': self.tcp_pose[1],
            'tcp_z': self.tcp_pose[2],
            'tcp_rx': self.tcp_pose[3],
            'tcp_ry': self.tcp_pose[4],
            'tcp_rz': self.tcp_pose[5],
            'joint_1': self.joint_pos[0],
            'joint_2': self.joint_pos[1],
            'joint_3': self.joint_pos[2],
            'joint_4': self.joint_pos[3],
            'joint_5': self.joint_pos[4],
            'joint_6': self.joint_pos[5],
            'force_x': self.forces[0],
            'force_y': self.forces[1],
            'force_z': self.forces[2],
            'torque_x': self.forces[3],
            'torque_y': self.forces[4],
            'torque_z': self.forces[5],
        }

    def to_list(self) -> List[float]:
        """Convert data point to flat list"""
        return [self.timestamp] + self.tcp_pose + self.joint_pos + self.forces


class DataLogger(QObject):
    """
    Data logger for recording robot state over time

    Features:
    - Real-time data buffering
    - CSV and HDF5 export
    - Circular buffer to prevent memory overflow
    - Thread-safe operations
    - Statistical analysis

    Signals:
        recording_started: Emitted when recording starts
        recording_stopped: Emitted when recording stops (includes filename)
        buffer_size_changed: Emitted when buffer size changes (current_size, max_size)
    """

    # Signals
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal(str)  # filename
    buffer_size_changed = pyqtSignal(int, int)  # current_size, max_size

    def __init__(self, max_buffer_size: int = None):
        """
        Initialize data logger

        Args:
            max_buffer_size: Maximum number of data points to store in memory
                           (default from Config.LOG_BUFFER_SIZE)
        """
        super().__init__()

        # Recording state
        self.is_recording = False
        self.is_paused = False

        # Data storage
        self.max_buffer_size = max_buffer_size or Config.LOG_BUFFER_SIZE
        self.data_buffer = deque(maxlen=self.max_buffer_size)

        # Recording session info
        self.start_time = None
        self.filename = None
        self.current_session_name = None

        # Thread safety
        self.mutex = QMutex()

        # Statistics cache
        self._stats_cache = None
        self._stats_cache_size = 0

        logger.info("DataLogger initialized with buffer size: %d", self.max_buffer_size)
        if not HDF5_AVAILABLE:
            logger.info("HDF5 import/export disabled (optional h5py package is not installed); CSV is available")

    # ========== Recording Control ==========

    def start_recording(self, filename: Optional[str] = None,
                       session_name: Optional[str] = None) -> bool:
        """
        Start recording data

        Args:
            filename: Custom filename (without extension). If None, auto-generate
            session_name: Session name for identification

        Returns:
            True if recording started successfully
        """
        with QMutexLocker(self.mutex):
            if self.is_recording:
                logger.warning("Recording already in progress")
                return False

            # Generate filename if not provided
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"robot_data_{timestamp}"

            self.filename = filename
            self.current_session_name = session_name or "Unnamed Session"
            self.start_time = time.time()
            self.is_recording = True
            self.is_paused = False

            # Clear buffer for new recording
            self.data_buffer.clear()
            self._invalidate_stats_cache()

            logger.info("Recording started: %s (session: %s)",
                       filename, self.current_session_name)

        # Emit signal AFTER releasing mutex to avoid deadlock
        self.recording_started.emit()

        return True

    def stop_recording(self, auto_save: bool = True,
                      save_format: str = 'csv') -> Optional[str]:
        """
        Stop recording and optionally save data

        Args:
            auto_save: Automatically save data to file
            save_format: 'csv' or 'hdf5'

        Returns:
            Saved filename if auto_save=True, None otherwise
        """
        saved_file = None
        duration = 0
        data_points = 0

        with QMutexLocker(self.mutex):
            if not self.is_recording:
                logger.warning("No recording in progress")
                return None

            self.is_recording = False
            self.is_paused = False

            if auto_save and len(self.data_buffer) > 0:
                # Determine save path
                logs_dir = Config.LOGS_DIR
                os.makedirs(logs_dir, exist_ok=True)

                if save_format.lower() == 'csv':
                    filepath = os.path.join(logs_dir, f"{self.filename}.csv")
                    saved_file = filepath
                elif save_format.lower() == 'hdf5' and HDF5_AVAILABLE:
                    filepath = os.path.join(logs_dir, f"{self.filename}.h5")
                    saved_file = filepath
                else:
                    logger.warning("Invalid save format or HDF5 not available, using CSV")
                    filepath = os.path.join(logs_dir, f"{self.filename}.csv")
                    saved_file = filepath

            duration = time.time() - self.start_time if self.start_time else 0
            data_points = len(self.data_buffer)

        # Save file AFTER releasing mutex to avoid nested lock
        if saved_file:
            if saved_file.endswith('.h5'):
                self.save_to_hdf5(saved_file)
            else:
                self.save_to_csv(saved_file)

        logger.info("Recording stopped. Duration: %.2f seconds, Points: %d",
                   duration, data_points)

        # Emit signal AFTER releasing mutex to avoid deadlock
        self.recording_stopped.emit(saved_file or "")

        return saved_file

    def pause_recording(self):
        """Pause recording (stop adding data but keep session active)"""
        with QMutexLocker(self.mutex):
            if self.is_recording and not self.is_paused:
                self.is_paused = True
                logger.info("Recording paused")

    def resume_recording(self):
        """Resume recording"""
        with QMutexLocker(self.mutex):
            if self.is_recording and self.is_paused:
                self.is_paused = False
                logger.info("Recording resumed")

    # ========== Data Management ==========

    def add_data_point(self, timestamp: float, tcp_pose: List[float],
                      joint_pos: List[float], forces: List[float]) -> bool:
        """
        Add a data point to the buffer

        Args:
            timestamp: Unix timestamp
            tcp_pose: TCP pose [x, y, z, rx, ry, rz]
            joint_pos: Joint positions [j1, j2, j3, j4, j5, j6]
            forces: Forces/torques [fx, fy, fz, tx, ty, tz]

        Returns:
            True if data point was added
        """
        should_emit_signal = False
        current_size = 0

        with QMutexLocker(self.mutex):
            # Only add if recording and not paused
            if not self.is_recording or self.is_paused:
                return False

            # Create data point
            data_point = DataPoint(timestamp, tcp_pose, joint_pos, forces)

            # Add to buffer (deque automatically removes oldest if full)
            self.data_buffer.append(data_point)

            # Invalidate statistics cache
            self._invalidate_stats_cache()

            # Check if we should emit buffer size update (every 100 points to avoid spam)
            if len(self.data_buffer) % 100 == 0:
                should_emit_signal = True
                current_size = len(self.data_buffer)

        # Emit signal AFTER releasing mutex to avoid deadlock
        if should_emit_signal:
            self.buffer_size_changed.emit(current_size, self.max_buffer_size)

        return True

    def clear_buffer(self):
        """Clear all data from buffer"""
        with QMutexLocker(self.mutex):
            self.data_buffer.clear()
            self._invalidate_stats_cache()
            logger.info("Data buffer cleared")

        # Emit signal AFTER releasing mutex to avoid deadlock
        self.buffer_size_changed.emit(0, self.max_buffer_size)

    def get_buffer_size(self) -> int:
        """Get current buffer size"""
        with QMutexLocker(self.mutex):
            return len(self.data_buffer)

    def get_recording_duration(self) -> float:
        """
        Get recording duration in seconds

        Returns:
            Duration in seconds, or 0 if not recording
        """
        with QMutexLocker(self.mutex):
            if not self.is_recording or self.start_time is None:
                return 0.0
            return time.time() - self.start_time

    # ========== Data Export ==========

    def save_to_csv(self, filepath: str) -> bool:
        """
        Save data buffer to CSV file

        Args:
            filepath: Full path to CSV file

        Returns:
            True if saved successfully
        """
        with QMutexLocker(self.mutex):
            if len(self.data_buffer) == 0:
                logger.warning("No data to save")
                return False

            try:
                # Create directory if needed
                os.makedirs(os.path.dirname(filepath), exist_ok=True)

                # Write CSV
                with open(filepath, 'w', newline='') as csvfile:
                    # Get column names from first data point
                    fieldnames = list(self.data_buffer[0].to_dict().keys())

                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()

                    for data_point in self.data_buffer:
                        writer.writerow(data_point.to_dict())

                logger.info("Data saved to CSV: %s (%d points)",
                           filepath, len(self.data_buffer))
                return True

            except Exception as e:
                logger.error("Failed to save CSV: %s", str(e))
                return False

    def save_to_hdf5(self, filepath: str) -> bool:
        """
        Save data buffer to HDF5 file (more efficient for large datasets)

        Args:
            filepath: Full path to HDF5 file

        Returns:
            True if saved successfully
        """
        if not HDF5_AVAILABLE:
            logger.error("HDF5 export not available (h5py not installed)")
            return False

        with QMutexLocker(self.mutex):
            if len(self.data_buffer) == 0:
                logger.warning("No data to save")
                return False

            try:
                import numpy as np

                # Create directory if needed
                os.makedirs(os.path.dirname(filepath), exist_ok=True)

                # Convert buffer to numpy arrays
                timestamps = np.array([dp.timestamp for dp in self.data_buffer])
                tcp_poses = np.array([dp.tcp_pose for dp in self.data_buffer])
                joint_positions = np.array([dp.joint_pos for dp in self.data_buffer])
                forces = np.array([dp.forces for dp in self.data_buffer])

                # Write HDF5
                with h5py.File(filepath, 'w') as f:
                    # Create datasets
                    f.create_dataset('timestamp', data=timestamps)
                    f.create_dataset('tcp_pose', data=tcp_poses)
                    f.create_dataset('joint_positions', data=joint_positions)
                    f.create_dataset('forces', data=forces)

                    # Add metadata
                    f.attrs['session_name'] = self.current_session_name or "Unknown"
                    f.attrs['start_time'] = self.start_time or 0
                    f.attrs['num_points'] = len(self.data_buffer)
                    f.attrs['created_at'] = datetime.now().isoformat()

                logger.info("Data saved to HDF5: %s (%d points)",
                           filepath, len(self.data_buffer))
                return True

            except Exception as e:
                logger.error("Failed to save HDF5: %s", str(e))
                return False

    # ========== Data Loading ==========

    def load_from_csv(self, filepath: str) -> bool:
        """
        Load data from CSV file

        Args:
            filepath: Full path to CSV file

        Returns:
            True if loaded successfully
        """
        loaded_size = 0

        with QMutexLocker(self.mutex):
            try:
                # Clear existing buffer
                self.data_buffer.clear()
                self._invalidate_stats_cache()

                # Read CSV
                with open(filepath, 'r') as csvfile:
                    reader = csv.DictReader(csvfile)

                    for row in reader:
                        # Parse data
                        timestamp = float(row['timestamp'])
                        tcp_pose = [float(row[f'tcp_{axis}'])
                                   for axis in ['x', 'y', 'z', 'rx', 'ry', 'rz']]
                        joint_pos = [float(row[f'joint_{i}']) for i in range(1, 7)]
                        forces = [float(row[f'force_{axis}'])
                                 for axis in ['x', 'y', 'z']] + \
                                [float(row[f'torque_{axis}'])
                                 for axis in ['x', 'y', 'z']]

                        # Add to buffer
                        data_point = DataPoint(timestamp, tcp_pose, joint_pos, forces)
                        self.data_buffer.append(data_point)

                loaded_size = len(self.data_buffer)
                logger.info("Data loaded from CSV: %s (%d points)",
                           filepath, loaded_size)

            except Exception as e:
                logger.error("Failed to load CSV: %s", str(e))
                return False

        # Emit signal AFTER releasing mutex to avoid deadlock
        self.buffer_size_changed.emit(loaded_size, self.max_buffer_size)
        return True

    def load_from_hdf5(self, filepath: str) -> bool:
        """
        Load data from HDF5 file

        Args:
            filepath: Full path to HDF5 file

        Returns:
            True if loaded successfully
        """
        if not HDF5_AVAILABLE:
            logger.error("HDF5 import not available (h5py not installed)")
            return False

        loaded_size = 0

        with QMutexLocker(self.mutex):
            try:
                # Clear existing buffer
                self.data_buffer.clear()
                self._invalidate_stats_cache()

                # Read HDF5
                with h5py.File(filepath, 'r') as f:
                    timestamps = f['timestamp'][:]
                    tcp_poses = f['tcp_pose'][:]
                    joint_positions = f['joint_positions'][:]
                    forces = f['forces'][:]

                    # Reconstruct data points
                    for i in range(len(timestamps)):
                        data_point = DataPoint(
                            timestamps[i],
                            tcp_poses[i].tolist(),
                            joint_positions[i].tolist(),
                            forces[i].tolist()
                        )
                        self.data_buffer.append(data_point)

                loaded_size = len(self.data_buffer)
                logger.info("Data loaded from HDF5: %s (%d points)",
                           filepath, loaded_size)

            except Exception as e:
                logger.error("Failed to load HDF5: %s", str(e))
                return False

        # Emit signal AFTER releasing mutex to avoid deadlock
        self.buffer_size_changed.emit(loaded_size, self.max_buffer_size)
        return True

    # ========== Data Analysis ==========

    def get_statistics(self) -> Dict[str, Any]:
        """
        Calculate statistics of recorded data

        Returns:
            Dictionary containing statistics for all channels
        """
        with QMutexLocker(self.mutex):
            # Return cached stats if buffer hasn't changed
            if (self._stats_cache is not None and
                self._stats_cache_size == len(self.data_buffer)):
                return self._stats_cache

            if len(self.data_buffer) == 0:
                return {}

            try:
                import numpy as np

                # Extract data arrays
                tcp_poses = np.array([dp.tcp_pose for dp in self.data_buffer])
                joint_pos = np.array([dp.joint_pos for dp in self.data_buffer])
                forces = np.array([dp.forces for dp in self.data_buffer])

                # Calculate statistics
                stats = {
                    'tcp_pose': {
                        'mean': tcp_poses.mean(axis=0).tolist(),
                        'std': tcp_poses.std(axis=0).tolist(),
                        'min': tcp_poses.min(axis=0).tolist(),
                        'max': tcp_poses.max(axis=0).tolist(),
                    },
                    'joint_positions': {
                        'mean': joint_pos.mean(axis=0).tolist(),
                        'std': joint_pos.std(axis=0).tolist(),
                        'min': joint_pos.min(axis=0).tolist(),
                        'max': joint_pos.max(axis=0).tolist(),
                    },
                    'forces': {
                        'mean': forces.mean(axis=0).tolist(),
                        'std': forces.std(axis=0).tolist(),
                        'min': forces.min(axis=0).tolist(),
                        'max': forces.max(axis=0).tolist(),
                    },
                    'num_points': len(self.data_buffer),
                    'duration': (self.data_buffer[-1].timestamp -
                               self.data_buffer[0].timestamp),
                }

                # Cache results
                self._stats_cache = stats
                self._stats_cache_size = len(self.data_buffer)

                return stats

            except Exception as e:
                logger.error("Failed to calculate statistics: %s", str(e))
                return {}

    def get_data_range(self, start_time: float, end_time: float) -> List[DataPoint]:
        """
        Get data points within a time range

        Args:
            start_time: Start timestamp
            end_time: End timestamp

        Returns:
            List of data points in the time range
        """
        with QMutexLocker(self.mutex):
            filtered_data = [
                dp for dp in self.data_buffer
                if start_time <= dp.timestamp <= end_time
            ]
            return filtered_data

    def export_summary(self, filepath: str) -> bool:
        """
        Export data summary report to text file

        Args:
            filepath: Full path to output file

        Returns:
            True if exported successfully
        """
        with QMutexLocker(self.mutex):
            try:
                stats = self.get_statistics()

                if not stats:
                    logger.warning("No statistics to export")
                    return False

                # Create directory if needed
                os.makedirs(os.path.dirname(filepath), exist_ok=True)

                with open(filepath, 'w') as f:
                    f.write("=" * 60 + "\n")
                    f.write("UR10e Robot Data Summary Report\n")
                    f.write("=" * 60 + "\n\n")

                    f.write(f"Session: {self.current_session_name or 'Unknown'}\n")
                    f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Number of data points: {stats['num_points']}\n")
                    f.write(f"Duration: {stats['duration']:.2f} seconds\n\n")

                    # TCP Pose statistics
                    f.write("-" * 60 + "\n")
                    f.write("TCP Pose Statistics\n")
                    f.write("-" * 60 + "\n")
                    axes = ['X', 'Y', 'Z', 'Rx', 'Ry', 'Rz']
                    for i, axis in enumerate(axes):
                        f.write(f"{axis:3s}: mean={stats['tcp_pose']['mean'][i]:8.4f}, "
                               f"std={stats['tcp_pose']['std'][i]:8.4f}, "
                               f"min={stats['tcp_pose']['min'][i]:8.4f}, "
                               f"max={stats['tcp_pose']['max'][i]:8.4f}\n")

                    # Joint statistics
                    f.write("\n" + "-" * 60 + "\n")
                    f.write("Joint Position Statistics (radians)\n")
                    f.write("-" * 60 + "\n")
                    for i in range(6):
                        f.write(f"J{i+1}: mean={stats['joint_positions']['mean'][i]:8.4f}, "
                               f"std={stats['joint_positions']['std'][i]:8.4f}, "
                               f"min={stats['joint_positions']['min'][i]:8.4f}, "
                               f"max={stats['joint_positions']['max'][i]:8.4f}\n")

                    # Force statistics
                    f.write("\n" + "-" * 60 + "\n")
                    f.write("Force/Torque Statistics\n")
                    f.write("-" * 60 + "\n")
                    force_axes = ['Fx', 'Fy', 'Fz', 'Tx', 'Ty', 'Tz']
                    for i, axis in enumerate(force_axes):
                        f.write(f"{axis:3s}: mean={stats['forces']['mean'][i]:8.4f}, "
                               f"std={stats['forces']['std'][i]:8.4f}, "
                               f"min={stats['forces']['min'][i]:8.4f}, "
                               f"max={stats['forces']['max'][i]:8.4f}\n")

                    f.write("\n" + "=" * 60 + "\n")

                logger.info("Summary exported to: %s", filepath)
                return True

            except Exception as e:
                logger.error("Failed to export summary: %s", str(e))
                return False

    # ========== Helper Methods ==========

    def _invalidate_stats_cache(self):
        """Invalidate statistics cache"""
        self._stats_cache = None
        self._stats_cache_size = 0

    def get_latest_data_points(self, count: int) -> List[DataPoint]:
        """
        Get the latest N data points

        Args:
            count: Number of recent points to retrieve

        Returns:
            List of most recent data points
        """
        with QMutexLocker(self.mutex):
            if len(self.data_buffer) == 0:
                return []

            # Return last 'count' items
            start_idx = max(0, len(self.data_buffer) - count)
            return list(self.data_buffer)[start_idx:]


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Create logger
    logger_instance = DataLogger(max_buffer_size=1000)

    # Start recording
    logger_instance.start_recording("test_session")

    # Simulate data collection
    import numpy as np
    for i in range(100):
        t = time.time()
        tcp = [0.5 + 0.01*i, 0.0, 0.3, 0.0, 0.0, 0.0]
        joints = [0.0, -1.57, 1.57, -1.57, -1.57, 0.0]
        forces = [np.random.randn(), np.random.randn(), 1.0 + np.random.randn()*0.1,
                 0.0, 0.0, 0.0]
        logger_instance.add_data_point(t, tcp, joints, forces)

    # Stop and save
    saved_file = logger_instance.stop_recording(auto_save=True, save_format='csv')
    print(f"Data saved to: {saved_file}")

    # Get statistics
    stats = logger_instance.get_statistics()
    print(f"Statistics: {stats}")
