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
python main.py
```

### Connect to the robot

1. Make sure the UR10e is powered on and ready to accept connections
2. Enter the robot's IP address (for example, 192.168.1.100) in the "Connection Settings" area of the application
3. Confirm that the port is 30004 (the RTDE default port)
4. Click the "Connect" button
5. After a successful connection, the status indicator turns green: "● Connected"

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
