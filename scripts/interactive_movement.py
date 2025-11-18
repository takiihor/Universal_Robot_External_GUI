#!/usr/bin/env python3
"""
Interactive Point-to-Point Movement
Record current position and move to saved positions
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

# Storage for saved positions
saved_positions = []

def get_current_position():
    """Get current TCP position"""
    return rtde_r.getActualTCPPose()

def save_position():
    """Save current position"""
    pos = get_current_position()
    saved_positions.append(pos)
    print(f"✓ Position {len(saved_positions)} saved:")
    print(f"  [{pos[0]:.4f}, {pos[1]:.4f}, {pos[2]:.4f}, {pos[3]:.4f}, {pos[4]:.4f}, {pos[5]:.4f}]")

def list_positions():
    """List all saved positions"""
    if not saved_positions:
        print("No positions saved yet")
        return
    
    print("\nSaved Positions:")
    for i, pos in enumerate(saved_positions):
        print(f"  {i+1}. [{pos[0]:.4f}, {pos[1]:.4f}, {pos[2]:.4f}, {pos[3]:.4f}, {pos[4]:.4f}, {pos[5]:.4f}]")
    print()

def move_to_position(index):
    """Move to saved position"""
    if index < 0 or index >= len(saved_positions):
        print("Invalid position number")
        return
    
    target = saved_positions[index]
    print(f"Moving to Position {index+1}...")
    rtde_c.moveL(target, 0.5, 0.5)
    print("  ✓ Movement complete")

def play_sequence():
    """Play through all saved positions"""
    if not saved_positions:
        print("No positions saved yet")
        return
    
    print("\n=== Playing Sequence ===")
    for i, pos in enumerate(saved_positions):
        print(f"Moving to Position {i+1}...")
        rtde_c.moveL(pos, 0.5, 0.5)
        print("  ✓ Reached")
        time.sleep(0.5)
    print("=== Sequence Complete ===\n")

# Main menu
def main():
    print("\n" + "="*50)
    print("  Interactive Point-to-Point Movement")
    print("="*50)
    
    while True:
        print("\nMenu:")
        print("  1. Save current position")
        print("  2. List saved positions")
        print("  3. Move to a saved position")
        print("  4. Play sequence (all positions)")
        print("  5. Clear all positions")
        print("  6. Show current position")
        print("  0. Exit")
        
        choice = input("\nEnter choice: ").strip()
        
        if choice == '1':
            save_position()
            
        elif choice == '2':
            list_positions()
            
        elif choice == '3':
            list_positions()
            if saved_positions:
                try:
                    num = int(input("Enter position number: ")) - 1
                    move_to_position(num)
                except ValueError:
                    print("Invalid input")
                    
        elif choice == '4':
            play_sequence()
            
        elif choice == '5':
            saved_positions.clear()
            print("✓ All positions cleared")
            
        elif choice == '6':
            pos = get_current_position()
            print(f"Current position:")
            print(f"  [{pos[0]:.4f}, {pos[1]:.4f}, {pos[2]:.4f}, {pos[3]:.4f}, {pos[4]:.4f}, {pos[5]:.4f}]")
            
        elif choice == '0':
            print("\nExiting...")
            break
            
        else:
            print("Invalid choice")
    
    # Disconnect
    rtde_c.stopScript()
    rtde_c.disconnect()
    rtde_r.disconnect()
    print("Disconnected from robot")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nProgram interrupted")
        rtde_c.stopScript()
        rtde_c.disconnect()
        rtde_r.disconnect()
