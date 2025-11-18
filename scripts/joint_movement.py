#!/usr/bin/env python3
"""
Safe Joint Space Point-to-Point Movement for UR10e
Reads current joint positions and moves relative to them
"""

import rtde_control
import rtde_receive
import time

# Robot IP address
ROBOT_IP = "192.168.5.17"

# Connect to robot
print("Connecting to robot...")
rtde_c = rtde_control.RTDEControlInterface(ROBOT_IP)
rtde_r = rtde_receive.RTDEReceiveInterface(ROBOT_IP)
print("Connected!")

# Get current joint positions
current_joints = rtde_r.getActualQ()
print("\nCurrent Joint Positions:")
for i, angle in enumerate(current_joints):
    print(f"  Joint {i+1}: {angle:7.4f} rad ({angle*57.2958:7.2f}°)")

# Movement parameters
velocity = 0.5      # rad/s
acceleration = 0.5  # rad/s^2
joint_move = 0.3    # Move 0.3 rad (~17 degrees)

# Calculate target positions relative to current joints
home_position = current_joints.copy()  # Starting position

position_1 = current_joints.copy()
position_1[0] += joint_move  # Move base joint

position_2 = current_joints.copy()
position_2[0] += joint_move
position_2[1] += joint_move  # Move shoulder joint

position_3 = current_joints.copy()
position_3[1] += joint_move  # Move shoulder joint only

print("\n=== Movement Plan ===")
print(f"Starting Position (current): Joint 1={home_position[0]:6.3f} rad")
print(f"Position 1 (base +{joint_move:.2f}):  Joint 1={position_1[0]:6.3f} rad")
print(f"Position 2 (base+shoulder):  Joint 1={position_2[0]:6.3f} rad, Joint 2={position_2[1]:6.3f} rad")
print(f"Position 3 (shoulder):       Joint 2={position_3[1]:6.3f} rad")
print(f"\nMovement: {joint_move:.2f} rad ({joint_move*57.2958:.1f}°) per joint")

# Safety check
print("\n⚠️  SAFETY CHECK ⚠️")
response = input("Proceed with movement? (yes/no): ").strip().lower()
if response != 'yes':
    print("Movement cancelled")
    rtde_c.disconnect()
    rtde_r.disconnect()
    exit()

print("\n=== Starting Joint Movement ===\n")

# Move to home position
print("Moving to Home Position...")
rtde_c.moveJ(home_position, velocity, acceleration)
print("  ✓ Reached Home")
time.sleep(0.5)

# Move to Position 1
print("Moving to Position 1...")
rtde_c.moveJ(position_1, velocity, acceleration)
print("  ✓ Reached Position 1")
time.sleep(0.5)

# Move to Position 2
print("Moving to Position 2...")
rtde_c.moveJ(position_2, velocity, acceleration)
print("  ✓ Reached Position 2")
time.sleep(0.5)

# Move to Position 3
print("Moving to Position 3...")
rtde_c.moveJ(position_3, velocity, acceleration)
print("  ✓ Reached Position 3")
time.sleep(0.5)

# Return to home
print("Returning to Home...")
rtde_c.moveJ(home_position, velocity, acceleration)
print("  ✓ Returned to Home")

print("\n=== Movement Complete ===\n")

# Disconnect
rtde_c.stopScript()
rtde_c.disconnect()
rtde_r.disconnect()
print("Disconnected from robot")
