# Hand Guiding 教學工具設計文檔

## 一、設計理念

### 1.1 用途定位

Hand Guiding 是一個**位置教學工具**，不是程式執行的一部分。它的主要功能是：

- ✅ 讓使用者手動移動機器人到目標位置
- ✅ 保存這些位置供後續程式使用
- ✅ 測試夾爪開關
- ✅ 建立位置庫

**重要概念分離:**

```
┌─────────────────────────────────────────────────────┐
│  Hand Guiding Tool (教學模式)                        │
│  - 用於建立位置庫                                    │
│  - 不會被執行                                        │
│  - 是準備階段                                        │
└─────────────────────────────────────────────────────┘
                      │
                      │ 保存位置
                      ▼
┌─────────────────────────────────────────────────────┐
│  Position Library (位置庫)                           │
│  - position1, position2, position3, position4...    │
└─────────────────────────────────────────────────────┘
                      │
                      │ 在程式中使用
                      ▼
┌─────────────────────────────────────────────────────┐
│  Sequential Controller Program (實際程式)           │
│  1. Move to position1                               │
│  2. Open gripper                                    │
│  3. Move to position2                               │
│  4. Close gripper                                   │
│  5. Move to position3                               │
└─────────────────────────────────────────────────────┘
```

---

## 二、介面設計

### 2.1 整體佈局

```
┌────────────────────────────────────────────────────────────┐
│  🎓 Hand Guiding - 位置教學工具                              │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌──────────────────────┐  ┌──────────────────────────┐  │
│  │  控制面板              │  │  已保存位置列表            │  │
│  │                      │  │                          │  │
│  │  [啟用手動引導]       │  │  📍 home                 │  │
│  │  [停止手動引導]       │  │  📍 position1            │  │
│  │                      │  │  📍 position2            │  │
│  │  當前位置:            │  │  📍 position3            │  │
│  │  X: 0.350           │  │  📍 position4            │  │
│  │  Y: -0.120          │  │                          │  │
│  │  Z: 0.550           │  │  [載入] [刪除] [測試]     │  │
│  │                      │  │                          │  │
│  │  [保存當前位置]       │  └──────────────────────────┘  │
│  │  [開啟夾爪]          │                              │
│  │  [關閉夾爪]          │                              │
│  │                      │                              │
│  └──────────────────────┘                              │
│                                                            │
│  ┌────────────────────────────────────────────────────┐  │
│  │  📝 操作指南                                          │  │
│  │  1. 點擊「啟用手動引導」進入教學模式                    │  │
│  │  2. 手動移動機器人到目標位置                           │  │
│  │  3. 點擊「保存當前位置」並輸入名稱                      │  │
│  │  4. 重複步驟 2-3 建立所有需要的位置                    │  │
│  │  5. 可以測試夾爪動作                                   │  │
│  │  6. 完成後點擊「停止手動引導」                          │  │
│  │  7. 在 Sequential Controller 中使用保存的位置          │  │
│  └────────────────────────────────────────────────────┘  │
│                                                            │
│  [關閉]                                    [匯出位置庫]     │
└────────────────────────────────────────────────────────────┘
```

### 2.2 工作流程

```
開始
  │
  ▼
點擊「啟用手動引導」
  │
  ▼
機器人進入 Freedrive 模式
  │
  ▼
手動移動到 Position 1
  │
  ▼
點擊「保存當前位置」→ 輸入名稱: "position1"
  │
  ▼
手動移動到 Position 2
  │
  ▼
點擊「保存當前位置」→ 輸入名稱: "position2"
  │
  ▼
測試夾爪: 點擊「開啟夾爪」
  │
  ▼
手動移動到 Position 3
  │
  ▼
點擊「保存當前位置」→ 輸入名稱: "position3"
  │
  ▼
測試夾爪: 點擊「關閉夾爪」
  │
  ▼
手動移動到 Position 4
  │
  ▼
點擊「保存當前位置」→ 輸入名稱: "position4"
  │
  ▼
點擊「停止手動引導」
  │
  ▼
位置已保存到位置庫
  │
  ▼
在 Sequential Controller 中使用這些位置
  │
  ▼
結束
```

---

## 三、程式碼實現

### 3.1 HandGuidingTool 類別

```python
"""
Hand Guiding Tool - 位置教學工具

這個工具用於教學機器人位置，不是程式執行的一部分。
使用者可以手動移動機器人並保存位置，這些位置會被保存到位置庫中。
"""

import logging
from typing import Dict, List, Optional
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QListWidget, QListWidgetItem,
    QGroupBox, QLineEdit, QMessageBox, QInputDialog,
    QDialog, QDialogButtonBox, QFormLayout, QTextEdit
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor
import json

logger = logging.getLogger(__name__)


class HandGuidingTool(QWidget):
    """Hand Guiding 位置教學工具"""
    
    # 信號
    position_saved = pyqtSignal(str, dict)  # 位置名稱, 位置數據
    
    def __init__(self, robot_interface, position_storage, parent=None):
        """
        初始化 Hand Guiding Tool
        
        Args:
            robot_interface: 機器人介面 (UR10e API)
            position_storage: 位置儲存器 (Config.PRESET_POSITIONS)
            parent: 父 Widget
        """
        super().__init__(parent)
        self.robot = robot_interface
        self.position_storage = position_storage
        self.is_freedrive_enabled = False
        self.position_update_timer = QTimer()
        
        self.init_ui()
        self.connect_signals()
        
    def init_ui(self):
        """初始化 UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # 標題
        title_label = QLabel("🎓 Hand Guiding - 位置教學工具")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        main_layout.addWidget(title_label)
        
        # 說明
        info_label = QLabel(
            "⚠️ 注意: 這是位置教學工具，不是程式執行的一部分。\n"
            "使用此工具手動移動機器人並保存位置，然後在 Sequential Controller 中使用這些位置。"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("""
            QLabel {
                background-color: #FFF3E0;
                padding: 10px;
                border-radius: 4px;
                border-left: 4px solid #FF9800;
            }
        """)
        main_layout.addWidget(info_label)
        
        # 主要內容區域
        content_layout = QHBoxLayout()
        
        # 左側: 控制面板
        control_panel = self.create_control_panel()
        content_layout.addWidget(control_panel, 1)
        
        # 右側: 位置列表
        position_list_panel = self.create_position_list_panel()
        content_layout.addWidget(position_list_panel, 1)
        
        main_layout.addLayout(content_layout)
        
        # 操作指南
        guide_panel = self.create_guide_panel()
        main_layout.addWidget(guide_panel)
        
        # 底部按鈕
        button_layout = QHBoxLayout()
        
        export_btn = QPushButton("📤 匯出位置庫")
        export_btn.clicked.connect(self.export_positions)
        button_layout.addWidget(export_btn)
        
        button_layout.addStretch()
        
        close_btn = QPushButton("關閉")
        close_btn.clicked.connect(self.close_tool)
        button_layout.addWidget(close_btn)
        
        main_layout.addLayout(button_layout)
        
    def create_control_panel(self) -> QWidget:
        """創建控制面板"""
        group = QGroupBox("控制面板")
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # Freedrive 控制
        freedrive_layout = QVBoxLayout()
        
        self.enable_freedrive_btn = QPushButton("🤚 啟用手動引導")
        self.enable_freedrive_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 15px;
                font-size: 14px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.enable_freedrive_btn.clicked.connect(self.enable_freedrive)
        freedrive_layout.addWidget(self.enable_freedrive_btn)
        
        self.disable_freedrive_btn = QPushButton("🛑 停止手動引導")
        self.disable_freedrive_btn.setEnabled(False)
        self.disable_freedrive_btn.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                color: white;
                font-weight: bold;
                padding: 15px;
                font-size: 14px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.disable_freedrive_btn.clicked.connect(self.disable_freedrive)
        freedrive_layout.addWidget(self.disable_freedrive_btn)
        
        layout.addLayout(freedrive_layout)
        
        # 狀態顯示
        status_group = QGroupBox("機器人狀態")
        status_layout = QFormLayout()
        
        self.status_label = QLabel("就緒")
        self.status_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        status_layout.addRow("狀態:", self.status_label)
        
        self.position_label = QLabel("N/A")
        self.position_label.setStyleSheet("font-family: monospace;")
        status_layout.addRow("當前位置:", self.position_label)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # 位置控制
        position_control_group = QGroupBox("位置控制")
        position_control_layout = QVBoxLayout()
        
        self.save_position_btn = QPushButton("💾 保存當前位置")
        self.save_position_btn.setEnabled(False)
        self.save_position_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.save_position_btn.clicked.connect(self.save_current_position)
        position_control_layout.addWidget(self.save_position_btn)
        
        position_control_group.setLayout(position_control_layout)
        layout.addWidget(position_control_group)
        
        # 夾爪控制
        gripper_group = QGroupBox("夾爪測試")
        gripper_layout = QHBoxLayout()
        
        self.open_gripper_btn = QPushButton("🤲 開啟夾爪")
        self.open_gripper_btn.setEnabled(False)
        self.open_gripper_btn.clicked.connect(self.open_gripper)
        gripper_layout.addWidget(self.open_gripper_btn)
        
        self.close_gripper_btn = QPushButton("✊ 關閉夾爪")
        self.close_gripper_btn.setEnabled(False)
        self.close_gripper_btn.clicked.connect(self.close_gripper)
        gripper_layout.addWidget(self.close_gripper_btn)
        
        gripper_group.setLayout(gripper_layout)
        layout.addWidget(gripper_group)
        
        layout.addStretch()
        
        group.setLayout(layout)
        return group
        
    def create_position_list_panel(self) -> QWidget:
        """創建位置列表面板"""
        group = QGroupBox("已保存位置")
        layout = QVBoxLayout()
        
        # 位置列表
        self.position_list = QListWidget()
        self.position_list.setStyleSheet("""
            QListWidget {
                font-size: 13px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #e0e0e0;
            }
            QListWidget::item:selected {
                background-color: #2196F3;
                color: white;
            }
        """)
        layout.addWidget(self.position_list)
        
        # 載入已有位置
        self.refresh_position_list()
        
        # 操作按鈕
        btn_layout = QHBoxLayout()
        
        load_btn = QPushButton("📥 載入")
        load_btn.setToolTip("將機器人移動到選中的位置")
        load_btn.clicked.connect(self.load_selected_position)
        btn_layout.addWidget(load_btn)
        
        test_btn = QPushButton("🔍 測試")
        test_btn.setToolTip("測試移動到選中的位置")
        test_btn.clicked.connect(self.test_selected_position)
        btn_layout.addWidget(test_btn)
        
        delete_btn = QPushButton("🗑️ 刪除")
        delete_btn.clicked.connect(self.delete_selected_position)
        btn_layout.addWidget(delete_btn)
        
        layout.addLayout(btn_layout)
        
        group.setLayout(layout)
        return group
        
    def create_guide_panel(self) -> QWidget:
        """創建操作指南面板"""
        group = QGroupBox("📝 操作指南")
        layout = QVBoxLayout()
        
        guide_text = QTextEdit()
        guide_text.setReadOnly(True)
        guide_text.setMaximumHeight(150)
        guide_text.setHtml("""
            <ol style="line-height: 1.6;">
                <li>點擊 <b>「啟用手動引導」</b> 進入教學模式</li>
                <li>用手輕輕移動機器人手臂到目標位置</li>
                <li>點擊 <b>「保存當前位置」</b> 並輸入位置名稱 (例如: position1)</li>
                <li>重複步驟 2-3 建立所有需要的位置</li>
                <li>可以使用 <b>「開啟/關閉夾爪」</b> 測試夾爪動作</li>
                <li>完成後點擊 <b>「停止手動引導」</b></li>
                <li>在 <b>Sequential Controller</b> 中使用保存的位置名稱創建程式</li>
            </ol>
        """)
        guide_text.setStyleSheet("background-color: #E3F2FD; border: none;")
        layout.addWidget(guide_text)
        
        group.setLayout(layout)
        return group
        
    def connect_signals(self):
        """連接信號"""
        # 定時更新位置顯示
        self.position_update_timer.timeout.connect(self.update_position_display)
        
    # ========================================
    # Freedrive 控制
    # ========================================
    
    def enable_freedrive(self):
        """啟用 Freedrive 模式"""
        try:
            # 確認對話框
            reply = QMessageBox.question(
                self,
                "確認啟用手動引導",
                "即將啟用手動引導模式。\n\n"
                "請確認:\n"
                "• 機器人周圍無障礙物\n"
                "• 您已準備好手動移動機器人\n\n"
                "繼續嗎?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return
                
            # 啟用 freedrive
            success = self.robot.enable_freedrive_mode()
            
            if success:
                self.is_freedrive_enabled = True
                
                # 更新 UI
                self.enable_freedrive_btn.setEnabled(False)
                self.disable_freedrive_btn.setEnabled(True)
                self.save_position_btn.setEnabled(True)
                self.open_gripper_btn.setEnabled(True)
                self.close_gripper_btn.setEnabled(True)
                
                self.status_label.setText("手動引導中")
                self.status_label.setStyleSheet("font-weight: bold; color: #FF9800;")
                
                # 開始更新位置顯示
                self.position_update_timer.start(100)  # 每 100ms 更新一次
                
                logger.info("Hand guiding enabled")
                
                QMessageBox.information(
                    self,
                    "手動引導已啟用",
                    "您現在可以手動移動機器人手臂。\n"
                    "移動到目標位置後，點擊「保存當前位置」。"
                )
            else:
                QMessageBox.warning(
                    self,
                    "啟用失敗",
                    "無法啟用手動引導模式，請檢查機器人連接。"
                )
                
        except Exception as e:
            logger.error(f"Failed to enable freedrive: {e}")
            QMessageBox.critical(self, "錯誤", f"啟用手動引導失敗: {str(e)}")
            
    def disable_freedrive(self):
        """停止 Freedrive 模式"""
        try:
            # 停止 freedrive
            success = self.robot.disable_freedrive_mode()
            
            if success:
                self.is_freedrive_enabled = False
                
                # 更新 UI
                self.enable_freedrive_btn.setEnabled(True)
                self.disable_freedrive_btn.setEnabled(False)
                self.save_position_btn.setEnabled(False)
                self.open_gripper_btn.setEnabled(False)
                self.close_gripper_btn.setEnabled(False)
                
                self.status_label.setText("就緒")
                self.status_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
                
                # 停止更新位置顯示
                self.position_update_timer.stop()
                
                logger.info("Hand guiding disabled")
                
                QMessageBox.information(
                    self,
                    "手動引導已停止",
                    "手動引導模式已停止。\n"
                    "您保存的位置可以在 Sequential Controller 中使用。"
                )
            else:
                QMessageBox.warning(
                    self,
                    "停止失敗",
                    "無法停止手動引導模式。"
                )
                
        except Exception as e:
            logger.error(f"Failed to disable freedrive: {e}")
            QMessageBox.critical(self, "錯誤", f"停止手動引導失敗: {str(e)}")
            
    def update_position_display(self):
        """更新位置顯示"""
        try:
            if self.is_freedrive_enabled:
                # 獲取當前位置
                position = self.robot.get_current_pose()
                
                if position:
                    # 顯示位置 (只顯示 XYZ)
                    pos_text = (
                        f"X: {position[0]:.3f} m\n"
                        f"Y: {position[1]:.3f} m\n"
                        f"Z: {position[2]:.3f} m"
                    )
                    self.position_label.setText(pos_text)
                    
        except Exception as e:
            logger.error(f"Failed to update position: {e}")
            
    # ========================================
    # 位置管理
    # ========================================
    
    def save_current_position(self):
        """保存當前位置"""
        try:
            # 獲取當前位置
            position = self.robot.get_current_pose()
            
            if not position:
                QMessageBox.warning(self, "警告", "無法獲取當前位置")
                return
                
            # 輸入位置名稱
            position_name, ok = QInputDialog.getText(
                self,
                "保存位置",
                "請輸入位置名稱:\n(例如: position1, pickup_point, home)",
                QLineEdit.Normal,
                ""
            )
            
            if not ok or not position_name.strip():
                return
                
            position_name = position_name.strip()
            
            # 檢查名稱是否已存在
            if position_name in self.position_storage:
                reply = QMessageBox.question(
                    self,
                    "位置已存在",
                    f"位置 '{position_name}' 已存在。\n是否覆蓋?",
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if reply != QMessageBox.Yes:
                    return
                    
            # 保存位置
            position_data = {
                "pose": position,
                "type": "taught",  # 標記為教學位置
                "description": f"Hand-guided position saved at {self.get_timestamp()}"
            }
            
            self.position_storage[position_name] = position_data
            
            # 發出信號
            self.position_saved.emit(position_name, position_data)
            
            # 刷新列表
            self.refresh_position_list()
            
            # 保存到配置文件
            self.save_position_storage()
            
            logger.info(f"Position '{position_name}' saved: {position}")
            
            QMessageBox.information(
                self,
                "保存成功",
                f"位置 '{position_name}' 已保存!\n\n"
                f"您可以在 Sequential Controller 中使用此位置。"
            )
            
        except Exception as e:
            logger.error(f"Failed to save position: {e}")
            QMessageBox.critical(self, "錯誤", f"保存位置失敗: {str(e)}")
            
    def load_selected_position(self):
        """載入選中的位置 (移動機器人到該位置)"""
        current_item = self.position_list.currentItem()
        
        if not current_item:
            QMessageBox.warning(self, "提示", "請先選擇一個位置")
            return
            
        position_name = current_item.text().replace("📍 ", "")
        
        # 確認
        reply = QMessageBox.question(
            self,
            "確認移動",
            f"將機器人移動到位置 '{position_name}'?\n\n"
            "⚠️ 請確保周圍無障礙物!",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
            
        try:
            # 如果在 freedrive 模式，先停止
            if self.is_freedrive_enabled:
                self.disable_freedrive()
                
            # 獲取位置數據
            position_data = self.position_storage.get(position_name)
            
            if not position_data:
                QMessageBox.warning(self, "錯誤", f"找不到位置 '{position_name}'")
                return
                
            # 移動機器人
            success = self.robot.move_to_pose(position_data["pose"], speed=0.1, acceleration=0.1)
            
            if success:
                QMessageBox.information(self, "成功", f"已移動到位置 '{position_name}'")
            else:
                QMessageBox.warning(self, "失敗", f"移動到位置 '{position_name}' 失敗")
                
        except Exception as e:
            logger.error(f"Failed to load position: {e}")
            QMessageBox.critical(self, "錯誤", f"載入位置失敗: {str(e)}")
            
    def test_selected_position(self):
        """測試選中的位置"""
        # 與 load_selected_position 相同，但使用較慢的速度
        current_item = self.position_list.currentItem()
        
        if not current_item:
            QMessageBox.warning(self, "提示", "請先選擇一個位置")
            return
            
        position_name = current_item.text().replace("📍 ", "")
        
        try:
            # 如果在 freedrive 模式，先停止
            if self.is_freedrive_enabled:
                self.disable_freedrive()
                
            position_data = self.position_storage.get(position_name)
            
            if not position_data:
                QMessageBox.warning(self, "錯誤", f"找不到位置 '{position_name}'")
                return
                
            # 以慢速測試移動
            success = self.robot.move_to_pose(
                position_data["pose"],
                speed=0.05,  # 很慢的速度
                acceleration=0.05
            )
            
            if success:
                QMessageBox.information(self, "測試成功", f"已成功測試位置 '{position_name}'")
            else:
                QMessageBox.warning(self, "測試失敗", f"測試位置 '{position_name}' 失敗")
                
        except Exception as e:
            logger.error(f"Failed to test position: {e}")
            QMessageBox.critical(self, "錯誤", f"測試位置失敗: {str(e)}")
            
    def delete_selected_position(self):
        """刪除選中的位置"""
        current_item = self.position_list.currentItem()
        
        if not current_item:
            QMessageBox.warning(self, "提示", "請先選擇一個位置")
            return
            
        position_name = current_item.text().replace("📍 ", "")
        
        # 確認
        reply = QMessageBox.question(
            self,
            "確認刪除",
            f"確定要刪除位置 '{position_name}'?\n\n"
            "此操作無法復原!",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
            
        try:
            # 刪除位置
            if position_name in self.position_storage:
                del self.position_storage[position_name]
                
                # 刷新列表
                self.refresh_position_list()
                
                # 保存到配置文件
                self.save_position_storage()
                
                logger.info(f"Position '{position_name}' deleted")
                
                QMessageBox.information(self, "刪除成功", f"位置 '{position_name}' 已刪除")
            else:
                QMessageBox.warning(self, "錯誤", f"找不到位置 '{position_name}'")
                
        except Exception as e:
            logger.error(f"Failed to delete position: {e}")
            QMessageBox.critical(self, "錯誤", f"刪除位置失敗: {str(e)}")
            
    def refresh_position_list(self):
        """刷新位置列表"""
        self.position_list.clear()
        
        for position_name in sorted(self.position_storage.keys()):
            item = QListWidgetItem(f"📍 {position_name}")
            self.position_list.addItem(item)
            
    # ========================================
    # 夾爪控制
    # ========================================
    
    def open_gripper(self):
        """開啟夾爪"""
        try:
            success = self.robot.open_gripper()
            
            if success:
                logger.info("Gripper opened")
                QMessageBox.information(self, "成功", "夾爪已開啟")
            else:
                QMessageBox.warning(self, "失敗", "開啟夾爪失敗")
                
        except Exception as e:
            logger.error(f"Failed to open gripper: {e}")
            QMessageBox.critical(self, "錯誤", f"開啟夾爪失敗: {str(e)}")
            
    def close_gripper(self):
        """關閉夾爪"""
        try:
            success = self.robot.close_gripper()
            
            if success:
                logger.info("Gripper closed")
                QMessageBox.information(self, "成功", "夾爪已關閉")
            else:
                QMessageBox.warning(self, "失敗", "關閉夾爪失敗")
                
        except Exception as e:
            logger.error(f"Failed to close gripper: {e}")
            QMessageBox.critical(self, "錯誤", f"關閉夾爪失敗: {str(e)}")
            
    # ========================================
    # 檔案操作
    # ========================================
    
    def save_position_storage(self):
        """保存位置庫到文件"""
        try:
            from config import Config
            Config.save_positions()
            logger.info("Position storage saved")
        except Exception as e:
            logger.error(f"Failed to save position storage: {e}")
            
    def export_positions(self):
        """匯出位置庫"""
        try:
            from PyQt5.QtWidgets import QFileDialog
            
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "匯出位置庫",
                "positions.json",
                "JSON Files (*.json);;All Files (*)"
            )
            
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(self.position_storage, f, indent=2, ensure_ascii=False)
                    
                QMessageBox.information(
                    self,
                    "匯出成功",
                    f"位置庫已匯出到:\n{filename}"
                )
                
        except Exception as e:
            logger.error(f"Failed to export positions: {e}")
            QMessageBox.critical(self, "錯誤", f"匯出失敗: {str(e)}")
            
    def close_tool(self):
        """關閉工具"""
        # 如果還在 freedrive 模式，先停止
        if self.is_freedrive_enabled:
            self.disable_freedrive()
            
        self.close()
        
    @staticmethod
    def get_timestamp():
        """獲取當前時間戳"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
```

### 3.2 整合到主程式

```python
# main_window.py 中添加 Hand Guiding Tool

class MainWindow(QMainWindow):
    """主視窗"""
    
    def __init__(self):
        super().__init__()
        # ... 其他初始化
        
        # 添加 Hand Guiding 選單項
        self.create_hand_guiding_menu()
        
    def create_hand_guiding_menu(self):
        """創建 Hand Guiding 選單"""
        tools_menu = self.menuBar().addMenu("工具")
        
        hand_guiding_action = QAction("🎓 Hand Guiding - 位置教學", self)
        hand_guiding_action.setShortcut("Ctrl+H")
        hand_guiding_action.triggered.connect(self.open_hand_guiding_tool)
        tools_menu.addAction(hand_guiding_action)
        
    def open_hand_guiding_tool(self):
        """開啟 Hand Guiding Tool"""
        if not hasattr(self, 'hand_guiding_tool'):
            from hand_guiding_tool import HandGuidingTool
            from config import Config
            
            self.hand_guiding_tool = HandGuidingTool(
                robot_interface=self.robot,
                position_storage=Config.PRESET_POSITIONS,
                parent=self
            )
            
        self.hand_guiding_tool.show()
        self.hand_guiding_tool.raise_()
        self.hand_guiding_tool.activateWindow()
```

### 3.3 在 Sequential Controller 中使用保存的位置

```python
# sequential_controller_ui.py 中的位置選擇器會自動載入新位置

class ActionParameterDialog(QDialog):
    """動作參數編輯對話框"""
    
    def _add_position_selector(self, layout):
        """添加位置選擇器"""
        from config import Config
        
        self.position_combo = QComboBox()
        
        # 載入所有位置 (包括 Hand Guiding Tool 保存的位置)
        positions = list(Config.PRESET_POSITIONS.keys())
        self.position_combo.addItems(positions)
        
        # 顯示位置來源
        self.position_combo.setToolTip(
            "這些位置來自:\n"
            "• 預設配置\n"
            "• Hand Guiding Tool 教學"
        )
        
        layout.addRow("位置名稱:", self.position_combo)
```

---

## 四、使用範例

### 4.1 完整工作流程

**步驟 1: 開啟 Hand Guiding Tool**

```
主選單 → 工具 → Hand Guiding - 位置教學
或按快捷鍵: Ctrl+H
```

**步驟 2: 教學位置**

```python
# 使用者操作流程:

1. 點擊 "啟用手動引導"
   → 機器人進入 Freedrive 模式
   
2. 手動移動機器人到第一個位置
   → 螢幕顯示即時座標
   
3. 點擊 "保存當前位置"
   → 輸入: "pickup_point"
   → 位置已保存
   
4. 手動移動機器人到第二個位置
   → 點擊 "保存當前位置"
   → 輸入: "place_point"
   
5. 測試夾爪: 點擊 "開啟夾爪"
   → 夾爪打開
   
6. 手動移動到第三個位置
   → 點擊 "保存當前位置"
   → 輸入: "intermediate_point"
   
7. 點擊 "停止手動引導"
   → 完成教學
```

**步驟 3: 在 Sequential Controller 中使用**

```python
# 在 Sequential Controller 中創建程式:

1. Move to Position: "pickup_point"  (剛才教學的位置)
2. Open Gripper
3. Relative Move: Down 5cm
4. Close Gripper
5. Move to Position: "intermediate_point"  (剛才教學的位置)
6. Move to Position: "place_point"  (剛才教學的位置)
7. Open Gripper
8. Home
```

### 4.2 程式碼範例

**完整的 Pick and Place 程式:**

```python
# 在 Sequential Controller 中:

from sequential_controller import SequentialController, Action, ActionType

controller = SequentialController(robot_interface)

# 使用 Hand Guiding Tool 教學的位置
controller.add_action(Action(ActionType.MOVE_TO_POSITION, {
    "position_name": "pickup_point",  # Hand Guiding 教學的位置
    "speed": "medium"
}))

controller.add_action(Action(ActionType.GRIPPER_OPEN, {}))

controller.add_action(Action(ActionType.RELATIVE_MOVE, {
    "direction": "down",
    "distance_cm": 5,
    "speed": "slow"
}))

controller.add_action(Action(ActionType.GRIPPER_CLOSE, {}))

controller.add_action(Action(ActionType.MOVE_TO_POSITION, {
    "position_name": "intermediate_point",  # Hand Guiding 教學的位置
    "speed": "fast"
}))

controller.add_action(Action(ActionType.MOVE_TO_POSITION, {
    "position_name": "place_point",  # Hand Guiding 教學的位置
    "speed": "medium"
}))

controller.add_action(Action(ActionType.GRIPPER_OPEN, {}))

controller.add_action(Action(ActionType.HOME, {}))

# 執行程式
controller.execute_sequence()
```

---

## 五、進階功能

### 5.1 位置微調功能

```python
class HandGuidingTool(QWidget):
    """Hand Guiding 工具 (進階版)"""
    
    def add_position_fine_tuning(self):
        """添加位置微調功能"""
        fine_tune_group = QGroupBox("位置微調")
        layout = QGridLayout()
        
        # 小幅移動按鈕
        step_size = 0.001  # 1mm
        
        # X 軸
        layout.addWidget(QLabel("X:"), 0, 0)
        x_minus = QPushButton("◀ -1mm")
        x_minus.clicked.connect(lambda: self.fine_tune_move('x', -step_size))
        layout.addWidget(x_minus, 0, 1)
        
        x_plus = QPushButton("+1mm ▶")
        x_plus.clicked.connect(lambda: self.fine_tune_move('x', step_size))
        layout.addWidget(x_plus, 0, 2)
        
        # Y 軸
        layout.addWidget(QLabel("Y:"), 1, 0)
        y_minus = QPushButton("◀ -1mm")
        y_minus.clicked.connect(lambda: self.fine_tune_move('y', -step_size))
        layout.addWidget(y_minus, 1, 1)
        
        y_plus = QPushButton("+1mm ▶")
        y_plus.clicked.connect(lambda: self.fine_tune_move('y', step_size))
        layout.addWidget(y_plus, 1, 2)
        
        # Z 軸
        layout.addWidget(QLabel("Z:"), 2, 0)
        z_minus = QPushButton("▼ -1mm")
        z_minus.clicked.connect(lambda: self.fine_tune_move('z', -step_size))
        layout.addWidget(z_minus, 2, 1)
        
        z_plus = QPushButton("▲ +1mm")
        z_plus.clicked.connect(lambda: self.fine_tune_move('z', step_size))
        layout.addWidget(z_plus, 2, 2)
        
        fine_tune_group.setLayout(layout)
        return fine_tune_group
        
    def fine_tune_move(self, axis: str, distance: float):
        """微調移動"""
        try:
            direction_map = {
                'x': 'right' if distance > 0 else 'left',
                'y': 'forward' if distance > 0 else 'backward',
                'z': 'up' if distance > 0 else 'down'
            }
            
            success = self.robot.relative_move(
                direction_map[axis],
                abs(distance) * 100,  # 轉換為 cm
                speed=0.01  # 很慢的速度
            )
            
            if not success:
                QMessageBox.warning(self, "警告", "微調移動失敗")
                
        except Exception as e:
            logger.error(f"Fine tune move failed: {e}")
```

### 5.2 位置序列錄製

```python
class HandGuidingTool(QWidget):
    """Hand Guiding 工具 (序列錄製)"""
    
    def __init__(self, robot_interface, position_storage, parent=None):
        super().__init__(parent)
        self.recording_positions = []  # 錄製的位置序列
        self.is_recording = False
        
    def add_recording_controls(self):
        """添加錄製控制"""
        record_group = QGroupBox("位置序列錄製")
        layout = QVBoxLayout()
        
        self.record_btn = QPushButton("⏺️ 開始錄製")
        self.record_btn.clicked.connect(self.start_recording)
        layout.addWidget(self.record_btn)
        
        self.capture_btn = QPushButton("📸 捕捉位置")
        self.capture_btn.setEnabled(False)
        self.capture_btn.clicked.connect(self.capture_position)
        layout.addWidget(self.capture_btn)
        
        self.stop_record_btn = QPushButton("⏹️ 停止錄製")
        self.stop_record_btn.setEnabled(False)
        self.stop_record_btn.clicked.connect(self.stop_recording)
        layout.addWidget(self.stop_record_btn)
        
        # 顯示已錄製的位置數量
        self.record_count_label = QLabel("已錄製: 0 個位置")
        layout.addWidget(self.record_count_label)
        
        record_group.setLayout(layout)
        return record_group
        
    def start_recording(self):
        """開始錄製序列"""
        self.recording_positions = []
        self.is_recording = True
        
        self.record_btn.setEnabled(False)
        self.capture_btn.setEnabled(True)
        self.stop_record_btn.setEnabled(True)
        
        QMessageBox.information(
            self,
            "開始錄製",
            "移動機器人到各個位置，點擊「捕捉位置」記錄每個位置。"
        )
        
    def capture_position(self):
        """捕捉當前位置"""
        position = self.robot.get_current_pose()
        
        if position:
            self.recording_positions.append(position)
            count = len(self.recording_positions)
            self.record_count_label.setText(f"已錄製: {count} 個位置")
            
            QMessageBox.information(
                self,
                "位置已捕捉",
                f"已捕捉第 {count} 個位置"
            )
            
    def stop_recording(self):
        """停止錄製"""
        self.is_recording = False
        
        self.record_btn.setEnabled(True)
        self.capture_btn.setEnabled(False)
        self.stop_record_btn.setEnabled(False)
        
        if len(self.recording_positions) == 0:
            QMessageBox.information(self, "提示", "未錄製任何位置")
            return
            
        # 保存錄製的序列
        sequence_name, ok = QInputDialog.getText(
            self,
            "保存序列",
            f"已錄製 {len(self.recording_positions)} 個位置。\n請輸入序列名稱:",
            QLineEdit.Normal,
            ""
        )
        
        if ok and sequence_name.strip():
            self.save_position_sequence(sequence_name.strip())
            
    def save_position_sequence(self, sequence_name: str):
        """保存位置序列"""
        for i, position in enumerate(self.recording_positions):
            position_name = f"{sequence_name}_step{i+1}"
            
            position_data = {
                "pose": position,
                "type": "taught_sequence",
                "sequence": sequence_name,
                "step": i + 1,
                "description": f"Recorded position {i+1} in sequence '{sequence_name}'"
            }
            
            self.position_storage[position_name] = position_data
            
        self.refresh_position_list()
        self.save_position_storage()
        
        QMessageBox.information(
            self,
            "保存成功",
            f"序列 '{sequence_name}' 已保存！\n"
            f"共 {len(self.recording_positions)} 個位置。\n\n"
            f"位置名稱:\n" +
            "\n".join([f"• {sequence_name}_step{i+1}" 
                      for i in range(len(self.recording_positions))])
        )
```

---

## 六、安全考量

### 6.1 安全檢查清單

```python
class SafetyChecker:
    """安全檢查器"""
    
    @staticmethod
    def check_before_freedrive() -> bool:
        """Freedrive 前的安全檢查"""
        checks = [
            ("機器人周圍是否無障礙物?", True),
            ("是否已通知周圍人員?", True),
            ("緊急停止按鈕是否可用?", True),
            ("是否熟悉機器人操作?", True),
        ]
        
        dialog = SafetyCheckDialog(checks)
        return dialog.exec_() == QDialog.Accepted
        

class SafetyCheckDialog(QDialog):
    """安全檢查對話框"""
    
    def __init__(self, checks: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("安全檢查")
        self.checks = checks
        self.checkboxes = []
        
        layout = QVBoxLayout(self)
        
        # 標題
        title = QLabel("⚠️ 啟用手動引導前的安全檢查")
        title.setStyleSheet("font-weight: bold; font-size: 14px; color: #F44336;")
        layout.addWidget(title)
        
        # 檢查項目
        for check_text, required in checks:
            cb = QCheckBox(check_text)
            if required:
                cb.setStyleSheet("font-weight: bold;")
            self.checkboxes.append((cb, required))
            layout.addWidget(cb)
            
        # 按鈕
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.validate_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def validate_and_accept(self):
        """驗證並接受"""
        for cb, required in self.checkboxes:
            if required and not cb.isChecked():
                QMessageBox.warning(
                    self,
                    "未完成檢查",
                    "請確認所有安全檢查項目後再繼續。"
                )
                return
                
        self.accept()
```

### 6.2 速度限制

```python
class HandGuidingTool(QWidget):
    """Hand Guiding 工具 (安全版)"""
    
    # 安全速度限制
    MAX_TEACHING_SPEED = 0.1  # m/s
    MAX_TEACHING_ACCELERATION = 0.1  # m/s²
    
    def enable_freedrive_safe(self):
        """啟用安全的 Freedrive 模式"""
        # 設置速度限制
        self.robot.set_speed_limit(self.MAX_TEACHING_SPEED)
        self.robot.set_acceleration_limit(self.MAX_TEACHING_ACCELERATION)
        
        # 啟用碰撞檢測
        self.robot.enable_collision_detection()
        
        # 啟用 freedrive
        success = self.robot.enable_freedrive_mode()
        
        return success
```

---

## 七、總結

### 7.1 核心概念

Hand Guiding Tool 是一個**教學工具**，不是程式邏輯的一部分:

```
❌ 錯誤理解: Hand guiding 是程式的一個步驟
   Program:
   1. Enable hand guiding
   2. Move to position1
   3. Save position1
   ...

✅ 正確理解: Hand guiding 是準備階段的工具
   Preparation (Hand Guiding Tool):
   1. Enable hand guiding
   2. Manually move to position1
   3. Save as "position1"
   4. Manually move to position2
   5. Save as "position2"
   ...
   
   Program (Sequential Controller):
   1. Move to "position1"
   2. Open gripper
   3. Move to "position2"
   4. Close gripper
   ...
```

### 7.2 優點

1. **直觀教學** - 使用者可以實際觸摸和移動機器人
2. **精確定位** - 比輸入數字更容易達到精確位置
3. **安全測試** - 可以在教學階段測試夾爪等功能
4. **位置重用** - 教學的位置可以在多個程式中重用

### 7.3 使用場景

**適合使用 Hand Guiding Tool 的情況:**
- ✅ 需要精確定位的任務
- ✅ 複雜的路徑規劃
- ✅ 新環境的位置學習
- ✅ 非工程背景使用者

**不適合的情況:**
- ❌ 需要動態計算的位置
- ❌ 相對移動 (使用 Relative Move 動作)
- ❌ 感測器驅動的位置

---

**文檔版本:** 1.0  
**最後更新:** 2024-01-15  
**作者:** Tetsu (R&D Associate Director)
