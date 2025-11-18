#!/usr/bin/env python3
"""
Safe Point-to-Point Movement Control for UR10e
Reads current position and moves relative to it
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

# Get current robot position
current_pose = rtde_r.getActualTCPPose()
print("\nCurrent Robot Position:")
print(f"  X:  {current_pose[0]:.4f} m")
print(f"  Y:  {current_pose[1]:.4f} m")
print(f"  Z:  {current_pose[2]:.4f} m")
print(f"  Rx: {current_pose[3]:.4f} rad")
print(f"  Ry: {current_pose[4]:.4f} rad")
print(f"  Rz: {current_pose[5]:.4f} rad")

# Movement parameters
velocity = 0.2      # m/s (slower for safety)
acceleration = 0.3  # m/s^2
move_distance = 0.1  # 10 cm movements

# Calculate target positions relative to current position
# Move in a square pattern: right -> forward -> left -> back
point_1 = current_pose.copy()  # Starting position

point_2 = current_pose.copy()
point_2[0] += move_distance  # Move +X (right)

point_3 = current_pose.copy()
point_3[0] += move_distance  # Move +X
point_3[1] += move_distance  # Move +Y (forward)

point_4 = current_pose.copy()
point_4[1] += move_distance  # Move +Y (forward)

print("\n=== Movement Plan (Square Pattern) ===")
print(f"Starting Point: [{point_1[0]:.4f}, {point_1[1]:.4f}, {point_1[2]:.4f}]")
print(f"Point 2 (+X):   [{point_2[0]:.4f}, {point_2[1]:.4f}, {point_2[2]:.4f}]")
print(f"Point 3 (+X+Y): [{point_3[0]:.4f}, {point_3[1]:.4f}, {point_3[2]:.4f}]")
print(f"Point 4 (+Y):   [{point_4[0]:.4f}, {point_4[1]:.4f}, {point_4[2]:.4f}]")
print(f"\nMovement distance: {move_distance*1000:.0f} mm each side")
print(f"Speed: {velocity} m/s")

# Ask for confirmation
print("\n⚠️  SAFETY CHECK ⚠️")
print("Please verify:")
print("  1. Robot workspace is clear")
print("  2. Movement path is safe")
print("  3. Emergency stop is accessible")
response = input("\nProceed with movement? (yes/no): ").strip().lower()

if response != 'yes':
    print("Movement cancelled by user")
    rtde_c.disconnect()
    rtde_r.disconnect()
    exit()

print("\n=== Starting Point-to-Point Movement ===\n")

# Move to Point 1
print("Moving to Point 1...")
rtde_c.moveL(point_1, velocity, acceleration)
print("  ✓ Reached Point 1")
time.sleep(0.5)

# Move to Point 2
print("Moving to Point 2...")
rtde_c.moveL(point_2, velocity, acceleration)
print("  ✓ Reached Point 2")
time.sleep(0.5)

# Move to Point 3
print("Moving to Point 3...")
rtde_c.moveL(point_3, velocity, acceleration)
print("  ✓ Reached Point 3")
time.sleep(0.5)

# Move to Point 4
print("Moving to Point 4...")
rtde_c.moveL(point_4, velocity, acceleration)
print("  ✓ Reached Point 4")
time.sleep(0.5)

# Return to Point 1
print("Returning to Point 1...")
rtde_c.moveL(point_1, velocity, acceleration)
print("  ✓ Returned to Point 1")

print("\n=== Movement Complete ===\n")

# Disconnect
rtde_c.stopScript()
rtde_c.disconnect()
rtde_r.disconnect()
print("Disconnected from robot")
