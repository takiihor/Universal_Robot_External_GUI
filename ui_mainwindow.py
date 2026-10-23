"""
UR10e Control UI Main Window - Stage 3

This module implements the main window interface with all UI components.
Stage 3: Data logging, real-time visualization with PyQtGraph charts,
and extended menu system.

Note: All user-facing text and logs are in English as requested.
"""

import logging
import math
import os
import time
from datetime import datetime
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QGroupBox, QStatusBar,
    QMessageBox, QSplitter, QTextEdit, QComboBox, QSlider,
    QTabWidget, QListWidget, QListWidgetItem, QDoubleSpinBox, QCheckBox, QScrollArea,
    QAction, QMenu, QMenuBar, QFileDialog, QDockWidget, QStackedWidget,
    QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, QPointF
from PyQt5.QtGui import QFont, QPalette, QColor, QKeySequence, QPainter, QPen, QBrush, QPolygonF

# PyQtGraph for real-time plotting
import pyqtgraph as pg
pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')

from robot_controller import RobotController
from data_logger import DataLogger
from config import Config
from force_control.ui import ForceModePage
from utils import format_pose, format_force, format_joints, degrees_to_radians, radians_to_degrees, list_scripts
from preset_manager import PresetManager, PresetData, PresetCategory

# Setup logging
logger = logging.getLogger(__name__)


class TCPOrientationWidget(QWidget):
    """Custom widget to visualize TCP orientation"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 200)
        self.setMaximumSize(250, 250)

        # TCP orientation (roll, pitch, yaw in radians)
        self.roll = 0.0
        self.pitch = 0.0
        self.yaw = 0.0

    def update_orientation(self, rx, ry, rz):
        """Update orientation and trigger repaint"""
        self.roll = rx
        self.pitch = ry
        self.yaw = rz
        self.update()  # Trigger paintEvent

    def paintEvent(self, event):
        """Draw TCP orientation visualization"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Get widget dimensions
        width = self.width()
        height = self.height()
        center_x = width // 2
        center_y = height // 2

        # Draw background
        painter.fillRect(0, 0, width, height, QColor(250, 250, 250))

        # Draw reference circle (base)
        painter.setPen(QPen(QColor(200, 200, 200), 2))
        painter.setBrush(QBrush(QColor(240, 240, 240)))
        radius = min(width, height) // 2 - 20
        painter.drawEllipse(center_x - radius, center_y - radius, radius * 2, radius * 2)

        # Calculate TCP frame vectors based on orientation
        # Simplified 2D projection
        scale = radius * 0.6

        # X-axis (red) - affected by roll and yaw
        x_angle = self.yaw
        x_end_x = center_x + scale * math.cos(x_angle)
        x_end_y = center_y - scale * math.sin(x_angle)
        self.draw_arrow(painter, center_x, center_y, x_end_x, x_end_y, QColor(255, 0, 0), "X")

        # Y-axis (green) - perpendicular to X
        y_angle = self.yaw + math.pi / 2
        y_end_x = center_x + scale * math.cos(y_angle)
        y_end_y = center_y - scale * math.sin(y_angle)
        self.draw_arrow(painter, center_x, center_y, y_end_x, y_end_y, QColor(0, 180, 0), "Y")

        # Z-axis indicator (blue) - show as circle size based on pitch
        # If pitch near 0, Z points up (out of page) - larger circle
        # If pitch near 90°, Z is in plane - smaller circle
        z_radius = max(5, int(15 * abs(math.cos(self.pitch))))
        painter.setPen(QPen(QColor(0, 0, 255), 2))
        painter.setBrush(QBrush(QColor(100, 150, 255)))
        painter.drawEllipse(center_x - z_radius, center_y - z_radius, z_radius * 2, z_radius * 2)

        # Draw center point
        painter.setPen(QPen(QColor(0, 0, 0), 1))
        painter.setBrush(QBrush(QColor(0, 0, 0)))
        painter.drawEllipse(center_x - 3, center_y - 3, 6, 6)

        # Draw orientation angles text
        painter.setPen(QColor(50, 50, 50))
        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)

        roll_deg = math.degrees(self.roll)
        pitch_deg = math.degrees(self.pitch)
        yaw_deg = math.degrees(self.yaw)

        painter.drawText(10, height - 30, f"R: {roll_deg:5.1f}°")
        painter.drawText(10, height - 15, f"P: {pitch_deg:5.1f}°")
        painter.drawText(10, height - 0, f"Y: {yaw_deg:5.1f}°")

        # Draw "Z" label near the Z-axis circle
        painter.drawText(center_x - 3, center_y - z_radius - 5, "Z")

    def draw_arrow(self, painter, start_x, start_y, end_x, end_y, color, label):
        """Draw an arrow with label"""
        painter.setPen(QPen(color, 3))

        # Draw line
        painter.drawLine(int(start_x), int(start_y), int(end_x), int(end_y))

        # Draw arrowhead
        angle = math.atan2(end_y - start_y, end_x - start_x)
        arrow_size = 10

        # Arrow tip points
        p1 = QPointF(end_x, end_y)
        p2 = QPointF(
            end_x - arrow_size * math.cos(angle - math.pi / 6),
            end_y - arrow_size * math.sin(angle - math.pi / 6)
        )
        p3 = QPointF(
            end_x - arrow_size * math.cos(angle + math.pi / 6),
            end_y - arrow_size * math.sin(angle + math.pi / 6)
        )

        painter.setBrush(QBrush(color))
        painter.drawPolygon(QPolygonF([p1, p2, p3]))

        # Draw label
        painter.setPen(QColor(0, 0, 0))
        font = painter.font()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(int(end_x + 10), int(end_y + 5), label)


class MainWindow(QMainWindow):
    """Main window class with Stage 3 features - Data Logging & Visualization"""

    def __init__(self):
        super().__init__()

        # Initialize robot controller
        self.robot_controller = RobotController()
        self.preset_manager = getattr(self.robot_controller, "preset_manager", PresetManager())

        # Initialize data logger
        self.data_logger = DataLogger(max_buffer_size=Config.LOG_BUFFER_SIZE)

        # Initialize sequential controller
        from sequential_controller import SequentialController
        self.sequential_controller = SequentialController(self.robot_controller)

        # Hand Guiding Tool (lazy initialized)
        self.hand_guiding_tool = None

        # Chart update control
        self.charts_paused = False
        self.chart_update_counter = 0
        self.chart_update_interval = 5  # Update charts every N data points

        # Data buffers for plotting (circular buffers)
        self.max_plot_points = 500
        self.time_data = []
        self.tcp_x_data = []
        self.tcp_y_data = []
        self.tcp_z_data = []

        # Initialize UI
        self.init_ui()

        # Connect signals and slots
        self.connect_signals()

        # Set window properties
        self.setWindowTitle("UR10e Remote Control System - Stage 3 (Data Logging)")

        # Set reasonable size constraints to enable maximize button
        self.setMinimumSize(800, 600)
        # Don't set maximum size - let window be freely resizable

        # Set initial geometry
        self.resize(1600, 950)
        self.move(50, 50)

        logger.info("Main window initialized successfully with Stage 3 features")

    def init_ui(self):
        """Initialize UI components"""
        # Create menu bar
        self.create_menu_bar()

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout (horizontal split)
        main_layout = QHBoxLayout(central_widget)

        # Create splitter
        splitter = QSplitter(Qt.Horizontal)

        # Left side: Navigation bar (replaces tabbed control panel)
        left_panel = self.create_navigation_bar()
        splitter.addWidget(left_panel)

        # Right side: Stacked widget for page switching
        self.page_stack = QStackedWidget()

        # Page 0: Basic page (connection + controls + monitor + charts)
        basic_page = self.create_basic_page()
        self.page_stack.addWidget(basic_page)

        # Page 1: Programs page (Sequential Controller)
        programs_page = self.create_sequential_controller_page()
        self.page_stack.addWidget(programs_page)

        # Page 2: Movement page (detailed movement controls)
        movement_page = self.create_movement_page()
        self.page_stack.addWidget(movement_page)

        # Page 3: Force Mode page
        self.force_page = ForceModePage(self.robot_controller.force_controller)
        self.force_page.add_left_widget(self.create_data_recording_section())
        self.page_stack.addWidget(self.force_page)

        # Page 4: Presets page
        presets_page = self.create_presets_page()
        self.page_stack.addWidget(presets_page)

        # Page 5: Scripts page
        scripts_page = self.create_scripts_page()
        self.page_stack.addWidget(scripts_page)

        # Set default page
        self.page_stack.setCurrentIndex(0)

        splitter.addWidget(self.page_stack)

        # Set split ratio (navigation:pages)
        splitter.setStretchFactor(0, 1)   # Navigation bar - compact
        splitter.setStretchFactor(1, 10)  # Page area - main focus

        main_layout.addWidget(splitter)

        # Create status bar
        self.create_status_bar()

        # Note: Data logging controls moved to Force Mode page
        # self.create_data_logging_dock()  # Removed - now in Force Mode page

    # ========================================
    # Menu Bar
    # ========================================

    def create_menu_bar(self):
        """Create menu bar with File, View, Tools, and Help menus"""
        menubar = self.menuBar()

        # File Menu
        file_menu = menubar.addMenu("&File")

        save_config_action = QAction("&Save Configuration", self)
        save_config_action.setShortcut(QKeySequence.Save)
        save_config_action.triggered.connect(self.on_save_configuration)
        file_menu.addAction(save_config_action)

        load_config_action = QAction("&Load Configuration", self)
        load_config_action.setShortcut(QKeySequence.Open)
        load_config_action.triggered.connect(self.on_load_configuration)
        file_menu.addAction(load_config_action)

        file_menu.addSeparator()

        export_data_action = QAction("&Export Data...", self)
        export_data_action.setShortcut("Ctrl+E")
        export_data_action.triggered.connect(self.on_export_data)
        file_menu.addAction(export_data_action)

        export_summary_action = QAction("Export &Summary Report...", self)
        export_summary_action.triggered.connect(self.on_export_summary)
        file_menu.addAction(export_summary_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # View Menu
        view_menu = menubar.addMenu("&View")

        # Page navigation shortcuts
        view_basic_action = QAction("Show &Basic", self)
        view_basic_action.setShortcut("Ctrl+1")
        view_basic_action.triggered.connect(lambda: self.switch_to_page(0))
        view_menu.addAction(view_basic_action)

        view_programs_action = QAction("Show &Programs", self)
        view_programs_action.setShortcut("Ctrl+2")
        view_programs_action.triggered.connect(lambda: self.switch_to_page(1))
        view_menu.addAction(view_programs_action)

        view_movement_action = QAction("Show &Movement", self)
        view_movement_action.setShortcut("Ctrl+3")
        view_movement_action.triggered.connect(lambda: self.switch_to_page(2))
        view_menu.addAction(view_movement_action)

        view_force_action = QAction("Show &Force Mode", self)
        view_force_action.setShortcut("Ctrl+4")
        view_force_action.triggered.connect(lambda: self.switch_to_page(3))
        view_menu.addAction(view_force_action)

        view_menu.addSeparator()

        view_presets_action = QAction("Show Pr&esets", self)
        view_presets_action.setShortcut("Ctrl+5")
        view_presets_action.triggered.connect(lambda: self.switch_to_page(4))
        view_menu.addAction(view_presets_action)

        view_scripts_action = QAction("Show &Scripts", self)
        view_scripts_action.setShortcut("Ctrl+6")
        view_scripts_action.triggered.connect(lambda: self.switch_to_page(5))
        view_menu.addAction(view_scripts_action)

        view_menu.addSeparator()

        refresh_action = QAction("&Refresh", self)
        refresh_action.setShortcut(QKeySequence.Refresh)
        refresh_action.triggered.connect(self.on_refresh_ui)
        view_menu.addAction(refresh_action)

        clear_charts_action = QAction("Clear &Charts", self)
        clear_charts_action.triggered.connect(self.on_clear_charts)
        view_menu.addAction(clear_charts_action)

        # Tools Menu
        tools_menu = menubar.addMenu("&Tools")

        data_logger_action = QAction("Data &Logger Settings", self)
        data_logger_action.triggered.connect(self.on_data_logger_settings)
        tools_menu.addAction(data_logger_action)

        script_manager_action = QAction("&Script Manager", self)
        script_manager_action.triggered.connect(self.on_script_manager)
        tools_menu.addAction(script_manager_action)

        hand_guiding_action = QAction("🎓 &Hand Guiding - Position Teaching", self)
        hand_guiding_action.setShortcut("Ctrl+H")
        hand_guiding_action.triggered.connect(self.on_hand_guiding_tool)
        tools_menu.addAction(hand_guiding_action)

        tools_menu.addSeparator()

        calibrate_force_action = QAction("&Calibrate Force Sensor", self)
        calibrate_force_action.triggered.connect(self.on_calibrate_force_sensor)
        tools_menu.addAction(calibrate_force_action)

        # Help Menu
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.triggered.connect(self.on_about)
        help_menu.addAction(about_action)

        documentation_action = QAction("&Documentation", self)
        documentation_action.setShortcut(QKeySequence.HelpContents)
        documentation_action.triggered.connect(self.on_documentation)
        help_menu.addAction(documentation_action)

    # ========================================
    # Data Logging Dock Widget
    # ========================================

    def create_data_logging_dock(self):
        """Create dockable widget for data logging control"""
        self.logging_dock = QDockWidget("Data Recording", self)
        self.logging_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea)

        dock_widget = QWidget()
        dock_layout = QVBoxLayout(dock_widget)

        # Recording control group
        recording_group = QGroupBox("Recording Control")
        recording_layout = QVBoxLayout()

        # Session name input
        session_layout = QHBoxLayout()
        session_layout.addWidget(QLabel("Session Name:"))
        self.session_name_input = QLineEdit()
        self.session_name_input.setPlaceholderText("Optional session name")
        session_layout.addWidget(self.session_name_input)
        recording_layout.addLayout(session_layout)

        # Start/Stop recording buttons
        self.start_recording_btn = QPushButton("Start Recording")
        self.start_recording_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 8px; }")
        self.start_recording_btn.clicked.connect(self.on_start_recording)
        recording_layout.addWidget(self.start_recording_btn)

        self.stop_recording_btn = QPushButton("Stop Recording")
        self.stop_recording_btn.setEnabled(False)
        self.stop_recording_btn.setStyleSheet("QPushButton { background-color: #f44336; color: white; font-weight: bold; padding: 8px; }")
        self.stop_recording_btn.clicked.connect(self.on_stop_recording)
        recording_layout.addWidget(self.stop_recording_btn)

        # Pause/Resume buttons
        self.pause_recording_btn = QPushButton("Pause Recording")
        self.pause_recording_btn.setEnabled(False)
        self.pause_recording_btn.clicked.connect(self.on_pause_recording)
        recording_layout.addWidget(self.pause_recording_btn)

        # Recording status
        self.recording_status_label = QLabel("Status: Not Recording")
        self.recording_status_label.setAlignment(Qt.AlignCenter)
        self.recording_status_label.setStyleSheet("QLabel { padding: 5px; background-color: #f0f0f0; }")
        recording_layout.addWidget(self.recording_status_label)

        # Recording duration
        self.recording_duration_label = QLabel("Duration: 0.0 s")
        self.recording_duration_label.setAlignment(Qt.AlignCenter)
        recording_layout.addWidget(self.recording_duration_label)

        # Buffer size
        self.buffer_size_label = QLabel("Buffer: 0 / 10000 points")
        self.buffer_size_label.setAlignment(Qt.AlignCenter)
        recording_layout.addWidget(self.buffer_size_label)

        recording_group.setLayout(recording_layout)
        dock_layout.addWidget(recording_group)

        # Format selection
        format_group = QGroupBox("Export Format")
        format_layout = QVBoxLayout()

        self.export_format_combo = QComboBox()
        self.export_format_combo.addItems(["CSV", "HDF5"])
        format_layout.addWidget(self.export_format_combo)

        format_group.setLayout(format_layout)
        dock_layout.addWidget(format_group)

        # Trajectory Replay group
        replay_group = QGroupBox("Trajectory Replay")
        replay_layout = QVBoxLayout()

        # Load trajectory button
        self.load_trajectory_btn = QPushButton("📁 Load Trajectory")
        self.load_trajectory_btn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; font-weight: bold; padding: 8px; }")
        self.load_trajectory_btn.clicked.connect(self.on_load_trajectory)
        replay_layout.addWidget(self.load_trajectory_btn)

        # Replay button
        self.replay_trajectory_btn = QPushButton("▶ Replay Trajectory")
        self.replay_trajectory_btn.setEnabled(False)
        self.replay_trajectory_btn.setStyleSheet("QPushButton { background-color: #FF9800; color: white; font-weight: bold; padding: 8px; }")
        self.replay_trajectory_btn.clicked.connect(self.on_replay_trajectory)
        replay_layout.addWidget(self.replay_trajectory_btn)

        # Pause/Resume control buttons (horizontal layout)
        control_layout = QHBoxLayout()

        # Soft stop button
        self.pause_trajectory_btn = QPushButton("⏸ Soft Stop")
        self.pause_trajectory_btn.setEnabled(False)
        self.pause_trajectory_btn.setStyleSheet("QPushButton { background-color: #FFC107; color: black; font-weight: bold; padding: 8px; }")
        self.pause_trajectory_btn.clicked.connect(self.on_pause_trajectory)
        control_layout.addWidget(self.pause_trajectory_btn)

        # Resume button
        self.resume_trajectory_btn = QPushButton("▶ Resume")
        self.resume_trajectory_btn.setEnabled(False)
        self.resume_trajectory_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 8px; }")
        self.resume_trajectory_btn.clicked.connect(self.on_resume_trajectory)
        control_layout.addWidget(self.resume_trajectory_btn)

        replay_layout.addLayout(control_layout)

        # Replay status
        self.replay_status_label = QLabel("Status: No trajectory loaded")
        self.replay_status_label.setAlignment(Qt.AlignCenter)
        self.replay_status_label.setStyleSheet("QLabel { padding: 5px; background-color: #f0f0f0; }")
        replay_layout.addWidget(self.replay_status_label)

        # Replay progress
        self.replay_progress_label = QLabel("Progress: 0 / 0")
        self.replay_progress_label.setAlignment(Qt.AlignCenter)
        replay_layout.addWidget(self.replay_progress_label)

        replay_group.setLayout(replay_layout)
        dock_layout.addWidget(replay_group)

        dock_layout.addStretch()

        self.logging_dock.setWidget(dock_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.logging_dock)

        # Timer to update recording duration
        self.recording_timer = QTimer()
        self.recording_timer.timeout.connect(self.update_recording_status)
        self.recording_timer.start(100)  # Update every 100ms

        # Continuous movement control
        self.continuous_move_timer = QTimer()
        self.continuous_move_timer.timeout.connect(self.on_continuous_move_tick)
        self.continuous_move_active = False
        self.continuous_move_axis = None
        self.continuous_move_direction = 0

    # ========================================
    # Navigation Bar (Vertical Button Layout)
    # ========================================

    def create_navigation_bar(self) -> QWidget:
        """Create vertical navigation bar with page switching buttons"""
        panel = QWidget()
        panel.setMaximumWidth(200)
        panel.setStyleSheet("""
            QWidget {
                background-color: #f5f5f5;
            }
        """)
        layout = QVBoxLayout(panel)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # Navigation buttons list
        self.nav_buttons = []

        # Button style
        button_style = """
            QPushButton {
                background-color: #f5f5f5;
                color: #333;
                text-align: left;
                padding: 15px 20px;
                border: none;
                border-bottom: 1px solid #ddd;
                font-size: 14px;
                font-weight: normal;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:checked {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                border-left: 4px solid #1976D2;
            }
        """

        # Create navigation buttons
        # Page 0: Basic
        btn_basic = QPushButton("🏠  Basic")
        btn_basic.setCheckable(True)
        btn_basic.setChecked(True)
        btn_basic.setStyleSheet(button_style)
        btn_basic.clicked.connect(lambda: self.switch_to_page(0))
        layout.addWidget(btn_basic)
        self.nav_buttons.append(btn_basic)

        # Page 1: Programs
        btn_programs = QPushButton("🎯  Programs")
        btn_programs.setCheckable(True)
        btn_programs.setStyleSheet(button_style)
        btn_programs.clicked.connect(lambda: self.switch_to_page(1))
        layout.addWidget(btn_programs)
        self.nav_buttons.append(btn_programs)

        # Page 2: Movement
        btn_movement = QPushButton("🔧  Movement")
        btn_movement.setCheckable(True)
        btn_movement.setStyleSheet(button_style)
        btn_movement.clicked.connect(lambda: self.switch_to_page(2))
        layout.addWidget(btn_movement)
        self.nav_buttons.append(btn_movement)

        # Page 3: Force Mode
        btn_force = QPushButton("⚡  Force Mode")
        btn_force.setCheckable(True)
        btn_force.setStyleSheet(button_style)
        btn_force.clicked.connect(lambda: self.switch_to_page(3))
        layout.addWidget(btn_force)
        self.nav_buttons.append(btn_force)

        # Separator
        separator = QWidget()
        separator.setFixedHeight(10)
        separator.setStyleSheet("background-color: #ddd;")
        layout.addWidget(separator)

        # Page 4: Presets
        btn_presets = QPushButton("📍  Presets")
        btn_presets.setCheckable(True)
        btn_presets.setStyleSheet(button_style)
        btn_presets.clicked.connect(lambda: self.switch_to_page(4))
        layout.addWidget(btn_presets)
        self.nav_buttons.append(btn_presets)

        # Page 5: Scripts
        btn_scripts = QPushButton("📜  Scripts")
        btn_scripts.setCheckable(True)
        btn_scripts.setStyleSheet(button_style)
        btn_scripts.clicked.connect(lambda: self.switch_to_page(5))
        layout.addWidget(btn_scripts)
        self.nav_buttons.append(btn_scripts)

        # Add stretch to push buttons to top
        layout.addStretch()

        return panel

    def create_connection_section(self) -> QGroupBox:
        """Create connection control section"""
        group = QGroupBox("Connection Settings")
        layout = QGridLayout()

        # IP address
        layout.addWidget(QLabel("IP Address:"), 0, 0)
        self.ip_input = QLineEdit(Config.DEFAULT_IP)
        self.ip_input.setPlaceholderText("e.g., 192.168.1.100")
        layout.addWidget(self.ip_input, 0, 1)

        # Port
        layout.addWidget(QLabel("Port:"), 1, 0)
        self.port_input = QLineEdit(str(Config.DEFAULT_PORT))
        self.port_input.setPlaceholderText("Default: 30004")
        layout.addWidget(self.port_input, 1, 1)

        # Connect button
        self.connect_button = QPushButton("Connect")
        self.connect_button.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 8px; }")
        layout.addWidget(self.connect_button, 2, 0)

        # Disconnect button
        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.setEnabled(False)
        self.disconnect_button.setStyleSheet("QPushButton { background-color: #f44336; color: white; font-weight: bold; padding: 8px; }")
        layout.addWidget(self.disconnect_button, 2, 1)

        # Connection status indicator
        self.connection_status_label = QLabel("● Disconnected")
        self.connection_status_label.setStyleSheet("QLabel { color: red; font-weight: bold; }")
        layout.addWidget(self.connection_status_label, 3, 0, 1, 2)

        group.setLayout(layout)
        return group

    def create_freedrive_section(self) -> QGroupBox:
        """Create freedrive control section"""
        group = QGroupBox("Freedrive Mode")
        layout = QVBoxLayout()

        # Enable button
        self.freedrive_enable_button = QPushButton("Enable Freedrive")
        self.freedrive_enable_button.setEnabled(False)
        self.freedrive_enable_button.setStyleSheet("QPushButton { background-color: #2196F3; color: white; font-weight: bold; padding: 10px; }")
        layout.addWidget(self.freedrive_enable_button)

        # Disable button
        self.freedrive_disable_button = QPushButton("Disable Freedrive")
        self.freedrive_disable_button.setEnabled(False)
        self.freedrive_disable_button.setStyleSheet("QPushButton { background-color: #FF9800; color: white; font-weight: bold; padding: 10px; }")
        layout.addWidget(self.freedrive_disable_button)

        # Status indicator
        self.freedrive_status_label = QLabel("Status: Inactive")
        self.freedrive_status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.freedrive_status_label)

        group.setLayout(layout)
        return group

    def create_emergency_stop_button(self) -> QPushButton:
        """Create emergency stop button"""
        button = QPushButton("⚠ EMERGENCY STOP ⚠")
        button.setEnabled(False)
        button.setMinimumHeight(80)
        button.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f;
                color: white;
                font-size: 24px;
                font-weight: bold;
                border: 3px solid #b71c1c;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #f44336;
            }
            QPushButton:pressed {
                background-color: #b71c1c;
            }
            QPushButton:disabled {
                background-color: #bdbdbd;
                border-color: #9e9e9e;
                color: #757575;
            }
        """)
        self.emergency_stop_button = button
        return button

    def create_unlock_robot_button(self) -> QPushButton:
        """Create unlock robot button - performs complete recovery"""
        button = QPushButton("🔓 RECOVER ROBOT")
        button.setEnabled(False)
        button.setMinimumHeight(60)
        button.setStyleSheet("""
            QPushButton {
                background-color: #2e7d32;
                color: white;
                font-size: 18px;
                font-weight: bold;
                border: 3px solid #1b5e20;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #43a047;
            }
            QPushButton:pressed {
                background-color: #1b5e20;
            }
            QPushButton:disabled {
                background-color: #bdbdbd;
                border-color: #9e9e9e;
                color: #757575;
            }
        """)
        self.unlock_robot_button = button
        return button

    # ========================================
    # Movement Control Tab (Combined TCP + Joint)
    # ========================================

    def create_movement_control_tab(self) -> QWidget:
        """Create combined TCP and Joint control tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # ===== TCP CONTROL SECTION =====
        tcp_section = QGroupBox("TCP Control (Cartesian Space)")
        tcp_layout = QVBoxLayout()

        # TCP Speed/Acceleration settings
        tcp_speed_group = QGroupBox("TCP Speed & Acceleration")
        tcp_speed_layout = QGridLayout()
        tcp_speed_layout.addWidget(QLabel("Speed (m/s):"), 0, 0)
        self.tcp_speed_spin = QDoubleSpinBox()
        self.tcp_speed_spin.setRange(Config.MIN_TCP_SPEED, Config.MAX_TCP_SPEED)
        self.tcp_speed_spin.setValue(Config.DEFAULT_TCP_SPEED)
        self.tcp_speed_spin.setSingleStep(0.01)
        self.tcp_speed_spin.setDecimals(2)
        tcp_speed_layout.addWidget(self.tcp_speed_spin, 0, 1)

        tcp_speed_layout.addWidget(QLabel("Accel (m/s²):"), 1, 0)
        self.tcp_accel_spin = QDoubleSpinBox()
        self.tcp_accel_spin.setRange(Config.MIN_TCP_ACCEL, Config.MAX_TCP_ACCEL)
        self.tcp_accel_spin.setValue(Config.DEFAULT_TCP_ACCEL)
        self.tcp_accel_spin.setSingleStep(0.1)
        self.tcp_accel_spin.setDecimals(2)
        tcp_speed_layout.addWidget(self.tcp_accel_spin, 1, 1)
        tcp_speed_group.setLayout(tcp_speed_layout)
        tcp_layout.addWidget(tcp_speed_group)

        # Position control
        pos_group = QGroupBox("Position (X, Y, Z)")
        pos_layout = QGridLayout()

        # X axis
        pos_layout.addWidget(QLabel("X:"), 0, 0)
        self.tcp_x_minus = QPushButton("-")
        self.tcp_x_minus.setEnabled(False)
        pos_layout.addWidget(self.tcp_x_minus, 0, 1)
        self.tcp_x_plus = QPushButton("+")
        self.tcp_x_plus.setEnabled(False)
        pos_layout.addWidget(self.tcp_x_plus, 0, 2)

        # Y axis
        pos_layout.addWidget(QLabel("Y:"), 1, 0)
        self.tcp_y_minus = QPushButton("-")
        self.tcp_y_minus.setEnabled(False)
        pos_layout.addWidget(self.tcp_y_minus, 1, 1)
        self.tcp_y_plus = QPushButton("+")
        self.tcp_y_plus.setEnabled(False)
        pos_layout.addWidget(self.tcp_y_plus, 1, 2)

        # Z axis
        pos_layout.addWidget(QLabel("Z:"), 2, 0)
        self.tcp_z_minus = QPushButton("-")
        self.tcp_z_minus.setEnabled(False)
        pos_layout.addWidget(self.tcp_z_minus, 2, 1)
        self.tcp_z_plus = QPushButton("+")
        self.tcp_z_plus.setEnabled(False)
        pos_layout.addWidget(self.tcp_z_plus, 2, 2)

        pos_group.setLayout(pos_layout)
        tcp_layout.addWidget(pos_group)

        # Orientation control
        orient_group = QGroupBox("Orientation (Rx, Ry, Rz)")
        orient_layout = QGridLayout()

        # Rx
        orient_layout.addWidget(QLabel("Rx:"), 0, 0)
        self.tcp_rx_minus = QPushButton("-")
        self.tcp_rx_minus.setEnabled(False)
        orient_layout.addWidget(self.tcp_rx_minus, 0, 1)
        self.tcp_rx_plus = QPushButton("+")
        self.tcp_rx_plus.setEnabled(False)
        orient_layout.addWidget(self.tcp_rx_plus, 0, 2)

        # Ry
        orient_layout.addWidget(QLabel("Ry:"), 1, 0)
        self.tcp_ry_minus = QPushButton("-")
        self.tcp_ry_minus.setEnabled(False)
        orient_layout.addWidget(self.tcp_ry_minus, 1, 1)
        self.tcp_ry_plus = QPushButton("+")
        self.tcp_ry_plus.setEnabled(False)
        orient_layout.addWidget(self.tcp_ry_plus, 1, 2)

        # Rz
        orient_layout.addWidget(QLabel("Rz:"), 2, 0)
        self.tcp_rz_minus = QPushButton("-")
        self.tcp_rz_minus.setEnabled(False)
        orient_layout.addWidget(self.tcp_rz_minus, 2, 1)
        self.tcp_rz_plus = QPushButton("+")
        self.tcp_rz_plus.setEnabled(False)
        orient_layout.addWidget(self.tcp_rz_plus, 2, 2)

        orient_group.setLayout(orient_layout)
        tcp_layout.addWidget(orient_group)

        tcp_section.setLayout(tcp_layout)
        layout.addWidget(tcp_section)

        # ===== JOINT CONTROL SECTION =====
        joint_section = QGroupBox("Joint Control (Joint Space)")
        joint_layout = QVBoxLayout()

        # Joint Speed/Acceleration settings
        joint_speed_group = QGroupBox("Joint Speed & Acceleration")
        joint_speed_layout = QGridLayout()
        joint_speed_layout.addWidget(QLabel("Speed (rad/s):"), 0, 0)
        self.joint_speed_spin = QDoubleSpinBox()
        self.joint_speed_spin.setRange(Config.MIN_JOINT_SPEED, Config.MAX_JOINT_SPEED)
        self.joint_speed_spin.setValue(Config.DEFAULT_JOINT_SPEED)
        self.joint_speed_spin.setSingleStep(0.05)
        self.joint_speed_spin.setDecimals(2)
        joint_speed_layout.addWidget(self.joint_speed_spin, 0, 1)

        joint_speed_layout.addWidget(QLabel("Accel (rad/s²):"), 1, 0)
        self.joint_accel_spin = QDoubleSpinBox()
        self.joint_accel_spin.setRange(Config.MIN_JOINT_ACCEL, Config.MAX_JOINT_ACCEL)
        self.joint_accel_spin.setValue(Config.DEFAULT_JOINT_ACCEL)
        self.joint_accel_spin.setSingleStep(0.1)
        self.joint_accel_spin.setDecimals(2)
        joint_speed_layout.addWidget(self.joint_accel_spin, 1, 1)
        joint_speed_group.setLayout(joint_speed_layout)
        joint_layout.addWidget(joint_speed_group)

        # Joint control buttons
        joint_controls_group = QGroupBox("Joint Axes (J1-J6)")
        joint_controls_layout = QGridLayout()

        # Store joint buttons for enabling/disabling
        self.joint_minus_buttons = []
        self.joint_plus_buttons = []

        for i in range(6):
            joint_controls_layout.addWidget(QLabel(f"J{i+1}:"), i, 0)
            minus_btn = QPushButton("-")
            minus_btn.setEnabled(False)
            minus_btn.pressed.connect(lambda joint=i: self.on_joint_move_pressed(joint, -1))
            minus_btn.released.connect(self.on_joint_move_released)
            joint_controls_layout.addWidget(minus_btn, i, 1)
            self.joint_minus_buttons.append(minus_btn)

            plus_btn = QPushButton("+")
            plus_btn.setEnabled(False)
            plus_btn.pressed.connect(lambda joint=i: self.on_joint_move_pressed(joint, 1))
            plus_btn.released.connect(self.on_joint_move_released)
            joint_controls_layout.addWidget(plus_btn, i, 2)
            self.joint_plus_buttons.append(plus_btn)

        joint_controls_group.setLayout(joint_controls_layout)
        joint_layout.addWidget(joint_controls_group)

        joint_section.setLayout(joint_layout)
        layout.addWidget(joint_section)

        layout.addStretch()

        return tab

    # ========================================
    # Preset Positions Tab
    # ========================================

    def create_preset_positions_tab(self) -> QWidget:
        """Create preset positions management tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Quick access buttons for default presets
        quick_group = QGroupBox("Quick Access")
        quick_layout = QVBoxLayout()

        self.preset_home_btn = QPushButton("Move to HOME")
        self.preset_home_btn.setEnabled(False)
        self.preset_home_btn.clicked.connect(lambda: self.on_preset_move_clicked('home'))
        quick_layout.addWidget(self.preset_home_btn)

        self.preset_safe_btn = QPushButton("Move to SAFE")
        self.preset_safe_btn.setEnabled(False)
        self.preset_safe_btn.clicked.connect(lambda: self.on_preset_move_clicked('safe'))
        quick_layout.addWidget(self.preset_safe_btn)

        self.preset_vertical_btn = QPushButton("Move to VERTICAL")
        self.preset_vertical_btn.setEnabled(False)
        self.preset_vertical_btn.clicked.connect(lambda: self.on_preset_move_clicked('vertical'))
        quick_layout.addWidget(self.preset_vertical_btn)

        quick_group.setLayout(quick_layout)
        layout.addWidget(quick_group)

        # Save current position
        save_group = QGroupBox("Save Current Position")
        save_layout = QHBoxLayout()
        save_layout.addWidget(QLabel("Name:"))
        self.preset_name_input = QLineEdit()
        self.preset_name_input.setPlaceholderText("Enter position name")
        save_layout.addWidget(self.preset_name_input)
        self.save_preset_btn = QPushButton("Save")
        self.save_preset_btn.setEnabled(False)
        self.save_preset_btn.clicked.connect(self.on_save_preset_clicked)
        save_layout.addWidget(self.save_preset_btn)
        save_group.setLayout(save_layout)
        layout.addWidget(save_group)

        # Preset list
        list_group = QGroupBox("Saved Positions")
        list_layout = QVBoxLayout()
        self.preset_list = QListWidget()
        self.update_preset_list()
        list_layout.addWidget(self.preset_list)

        # List control buttons
        list_btn_layout = QHBoxLayout()
        self.load_preset_btn = QPushButton("Load")
        self.load_preset_btn.setEnabled(False)
        self.load_preset_btn.clicked.connect(self.on_load_preset_clicked)
        list_btn_layout.addWidget(self.load_preset_btn)

        self.delete_preset_btn = QPushButton("Delete")
        self.delete_preset_btn.clicked.connect(self.on_delete_preset_clicked)
        list_btn_layout.addWidget(self.delete_preset_btn)

        list_layout.addLayout(list_btn_layout)
        list_group.setLayout(list_layout)
        layout.addWidget(list_group)

        layout.addStretch()

        return tab

    # ========================================
    # Script Execution Tab
    # ========================================

    def create_script_execution_tab(self) -> QWidget:
        """Create script execution tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Script list
        list_group = QGroupBox("Available Scripts")
        list_layout = QVBoxLayout()

        self.script_list = QListWidget()
        self.refresh_script_list()
        list_layout.addWidget(self.script_list)

        # Refresh button
        refresh_btn = QPushButton("Refresh List")
        refresh_btn.clicked.connect(self.refresh_script_list)
        list_layout.addWidget(refresh_btn)

        list_group.setLayout(list_layout)
        layout.addWidget(list_group)

        # Execution control
        exec_group = QGroupBox("Execution Control")
        exec_layout = QVBoxLayout()

        self.execute_script_btn = QPushButton("Execute Selected Script")
        self.execute_script_btn.setEnabled(False)
        self.execute_script_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 10px; }")
        self.execute_script_btn.clicked.connect(self.on_execute_script_clicked)
        exec_layout.addWidget(self.execute_script_btn)

        self.stop_script_btn = QPushButton("Stop Script")
        self.stop_script_btn.setEnabled(False)
        self.stop_script_btn.setStyleSheet("QPushButton { background-color: #f44336; color: white; font-weight: bold; padding: 10px; }")
        self.stop_script_btn.clicked.connect(self.on_stop_script_clicked)
        exec_layout.addWidget(self.stop_script_btn)

        self.script_status_label = QLabel("Status: No script running")
        self.script_status_label.setAlignment(Qt.AlignCenter)
        exec_layout.addWidget(self.script_status_label)

        exec_group.setLayout(exec_layout)
        layout.addWidget(exec_group)

        layout.addStretch()

        return tab

    # ========================================
    # Page Widgets (for page switching)
    # ========================================

    def create_sequential_controller_page(self) -> QWidget:
        """Create Sequential Controller page"""
        # Create sequential controller page widget with new UI improvements
        from sequential_controller_ui_page import SequentialControllerPageWidget

        page = SequentialControllerPageWidget(self.sequential_controller, self)
        return page

    def create_basic_page(self) -> QWidget:
        """Create simplified Basic page - two-column layout"""
        page = QWidget()
        main_layout = QHBoxLayout(page)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # LEFT COLUMN: Status information
        left_column = QWidget()
        left_layout = QVBoxLayout(left_column)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(15)

        # Connection controls
        connection_section = self.create_connection_section()
        left_layout.addWidget(connection_section)

        # Robot status overview
        status_overview = self.create_status_overview_section()
        left_layout.addWidget(status_overview)

        # Safety status (moved below robot status)
        safety_status = self.create_safety_status_panel()
        left_layout.addWidget(safety_status)

        left_layout.addStretch()

        main_layout.addWidget(left_column, 1)

        # RIGHT COLUMN: Controls and messages
        right_column = QWidget()
        right_layout = QVBoxLayout(right_column)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(15)

        # Quick controls
        quick_controls_section = self.create_quick_controls_section()
        right_layout.addWidget(quick_controls_section)

        # System Messages Log (moved here for more vertical space)
        log_display = self.create_log_display()
        right_layout.addWidget(log_display, 1)

        main_layout.addWidget(right_column, 1)

        return page

    def create_status_overview_section(self) -> QGroupBox:
        """Create simplified status overview for Basic page"""
        group = QGroupBox("Robot Status Overview")
        layout = QVBoxLayout()

        # Connection status
        conn_layout = QHBoxLayout()
        conn_layout.addWidget(QLabel("Connection:"))
        self.status_connection_label = QLabel("Disconnected")
        self.status_connection_label.setStyleSheet("QLabel { background-color: #f44336; color: white; padding: 5px; font-weight: bold; border-radius: 3px; }")
        conn_layout.addWidget(self.status_connection_label)
        conn_layout.addStretch()
        layout.addLayout(conn_layout)

        # Robot mode
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Robot Mode:"))
        self.status_mode_label = QLabel("Unknown")
        self.status_mode_label.setStyleSheet("QLabel { background-color: #9E9E9E; color: white; padding: 5px; font-weight: bold; border-radius: 3px; }")
        mode_layout.addWidget(self.status_mode_label)
        mode_layout.addStretch()
        layout.addLayout(mode_layout)

        # Current position (simplified)
        pos_layout = QHBoxLayout()
        pos_layout.addWidget(QLabel("TCP Position:"))
        self.status_tcp_label = QLabel("X: -, Y: -, Z: -")
        self.status_tcp_label.setStyleSheet("QLabel { background-color: #f0f0f0; padding: 5px; font-family: monospace; }")
        pos_layout.addWidget(self.status_tcp_label)
        pos_layout.addStretch()
        layout.addLayout(pos_layout)

        # Current force (simplified)
        force_layout = QHBoxLayout()
        force_layout.addWidget(QLabel("Force Magnitude:"))
        self.status_force_label = QLabel("0.0 N")
        self.status_force_label.setStyleSheet("QLabel { background-color: #f0f0f0; padding: 5px; font-family: monospace; }")
        force_layout.addWidget(self.status_force_label)
        force_layout.addStretch()
        layout.addLayout(force_layout)

        layout.addStretch()

        group.setLayout(layout)
        return group

    def create_quick_controls_section(self) -> QGroupBox:
        """Create quick control buttons section for Basic page"""
        group = QGroupBox("Quick Controls")
        layout = QVBoxLayout()

        # Freedrive section
        freedrive_group = self.create_freedrive_section()
        layout.addWidget(freedrive_group)

        # Emergency stop button
        emergency_btn = self.create_emergency_stop_button()
        layout.addWidget(emergency_btn)

        # Recover button
        recover_btn = self.create_unlock_robot_button()
        layout.addWidget(recover_btn)

        layout.addStretch()

        group.setLayout(layout)
        return group

    def create_movement_page(self) -> QWidget:
        """Create Movement page with controls, TCP chart, and detailed pose display"""
        page = QWidget()
        main_layout = QHBoxLayout(page)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Left side: Movement controls
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # Movement controls (scrollable)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        movement_content = self.create_movement_control_tab()
        scroll_area.setWidget(movement_content)
        left_layout.addWidget(scroll_area)

        main_layout.addWidget(left_panel, 2)

        # Right side: TCP visualization
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        # Detailed TCP Pose display
        tcp_pose_group = self.create_tcp_display()
        right_layout.addWidget(tcp_pose_group)

        # Joint angles display
        joint_group = self.create_joint_display()
        right_layout.addWidget(joint_group)

        # TCP Position Chart
        tcp_chart_group = QGroupBox("TCP Position History")
        tcp_chart_layout = QVBoxLayout()

        # Chart controls
        chart_control_layout = QHBoxLayout()
        self.movement_pause_chart_btn = QPushButton("Pause Chart")
        self.movement_pause_chart_btn.clicked.connect(self.on_pause_charts)
        chart_control_layout.addWidget(self.movement_pause_chart_btn)

        movement_clear_chart_btn = QPushButton("Clear Chart")
        movement_clear_chart_btn.clicked.connect(self.on_clear_charts)
        chart_control_layout.addWidget(movement_clear_chart_btn)
        chart_control_layout.addStretch()
        tcp_chart_layout.addLayout(chart_control_layout)

        # Create TCP position plot
        self.tcp_plot_widget = pg.PlotWidget(title="TCP Position (X, Y, Z)")
        self.tcp_plot_widget.setLabel('left', 'Position', units='m')
        self.tcp_plot_widget.setLabel('bottom', 'Time', units='s')
        self.tcp_plot_widget.addLegend()
        self.tcp_plot_widget.showGrid(x=True, y=True, alpha=0.3)

        # Create plot lines
        self.tcp_x_curve = self.tcp_plot_widget.plot(pen=pg.mkPen(color='r', width=2), name='X')
        self.tcp_y_curve = self.tcp_plot_widget.plot(pen=pg.mkPen(color='g', width=2), name='Y')
        self.tcp_z_curve = self.tcp_plot_widget.plot(pen=pg.mkPen(color='b', width=2), name='Z')

        tcp_chart_layout.addWidget(self.tcp_plot_widget)
        tcp_chart_group.setLayout(tcp_chart_layout)
        right_layout.addWidget(tcp_chart_group)

        main_layout.addWidget(right_panel, 3)

        return page

    def create_data_recording_section(self) -> QGroupBox:
        """Create data recording control section (moved from dock widget)"""
        group = QGroupBox("Data Recording")
        layout = QVBoxLayout()

        # Session name input
        session_layout = QHBoxLayout()
        session_layout.addWidget(QLabel("Session Name:"))
        self.session_name_input = QLineEdit()
        self.session_name_input.setPlaceholderText("Optional session name")
        session_layout.addWidget(self.session_name_input)
        layout.addLayout(session_layout)

        # Start/Stop recording buttons
        self.start_recording_btn = QPushButton("Start Recording")
        self.start_recording_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 8px; }")
        self.start_recording_btn.clicked.connect(self.on_start_recording)
        layout.addWidget(self.start_recording_btn)

        self.stop_recording_btn = QPushButton("Stop Recording")
        self.stop_recording_btn.setStyleSheet("QPushButton { background-color: #f44336; color: white; font-weight: bold; padding: 8px; }")
        self.stop_recording_btn.setEnabled(False)
        self.stop_recording_btn.clicked.connect(self.on_stop_recording)
        layout.addWidget(self.stop_recording_btn)

        # Recording status
        self.recording_status_label = QLabel("Status: Not Recording")
        self.recording_status_label.setStyleSheet("QLabel { background-color: #f0f0f0; padding: 5px; border-radius: 3px; }")
        layout.addWidget(self.recording_status_label)

        # Buffer status
        self.buffer_status_label = QLabel("Buffer: 0 / 0 points")
        self.buffer_status_label.setStyleSheet("QLabel { font-size: 10px; color: #666; }")
        layout.addWidget(self.buffer_status_label)

        group.setLayout(layout)
        return group

    def create_presets_page(self) -> QWidget:
        """Create Presets page"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(15, 15, 15, 15)

        # Use the existing preset positions tab content
        presets_content = self.create_preset_positions_tab()
        layout.addWidget(presets_content)

        return page

    def create_scripts_page(self) -> QWidget:
        """Create Scripts page"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(15, 15, 15, 15)

        # Use the existing script execution tab content
        scripts_content = self.create_script_execution_tab()
        layout.addWidget(scripts_content)

        return page

    # ========================================
    # Monitor Panel
    # ========================================

    def create_tcp_display(self) -> QGroupBox:
        """Create TCP pose display with orientation visualization"""
        group = QGroupBox("TCP Pose")
        main_layout = QVBoxLayout()

        # Position and rotation values
        values_layout = QGridLayout()

        labels = ['X (m):', 'Y (m):', 'Z (m):', 'Rx (rad):', 'Ry (rad):', 'Rz (rad):']
        self.tcp_labels = []

        for i, label_text in enumerate(labels):
            row = i // 3
            col = (i % 3) * 2

            values_layout.addWidget(QLabel(label_text), row, col)

            value_label = QLabel("0.000")
            value_label.setStyleSheet("QLabel { background-color: #f0f0f0; padding: 5px; font-family: monospace; }")
            value_label.setMinimumWidth(100)
            values_layout.addWidget(value_label, row, col + 1)

            self.tcp_labels.append(value_label)

        main_layout.addLayout(values_layout)

        # Orientation in degrees
        orientation_layout = QHBoxLayout()
        orientation_layout.addWidget(QLabel("Orientation (deg):"))

        self.tcp_roll_deg_label = QLabel("Roll: 0.0°")
        self.tcp_roll_deg_label.setStyleSheet("QLabel { background-color: #e3f2fd; padding: 3px; font-family: monospace; font-weight: bold; }")
        orientation_layout.addWidget(self.tcp_roll_deg_label)

        self.tcp_pitch_deg_label = QLabel("Pitch: 0.0°")
        self.tcp_pitch_deg_label.setStyleSheet("QLabel { background-color: #e3f2fd; padding: 3px; font-family: monospace; font-weight: bold; }")
        orientation_layout.addWidget(self.tcp_pitch_deg_label)

        self.tcp_yaw_deg_label = QLabel("Yaw: 0.0°")
        self.tcp_yaw_deg_label.setStyleSheet("QLabel { background-color: #e3f2fd; padding: 3px; font-family: monospace; font-weight: bold; }")
        orientation_layout.addWidget(self.tcp_yaw_deg_label)

        main_layout.addLayout(orientation_layout)

        # Horizontal indicator
        horizontal_layout = QHBoxLayout()
        horizontal_layout.addWidget(QLabel("TCP Level:"))

        self.tcp_horizontal_indicator = QLabel("⬤ Checking...")
        self.tcp_horizontal_indicator.setStyleSheet("QLabel { font-size: 14px; padding: 3px; }")
        horizontal_layout.addWidget(self.tcp_horizontal_indicator)
        horizontal_layout.addStretch()

        main_layout.addLayout(horizontal_layout)

        # TCP Orientation Visualization Widget
        self.tcp_orientation_widget = TCPOrientationWidget()
        main_layout.addWidget(self.tcp_orientation_widget)

        group.setLayout(main_layout)
        return group

    def create_joint_display(self) -> QGroupBox:
        """Create joint angle display"""
        group = QGroupBox("Joint Angles")
        layout = QGridLayout()

        self.joint_labels = []

        for i in range(6):
            row = i // 3
            col = (i % 3) * 2

            layout.addWidget(QLabel(f"J{i+1} (rad):"), row, col)

            value_label = QLabel("0.000")
            value_label.setStyleSheet("QLabel { background-color: #f0f0f0; padding: 5px; font-family: monospace; }")
            value_label.setMinimumWidth(100)
            layout.addWidget(value_label, row, col + 1)

            self.joint_labels.append(value_label)

        group.setLayout(layout)
        return group

    def create_safety_status_panel(self) -> QGroupBox:
        """Create safety monitoring status panel (NEW - Stage 4)"""
        group = QGroupBox("Safety Status")
        layout = QVBoxLayout()

        # Workspace status
        self.workspace_status_label = QLabel("● Workspace: OK")
        self.workspace_status_label.setStyleSheet(
            "QLabel { background-color: #4CAF50; color: white; padding: 8px; font-weight: bold; border-radius: 4px; }"
        )
        self.workspace_status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.workspace_status_label)

        # Force status (safety monitoring, separate from the force mode state)
        self.force_safety_label = QLabel("● Forces: OK")
        self.force_safety_label.setStyleSheet(
            "QLabel { background-color: #4CAF50; color: white; padding: 8px; font-weight: bold; border-radius: 4px; }"
        )
        self.force_safety_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.force_safety_label)

        # Collision status
        self.collision_status_label = QLabel("● Collision: None")
        self.collision_status_label.setStyleSheet(
            "QLabel { background-color: #4CAF50; color: white; padding: 8px; font-weight: bold; border-radius: 4px; }"
        )
        self.collision_status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.collision_status_label)

        group.setLayout(layout)
        return group

    def create_log_display(self) -> QGroupBox:
        """Create log display"""
        group = QGroupBox("System Messages")
        layout = QVBoxLayout()

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        # Removed maximum height constraint - let it expand vertically to fill available space
        self.log_text.setMinimumHeight(300)  # Set minimum height for better visibility
        self.log_text.setStyleSheet("QTextEdit { background-color: #2b2b2b; color: #f0f0f0; font-family: monospace; }")
        layout.addWidget(self.log_text)

        # Clear log button
        clear_button = QPushButton("Clear Log")
        clear_button.clicked.connect(self.log_text.clear)
        layout.addWidget(clear_button)

        group.setLayout(layout)
        return group

    # ========================================
    # Charts Panel (NEW IN STAGE 3)
    # ========================================

    def create_status_bar(self):
        """Create status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready - Stage 3 (Data Logging & Visualization)")

    # ========================================
    # Signal/Slot Connections
    # ========================================

    def connect_signals(self):
        """Connect signals and slots"""
        # Basic control buttons
        self.connect_button.clicked.connect(self.on_connect_clicked)
        self.disconnect_button.clicked.connect(self.on_disconnect_clicked)
        self.freedrive_enable_button.clicked.connect(self.on_freedrive_enable_clicked)
        self.freedrive_disable_button.clicked.connect(self.on_freedrive_disable_clicked)
        self.emergency_stop_button.clicked.connect(self.on_emergency_stop_clicked)
        self.unlock_robot_button.clicked.connect(self.on_unlock_robot_clicked)

        # TCP control buttons - continuous movement (press and hold)
        self.tcp_x_minus.pressed.connect(lambda: self.on_tcp_move_pressed('x', -1))
        self.tcp_x_minus.released.connect(self.on_tcp_move_released)
        self.tcp_x_plus.pressed.connect(lambda: self.on_tcp_move_pressed('x', 1))
        self.tcp_x_plus.released.connect(self.on_tcp_move_released)

        self.tcp_y_minus.pressed.connect(lambda: self.on_tcp_move_pressed('y', -1))
        self.tcp_y_minus.released.connect(self.on_tcp_move_released)
        self.tcp_y_plus.pressed.connect(lambda: self.on_tcp_move_pressed('y', 1))
        self.tcp_y_plus.released.connect(self.on_tcp_move_released)

        self.tcp_z_minus.pressed.connect(lambda: self.on_tcp_move_pressed('z', -1))
        self.tcp_z_minus.released.connect(self.on_tcp_move_released)
        self.tcp_z_plus.pressed.connect(lambda: self.on_tcp_move_pressed('z', 1))
        self.tcp_z_plus.released.connect(self.on_tcp_move_released)

        self.tcp_rx_minus.pressed.connect(lambda: self.on_tcp_move_pressed('rx', -1))
        self.tcp_rx_minus.released.connect(self.on_tcp_move_released)
        self.tcp_rx_plus.pressed.connect(lambda: self.on_tcp_move_pressed('rx', 1))
        self.tcp_rx_plus.released.connect(self.on_tcp_move_released)

        self.tcp_ry_minus.pressed.connect(lambda: self.on_tcp_move_pressed('ry', -1))
        self.tcp_ry_minus.released.connect(self.on_tcp_move_released)
        self.tcp_ry_plus.pressed.connect(lambda: self.on_tcp_move_pressed('ry', 1))
        self.tcp_ry_plus.released.connect(self.on_tcp_move_released)

        self.tcp_rz_minus.pressed.connect(lambda: self.on_tcp_move_pressed('rz', -1))
        self.tcp_rz_minus.released.connect(self.on_tcp_move_released)
        self.tcp_rz_plus.pressed.connect(lambda: self.on_tcp_move_pressed('rz', 1))
        self.tcp_rz_plus.released.connect(self.on_tcp_move_released)

        # Robot controller signals
        self.robot_controller.tcp_pose_updated.connect(self.update_tcp_display)
        self.robot_controller.joint_positions_updated.connect(self.update_joint_display)
        self.robot_controller.connection_status_changed.connect(self.on_connection_status_changed)
        self.robot_controller.error_occurred.connect(self.show_error_message)
        self.robot_controller.info_message.connect(self.show_info_message)

        # Connect robot controller signals to data logger
        self.robot_controller.tcp_pose_updated.connect(self.on_data_received_for_logging)
        self.robot_controller.joint_positions_updated.connect(self.on_joint_data_received)
        self.robot_controller.force_data_updated.connect(self.on_force_data_received)

        # Data logger signals
        self.data_logger.recording_started.connect(self.on_recording_started_signal)
        self.data_logger.recording_stopped.connect(self.on_recording_stopped_signal)
        self.data_logger.buffer_size_changed.connect(self.on_buffer_size_changed)

        # Safety monitor signals (NEW - Stage 4)
        self.robot_controller.safety_monitor.workspace_warning.connect(self.on_workspace_warning)
        self.robot_controller.safety_monitor.workspace_violation.connect(self.on_workspace_violation)
        self.robot_controller.safety_monitor.force_warning.connect(self.on_force_warning)
        self.robot_controller.safety_monitor.force_violation.connect(self.on_force_violation)
        self.robot_controller.safety_monitor.collision_detected.connect(self.on_collision_detected)

        # Robot safety status signal (for protective stop detection)
        self.robot_controller.safety_status_changed.connect(self.on_safety_status_changed)

        # Force mode state
        self.robot_controller.force_mode_changed.connect(self.force_page.set_mode_state)
        self.robot_controller.force_mode_timeout.connect(self.force_page.on_mode_timeout)

        # Connect trajectory replay signals
        self.robot_controller.trajectory_replay_started.connect(self.on_trajectory_replay_started)
        self.robot_controller.trajectory_replay_progress.connect(self.on_trajectory_replay_progress)
        self.robot_controller.trajectory_replay_completed.connect(self.on_trajectory_replay_completed)
        self.robot_controller.trajectory_replay_paused.connect(self.on_trajectory_replay_paused)

    # ========================================
    # Event Handlers - Basic Control
    # ========================================

    def on_connect_clicked(self):
        """Connection button clicked"""
        ip = self.ip_input.text().strip()
        port_text = self.port_input.text().strip()

        # Validate input
        if not ip:
            QMessageBox.warning(self, "Input Error", "Please enter IP address")
            return

        try:
            port = int(port_text)
            if not (1 <= port <= 65535):
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Please enter valid port (1-65535)")
            return

        # Attempt connection
        self.show_info_message(f"Connecting to {ip}:{port}...")
        success = self.robot_controller.connect(ip, port)

        if not success:
            QMessageBox.critical(self, "Connection Failed", f"Unable to connect to robot at {ip}:{port}")

    def on_disconnect_clicked(self):
        """Disconnect button clicked"""
        self.robot_controller.disconnect()

    def on_freedrive_enable_clicked(self):
        """Enable freedrive button clicked"""
        reply = QMessageBox.question(
            self,
            "Confirm",
            "Are you sure you want to enable freedrive mode?\nThe robot can be moved manually.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if self.robot_controller.enable_freedrive():
                self.freedrive_status_label.setText("Status: Active")
                self.freedrive_status_label.setStyleSheet("QLabel { color: green; font-weight: bold; }")
                self.freedrive_enable_button.setEnabled(False)
                # Change disable button to active orange color
                self.freedrive_disable_button.setStyleSheet("QPushButton { background-color: #FF9800; color: white; font-weight: bold; padding: 10px; }")
                self.freedrive_disable_button.setEnabled(True)

    def on_freedrive_disable_clicked(self):
        """Disable freedrive button clicked"""
        if self.robot_controller.disable_freedrive():
            self.freedrive_status_label.setText("Status: Inactive")
            self.freedrive_status_label.setStyleSheet("QLabel { color: black; }")
            # Reset enable button to active blue color
            self.freedrive_enable_button.setStyleSheet("QPushButton { background-color: #2196F3; color: white; font-weight: bold; padding: 10px; }")
            self.freedrive_enable_button.setEnabled(True)
            # Disable button to gray
            self.freedrive_disable_button.setStyleSheet("QPushButton:disabled { background-color: #bdbdbd; color: #757575; }")
            self.freedrive_disable_button.setEnabled(False)

    def on_emergency_stop_clicked(self):
        """Emergency stop button clicked"""
        reply = QMessageBox.critical(
            self,
            "Emergency Stop Confirmation",
            "Are you sure you want to execute emergency stop?\nThe robot will immediately stop all motion.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.robot_controller.emergency_stop()
            QMessageBox.information(self, "Emergency Stop",
                                   "Emergency stop executed (software stop).\n\n"
                                   "Robot motion has been stopped.\n"
                                   "Click '🔓 RECOVER ROBOT' to unlock and resume.")

    def on_unlock_robot_clicked(self):
        """Unlock robot button clicked"""
        result = self.robot_controller.unlock_protective_stop()
        if result:
            # Reset safety indicators to OK state
            self._reset_safety_indicators()

            # Clear active warnings in safety monitor
            self.robot_controller.safety_monitor.clear_warnings()

            # Update safety status to safe
            self.robot_controller.safety_monitor._update_safety_status(True)

            QMessageBox.information(self, "Robot Unlocked",
                                   "Unlock successful!\n\n"
                                   "✓ Protective stop released\n"
                                   "✓ Safety popup closed\n"
                                   "✓ Safety indicators reset\n\n"
                                   "Robot is ready to move.")

            self.show_info_message("Recovery complete - all safety indicators reset")
        else:
            QMessageBox.warning(self, "Unlock Failed",
                               "Failed to unlock robot.\n\n"
                               "Check:\n"
                               "• Robot connection\n"
                               "• Robot is in Remote Control mode\n"
                               "• Try power cycling robot if issue persists")

    # ========================================
    # Event Handlers - TCP Control
    # ========================================

    def on_tcp_move_pressed(self, axis: str, direction: int):
        """TCP movement button pressed - start smooth continuous velocity control"""
        # Get velocity from speed setting
        speed = self.tcp_speed_spin.value()
        accel = self.tcp_accel_spin.value()

        # Calculate velocity vector (speed * direction)
        velocity = speed * direction

        # Map axis to velocity parameters
        velocity_params = {
            'x': (velocity, 0, 0, 0, 0, 0),
            'y': (0, velocity, 0, 0, 0, 0),
            'z': (0, 0, velocity, 0, 0, 0),
            'rx': (0, 0, 0, velocity, 0, 0),
            'ry': (0, 0, 0, 0, velocity, 0),
            'rz': (0, 0, 0, 0, 0, velocity)
        }

        if axis in velocity_params:
            vx, vy, vz, vrx, vry, vrz = velocity_params[axis]
            self.robot_controller.start_tcp_velocity_mode(vx, vy, vz, vrx, vry, vrz, accel)

    def on_tcp_move_released(self):
        """TCP movement button released - stop velocity smoothly"""
        accel = self.tcp_accel_spin.value()
        self.robot_controller.stop_tcp_velocity_mode(accel)

    def on_continuous_move_tick(self):
        """Legacy method - no longer used with velocity control"""
        pass

    # ========================================
    # Event Handlers - Joint Control
    # ========================================

    def on_joint_move_pressed(self, joint: int, direction: int):
        """Joint movement button pressed - start smooth continuous velocity control"""
        # Get velocity from speed setting
        speed = self.joint_speed_spin.value()
        accel = self.joint_accel_spin.value()

        # Calculate velocity (speed * direction)
        velocity = speed * direction

        # Create velocity array (all zeros except the active joint)
        velocities = [0.0] * 6
        velocities[joint] = velocity

        # Start continuous velocity control
        self.robot_controller.start_joint_velocity_mode(*velocities, accel=accel)

    def on_joint_move_released(self):
        """Joint movement button released - stop velocity smoothly"""
        accel = self.joint_accel_spin.value()
        self.robot_controller.stop_joint_velocity_mode(accel)

    # ========================================
    # Event Handlers - Preset Positions
    # ========================================

    def on_preset_move_clicked(self, position_name: str):
        """Preset position button clicked"""
        reply = QMessageBox.question(
            self,
            "Confirm Movement",
            f"Move robot to '{position_name}' position?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.robot_controller.move_to_preset_position(position_name)

    def on_save_preset_clicked(self):
        """Save preset button clicked"""
        name = self.preset_name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Input Error", "Please enter a position name")
            return

        # Get current joint positions
        joints = self.robot_controller.get_joint_positions()
        if joints is None:
            QMessageBox.warning(self, "Error", "Cannot read current position")
            return

        preset_manager = getattr(self, "preset_manager", None)
        if not preset_manager:
            QMessageBox.warning(self, "Error", "Preset manager unavailable")
            return

        preset = PresetData(
            name=name,
            joints=joints,
            description="User defined position",
            category=PresetCategory.USER
        )

        if preset_manager.add_preset(preset):
            self.show_info_message(f"Position '{name}' saved")
            self.update_preset_list()
            self.preset_name_input.clear()
        else:
            QMessageBox.warning(self, "Error", "Failed to save position")

    def on_load_preset_clicked(self):
        """Load preset button clicked"""
        current_item = self.preset_list.currentItem()
        if current_item:
            position_name = current_item.data(Qt.UserRole) or current_item.text()
            self.on_preset_move_clicked(position_name)

    def on_delete_preset_clicked(self):
        """Delete preset button clicked"""
        current_item = self.preset_list.currentItem()
        if not current_item:
            return

        position_name = current_item.data(Qt.UserRole) or current_item.text()

        preset_manager = getattr(self, "preset_manager", None)
        preset = preset_manager.get_preset(position_name) if preset_manager else None

        # Don't allow deletion of locked/system positions
        if preset and preset.locked:
            QMessageBox.warning(self, "Cannot Delete", "Cannot delete default positions")
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete position '{position_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if preset_manager and preset_manager.delete_preset(position_name):
                self.show_info_message(f"Position '{position_name}' deleted")
                self.update_preset_list()

    def update_preset_list(self):
        """Update preset position list"""
        self.preset_list.clear()
        preset_manager = getattr(self, "preset_manager", None)
        if not preset_manager:
            for name in Config.PRESET_POSITIONS.keys():
                self.preset_list.addItem(name)
            return

        presets = preset_manager.list_presets()
        for preset in presets:
            display_text = f"{preset.icon} {preset.name}" if getattr(preset, "icon", None) else preset.name
            item = QListWidgetItem(display_text)
            item.setData(Qt.UserRole, preset.name)
            self.preset_list.addItem(item)

    # ========================================
    # Event Handlers - Script Execution
    # ========================================

    def refresh_script_list(self):
        """Refresh script list"""
        self.script_list.clear()
        scripts = list_scripts(Config.SCRIPTS_DIR)
        for script_path in scripts:
            # Get filename only
            import os
            filename = os.path.basename(script_path)
            self.script_list.addItem(filename)

    def on_execute_script_clicked(self):
        """Execute script button clicked"""
        current_item = self.script_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select a script to execute")
            return

        script_name = current_item.text()
        script_path = f"{Config.SCRIPTS_DIR}/{script_name}"

        reply = QMessageBox.question(
            self,
            "Confirm Execution",
            f"Execute script '{script_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if self.robot_controller.execute_script(script_path):
                self.script_status_label.setText(f"Status: Running {script_name}")
                self.script_status_label.setStyleSheet("QLabel { color: green; font-weight: bold; }")
                self.execute_script_btn.setEnabled(False)
                self.stop_script_btn.setEnabled(True)

    def on_stop_script_clicked(self):
        """Stop script button clicked"""
        if self.robot_controller.stop_script():
            self.script_status_label.setText("Status: No script running")
            self.script_status_label.setStyleSheet("QLabel { color: black; }")
            self.execute_script_btn.setEnabled(True)
            self.stop_script_btn.setEnabled(False)

    # ========================================
    # Event Handlers - Data Logging (NEW STAGE 3)
    # ========================================

    # Storage for the most recent data (for combining into DataPoint)
    def __init_data_storage(self):
        """Initialize data storage for logging"""
        self.latest_tcp_pose = [0.0] * 6
        self.latest_joint_pos = [0.0] * 6
        self.latest_forces = [0.0] * 6

    def on_data_received_for_logging(self, tcp_pose: list):
        """TCP pose data received - store for logging"""
        self.latest_tcp_pose = tcp_pose
        self._try_log_data_point()

        # Update chart data
        if not self.charts_paused:
            self.chart_update_counter += 1
            if self.chart_update_counter >= self.chart_update_interval:
                self.update_charts(tcp_pose, None, None)
                self.chart_update_counter = 0

    def on_joint_data_received(self, joint_pos: list):
        """Joint data received - store for logging"""
        self.latest_joint_pos = joint_pos

    def on_force_data_received(self, forces: list):
        """Force data received - store for logging and update the force page"""
        self.latest_forces = forces
        self.force_page.on_force_data(forces)

        if len(forces) >= 3:
            magnitude = math.sqrt(forces[0] ** 2 + forces[1] ** 2 + forces[2] ** 2)
            self.status_force_label.setText(f"{magnitude:.1f} N")

    def _try_log_data_point(self):
        """Try to log a complete data point to the logger"""
        if self.data_logger.is_recording and not self.data_logger.is_paused:
            timestamp = time.time()
            self.data_logger.add_data_point(
                timestamp,
                self.latest_tcp_pose,
                self.latest_joint_pos,
                self.latest_forces
            )

    def on_start_recording(self):
        """Start recording button clicked"""
        session_name = self.session_name_input.text().strip()
        if not session_name:
            session_name = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        if self.data_logger.start_recording(session_name=session_name):
            self.start_recording_btn.setEnabled(False)
            self.stop_recording_btn.setEnabled(True)
            self.pause_recording_btn.setEnabled(True)
            self.show_info_message(f"Recording started: {session_name}")

    def on_stop_recording(self):
        """Stop recording button clicked"""
        save_format = self.export_format_combo.currentText().lower()
        saved_file = self.data_logger.stop_recording(auto_save=True, save_format=save_format)

        self.start_recording_btn.setEnabled(True)
        self.stop_recording_btn.setEnabled(False)
        self.pause_recording_btn.setEnabled(False)

        if saved_file:
            self.show_info_message(f"Recording stopped and saved: {saved_file}")
            QMessageBox.information(self, "Recording Saved", f"Data saved to:\n{saved_file}")

    def on_pause_recording(self):
        """Pause/resume recording button clicked"""
        if self.data_logger.is_paused:
            self.data_logger.resume_recording()
            self.pause_recording_btn.setText("Pause Recording")
            self.show_info_message("Recording resumed")
        else:
            self.data_logger.pause_recording()
            self.pause_recording_btn.setText("Resume Recording")
            self.show_info_message("Recording paused")

    def update_recording_status(self):
        """Update recording status display (called by timer)"""
        if self.data_logger.is_recording:
            duration = self.data_logger.get_recording_duration()

            status_text = "Recording"
            if self.data_logger.is_paused:
                status_text += " (Paused)"

            self.recording_status_label.setText(f"Status: {status_text} ({duration:.1f} s)")
            self.recording_status_label.setStyleSheet("QLabel { padding: 5px; background-color: #4CAF50; color: white; font-weight: bold; border-radius: 3px; }")
        else:
            self.recording_status_label.setText("Status: Not Recording")
            self.recording_status_label.setStyleSheet("QLabel { padding: 5px; background-color: #f0f0f0; border-radius: 3px; }")

    def on_recording_started_signal(self):
        """Data logger emitted recording started signal"""
        logger.info("Data recording started")

    def on_recording_stopped_signal(self, filename: str):
        """Data logger emitted recording stopped signal"""
        logger.info(f"Data recording stopped: {filename}")

    def on_buffer_size_changed(self, current_size: int, max_size: int):
        """Buffer size changed"""
        self.buffer_status_label.setText(f"Buffer: {current_size} / {max_size} points")

    def on_load_trajectory(self):
        """Load trajectory button clicked"""
        # Open file dialog
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Load Trajectory",
            Config.LOGS_DIR,
            "CSV Files (*.csv);;HDF5 Files (*.h5 *.hdf5);;All Files (*)"
        )

        if not filename:
            return

        # Load the file
        success = False
        if filename.endswith('.csv'):
            success = self.data_logger.load_from_csv(filename)
        elif filename.endswith('.h5') or filename.endswith('.hdf5'):
            success = self.data_logger.load_from_hdf5(filename)
        else:
            QMessageBox.warning(self, "Invalid File", "Please select a CSV or HDF5 file")
            return

        if success:
            num_points = len(self.data_logger.data_buffer)
            self.replay_status_label.setText(f"Loaded: {num_points} points")
            self.replay_status_label.setStyleSheet("QLabel { padding: 5px; background-color: #4CAF50; color: white; font-weight: bold; }")
            self.replay_trajectory_btn.setEnabled(True)
            self.replay_progress_label.setText(f"Progress: 0 / {num_points}")
            self.show_info_message(f"Trajectory loaded: {num_points} points")
            QMessageBox.information(self, "Trajectory Loaded", f"Successfully loaded {num_points} trajectory points from:\n{filename}")
        else:
            self.replay_status_label.setText("Status: Load failed")
            self.replay_status_label.setStyleSheet("QLabel { padding: 5px; background-color: #f44336; color: white; font-weight: bold; }")
            QMessageBox.critical(self, "Load Failed", f"Failed to load trajectory from:\n{filename}")

    def on_replay_trajectory(self):
        """Replay trajectory button clicked"""
        if len(self.data_logger.data_buffer) == 0:
            QMessageBox.warning(self, "No Trajectory", "Please load a trajectory first")
            return

        # Confirm replay
        num_points = len(self.data_logger.data_buffer)
        reply = QMessageBox.question(
            self,
            "Replay Trajectory",
            f"Replay trajectory with {num_points} points?\n\nThe robot will move through the recorded positions.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Update button states
            self.replay_trajectory_btn.setEnabled(False)
            self.pause_trajectory_btn.setEnabled(True)
            self.resume_trajectory_btn.setEnabled(False)

            self.replay_status_label.setText("Status: Replaying...")
            self.replay_status_label.setStyleSheet("QLabel { padding: 5px; background-color: #FF9800; color: white; font-weight: bold; }")

            # Start replay in robot controller
            self.robot_controller.replay_trajectory(
                self.data_logger.data_buffer,
                use_joint_space=True
            )

    def on_trajectory_replay_started(self, total_points: int):
        """Trajectory replay started signal from robot controller"""
        logger.info(f"Trajectory replay started: {total_points} points")
        self.replay_progress_label.setText(f"Progress: 0 / {total_points}")
        # Ensure pause button is enabled
        self.pause_trajectory_btn.setEnabled(True)

    def on_trajectory_replay_progress(self, current: int, total: int):
        """Trajectory replay progress signal from robot controller"""
        self.replay_progress_label.setText(f"Progress: {current} / {total}")
        logger.debug(f"Replay progress: {current}/{total}")

    def on_trajectory_replay_completed(self, success: bool):
        """Trajectory replay completed signal from robot controller"""
        self.replay_trajectory_btn.setEnabled(True)
        self.pause_trajectory_btn.setEnabled(False)
        self.resume_trajectory_btn.setEnabled(False)

        if success:
            self.replay_status_label.setText("Status: Replay completed")
            self.replay_status_label.setStyleSheet("QLabel { padding: 5px; background-color: #4CAF50; color: white; font-weight: bold; }")
            self.show_info_message("Trajectory replay completed successfully")
            QMessageBox.information(self, "Replay Complete", "Trajectory replay completed successfully!")
        else:
            self.replay_status_label.setText("Status: Replay failed")
            self.replay_status_label.setStyleSheet("QLabel { padding: 5px; background-color: #f44336; color: white; font-weight: bold; }")
            QMessageBox.warning(self, "Replay Failed", "Trajectory replay failed. Check connection and robot status.")

    def on_trajectory_replay_paused(self, current_point: int, total_points: int):
        """Trajectory replay paused signal from robot controller"""
        logger.info(f"Trajectory replay paused at point {current_point}/{total_points}")
        self.replay_status_label.setText(f"Status: Paused at point {current_point}/{total_points}")
        self.replay_status_label.setStyleSheet("QLabel { padding: 5px; background-color: #FFC107; color: black; font-weight: bold; }")
        self.replay_progress_label.setText(f"Progress: {current_point} / {total_points} (Paused)")

        # Update button states
        self.replay_trajectory_btn.setEnabled(False)
        self.pause_trajectory_btn.setEnabled(False)
        self.resume_trajectory_btn.setEnabled(True)

        self.show_info_message(f"Trajectory replay paused at point {current_point}/{total_points}")

    def on_pause_trajectory(self):
        """Soft stop button clicked - pause trajectory replay"""
        logger.info("User requested trajectory replay pause")
        success = self.robot_controller.pause_trajectory_replay()

        if success:
            self.pause_trajectory_btn.setEnabled(False)
            self.show_info_message("Trajectory replay will pause at next point...")
        else:
            QMessageBox.warning(self, "Pause Failed", "Cannot pause: No trajectory replay in progress")

    def on_resume_trajectory(self):
        """Resume button clicked - resume trajectory replay from pause point"""
        logger.info("User requested trajectory replay resume")

        # Confirm resume
        reply = QMessageBox.question(
            self,
            "Resume Trajectory Replay",
            "Resume trajectory replay from pause point?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Update UI state
            self.resume_trajectory_btn.setEnabled(False)
            self.pause_trajectory_btn.setEnabled(True)
            self.replay_status_label.setText("Status: Resuming...")
            self.replay_status_label.setStyleSheet("QLabel { padding: 5px; background-color: #2196F3; color: white; font-weight: bold; }")

            # Start resume in separate thread to avoid blocking UI
            import threading
            resume_thread = threading.Thread(
                target=self.robot_controller.resume_trajectory_replay,
                daemon=True
            )
            resume_thread.start()

            self.show_info_message("Resuming trajectory replay...")

    # ========================================
    # Event Handlers - Charts (NEW STAGE 3)
    # ========================================

    def update_charts(self, tcp_pose=None, joint_pos=None, forces=None):
        """Update real-time charts with new data"""
        if self.charts_paused:
            return

        current_time = time.time()

        # Initialize start time if needed
        if not hasattr(self, 'chart_start_time'):
            self.chart_start_time = current_time

        relative_time = current_time - self.chart_start_time

        # Update TCP position data
        if tcp_pose and len(tcp_pose) >= 3:
            self.time_data.append(relative_time)
            self.tcp_x_data.append(tcp_pose[0])
            self.tcp_y_data.append(tcp_pose[1])
            self.tcp_z_data.append(tcp_pose[2])

            # Limit buffer size
            if len(self.time_data) > self.max_plot_points:
                self.time_data.pop(0)
            if len(self.tcp_x_data) > self.max_plot_points:
                self.tcp_x_data.pop(0)
                self.tcp_y_data.pop(0)
                self.tcp_z_data.pop(0)

            # Update TCP curves - ensure arrays have same length
            if len(self.time_data) > 1 and len(self.tcp_x_data) > 1:
                # Use the minimum length to ensure arrays match
                min_len = min(len(self.time_data), len(self.tcp_x_data))
                time_subset = self.time_data[-min_len:]
                tcp_x_subset = self.tcp_x_data[-min_len:]
                tcp_y_subset = self.tcp_y_data[-min_len:]
                tcp_z_subset = self.tcp_z_data[-min_len:]

                self.tcp_x_curve.setData(time_subset, tcp_x_subset)
                self.tcp_y_curve.setData(time_subset, tcp_y_subset)
                self.tcp_z_curve.setData(time_subset, tcp_z_subset)

    def on_pause_charts(self):
        """Pause/resume TCP chart updates"""
        self.charts_paused = not self.charts_paused

        if self.charts_paused:
            self.movement_pause_chart_btn.setText("Resume Chart")
            self.show_info_message("Chart updates paused")
        else:
            self.movement_pause_chart_btn.setText("Pause Chart")
            self.show_info_message("Chart updates resumed")

    def on_clear_charts(self):
        """Clear all chart data"""
        self.time_data.clear()
        self.tcp_x_data.clear()
        self.tcp_y_data.clear()
        self.tcp_z_data.clear()

        # Clear plots
        self.tcp_x_curve.setData([], [])
        self.tcp_y_curve.setData([], [])
        self.tcp_z_curve.setData([], [])
        self.force_page.clear_chart()

        # Reset start time
        if hasattr(self, 'chart_start_time'):
            delattr(self, 'chart_start_time')

        self.show_info_message("Charts cleared")

    # ========================================
    # Menu Action Handlers (NEW STAGE 3)
    # ========================================

    def on_save_configuration(self):
        """Save configuration menu action"""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Configuration",
            "",
            "JSON Files (*.json);;All Files (*)"
        )

        if filename:
            try:
                Config.save_config(filename)
                self.show_info_message(f"Configuration saved to {filename}")
                QMessageBox.information(self, "Success", "Configuration saved successfully")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save configuration:\n{str(e)}")

    def on_load_configuration(self):
        """Load configuration menu action"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Load Configuration",
            "",
            "JSON Files (*.json);;All Files (*)"
        )

        if filename:
            try:
                Config.load_config(filename)
                self.show_info_message(f"Configuration loaded from {filename}")
                QMessageBox.information(self, "Success", "Configuration loaded successfully")
                self.update_preset_list()  # Refresh presets
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load configuration:\n{str(e)}")

    def on_export_data(self):
        """Export data menu action"""
        if self.data_logger.get_buffer_size() == 0:
            QMessageBox.warning(self, "No Data", "No data available to export")
            return

        filename, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Data",
            "",
            "CSV Files (*.csv);;HDF5 Files (*.h5);;All Files (*)"
        )

        if filename:
            try:
                if 'CSV' in selected_filter or filename.endswith('.csv'):
                    success = self.data_logger.save_to_csv(filename)
                elif 'HDF5' in selected_filter or filename.endswith('.h5'):
                    success = self.data_logger.save_to_hdf5(filename)
                else:
                    # Default to CSV
                    if not filename.endswith('.csv'):
                        filename += '.csv'
                    success = self.data_logger.save_to_csv(filename)

                if success:
                    self.show_info_message(f"Data exported to {filename}")
                    QMessageBox.information(self, "Success", f"Data exported successfully to:\n{filename}")
                else:
                    QMessageBox.warning(self, "Export Failed", "Failed to export data")

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Export failed:\n{str(e)}")

    def on_export_summary(self):
        """Export summary report menu action"""
        if self.data_logger.get_buffer_size() == 0:
            QMessageBox.warning(self, "No Data", "No data available for summary")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Summary Report",
            "",
            "Text Files (*.txt);;All Files (*)"
        )

        if filename:
            try:
                success = self.data_logger.export_summary(filename)
                if success:
                    self.show_info_message(f"Summary exported to {filename}")
                    QMessageBox.information(self, "Success", f"Summary exported successfully to:\n{filename}")
                else:
                    QMessageBox.warning(self, "Export Failed", "Failed to export summary")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Export failed:\n{str(e)}")

    def on_refresh_ui(self):
        """Refresh UI (F5)"""
        self.update_preset_list()
        self.refresh_script_list()
        self.show_info_message("UI refreshed")

    def switch_to_page(self, page_index: int):
        """Switch to specified page in the stacked widget"""
        self.page_stack.setCurrentIndex(page_index)

        # Update navigation button states
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == page_index)

        # Update status bar
        page_names = ["Basic", "Programs", "Movement", "Force Mode", "Presets", "Scripts"]
        if 0 <= page_index < len(page_names):
            self.status_bar.showMessage(f"Switched to {page_names[page_index]}")

    def on_data_logger_settings(self):
        """Open data logger settings dialog"""
        QMessageBox.information(
            self,
            "Data Logger Settings",
            f"Current Settings:\n\n"
            f"Buffer Size: {self.data_logger.max_buffer_size} points\n"
            f"Current Buffer: {self.data_logger.get_buffer_size()} points\n"
            f"Recording: {'Yes' if self.data_logger.is_recording else 'No'}\n\n"
            f"Note: Settings dialog not yet implemented"
        )

    def on_script_manager(self):
        """Open script manager"""
        scripts_dir = Config.SCRIPTS_DIR
        scripts = list_scripts(scripts_dir)

        info_text = f"Script Directory: {scripts_dir}\n\n"
        info_text += f"Available Scripts ({len(scripts)}):\n"
        for script in scripts:
            info_text += f"  - {os.path.basename(script)}\n"

        QMessageBox.information(self, "Script Manager", info_text)

    def on_hand_guiding_tool(self):
        """Open Hand Guiding Tool"""
        try:
            # Import HandGuidingTool
            from hand_guiding_tool import HandGuidingTool

            # Create tool if not exists
            if not hasattr(self, 'hand_guiding_tool') or self.hand_guiding_tool is None:
                self.hand_guiding_tool = HandGuidingTool(
                    robot_controller=self.robot_controller,
                    position_storage=Config.PRESET_POSITIONS,
                    parent=self
                )

            # Show and activate tool
            self.hand_guiding_tool.show()
            self.hand_guiding_tool.raise_()
            self.hand_guiding_tool.activateWindow()

        except Exception as e:
            logger.error(f"Failed to open Hand Guiding Tool: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open Hand Guiding Tool:\n{str(e)}")

    def on_calibrate_force_sensor(self):
        """Calibrate force sensor"""
        if not self.robot_controller.is_connected():
            QMessageBox.warning(self, "Not Connected", "Connect to the robot before calibrating the sensor.")
            return

        reply = QMessageBox.question(
            self,
            "Calibrate Force Sensor",
            "This will zero the force sensor.\nEnsure no external forces are applied.\n\nContinue?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if self.robot_controller.zero_force_sensor():
                QMessageBox.information(self, "Calibration", "Force sensor zeroed successfully")
            else:
                QMessageBox.warning(self, "Calibration Failed", "Could not zero the force sensor. Check the log.")

    def on_about(self):
        """Show about dialog"""
        about_text = """
        <h2>UR10e Remote Control System</h2>
        <p><b>Version:</b> Stage 3 - Data Logging & Visualization</p>
        <p><b>Date:</b> 2025-11-04</p>
        <hr>
        <p>A comprehensive control and monitoring system for UR10e robotic arm.</p>
        <p><b>Features:</b></p>
        <ul>
        <li>Real-time robot control (TCP & Joint)</li>
        <li>Force control integration</li>
        <li>Preset position management</li>
        <li>URScript execution</li>
        <li>Real-time data logging (CSV/HDF5)</li>
        <li>Live visualization with PyQtGraph</li>
        </ul>
        <hr>
        <p><b>Technologies:</b> Python, PyQt5, ur_rtde, PyQtGraph</p>
        """
        QMessageBox.about(self, "About UR10e Control System", about_text)

    def on_documentation(self):
        """Show documentation"""
        doc_text = """
        <h3>Quick Start Guide</h3>
        <p><b>1. Connection:</b> Enter robot IP and click Connect</p>
        <p><b>2. Manual Control:</b> Use TCP/Joint tabs for movement</p>
        <p><b>3. Data Recording:</b> Use Data Recording dock to start/stop logging</p>
        <p><b>4. Charts:</b> Real-time data visualization on the right panel</p>
        <hr>
        <p>For full documentation, see README.md and STAGE3_DOCUMENTATION.md</p>
        """
        QMessageBox.information(self, "Documentation", doc_text)

    # ========================================
    # UI Update Functions (Slots)
    # ========================================

    def update_tcp_display(self, pose: list):
        """Update TCP pose display with orientation visualization"""
        if len(pose) != 6:
            return

        # Update position and rotation values
        for i, value in enumerate(pose):
            self.tcp_labels[i].setText(f"{value:.4f}")

        # Update orientation in degrees (Rx, Ry, Rz are indices 3, 4, 5)
        roll_deg = math.degrees(pose[3])
        pitch_deg = math.degrees(pose[4])
        yaw_deg = math.degrees(pose[5])

        self.tcp_roll_deg_label.setText(f"Roll: {roll_deg:6.1f}°")
        self.tcp_pitch_deg_label.setText(f"Pitch: {pitch_deg:6.1f}°")
        self.tcp_yaw_deg_label.setText(f"Yaw: {yaw_deg:6.1f}°")

        # Update horizontal indicator
        # Check if TCP is approximately horizontal (roll and pitch near 0° or 180°)
        # Tolerance: within 5 degrees
        tolerance = 5.0

        # Normalize angles to -180 to 180
        def normalize_angle(angle):
            while angle > 180:
                angle -= 360
            while angle < -180:
                angle += 360
            return angle

        roll_normalized = normalize_angle(roll_deg)
        pitch_normalized = normalize_angle(pitch_deg)

        # Check if near horizontal (0°) or upside down horizontal (180°)
        is_horizontal = (
            (abs(roll_normalized) < tolerance and abs(pitch_normalized) < tolerance) or
            (abs(abs(roll_normalized) - 180) < tolerance and abs(abs(pitch_normalized) - 180) < tolerance)
        )

        if is_horizontal:
            self.tcp_horizontal_indicator.setText("✓ Horizontal")
            self.tcp_horizontal_indicator.setStyleSheet("QLabel { font-size: 14px; padding: 3px; color: green; font-weight: bold; }")
        else:
            self.tcp_horizontal_indicator.setText("⚠ Tilted")
            self.tcp_horizontal_indicator.setStyleSheet("QLabel { font-size: 14px; padding: 3px; color: orange; font-weight: bold; }")

        # Update TCP orientation visualization widget
        self.tcp_orientation_widget.update_orientation(pose[3], pose[4], pose[5])

        # Update simplified status overview (Basic page)
        self.status_tcp_label.setText(f"X: {pose[0]:.3f}, Y: {pose[1]:.3f}, Z: {pose[2]:.3f}")

    def update_joint_display(self, joints: list):
        """Update joint angle display"""
        if len(joints) != 6:
            return

        for i, value in enumerate(joints):
            self.joint_labels[i].setText(f"{value:.4f}")

    def on_connection_status_changed(self, connected: bool):
        """Connection status changed"""
        if connected:
            self.connection_status_label.setText("● Connected")
            self.connection_status_label.setStyleSheet("QLabel { color: green; font-weight: bold; }")

            # Update status overview (Basic page)
            self.status_connection_label.setText("Connected")
            self.status_connection_label.setStyleSheet("QLabel { background-color: #4CAF50; color: white; padding: 5px; font-weight: bold; border-radius: 3px; }")
            self.status_mode_label.setText("Normal")
            self.status_mode_label.setStyleSheet("QLabel { background-color: #2196F3; color: white; padding: 5px; font-weight: bold; border-radius: 3px; }")
            self.connect_button.setEnabled(False)
            self.disconnect_button.setEnabled(True)
            self.freedrive_enable_button.setEnabled(True)
            self.emergency_stop_button.setEnabled(True)
            self.unlock_robot_button.setEnabled(True)

            # Reset safety indicators to OK state on new connection
            self._reset_safety_indicators()
            self.robot_controller.safety_monitor.clear_warnings()
            self.robot_controller.safety_monitor._update_safety_status(True)

            # Enable TCP control buttons
            tcp_buttons = [
                self.tcp_x_minus, self.tcp_x_plus, self.tcp_y_minus, self.tcp_y_plus,
                self.tcp_z_minus, self.tcp_z_plus, self.tcp_rx_minus, self.tcp_rx_plus,
                self.tcp_ry_minus, self.tcp_ry_plus, self.tcp_rz_minus, self.tcp_rz_plus
            ]
            for btn in tcp_buttons:
                btn.setEnabled(True)

            # Enable joint control buttons
            for btn in self.joint_minus_buttons + self.joint_plus_buttons:
                btn.setEnabled(True)

            # Enable preset buttons
            self.preset_home_btn.setEnabled(True)
            self.preset_safe_btn.setEnabled(True)
            self.preset_vertical_btn.setEnabled(True)
            self.save_preset_btn.setEnabled(True)
            self.load_preset_btn.setEnabled(True)

            # Enable force control
            self.force_page.set_connected(True)

            # Enable script execution
            self.execute_script_btn.setEnabled(True)

            self.status_bar.showMessage("Connected to robot - Ready for data logging")

            # Initialize data storage
            self.__init_data_storage()

        else:
            self.connection_status_label.setText("● Disconnected")
            self.connection_status_label.setStyleSheet("QLabel { color: red; font-weight: bold; }")

            # Update status overview (Basic page)
            self.status_connection_label.setText("Disconnected")
            self.status_connection_label.setStyleSheet("QLabel { background-color: #f44336; color: white; padding: 5px; font-weight: bold; border-radius: 3px; }")
            self.status_mode_label.setText("Unknown")
            self.status_mode_label.setStyleSheet("QLabel { background-color: #9E9E9E; color: white; padding: 5px; font-weight: bold; border-radius: 3px; }")

            self.connect_button.setEnabled(True)
            self.disconnect_button.setEnabled(False)
            self.freedrive_enable_button.setEnabled(False)
            self.freedrive_disable_button.setEnabled(False)
            self.emergency_stop_button.setEnabled(False)
            self.unlock_robot_button.setEnabled(False)

            # Disable TCP control buttons
            tcp_buttons = [
                self.tcp_x_minus, self.tcp_x_plus, self.tcp_y_minus, self.tcp_y_plus,
                self.tcp_z_minus, self.tcp_z_plus, self.tcp_rx_minus, self.tcp_rx_plus,
                self.tcp_ry_minus, self.tcp_ry_plus, self.tcp_rz_minus, self.tcp_rz_plus
            ]
            for btn in tcp_buttons:
                btn.setEnabled(False)

            # Disable joint control buttons
            for btn in self.joint_minus_buttons + self.joint_plus_buttons:
                btn.setEnabled(False)

            # Disable preset buttons
            self.preset_home_btn.setEnabled(False)
            self.preset_safe_btn.setEnabled(False)
            self.preset_vertical_btn.setEnabled(False)
            self.save_preset_btn.setEnabled(False)
            self.load_preset_btn.setEnabled(False)

            # Disable force control
            self.force_page.set_connected(False)

            # Disable script execution
            self.execute_script_btn.setEnabled(False)
            self.stop_script_btn.setEnabled(False)

            self.status_bar.showMessage("Disconnected")

    def show_error_message(self, message: str):
        """Display error message"""
        self.log_text.append(f"<span style='color: #ff5555;'>[ERROR] {message}</span>")
        self.status_bar.showMessage(f"Error: {message}", 5000)
        logger.error(message)

    def show_info_message(self, message: str):
        """Display info message"""
        self.log_text.append(f"<span style='color: #50fa7b;'>[INFO] {message}</span>")
        self.status_bar.showMessage(message, 3000)
        logger.info(message)

    # ========================================
    # Safety Signal Handlers (NEW - Stage 4)
    # ========================================

    def on_workspace_warning(self, axis: str):
        """Handle workspace boundary warning"""
        self.workspace_status_label.setText(f"⚠ Workspace: Near {axis}")
        self.workspace_status_label.setStyleSheet(
            "QLabel { background-color: #FF9800; color: white; padding: 8px; font-weight: bold; border-radius: 4px; }"
        )
        self.show_info_message(f"WARNING: Approaching workspace boundary {axis}")

    def on_workspace_violation(self, axis: str):
        """Handle workspace boundary violation"""
        self.workspace_status_label.setText(f"🚫 Workspace: VIOLATED {axis}")
        self.workspace_status_label.setStyleSheet(
            "QLabel { background-color: #F44336; color: white; padding: 8px; font-weight: bold; border-radius: 4px; }"
        )
        self.show_error_message(f"CRITICAL: Workspace boundary {axis} VIOLATED!")

    def on_force_warning(self, magnitude: float):
        """Handle force/torque warning"""
        self.force_safety_label.setText(f"⚠ Forces: High ({magnitude:.1f})")
        self.force_safety_label.setStyleSheet(
            "QLabel { background-color: #FF9800; color: white; padding: 8px; font-weight: bold; border-radius: 4px; }"
        )
        self.force_page.show_force_warning(magnitude)
        self.show_info_message(f"WARNING: Force/torque level high: {magnitude:.2f}")

    def on_force_violation(self, magnitude: float):
        """Handle force/torque limit violation"""
        self.force_safety_label.setText(f"🚫 Forces: EXCEEDED ({magnitude:.1f})")
        self.force_safety_label.setStyleSheet(
            "QLabel { background-color: #F44336; color: white; padding: 8px; font-weight: bold; border-radius: 4px; }"
        )
        self.force_page.show_force_violation(magnitude)
        self.show_error_message(f"CRITICAL: Force/torque limit EXCEEDED: {magnitude:.2f}!")

    def on_collision_detected(self, description: str):
        """Handle collision detection"""
        self.collision_status_label.setText(f"💥 Collision: DETECTED")
        self.collision_status_label.setStyleSheet(
            "QLabel { background-color: #F44336; color: white; padding: 8px; font-weight: bold; border-radius: 4px; }"
        )
        self.show_error_message(f"CRITICAL: COLLISION DETECTED! {description}")

    def on_safety_status_changed(self, safety_mode: int):
        """
        Handle robot safety status changes.

        UR Robot Safety Modes:
        1 = NORMAL
        2 = REDUCED
        3 = PROTECTIVE_STOP
        4 = RECOVERY
        5 = SAFEGUARD_STOP
        6 = SYSTEM_EMERGENCY_STOP
        7 = ROBOT_EMERGENCY_STOP
        8 = VIOLATION
        9 = FAULT

        When protective stop (mode >= 3) is triggered during freedrive,
        automatically disable freedrive in UI to keep status synchronized.
        """
        logger.debug(f"Safety status changed to mode: {safety_mode}")

        # Check if protective stop or other unsafe state is triggered (mode >= 3)
        # and freedrive is currently active
        if safety_mode >= 3:
            # Check if freedrive is active by checking if disable button is enabled
            if self.freedrive_disable_button.isEnabled():
                logger.info(f"Protective stop detected (mode {safety_mode}) during active freedrive - auto-disabling freedrive UI")

                # Restore normal safety profile (important for safety limits)
                self.robot_controller.safety_monitor.disable_freedrive_profile()

                # Automatically disable freedrive in UI (same as manual disable)
                self.freedrive_status_label.setText("Status: Inactive (Auto-disabled)")
                self.freedrive_status_label.setStyleSheet("QLabel { color: #FF9800; font-style: italic; }")

                # Reset enable button to active blue color
                self.freedrive_enable_button.setStyleSheet(
                    "QPushButton { background-color: #2196F3; color: white; font-weight: bold; padding: 10px; }"
                )
                self.freedrive_enable_button.setEnabled(True)

                # Disable button to gray
                self.freedrive_disable_button.setStyleSheet(
                    "QPushButton:disabled { background-color: #bdbdbd; color: #757575; }"
                )
                self.freedrive_disable_button.setEnabled(False)

                # Show info message
                self.show_info_message("Freedrive auto-disabled due to protective stop - Normal safety limits restored. Press 'Recover Robot' then re-enable freedrive if needed")

    def _reset_safety_indicators(self):
        """Reset safety status indicators to OK state"""
        self.workspace_status_label.setText("● Workspace: OK")
        self.workspace_status_label.setStyleSheet(
            "QLabel { background-color: #4CAF50; color: white; padding: 8px; font-weight: bold; border-radius: 4px; }"
        )

        self.force_safety_label.setText("● Forces: OK")
        self.force_safety_label.setStyleSheet(
            "QLabel { background-color: #4CAF50; color: white; padding: 8px; font-weight: bold; border-radius: 4px; }"
        )
        self.force_page.reset_safety()

        self.collision_status_label.setText("● Collision: None")
        self.collision_status_label.setStyleSheet(
            "QLabel { background-color: #4CAF50; color: white; padding: 8px; font-weight: bold; border-radius: 4px; }"
        )

    # ========================================
    # Window Close Event
    # ========================================

    def closeEvent(self, event):
        """Window close event"""
        # Check if recording is active
        if self.data_logger.is_recording:
            reply = QMessageBox.question(
                self,
                "Recording Active",
                "Data recording is still active.\nDo you want to stop and save before exiting?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )

            if reply == QMessageBox.Yes:
                self.on_stop_recording()
            elif reply == QMessageBox.Cancel:
                event.ignore()
                return

        reply = QMessageBox.question(
            self,
            "Confirm Exit",
            "Are you sure you want to exit?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Disconnect from robot
            if self.robot_controller.is_connected():
                self.robot_controller.disconnect()

            logger.info("Application exiting normally")
            event.accept()
        else:
            event.ignore()
