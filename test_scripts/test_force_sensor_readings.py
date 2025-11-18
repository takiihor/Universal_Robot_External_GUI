#!/usr/bin/env python3
"""
Test to diagnose force sensor readings and chart behavior
This will help identify if the oscillation is from sensor noise or a software issue
"""

import sys
import time
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QTextEdit
from PyQt5.QtCore import QTimer
from ui_mainwindow import MainWindow

class ForceDiagnosticWindow(QMainWindow):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setWindowTitle("Force Sensor Diagnostic")
        self.setGeometry(100, 100, 600, 400)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Info label
        info = QLabel("Force Sensor Raw Readings (Fx, Fy, Fz):\n"
                     "Monitoring for 10 seconds to check for oscillations...")
        layout.addWidget(info)

        # Text area for readings
        self.readings_text = QTextEdit()
        self.readings_text.setReadOnly(True)
        layout.addWidget(self.readings_text)

        # Stats label
        self.stats_label = QLabel()
        layout.addWidget(self.stats_label)

        # Storage for readings
        self.force_readings = []
        self.start_time = time.time()

        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.collect_reading)
        self.update_timer.start(100)  # Collect every 100ms

        # Stop timer
        QTimer.singleShot(10000, self.analyze_and_close)

    def collect_reading(self):
        """Collect a force sensor reading"""
        if hasattr(self.main_window, 'latest_forces') and self.main_window.latest_forces:
            forces = self.main_window.latest_forces
            if len(forces) >= 3:
                elapsed = time.time() - self.start_time
                reading = {
                    'time': elapsed,
                    'fx': forces[0],
                    'fy': forces[1],
                    'fz': forces[2]
                }
                self.force_readings.append(reading)

                # Display latest reading
                text = f"[{elapsed:.2f}s] Fx:{forces[0]:7.2f} N  Fy:{forces[1]:7.2f} N  Fz:{forces[2]:7.2f} N"
                self.readings_text.append(text)

    def analyze_and_close(self):
        """Analyze collected readings and display statistics"""
        if not self.force_readings:
            self.stats_label.setText("No force data received!")
            QTimer.singleShot(2000, self.close)
            return

        # Calculate statistics
        fx_values = [r['fx'] for r in self.force_readings]
        fy_values = [r['fy'] for r in self.force_readings]
        fz_values = [r['fz'] for r in self.force_readings]

        import statistics

        fx_mean = statistics.mean(fx_values)
        fy_mean = statistics.mean(fy_values)
        fz_mean = statistics.mean(fz_values)

        fx_stdev = statistics.stdev(fx_values) if len(fx_values) > 1 else 0
        fy_stdev = statistics.stdev(fy_values) if len(fy_values) > 1 else 0
        fz_stdev = statistics.stdev(fz_values) if len(fz_values) > 1 else 0

        fx_range = max(fx_values) - min(fx_values)
        fy_range = max(fy_values) - min(fy_values)
        fz_range = max(fz_values) - min(fz_values)

        # Display analysis
        analysis = f"""
========================================
FORCE SENSOR ANALYSIS ({len(self.force_readings)} samples)
========================================

Fx (Forward/Backward):
  Mean:   {fx_mean:7.2f} N
  StdDev: {fx_stdev:7.2f} N
  Range:  {fx_range:7.2f} N  ({min(fx_values):.2f} to {max(fx_values):.2f})

Fy (Left/Right):
  Mean:   {fy_mean:7.2f} N
  StdDev: {fy_stdev:7.2f} N
  Range:  {fy_range:7.2f} N  ({min(fy_values):.2f} to {max(fy_values):.2f})

Fz (Up/Down):
  Mean:   {fz_mean:7.2f} N
  StdDev: {fz_stdev:7.2f} N
  Range:  {fz_range:7.2f} N  ({min(fz_values):.2f} to {max(fz_values):.2f})

========================================
INTERPRETATION:
========================================
"""

        # Interpret results
        max_stdev = max(fx_stdev, fy_stdev, fz_stdev)
        max_range = max(fx_range, fy_range, fz_range)

        if max_stdev < 0.5:
            analysis += "✓ LOW NOISE: Force sensor readings are very stable (StdDev < 0.5 N)\n"
        elif max_stdev < 2.0:
            analysis += "! MODERATE NOISE: Some oscillation present (StdDev < 2.0 N)\n"
            analysis += "  This is normal for force sensors - consider zeroing the sensor\n"
        else:
            analysis += "✗ HIGH NOISE: Significant oscillation (StdDev > 2.0 N)\n"
            analysis += "  Possible causes:\n"
            analysis += "  - Robot moving or vibrating\n"
            analysis += "  - Force mode active with compliance\n"
            analysis += "  - External disturbances\n"
            analysis += "  - Sensor needs calibration\n"

        if max_range < 1.0:
            analysis += "\n✓ STABLE: Peak-to-peak variation < 1.0 N\n"
        elif max_range < 5.0:
            analysis += "\n! MODERATE VARIATION: Peak-to-peak variation < 5.0 N\n"
        else:
            analysis += "\n✗ LARGE VARIATION: Peak-to-peak variation > 5.0 N\n"

        # Check if force mode is active
        if hasattr(self.main_window, 'force_mode_active') and self.main_window.force_mode_active:
            analysis += "\n⚠ FORCE MODE IS ACTIVE - This will cause oscillations!\n"
            analysis += "  The robot is actively applying forces, not idle.\n"
        else:
            analysis += "\n✓ Force mode is inactive\n"

        analysis += "\n========================================\n"
        analysis += "Window will close in 5 seconds...\n"

        self.readings_text.append(analysis)
        print(analysis)

        QTimer.singleShot(5000, self.close)


def main():
    """Run diagnostic test"""
    app = QApplication(sys.argv)

    # Create main window (but don't show it prominently)
    main_window = MainWindow()
    main_window.setGeometry(0, 0, 800, 600)
    main_window.show()

    print("\n" + "="*70)
    print("FORCE SENSOR DIAGNOSTIC TEST")
    print("="*70)
    print("\nThis test will:")
    print("1. Connect to the robot (use main window to connect)")
    print("2. Monitor force sensor readings for 10 seconds")
    print("3. Analyze oscillation/noise characteristics")
    print("4. Provide recommendations")
    print("\n⚠  Please ensure robot is stationary and not in force mode")
    print("="*70 + "\n")

    # Wait a bit for connection, then show diagnostic window
    def show_diagnostic():
        if not hasattr(main_window, 'robot_controller') or not main_window.robot_controller._connected:
            print("⚠  Robot not connected! Please connect using the main window.")
            print("   Test will continue, but no data will be collected.")

        diagnostic = ForceDiagnosticWindow(main_window)
        diagnostic.show()

    QTimer.singleShot(2000, show_diagnostic)

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
