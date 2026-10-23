"""Parameters and helpers for UR10e force control.

Values map onto the arguments of ``ur_rtde``'s
``RTDEControlInterface.forceMode(task_frame, selection_vector, wrench, type,
limits)``.
"""

from typing import Any, Dict, List, Optional, Sequence

FORCE_AXES = ("Fx", "Fy", "Fz", "Tx", "Ty", "Tz")


class ForceConfig:
    """Tunables for the robot's built-in force mode."""

    # Target wrench magnitude
    MIN_TARGET_FORCE = 0.01  # N
    MAX_TARGET_FORCE = 50.0  # N
    DEFAULT_TARGET_FORCE = 2.0  # N

    # Named levels written by the sequential controller / action dialog
    FORCE_LEVELS = {"gentle": 5.0, "medium": 10.0, "strong": 15.0}
    DEFAULT_LEVEL_NAME = "medium"

    # Which axes are compliant: [Fx, Fy, Fz, Tx, Ty, Tz]
    DEFAULT_SELECTION = [0, 0, 1, 0, 0, 0]

    # forceMode `type`: 1 = force frame y-axis points from the TCP towards the
    # task frame origin, 2 = force frame is used as given (no transform),
    # 3 = force frame x-axis follows the projection of the TCP velocity.
    # Type 2 with the default frame below applies the wrench in the base frame.
    DEFAULT_FORCE_TYPE = 2
    FORCE_TYPES = {
        1: "Type 1 - Y axis towards task frame origin",
        2: "Type 2 - Fixed task frame",
        3: "Type 3 - X axis along TCP velocity",
    }
    DEFAULT_TASK_FRAME = [0.0] * 6  # identity rotation = base frame axes

    # Torque axes are driven at a fraction of the force magnitude
    TORQUE_SCALE = 0.3
    MAX_TORQUE = 5.0  # Nm

    # forceMode `limits`: max TCP speed on compliant axes (m/s and rad/s) and
    # max deviation on non-compliant axes (m and rad). The same vector carries
    # both roles, so a value is read differently depending on `selection`.
    DEFAULT_LINEAR_SPEED = 0.2  # m/s
    DEFAULT_ANGULAR_SPEED = 2.0  # rad/s
    MAX_LINEAR_SPEED = 0.5  # m/s
    MAX_ANGULAR_SPEED = 5.0  # rad/s

    # Non-compliant axes use the same limits vector as a maximum deviation
    DEFAULT_LINEAR_DEVIATION = 0.005  # m
    DEFAULT_ANGULAR_DEVIATION = 0.02  # rad (~1.1 deg)
    MAX_LINEAR_DEVIATION = 0.05  # m
    MAX_ANGULAR_DEVIATION = 0.175  # rad (~10 deg)

    # Force mode is released automatically after this many seconds (0 = never)
    DEFAULT_TIMEOUT = 20.0  # s
    MAX_TIMEOUT = 600.0  # s


def clamp_target_force(newtons: float) -> float:
    """Clamp a target force into the supported range."""
    return max(ForceConfig.MIN_TARGET_FORCE, min(float(newtons), ForceConfig.MAX_TARGET_FORCE))


def resolve_target_force(
    parameters: Optional[Dict[str, Any]],
    default: Optional[float] = None,
) -> float:
    """Read a target force in newtons from sequential-action parameters.

    Accepts numeric newtons (`force_newtons`, or numeric `force_level`) and the
    named levels the action dialog can store.
    """
    fallback = (
        ForceConfig.FORCE_LEVELS[ForceConfig.DEFAULT_LEVEL_NAME]
        if default is None
        else float(default)
    )
    if not parameters:
        return clamp_target_force(fallback)

    raw = parameters.get("force_newtons", parameters.get("force_level", fallback))
    return clamp_target_force(_as_newtons(raw, fallback))


def build_wrench(target_force: float, selection: Sequence[int]) -> List[float]:
    """Turn a scalar target force into the wrench for the selected axes.

    Fz pushes along -Z of the force frame (base frame by default), Fx/Fy push
    along +X/+Y, and torque axes use a scaled-down magnitude so a 10 N request
    does not become 10 Nm.
    """
    wrench = [0.0] * 6
    for axis, is_compliant in enumerate(selection):
        if not is_compliant:
            continue
        if axis == 2:
            wrench[axis] = -target_force
        elif axis < 3:
            wrench[axis] = target_force
        else:
            wrench[axis] = min(target_force * ForceConfig.TORQUE_SCALE, ForceConfig.MAX_TORQUE)
    return wrench


def build_limits(
    selection: Sequence[int],
    linear_speed: float,
    angular_speed: float,
    linear_deviation: Optional[float] = None,
    angular_deviation: Optional[float] = None,
) -> List[float]:
    """Build the 6-axis `limits` vector for a selection vector.

    Compliant axes get a maximum speed; non-compliant axes get a maximum
    deviation, so the same entry means different things depending on `selection`.
    """
    lin_dev = (
        ForceConfig.DEFAULT_LINEAR_DEVIATION
        if linear_deviation is None
        else float(linear_deviation)
    )
    ang_dev = (
        ForceConfig.DEFAULT_ANGULAR_DEVIATION
        if angular_deviation is None
        else float(angular_deviation)
    )

    limits = []
    for axis, is_compliant in enumerate(selection):
        if axis < 3:
            limits.append(linear_speed if is_compliant else lin_dev)
        else:
            limits.append(angular_speed if is_compliant else ang_dev)
    return [float(v) for v in limits]


def _as_newtons(value: Any, fallback: float) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        key = value.strip().lower()
        if key in ForceConfig.FORCE_LEVELS:
            return ForceConfig.FORCE_LEVELS[key]
        try:
            return float(key)
        except ValueError:
            return fallback
    return fallback
