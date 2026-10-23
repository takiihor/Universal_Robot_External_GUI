#!/bin/bash
echo "============================================"
echo "UR10e Robot Connection Checker"
echo "============================================"
echo ""
echo "Enter your robot's IP address (e.g., 192.168.1.10):"
read ROBOT_IP

echo ""
echo "Testing connection to robot at $ROBOT_IP..."
echo ""

# Test ping
echo "1. Testing network connectivity (ping)..."
if ping -c 3 -W 2 $ROBOT_IP > /dev/null 2>&1; then
    echo "   ✅ Robot is reachable on network"
else
    echo "   ❌ Cannot reach robot. Check:"
    echo "      - Robot is powered on"
    echo "      - Network cable is connected"
    echo "      - IP address is correct"
    echo "      - You're on the same network"
    exit 1
fi

# Test RTDE port (30004)
echo ""
echo "2. Testing RTDE port (30004)..."
if timeout 2 bash -c "echo > /dev/tcp/$ROBOT_IP/30004" 2>/dev/null; then
    echo "   ✅ RTDE port 30004 is open"
else
    echo "   ⚠️  Port 30004 not accessible. This may be normal if:"
    echo "      - Robot is in safe mode"
    echo "      - RTDE is not enabled"
fi

echo ""
echo "============================================"
echo "Connection check complete!"
echo "============================================"
echo ""
echo "Next steps:"
echo "1. Launch the UI: python3 main.py"
echo "2. Enter IP: $ROBOT_IP"
echo "3. Port: 30004"
echo "4. Click 'Connect'"
