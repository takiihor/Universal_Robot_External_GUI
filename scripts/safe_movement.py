#!/usr/bin/env python3
"""
Safe Configurable Point-to-Point Movement
Gets current position and allows user to define safe movements
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
print("✓ Connected!")

# Get starting position
start_pose = rtde_r.getActualTCPPose()
print("\n" + "="*60)
print("Current Robot TCP Position:")
print("="*60)
print(f"  X:  {start_pose[0]:7.4f} m")
print(f"  Y:  {start_pose[1]:7.4f} m")
print(f"  Z:  {start_pose[2]:7.4f} m")
print(f"  Rx: {start_pose[3]:7.4f} rad")
print(f"  Ry: {start_pose[4]:7.4f} rad")
print(f"  Rz: {start_pose[5]:7.4f} rad")
print("="*60)

# User configuration
print("\n⚙️  Movement Configuration")
print("-" * 60)

# Get movement distance
while True:
    try:
        distance_mm = float(input("Enter movement distance in mm (e.g., 50): "))
        if 0 < distance_mm <= 200:
            distance_m = distance_mm / 1000.0
            break
        else:
            print("Please enter a value between 0 and 200 mm")
    except ValueError:
        print("Invalid input. Please enter a number.")

# Get velocity
while True:
    try:
        velocity = float(input("Enter velocity in m/s (0.05-0.5, default 0.2): ") or "0.2")
        if 0.05 <= velocity <= 0.5:
            break
        else:
            print("Please enter a value between 0.05 and 0.5")
    except ValueError:
        print("Invalid input. Using default 0.2 m/s")
        velocity = 0.2
        break

acceleration = velocity * 2  # Acceleration = 2x velocity

# Define movement pattern
print("\n📍 Movement Pattern Options:")
print("  1. Square in XY plane (right-forward-left-back)")
print("  2. Line along X axis (right-left)")
print("  3. Line along Y axis (forward-back)")
print("  4. Line along Z axis (up-down)")

pattern = input("Select pattern (1-4): ").strip()

# Calculate target positions based on pattern
if pattern == "1":
    # Square pattern
    point_1 = start_pose.copy()
    
    point_2 = start_pose.copy()
    point_2[0] += distance_m  # +X
    
    point_3 = start_pose.copy()
    point_3[0] += distance_m  # +X
    point_3[1] += distance_m  # +Y
    
    point_4 = start_pose.copy()
    point_4[1] += distance_m  # +Y
    
    points = [point_1, point_2, point_3, point_4, point_1]
    pattern_name = "Square Pattern"
    
elif pattern == "2":
    # X-axis line
    point_1 = start_pose.copy()
    
    point_2 = start_pose.copy()
    point_2[0] += distance_m  # +X
    
    points = [point_1, point_2, point_1]
    pattern_name = "X-axis Line"
    
elif pattern == "3":
    # Y-axis line
    point_1 = start_pose.copy()
    
    point_2 = start_pose.copy()
    point_2[1] += distance_m  # +Y
    
    points = [point_1, point_2, point_1]
    pattern_name = "Y-axis Line"
    
elif pattern == "4":
    # Z-axis line
    point_1 = start_pose.copy()
    
    point_2 = start_pose.copy()
    point_2[2] += distance_m  # +Z
    
    points = [point_1, point_2, point_1]
    pattern_name = "Z-axis Line"
    
else:
    print("Invalid pattern selected. Using square pattern.")
    point_1 = start_pose.copy()
    point_2 = start_pose.copy()
    point_2[0] += distance_m
    point_3 = start_pose.copy()
    point_3[0] += distance_m
    point_3[1] += distance_m
    point_4 = start_pose.copy()
    point_4[1] += distance_m
    points = [point_1, point_2, point_3, point_4, point_1]
    pattern_name = "Square Pattern"

# Display movement plan
print("\n" + "="*60)
print(f"Movement Plan: {pattern_name}")
print("="*60)
for i, point in enumerate(points):
    print(f"Point {i+1}: [X:{point[0]:7.4f}, Y:{point[1]:7.4f}, Z:{point[2]:7.4f}]")
print(f"\nMovement distance: {distance_mm:.0f} mm")
print(f"Velocity: {velocity:.2f} m/s")
print(f"Acceleration: {acceleration:.2f} m/s²")
print("="*60)

# Safety confirmation
print("\n⚠️  SAFETY CHECK ⚠️")
print("Before proceeding, verify:")
print("  ✓ Robot workspace is clear of obstacles")
print("  ✓ Movement path will not cause collisions")
print("  ✓ Emergency stop button is accessible")
print("  ✓ Personnel are at safe distance")
print()
response = input("Type 'START' to proceed with movement: ").strip().upper()

if response != 'START':
    print("\n❌ Movement cancelled by user")
    rtde_c.disconnect()
    rtde_r.disconnect()
    exit()

# Execute movement
print("\n" + "="*60)
print("=== STARTING MOVEMENT ===")
print("="*60 + "\n")

try:
    for i in range(len(points)):
        print(f"Moving to Point {i+1}...")
        rtde_c.moveL(points[i], velocity, acceleration)
        print(f"  ✓ Reached Point {i+1}")
        time.sleep(0.5)
    
    print("\n" + "="*60)
    print("=== MOVEMENT COMPLETED SUCCESSFULLY ===")
    print("="*60)

except Exception as e:
    print(f"\n❌ ERROR during movement: {e}")
    rtde_c.stopScript()

finally:
    # Always disconnect
    print("\nDisconnecting from robot...")
    rtde_c.stopScript()
    rtde_c.disconnect()
    rtde_r.disconnect()
    print("✓ Disconnected")
