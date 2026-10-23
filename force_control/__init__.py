"""Force control for the UR10e.

The package wraps the UR controller's built-in force mode (RTDE
``forceMode`` / ``forceModeStop``), which runs the compliance loop in the robot
firmware. Nothing here implements an admittance or impedance controller in
Python.

The core (config + controller) has no Qt dependency so it can be exercised
without a GUI or hardware. ``force_control.ui`` holds the PyQt5 page and is
imported explicitly by the main window.
"""

from .config import (
    FORCE_AXES,
    ForceConfig,
    build_wrench,
    clamp_target_force,
    resolve_target_force,
)
from .controller import ForceController

__all__ = [
    "FORCE_AXES",
    "ForceConfig",
    "ForceController",
    "build_wrench",
    "clamp_target_force",
    "resolve_target_force",
]
