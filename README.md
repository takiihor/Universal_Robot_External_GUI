# UR10e Remote Control UI System

A graphical remote control interface for the UR10e robot arm built with Python + PyQt5 + ur_rtde.

## Project Overview

This system provides a user-friendly graphical interface that lets users easily control and monitor the UR10e robot arm, including:

- Live connection management
- TCP pose and joint angle monitoring
- Force sensor data display
- Freedrive mode control
- Software emergency stop

## Development Stages

**Current version: Stage 2 - Expanded Control Features** ✅

### Stage 1: Core Features ✅

- [x] Connection management
- [x] Real-time status monitoring
- [x] Freedrive mode
- [x] Emergency stop

### Stage 2: Expanded Control Features ✅

- [x] Manual TCP control (6-DOF with adjustable steps)
- [x] Manual joint control (individual joint control)
- [x] Preset position management (save/load/delete positions)
- [x] Force control (force mode with parameters)
- [x] Script execution (URScript execution)
- [x] I/O control (digital and analog I/O backend)

### Stage 3: Data Visualization & Logging ⏳

- [ ] Real-time charts (PyQtGraph charts)
- [ ] Data logging and export (CSV/HDF5 format)
- [ ] Trajectory recording and playback

## System Requirements

- Python 3.7 or later
- UR10e robot arm (RTDE protocol support)
- Network connection (robot and computer on the same subnet)

## Installation

### 1. Clone or download the project

```bash
cd /path/to/your/workspace
# If downloading from git
git clone <repository_url>
cd ur10e_control_ui
```

### 2. Create a virtual environment (recommended)

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Verify the installation

```bash
python -c "import PyQt5; import rtde_control; print('Dependencies installed successfully')"
```

## Usage

### Launch the application

```bash
./start.sh
```

The launcher installs Python dependencies when needed and prefers native Wayland
on Wayland desktops. To choose a Qt backend explicitly, use
`QT_QPA_PLATFORM=xcb ./start.sh` (X11) or
`QT_QPA_PLATFORM=wayland ./start.sh` (Wayland).

### Connect to the robot

1. Make sure the UR10e is powered on and ready to accept connections
2. Confirm the IP address in "Connection Settings" is `192.168.1.10` (the default). You can edit it or launch with `ROBOT_IP=<robot_ip> ./start.sh` to use another address.
3. Confirm that the port is 30004 (the RTDE default port)
4. Click the "Connect" button
5. After a successful connection, the status indicator turns green: "● Connected"

### RG2 pick and force-mode placement

`./start.sh pick-place` runs `test_scripts/test_rg2_pick_place.py`. It uses
`positionA` as the taught grasp pose and the lower endpoint of the pick search.
Earlier force contact can raise the grasp height. The sequence is:

1. Move to `home_a` and open the RG2.
2. Move above `positionA`, settle/tare, and search downward in base-Z force mode
   with open fingers until earlier contact or the taught pick Z is reached.
3. Stop force mode. At the taught pick Z, position at `positionA` and close
   directly, without a 50 mm rise. For force contact above that Z, rise 50 mm
   from the measured contact pose in position mode, then close. Grip detection
   is required before carrying the block.
4. Lift vertically from the new grasp height and return to `home_a`; check grip
   feedback again. The lift does not return to an old, potentially lower pick Z.
5. Call the existing drop-test functions in the same RTDE connection: approach
   above `drop`, descend in position mode to the configured force-start height,
   tare with the block held, descend in base-Z force mode, stop at
   contact, verify RG2 release, and retract.

Save `home_a`, `positionA`, and `drop` in the UI before running. No extra taught
pick-approach preset is needed. The approach above `positionA` must clear the
highest expected surface before entering force mode. Disconnect other robot-control applications
before running the test. Configure the tool/payload for the carried object;
this runner does not infer the block's mass or change the payload automatically.

Copy `pick_place.example.json` to your own recipe and fill the three `null`
values: `open_width_mm`, `grip_width_mm`, and `grip_force_n`. The opening width
must clear the block and be reachable with the installed fingers. The closing
target must be narrower than the block for an external grip. Jaw forces are
separate from `contact_force` and `command_force`, which control table contact.

Force picking has its own settings, independent of placement:

| Recipe setting | Default | Purpose |
|---|---:|---|
| `pick_contact_force_n` | 10 N | Measured vertical force change that stops the pick probe |
| `pick_command_force_n` | 1.2 × threshold | Commanded downward pick force |
| `pick_descent_speed_mm_s` | 5 mm/s | Pick force-mode speed limit |
| `pick_max_descent_mm` | 150 mm | Search travel budget from the approach, capped at the taught pick Z |
| `pick_backoff_mm` | 50 mm | Rise before gripping only for contact above the taught pick Z |
| `pick_speed_mm_s` | 10 mm/s | Position-mode speed for final pick positioning, rise, and loaded lift |

Equivalent command-line flags use hyphens, for example `--pick-backoff-mm 50`.
`pick_height_mm` sets the initial approach above the pick reference and the
loaded lift above the measured grasp. Contact, rise, and lift ranges are checked
against workspace limits. With a 100 mm approach, a 150 mm search budget is
capped at 100 mm: it does not authorize searching below `positionA`. A smaller
budget that expires before reaching either contact or the taught pose aborts
the sequence. The pick endpoint is monitored in software, so network and robot
stopping delays can cause physical overshoot; it is not a safety-rated boundary.
Failed force-mode stop, failed positioning/rise, or failed grip aborts subsequent
picking/placement steps. Only the pick probe's
downward search uses force mode; rise and loaded lift use position mode.

The pick probe checks RG2 safety feedback before probing, during the search,
and before accepting contact. A safety-switch fault or unavailable feedback
stops the force search and blocks the subsequent rise/grip sequence. This is a
software guard, not a safety-rated robot stop. It does not reset the gripper.
The intended probe surface must avoid activating RG2 S1/S2; a safety-switch
collision is not treated as a successful height measurement.

```bash
cp pick_place.example.json pick_place.json
# Edit pick_place.json to set jaw widths and gripping force.
./start.sh pick-place --config pick_place.json --dry-run
# After reviewing the plan, run and enter uppercase YES at the prompt:
./start.sh pick-place --config pick_place.json
```

Command-line options override recipe values, for example
`--pick-height-mm 60 --pick-speed-mm-s 5 --contact-force 10`. Use
`./start.sh pick-place --help` for all options. The `--dry-run` flag never commands
the jaws, robot moves, sensor taring, or force mode, but may establish a control
connection to resolve joint-only presets. It also reads RG2 status. Dry runs can
preview without jaw parameters; live runs require all three values.

`force_start_height_mm` separates the faster position-mode descent from the
contact search. It is a height above the saved `drop` TCP pose, between 0 and
`approach_height_mm`. For example, an initial height of 100 mm and force-start
height of 10 mm gives a 90 mm position-mode descent at
`approach_speed_mm_s`, then force mode at `descent_speed_mm_s`. The block must
still be clear of the table at the force-start pose. A value of 0 means the
saved drop TCP pose, not the table's surface height. Omitting this setting
retains the original force-mode descent from the high approach pose.

`max_descent_mm` is the total downward travel budget from the initial approach.
The faster portion is subtracted from the remaining force search, preserving
the same lowest allowed Z. With a 100 mm fast descent and a 150 mm total budget,
force mode can descend at most another 50 mm. Taring occurs after the faster
descent has completed and settled. Gripping force and table contact force have
separate controls.

For a repeated demo using the same taught pick and drop locations:

```bash
# Preview the plan once, including the requested cycle count:
./start.sh pick-place --config pick_place.json --cycles 10 --dry-run
# Run ten cycles, with a two-second pause between completed cycles:
./start.sh pick-place --config pick_place.json --cycles 10 --cycle-wait-s 2
# Repeat continuously until interrupted:
./start.sh pick-place --config pick_place.json --cycles 0
```

The default is one cycle. `cycles` and `cycle_wait_s` may also be saved in the
recipe. Enter uppercase `YES` once to confirm the requested job. Each cycle
revalidates the plan and grip/release feedback. A failed or cancelled cycle stops
the job without retrying. A dry run previews once even when `--cycles 0` is set.
`Ctrl+C` interrupts the sequence; synchronous robot moves may finish before
Python handles the interruption, so it is not an immediate robot-stop control.

Home joint speed is controlled by `joint_speed_rad_s` in the recipe or
`--joint-speed-rad-s` on the command line. For example, `0.3` rad/s is about
17.2 degrees/s; the configured upper limit is `0.4` rad/s. Cartesian transit,
pick/lift, and force-descent speeds have their own separate settings.

The RG2 client opens a fresh HTTP connection for each XML-RPC request because
the OnRobot service closes idle connections during longer arm moves. Failed
jaw-command requests are not automatically replayed, since a lost response does
not establish whether the gripper accepted the command.

Preset endpoints, calculated approaches, and the configured vertical descent/
retract envelope are checked against the existing workspace limits before any
motion. This does not prove that the paths are collision-free. Failed grip or
release feedback aborts subsequent moves; errors do not automatically open the
gripper or return the arm home. The RG2 service uses the robot IP, port 41414,
and tool index 0 by default. The physical pick/place cycle still needs operator
validation; automated regression tests use fake hardware.

The saved `drop` pose is an approach reference. The actual release position is
the measured contact TCP pose, including when a raised surface is encountered
above the taught drop. Force mode stops before release; no further downward
position move is commanded. The current trigger is vertical force change in N,
not rotational torque in Nm. Force-guided picking can find a changed height
within its configured search range; X/Y and orientation still use the saved
reference, and its initial approach must remain above the surface.

An RG2 safety fault is separate from the robot's force-contact trigger. Errors
now report the gripper status code and S1/S2 switch flags. A latched switch fault
blocks jaw commands; the runner does not clear/reset or bypass it. Inspect tool
clearance and follow the OnRobot fault-recovery procedure with the block
supported before restarting. Failed release leaves the arm at contact and does
not retract or start another cycle.

### Monitor robot status

After connecting, the following information updates in real time:

- **TCP pose**: X, Y, Z positions (meters) and Rx, Ry, Rz orientation (radians)
- **Joint angles**: current angles of the six joints J1-J6 (radians)
- **Force/torque sensor**: Fx, Fy, Fz forces (newtons) and Tx, Ty, Tz torques (newton-meters)

### Using freedrive mode

1. Make sure the robot is connected
2. Click the "Start Freedrive" button
3. After confirming the dialog, the robot arm enters freedrive mode
4. You can now drag the robot arm by hand to any position
5. Click the "Stop Freedrive" button when finished

> ⚠️ **Safety notice**: Before enabling freedrive, make sure there are no obstacles or people around the robot arm.

### Emergency stop

- In an emergency, click the large red "⚠ Emergency Stop ⚠" button
- The robot arm immediately stops all motion
- After an emergency stop, verify the robot's state before resuming

### Disconnect

- Click the "Disconnect" button to safely disconnect from the robot
- The application disconnects automatically when closed

## File Structure

```
ur10e_control_ui/
├── main.py                  # Main program entry point
├── robot_controller.py      # Robot control core
├── ui_mainwindow.py        # Main window UI
├── config.py               # Configuration management
├── utils.py                # Utility functions
├── requirements.txt        # Dependency list
├── README.md              # This documentation
├── scripts/               # URScript scripts folder
├── logs/                  # Log files folder
└── assets/                # Resource files (icons, stylesheets, etc.)
```

## Configuration File

The application generates a `config.json` configuration file after its first run. You can edit this file to adjust the default parameters.

Main settings:

- `connection.ip`: default IP address
- `connection.port`: default port
- `motion.tcp_speed`: TCP movement speed (m/s)
- `motion.joint_speed`: joint movement speed (rad/s)
- `safety.workspace_limits`: workspace limits

## Logging System

- The application automatically records operation logs in the `logs/` folder
- Logs contain all important operations, error messages, and system status
- The "System Messages" area in the UI also displays live logs

## Troubleshooting

### Unable to connect to the robot

1. Check that the robot IP address is correct
2. Confirm that the computer and robot are on the same subnet
3. Use `ping <robot_ip>` to test the network connection
4. Confirm that the robot is powered on and in normal mode
5. Check whether firewall settings are blocking port 30004

### Dependency installation fails

```bash
# Upgrade pip
pip install --upgrade pip

# If PyQt5 installation fails, try
pip install PyQt5 --no-cache-dir

# If ur-rtde installation fails
pip install ur-rtde --no-binary :all:
```

### UI does not display or freezes

- Confirm that PyQt5 is installed correctly
- Check that the system supports a graphical interface
- Check the log files in logs/ for detailed error messages

### Startup warnings on GNOME / Wayland

- `Ignoring XDG_SESSION_TYPE=wayland on Gnome` can appear even when Qt uses
  Wayland. Check the application's `Qt platform initialized: wayland` message
  to confirm the backend.
- `QSocketNotifier: Can only be used with threads started with QThread` was
  traced to the bundled Qt 5 IBus input-method plugin during Wayland startup.
  If `Main window displayed` and `Entering application event loop` follow,
  the application has started. This warning alone does not indicate a robot
  connection failure.
- `HDF5 import/export disabled` is informational. CSV recording remains
  available; HDF5 requires the optional `h5py` package. Pandas is not required.

### Data does not update after connecting

- Confirm that the RTDE service is enabled on the robot
- Check network latency (high latency causes slow updates)
- Try reconnecting

## Advanced Features (Later Stages)

Stage 2 will add:

- Manual TCP movement control (Cartesian space)
- Manual joint movement control
- Preset position management
- Force control mode
- Script execution

Stage 3 will add:

- Real-time data charts
- Data logging and export
- 3D visualization (optional)

## Safety Notes

⚠️ **Important safety notice**

1. **Personnel safety**: Make sure no one is in the work area when operating the robot arm
2. **Workspace**: Understand the robot arm's range of motion and avoid collisions
3. **Emergency stop device**: Make sure the robot's physical emergency stop button is always within reach
4. **Test environment**: When using the system for the first time, test all functions in a safe environment
5. **Back up settings**: Back up important settings before modifying them
6. **Network security**: Use the system on an isolated local network to prevent external access

## License

This project is intended for learning and research purposes only. Users are solely responsible for all robot operations.

## Technical Support

If you encounter problems:

1. Check the log files in the `logs/` folder
2. Review the troubleshooting section of this README
3. Refer to the official ur_rtde documentation: https://sdurobotics.gitlab.io/ur_rtde/

## Version History

- **v1.0.0 (2025-11-04)**: Stage 1 core features completed
  - Basic connection management
  - Real-time status monitoring
  - Freedrive mode
  - Emergency stop

## Development Team

Development framework: Python + PyQt5 + ur_rtde
Development stage: Stage 1 (core features)

---

**Enjoy using the system!** 🤖
