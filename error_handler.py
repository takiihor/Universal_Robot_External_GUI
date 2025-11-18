"""
Error Handler Module for UR10e Control UI - Stage 4

This module provides comprehensive error handling, recovery mechanisms,
and user-friendly error reporting for the entire application.

Author: UR10e Control UI Development Team
Date: 2025-11-04
Stage: 4 - Optimization & Refinement
"""

import logging
import traceback
import sys
from datetime import datetime
from typing import Optional, Callable, Any
from enum import Enum
from PyQt5.QtWidgets import QMessageBox, QWidget
from PyQt5.QtCore import QObject, pyqtSignal

# Setup logger
logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels"""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ErrorCategory(Enum):
    """Error categories for better handling"""
    CONNECTION = "Connection Error"
    COMMUNICATION = "Communication Error"
    MOTION_CONTROL = "Motion Control Error"
    SAFETY = "Safety Error"
    DATA_LOGGING = "Data Logging Error"
    FILE_IO = "File I/O Error"
    CONFIGURATION = "Configuration Error"
    VALIDATION = "Validation Error"
    TIMEOUT = "Timeout Error"
    PERMISSION = "Permission Error"
    RESOURCE = "Resource Error"
    UNKNOWN = "Unknown Error"


class RobotError(Exception):
    """Base exception class for robot-related errors"""

    def __init__(self, message: str, category: ErrorCategory = ErrorCategory.UNKNOWN,
                 severity: ErrorSeverity = ErrorSeverity.ERROR,
                 recoverable: bool = True, **kwargs):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.recoverable = recoverable
        self.timestamp = datetime.now()
        self.extra_info = kwargs

    def __str__(self):
        return f"[{self.category.value}] {self.message}"


class ConnectionError(RobotError):
    """Connection-related errors"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.CONNECTION, **kwargs)


class CommunicationError(RobotError):
    """Communication errors with robot"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.COMMUNICATION, **kwargs)


class MotionControlError(RobotError):
    """Motion control errors"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.MOTION_CONTROL, **kwargs)


class SafetyError(RobotError):
    """Safety-related errors"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.SAFETY,
                        severity=ErrorSeverity.CRITICAL, recoverable=False, **kwargs)


class DataLoggingError(RobotError):
    """Data logging errors"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.DATA_LOGGING,
                        severity=ErrorSeverity.WARNING, **kwargs)


class FileIOError(RobotError):
    """File I/O errors"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.FILE_IO, **kwargs)


class ConfigurationError(RobotError):
    """Configuration errors"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.CONFIGURATION, **kwargs)


class ValidationError(RobotError):
    """Data validation errors"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.VALIDATION,
                        severity=ErrorSeverity.WARNING, **kwargs)


class TimeoutError(RobotError):
    """Timeout errors"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.TIMEOUT, **kwargs)


class ErrorHandler(QObject):
    """
    Central error handling system with recovery mechanisms

    Features:
    - Centralized error logging
    - User-friendly error dialogs
    - Automatic error recovery
    - Error history tracking
    - Reconnection logic for network errors

    Signals:
        error_occurred: Emitted when an error occurs (severity, category, message)
        recovery_attempted: Emitted when recovery is attempted (success, message)
    """

    # Signals
    error_occurred = pyqtSignal(str, str, str)  # severity, category, message
    recovery_attempted = pyqtSignal(bool, str)  # success, message

    def __init__(self, parent: QWidget = None):
        super().__init__()
        self.parent = parent
        self.error_history = []
        self.max_history = 100
        self.recovery_callbacks = {}

        logger.info("ErrorHandler initialized")

    def handle_error(self, error: Exception, context: str = "",
                     show_dialog: bool = True, attempt_recovery: bool = True) -> bool:
        """
        Handle an error with optional recovery

        Args:
            error: The exception object
            context: Context information about where error occurred
            show_dialog: Whether to show error dialog to user
            attempt_recovery: Whether to attempt automatic recovery

        Returns:
            True if error was recovered, False otherwise
        """
        # Convert to RobotError if needed
        if not isinstance(error, RobotError):
            robot_error = RobotError(
                str(error),
                category=ErrorCategory.UNKNOWN,
                severity=ErrorSeverity.ERROR
            )
        else:
            robot_error = error

        # Log error
        self._log_error(robot_error, context)

        # Add to history
        self._add_to_history(robot_error, context)

        # Emit signal
        self.error_occurred.emit(
            robot_error.severity.value,
            robot_error.category.value,
            robot_error.message
        )

        # Show dialog if requested
        if show_dialog:
            self._show_error_dialog(robot_error, context)

        # Attempt recovery if applicable
        recovered = False
        if attempt_recovery and robot_error.recoverable:
            recovered = self._attempt_recovery(robot_error)

        return recovered

    def register_recovery_callback(self, category: ErrorCategory,
                                   callback: Callable) -> None:
        """
        Register a recovery callback for a specific error category

        Args:
            category: Error category
            callback: Recovery function (should return bool indicating success)
        """
        self.recovery_callbacks[category] = callback
        logger.info(f"Registered recovery callback for {category.value}")

    def _log_error(self, error: RobotError, context: str):
        """Log error with appropriate severity"""
        log_message = f"{error.category.value}: {error.message}"
        if context:
            log_message += f" (Context: {context})"

        if error.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message)
        elif error.severity == ErrorSeverity.ERROR:
            logger.error(log_message)
        elif error.severity == ErrorSeverity.WARNING:
            logger.warning(log_message)
        else:
            logger.info(log_message)

        # Log stack trace for errors and critical issues
        if error.severity in [ErrorSeverity.ERROR, ErrorSeverity.CRITICAL]:
            logger.debug(f"Stack trace: {traceback.format_exc()}")

    def _add_to_history(self, error: RobotError, context: str):
        """Add error to history"""
        self.error_history.append({
            'timestamp': error.timestamp,
            'category': error.category,
            'severity': error.severity,
            'message': error.message,
            'context': context,
            'recoverable': error.recoverable
        })

        # Limit history size
        if len(self.error_history) > self.max_history:
            self.error_history.pop(0)

    def _show_error_dialog(self, error: RobotError, context: str):
        """Show user-friendly error dialog"""
        if not self.parent:
            return

        # Determine dialog icon
        if error.severity == ErrorSeverity.CRITICAL:
            icon = QMessageBox.Critical
            title = "Critical Error"
        elif error.severity == ErrorSeverity.ERROR:
            icon = QMessageBox.Critical
            title = "Error"
        elif error.severity == ErrorSeverity.WARNING:
            icon = QMessageBox.Warning
            title = "Warning"
        else:
            icon = QMessageBox.Information
            title = "Information"

        # Construct message
        message = f"<b>{error.category.value}</b><br><br>"
        message += f"{error.message}<br><br>"

        if context:
            message += f"<i>Context: {context}</i><br><br>"

        if error.recoverable:
            message += "The system will attempt to recover automatically."
        else:
            message += "Manual intervention may be required."

        # Show dialog
        msg_box = QMessageBox(icon, title, message, parent=self.parent)
        msg_box.setTextFormat(1)  # Rich text
        msg_box.exec_()

    def _attempt_recovery(self, error: RobotError) -> bool:
        """
        Attempt automatic error recovery

        Args:
            error: The error to recover from

        Returns:
            True if recovery successful
        """
        logger.info(f"Attempting recovery for {error.category.value}")

        # Check if recovery callback is registered
        if error.category in self.recovery_callbacks:
            try:
                callback = self.recovery_callbacks[error.category]
                success = callback(error)

                if success:
                    logger.info(f"Recovery successful for {error.category.value}")
                    self.recovery_attempted.emit(True, f"Recovered from {error.category.value}")
                else:
                    logger.warning(f"Recovery failed for {error.category.value}")
                    self.recovery_attempted.emit(False, f"Could not recover from {error.category.value}")

                return success
            except Exception as e:
                logger.error(f"Recovery callback failed: {e}")
                return False
        else:
            logger.warning(f"No recovery callback registered for {error.category.value}")
            return False

    def get_error_history(self, count: int = None) -> list:
        """
        Get error history

        Args:
            count: Number of recent errors to retrieve (None for all)

        Returns:
            List of error history entries
        """
        if count is None:
            return self.error_history.copy()
        else:
            return self.error_history[-count:].copy()

    def clear_error_history(self):
        """Clear error history"""
        self.error_history.clear()
        logger.info("Error history cleared")

    def export_error_log(self, filepath: str) -> bool:
        """
        Export error history to file

        Args:
            filepath: Path to export file

        Returns:
            True if successful
        """
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("UR10e Control UI - Error Log\n")
                f.write("=" * 60 + "\n")
                f.write(f"Generated: {datetime.now().isoformat()}\n")
                f.write(f"Total Errors: {len(self.error_history)}\n")
                f.write("=" * 60 + "\n\n")

                for i, entry in enumerate(self.error_history, 1):
                    f.write(f"Error #{i}\n")
                    f.write(f"Timestamp: {entry['timestamp'].isoformat()}\n")
                    f.write(f"Category: {entry['category'].value}\n")
                    f.write(f"Severity: {entry['severity'].value}\n")
                    f.write(f"Message: {entry['message']}\n")
                    if entry['context']:
                        f.write(f"Context: {entry['context']}\n")
                    f.write(f"Recoverable: {entry['recoverable']}\n")
                    f.write("-" * 60 + "\n\n")

            logger.info(f"Error log exported to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to export error log: {e}")
            return False


def safe_execute(func: Callable, error_handler: ErrorHandler = None,
                context: str = "", default_return: Any = None) -> Any:
    """
    Decorator/wrapper for safe function execution with error handling

    Args:
        func: Function to execute
        error_handler: ErrorHandler instance (if None, just logs)
        context: Context description
        default_return: Value to return on error

    Returns:
        Function result or default_return on error
    """
    try:
        return func()
    except Exception as e:
        if error_handler:
            error_handler.handle_error(e, context=context or func.__name__)
        else:
            logger.error(f"Error in {context or func.__name__}: {e}")
        return default_return


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Create error handler
    handler = ErrorHandler()

    # Test different error types
    try:
        raise ConnectionError("Failed to connect to robot at 192.168.1.100")
    except Exception as e:
        handler.handle_error(e, context="Connection attempt", show_dialog=False)

    try:
        raise SafetyError("Emergency stop triggered - force limit exceeded")
    except Exception as e:
        handler.handle_error(e, context="Force monitoring", show_dialog=False)

    # Export log
    handler.export_error_log("error_log_test.txt")
    print(f"Logged {len(handler.get_error_history())} errors")
