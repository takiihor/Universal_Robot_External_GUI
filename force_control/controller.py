"""RTDE wrapper around the UR controller's built-in force mode.

The robot firmware runs the force control loop; this class validates requests,
issues ``forceMode`` / ``forceModeStop``, keeps the active target so the force
level can be changed at runtime, and releases force mode after a configurable
timeout so an abandoned session cannot leave the robot compliant forever.

No Qt dependency: callbacks are plain callables so the class can be tested with
a fake control interface.
"""

import logging
import threading
from typing import Callable, List, Optional, Sequence

from .config import (
    ForceConfig,
    build_limits,
    build_wrench,
    clamp_target_force,
)

logger = logging.getLogger(__name__)

StateCallback = Callable[[bool, Optional[float]], None]
TimeoutCallback = Callable[[float, float], None]
ErrorCallback = Callable[[str], None]


class ForceController:
    """Start, retarget and stop force mode on a UR10e."""

    def __init__(
        self,
        control_interface=None,
        on_state_changed: Optional[StateCallback] = None,
        on_timeout: Optional[TimeoutCallback] = None,
        on_error: Optional[ErrorCallback] = None,
    ):
        self._control = control_interface
        self._on_state_changed = on_state_changed
        self._on_timeout = on_timeout
        self._on_error = on_error

        self._lock = threading.RLock()
        self._active = False
        self._target_force: Optional[float] = None
        self._selection: List[int] = list(ForceConfig.DEFAULT_SELECTION)
        self._force_type = ForceConfig.DEFAULT_FORCE_TYPE
        self._speed_limits: List[float] = build_limits(
            ForceConfig.DEFAULT_SELECTION,
            ForceConfig.DEFAULT_LINEAR_SPEED,
            ForceConfig.DEFAULT_ANGULAR_SPEED,
        )
        self._task_frame: Optional[List[float]] = None
        self._timeout = ForceConfig.DEFAULT_TIMEOUT
        self._watchdog: Optional[threading.Timer] = None
        self._watchdog_generation = 0
        self._last_error = ""

    # ========================================
    # Lifecycle
    # ========================================

    def attach(self, control_interface):
        """Bind the controller to a live RTDE control interface."""
        with self._lock:
            self._control = control_interface
            self._active = False
            self._task_frame = None
            self._disarm_watchdog()

    def detach(self):
        """Stop force mode (if needed) and drop the RTDE interface."""
        with self._lock:
            if self._active:
                self.stop()
            self._control = None
            self._active = False
            self._task_frame = None
            self._disarm_watchdog()

    def shutdown(self):
        """Alias for detach(), used when the application closes."""
        self.detach()

    # ========================================
    # State
    # ========================================

    @property
    def is_available(self) -> bool:
        return self._control is not None

    @property
    def is_active(self) -> bool:
        with self._lock:
            return self._active

    @property
    def target_force(self) -> Optional[float]:
        with self._lock:
            return self._target_force

    @property
    def selection_vector(self) -> List[int]:
        with self._lock:
            return list(self._selection)

    @property
    def last_error(self) -> str:
        with self._lock:
            return self._last_error

    # ========================================
    # Force mode
    # ========================================

    def start(
        self,
        target_force: Optional[float] = None,
        selection_vector: Optional[Sequence[int]] = None,
        force_type: Optional[int] = None,
        speed_limits: Optional[Sequence[float]] = None,
        task_frame: Optional[Sequence[float]] = None,
        timeout: Optional[float] = None,
    ) -> bool:
        """Enter force mode. Returns True when the robot accepted the command."""
        with self._lock:
            try:
                force = clamp_target_force(
                    ForceConfig.DEFAULT_TARGET_FORCE if target_force is None else target_force
                )
                selection = self._validate_selection(selection_vector)
                fc_type = self._validate_force_type(force_type)
                limits = self._validate_limits(speed_limits, selection)
                wait = self._validate_timeout(timeout)
                frame = self._validate_frame(
                    ForceConfig.DEFAULT_TASK_FRAME if task_frame is None else task_frame
                )
            except ValueError as exc:
                self._fail(str(exc))
                return False

            # Re-issuing forceMode with a new target requires a clean stop first
            if self._active and not self._stop_locked():
                return False

            if not self._apply_locked(frame, selection, force, fc_type, limits):
                return False

            self._target_force = force
            self._selection = selection
            self._force_type = fc_type
            self._speed_limits = limits
            self._task_frame = frame
            self._timeout = wait
            self._arm_watchdog(wait)
            self._emit_state()
            return True

    def stop(self) -> bool:
        """Leave force mode."""
        with self._lock:
            if self._control is None:
                self._active = False
                self._emit_state()
                return False
            stopped = self._stop_locked()
            if stopped:
                self._emit_state()
            return stopped

    def set_target_force(self, newtons: float) -> bool:
        """Change the target force, restarting force mode if it is running.

        RTDE has no runtime update for force mode parameters, so an active
        session is stopped and re-issued with the same frame and selection.
        Restarting re-arms the auto-release timer.
        """
        with self._lock:
            force = clamp_target_force(newtons)
            if not self._active:
                self._target_force = force
                self._emit_state()
                return True
            return self.start(
                target_force=force,
                selection_vector=self._selection,
                force_type=self._force_type,
                speed_limits=self._speed_limits,
                task_frame=self._task_frame,
                timeout=self._timeout,
            )

    def zero_sensor(self) -> bool:
        """Zero the force/torque sensor to remove the payload offset."""
        with self._lock:
            if self._control is None:
                self._fail("Robot is not connected")
                return False
            try:
                self._control.zeroFtSensor()
                logger.info("Force/torque sensor zeroed")
                return True
            except Exception as exc:
                self._fail(f"Failed to zero force sensor: {exc}")
                return False

    # ========================================
    # Internals
    # ========================================

    def _apply_locked(self, frame, selection, force, force_type, limits) -> bool:
        wrench = build_wrench(force, selection)
        try:
            self._control.forceMode(frame, selection, wrench, force_type, limits)
        except Exception as exc:
            self._fail(f"forceMode failed: {exc}")
            return False

        self._active = True
        logger.info(
            "Force mode started: target=%.2f N, axes=%s, type=%s, limits=%s",
            force, selection, force_type, limits,
        )
        return True

    def _stop_locked(self) -> bool:
        self._disarm_watchdog()
        try:
            self._control.forceModeStop()
        except Exception as exc:
            self._fail(f"forceModeStop failed: {exc}")
            return False

        self._active = False
        logger.info("Force mode stopped")
        return True

    @staticmethod
    def _validate_selection(selection: Optional[Sequence[int]]) -> List[int]:
        values = list(ForceConfig.DEFAULT_SELECTION if selection is None else selection)
        if len(values) != 6 or any(int(v) not in (0, 1) for v in values):
            raise ValueError("Selection vector must be six values of 0 or 1")
        result = [int(v) for v in values]
        if not any(result):
            raise ValueError("Select at least one compliant axis")
        return result

    @staticmethod
    def _validate_force_type(force_type: Optional[int]) -> int:
        value = ForceConfig.DEFAULT_FORCE_TYPE if force_type is None else int(force_type)
        if value not in ForceConfig.FORCE_TYPES:
            raise ValueError(f"Force type must be one of {sorted(ForceConfig.FORCE_TYPES)}")
        return value

    @staticmethod
    def _validate_limits(
        limits: Optional[Sequence[float]], selection: Sequence[int]
    ) -> List[float]:
        values = list(
            build_limits(
                selection,
                ForceConfig.DEFAULT_LINEAR_SPEED,
                ForceConfig.DEFAULT_ANGULAR_SPEED,
            )
            if limits is None
            else limits
        )
        if len(values) != 6 or any(float(v) <= 0 for v in values):
            raise ValueError("Force limits must be six positive values")
        return [float(v) for v in values]

    @staticmethod
    def _validate_timeout(timeout: Optional[float]) -> float:
        value = ForceConfig.DEFAULT_TIMEOUT if timeout is None else float(timeout)
        if value < 0:
            raise ValueError("Auto-release timeout cannot be negative")
        return min(value, ForceConfig.MAX_TIMEOUT)

    @staticmethod
    def _validate_frame(frame: Optional[Sequence[float]]) -> List[float]:
        if frame is None or len(frame) != 6:
            raise ValueError("Task frame must be a 6-element pose")
        return [float(v) for v in frame]

    def _arm_watchdog(self, timeout: float) -> None:
        self._disarm_watchdog()
        if timeout <= 0:
            return

        self._watchdog_generation += 1
        generation = self._watchdog_generation
        timer = threading.Timer(timeout, self._watchdog_fired, args=(generation,))
        timer.daemon = True
        self._watchdog = timer
        timer.start()

    def _disarm_watchdog(self) -> None:
        self._watchdog_generation += 1
        if self._watchdog is not None:
            self._watchdog.cancel()
            self._watchdog = None

    def _watchdog_fired(self, generation: int) -> None:
        with self._lock:
            if generation != self._watchdog_generation or not self._active:
                return
            target = self._target_force
            logger.warning(
                "Force mode auto-released after %.1f s without retarget", self._timeout
            )
            stopped = self._stop_locked()
            if stopped:
                self._emit_state()

        if stopped and self._on_timeout is not None:
            try:
                self._on_timeout(target if target is not None else 0.0, self._timeout)
            except Exception:
                logger.exception("Force timeout callback failed")

    def _fail(self, message: str) -> None:
        self._last_error = message
        logger.error(message)
        if self._on_error is not None:
            try:
                self._on_error(message)
            except Exception:
                logger.exception("Force error callback failed")

    def _emit_state(self) -> None:
        if self._on_state_changed is not None:
            try:
                self._on_state_changed(self._active, self._target_force)
            except Exception:
                logger.exception("Force state callback failed")
