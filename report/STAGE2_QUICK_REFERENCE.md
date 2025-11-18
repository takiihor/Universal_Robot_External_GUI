# Stage 2 Quick Reference

## New Features Quick Guide

### 📋 UI Layout
```
Main Window
├── Left Panel (Tabbed Controls)
│   ├── [Basic] Connection, Freedrive, E-Stop
│   ├── [TCP Control] 6-DOF Cartesian movement
│   ├── [Joint Control] 6-joint individual control
│   ├── [Presets] Position save/load/delete
│   ├── [Force] Force control parameters
│   └── [Scripts] URScript execution
└── Right Panel (Monitor)
    ├── TCP Pose display
    ├── Joint Angles display
    ├── Force/Torque display
    └── System Messages log
```

## 🎮 Control Reference

### TCP Control
**Step Sizes**: 1mm, 5mm, 10mm, 50mm
**Speed Range**: 0.01 - 1.0 m/s
**Accel Range**: 0.1 - 2.0 m/s²

**Axes**:
- X/Y/Z: Position control
- Rx/Ry/Rz: Orientation control

**Usage**:
1. Select step size
2. Adjust speed/accel if needed
3. Click +/- buttons for desired axis

### Joint Control
**Step Sizes**: 1°, 5°, 10°, 45°
**Speed Range**: 0.05 - 2.0 rad/s
**Accel Range**: 0.1 - 3.0 rad/s²

**Joints**: J1, J2, J3, J4, J5, J6

**Usage**:
1. Select step size
2. Adjust speed/accel if needed
3. Click +/- buttons for desired joint

### Preset Positions
**Default Presets**:
- `home`: Origin position [0, -1.57, 1.57, -1.57, -1.57, 0]
- `safe`: Safe position (elevated)
- `vertical`: Straight down position

**Operations**:
- **Quick Move**: Click preset button → Confirm → Move
- **Save Current**: Enter name → Click Save
- **Load Custom**: Select from list → Click Load → Confirm
- **Delete Custom**: Select from list → Click Delete → Confirm
  (Cannot delete default presets)

### Force Control
**Parameters**:
- Target Force: 0.5 - 50 N
- Gain: 0.001 - 0.01
- Max Displacement: 0.01 - 0.1 m

**Direction Selection**:
- Check Fx, Fy, Fz for linear forces
- Check Tx, Ty, Tz for torques

**Usage**:
1. Set parameters
2. Select force direction(s)
3. Click Start Force Mode
4. Monitor force display
5. Click Stop when done

### Script Execution
**Script Location**: `scripts/` directory

**Operations**:
- **Refresh List**: Updates available scripts
- **Execute**: Select script → Click Execute → Confirm
- **Stop**: Click Stop Script button

**Script Format**: URScript (.script files)

## 🔧 RobotController API Updates

### New Methods

#### Force Control
```python
# Start force mode
robot_controller.start_force_mode(
    task_frame=[x,y,z,rx,ry,rz],
    selection_vector=[fx,fy,fz,tx,ty,tz],  # 1=active, 0=inactive
    wrench=[fx,fy,fz,tx,ty,tz],
    force_type=2,  # 2=base frame
    limits=[vx,vy,vz,wx,wy,wz]
)

# Stop force mode
robot_controller.stop_force_mode()
```

#### Script Execution
```python
# Execute from file
robot_controller.execute_script("scripts/my_script.script")

# Execute code directly
robot_controller.execute_urscript_code("movej([0,-1.57,0,0,0,0], a=1.0, v=0.5)")

# Stop script
robot_controller.stop_script()
```

#### I/O Control
```python
# Digital I/O
robot_controller.set_digital_out(pin=0, value=True)  # Set pin 0 HIGH
state = robot_controller.get_digital_in(pin=0)  # Read pin 0

# Analog I/O
robot_controller.set_analog_out(pin=0, value=0.5)  # Set pin 0 to 0.5
value = robot_controller.get_analog_in(pin=0)  # Read pin 0
```

## 📊 Status Indicators

### Connection Status
- 🟢 **Green "● Connected"**: Robot connected and ready
- 🔴 **Red "● Disconnected"**: No connection

### Freedrive Status
- **Active** (green): Freedrive mode enabled
- **Inactive** (black): Freedrive mode disabled

### Force Mode Status
- **Active** (green): Force control running
- **Inactive** (black): Force control stopped

### Script Status
- **Running [script_name]** (green): Script executing
- **No script running** (black): Idle

## ⚠️ Safety Notes

### Before Moving Robot
1. Ensure work area is clear
2. Check workspace limits
3. Start with small step sizes
4. Use slow speeds for testing

### Emergency Stop
- Big red "⚠ EMERGENCY STOP ⚠" button
- Available on Basic tab
- Requires confirmation
- Stops all motion immediately

### Confirmation Dialogs
Required for:
- Moving to preset positions
- Starting force mode
- Executing scripts
- Emergency stop
- Deleting presets

## 🔢 Default Values

### TCP Movement
- Speed: 0.1 m/s
- Accel: 0.5 m/s²
- Step: 5mm

### Joint Movement
- Speed: 0.5 rad/s
- Accel: 1.0 rad/s²
- Step: 5°

### Force Control
- Target Force: 1.5 N
- Gain: 0.003
- Max Disp: 0.03 m
- Direction: [0, 0, 1, 0, 0, 0] (Z-axis)

## 🎯 Common Tasks

### Task 1: Move to Home Position
1. Go to "Presets" tab
2. Click "Move to HOME"
3. Confirm
4. Wait for completion

### Task 2: Manual TCP Adjustment
1. Go to "TCP Control" tab
2. Select step size (e.g., 5mm)
3. Click +/- buttons for desired axis
4. Monitor TCP display for feedback

### Task 3: Save Current Position
1. Move robot to desired position
2. Go to "Presets" tab
3. Enter position name
4. Click "Save"
5. Position added to list

### Task 4: Apply Force in Z Direction
1. Go to "Force" tab
2. Set Target Force (e.g., 2.0 N)
3. Check only "Fz"
4. Click "Start Force Mode"
5. Monitor force display
6. Click "Stop Force Mode" when done

### Task 5: Execute Custom Script
1. Place .script file in `scripts/` folder
2. Go to "Scripts" tab
3. Click "Refresh List"
4. Select your script
5. Click "Execute Selected Script"
6. Confirm
7. Monitor status

## 🐛 Troubleshooting

### Controls Disabled
**Problem**: All control buttons grayed out
**Solution**: Check connection status. Connect to robot first.

### Movement Not Happening
**Problem**: Clicked +/- but robot doesn't move
**Possible Causes**:
1. Not connected → Check connection
2. Out of workspace → Check limits
3. Safety stop active → Check robot status
4. Speed too slow → Increase speed

### Preset Not Saving
**Problem**: Click Save but position doesn't appear
**Solution**:
1. Ensure position name is entered
2. Check if connected to robot
3. Check logs for error messages

### Force Mode Fails
**Problem**: Force mode doesn't start
**Possible Causes**:
1. Invalid parameters → Check ranges
2. Robot not in correct mode → Check robot status
3. Position limits → Ensure safe position

### Script Won't Execute
**Problem**: Script execution fails
**Possible Causes**:
1. Syntax error in script → Check script file
2. File not found → Check scripts/ directory
3. Wrong file format → Ensure .script extension

## 📝 Logging

### Log Colors
- 🟢 **Green [INFO]**: Normal operation
- 🔴 **Red [ERROR]**: Error occurred

### Common Messages
- `"Connected to robot"` - Connection successful
- `"TCP movement completed"` - Movement finished
- `"Force mode started"` - Force control active
- `"Script executed"` - Script sent to robot
- `"Position 'name' saved"` - Preset saved successfully

## 🔄 Workflow Example

### Complete Control Sequence
```
1. Launch application
   └─> python main.py

2. Connect to robot
   ├─> Basic tab
   ├─> Enter IP (e.g., 192.168.1.100)
   ├─> Click Connect
   └─> Wait for "● Connected"

3. Move to safe position
   ├─> Presets tab
   ├─> Click "Move to SAFE"
   └─> Confirm

4. Adjust TCP position
   ├─> TCP Control tab
   ├─> Select step size (5mm)
   ├─> Click Z+ to raise
   └─> Wait for completion

5. Save position
   ├─> Presets tab
   ├─> Enter "work_height"
   ├─> Click Save
   └─> Verify in list

6. Return home
   ├─> Presets tab
   ├─> Click "Move to HOME"
   └─> Confirm

7. Disconnect
   ├─> Basic tab
   └─> Click Disconnect
```

## 📖 Related Documentation

- **Installation**: See `INSTALLATION.md`
- **Full Stage 2 Summary**: See `DEVELOPMENT_STAGE2_SUMMARY.md`
- **General Reference**: See `QUICK_REFERENCE.md`
- **User Guide**: See `README.md`

---

**Version**: Stage 2 (2025-11-04)
**Status**: Production Ready
