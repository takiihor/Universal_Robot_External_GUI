"""
Demo Script - Compare Original vs Improved Layouts

This script demonstrates the difference between the original vertical tab layout
and the improved List + Stack layout.
"""

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt

# Mock data for demonstration
class ActionType:
    MOVE_TO_POSITION = "move_to_position"
    RELATIVE_MOVE = "relative_move"
    HOME = "home"

ACTION_METADATA = {
    ActionType.MOVE_TO_POSITION: {
        "icon": "🎯",
        "name": "Move to Position",
        "description": "Move to a preset position"
    },
    ActionType.RELATIVE_MOVE: {
        "icon": "➡️",
        "name": "Relative Move",
        "description": "Move small distances"
    },
    ActionType.HOME: {
        "icon": "🏠",
        "name": "Home",
        "description": "Return to safe position"
    }
}

ACTION_CATEGORIES = {
    "movement": {
        "icon": "🏃",
        "name": "Movement",
        "color": "#4CAF50",
        "description": "Robot movement and positioning actions",
        "actions": [ActionType.MOVE_TO_POSITION, ActionType.RELATIVE_MOVE, ActionType.HOME]
    },
    "control": {
        "icon": "🎮",
        "name": "Control",
        "color": "#2196F3",
        "description": "Control actions",
        "actions": []
    }
}


class DemoWindow(QMainWindow):
    """Demo window to compare layouts"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Action Library Layout Comparison")
        self.setGeometry(100, 100, 1200, 700)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QVBoxLayout(central)
        
        # Title
        title = QLabel("📊 Layout Comparison: Original vs Improved")
        title.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Comparison layout
        compare_layout = QHBoxLayout()
        
        # Left: Problem explanation
        problem_widget = self.create_problem_widget()
        compare_layout.addWidget(problem_widget)
        
        # Right: Solution explanation
        solution_widget = self.create_solution_widget()
        compare_layout.addWidget(solution_widget)
        
        layout.addLayout(compare_layout)
        
        # Bottom: Instructions
        instructions = QLabel("""
        <b>实施步骤:</b><br>
        1️⃣ 将改进文件复制到项目目录<br>
        2️⃣ 在 sequential_controller_ui_page.py 第76行修改导入<br>
        3️⃣ 运行测试,立即看到效果!
        """)
        instructions.setStyleSheet("""
            QLabel {
                background-color: #E8F5E9;
                padding: 15px;
                border-radius: 8px;
                border: 2px solid #4CAF50;
            }
        """)
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
    
    def create_problem_widget(self) -> QWidget:
        """Create widget showing the problem"""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background-color: #FFEBEE;
                border-radius: 8px;
                border: 2px solid #F44336;
            }
        """)
        
        layout = QVBoxLayout(widget)
        
        # Title
        title = QLabel("❌ 原问题: 垂直标签旋转")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #C62828; padding: 10px;")
        layout.addWidget(title)
        
        # Problem visualization
        problem_text = QLabel("""
<pre style='font-size: 14px; line-height: 1.8;'>
<b>垂直标签 (QTabWidget.West):</b>

┌─────┐
│ M   │ ← 文字被旋转90度
│ o   │
│ v   │
│ e   │
│ m   │
│ e   │
│ n   │
│ t 🏃│ ← 图标和文字挤在一起
└─────┘

<b>问题:</b>
• min-width: 120px 太窄
• Emoji + 文字同时旋转
• 系统字体渲染不一致
• 难以阅读
</pre>
        """)
        layout.addWidget(problem_text)
        
        # Code snippet
        code = QLabel("""
<b>原代码片段:</b>
<pre style='background: #FFE0E0; padding: 10px; border-radius: 4px;'>
self.tab_widget.setTabPosition(
    QTabWidget.West  # ❌ 导致旋转
)
QTabBar::tab {
    min-width: 120px;  # ❌ 太窄
}
</pre>
        """)
        layout.addWidget(code)
        
        return widget
    
    def create_solution_widget(self) -> QWidget:
        """Create widget showing the solution"""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background-color: #E8F5E9;
                border-radius: 8px;
                border: 2px solid #4CAF50;
            }
        """)
        
        layout = QVBoxLayout(widget)
        
        # Title
        title = QLabel("✅ 解决方案: List + Stack")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #2E7D32; padding: 10px;")
        layout.addWidget(title)
        
        # Solution visualization
        solution_text = QLabel("""
<pre style='font-size: 14px; line-height: 1.8;'>
<b>横向列表 (QListWidget):</b>

┌──────────────────┐
│ 🏃  Movement     │ ← 清晰,无旋转
├──────────────────┤
│ 🎮  Control      │ ← 图标+文字并排
├──────────────────┤
│ ⏰  Timing       │ ← 易于阅读
└──────────────────┘

<b>优势:</b>
• 无旋转,横向布局
• 自定义item widget
• 响应式设计
• 只需改一行代码!
</pre>
        """)
        layout.addWidget(solution_text)
        
        # Code snippet
        code = QLabel("""
<b>新代码 (只需改一行!):</b>
<pre style='background: #E0F0E0; padding: 10px; border-radius: 4px;'>
# 原来:
from categorized_action_library import ...

# 改为:
from categorized_action_library_improved \\
    import CategorizedActionLibrary  # ✅
</pre>
        """)
        layout.addWidget(code)
        
        return widget


def main():
    """Run the demo"""
    app = QApplication(sys.argv)
    
    # Set font
    font = app.font()
    font.setPointSize(10)
    app.setFont(font)
    
    window = DemoWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    # Note: This demo doesn't require the actual sequential_controller module
    # It just visualizes the concept
    print("=" * 60)
    print("Action Library UI Improvement Demo")
    print("=" * 60)
    print("\n📊 This demo shows the visual difference between:")
    print("   • Original: Vertical tabs (rotated text)")
    print("   • Improved: List + Stack (horizontal layout)")
    print("\n🚀 Opening demo window...\n")
    
    main()
