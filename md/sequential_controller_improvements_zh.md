# UR10e 順序控制器介面改進建議

## 執行摘要

當前的順序控制器介面為工程師設計,採用線性列表式的步驟編排方式。雖然功能完整,但對於非工程背景的學生來說,學習曲線較陡峭,缺乏視覺化引導和直觀的操作體驗。本文檔提供具體的改進建議,旨在將介面轉變為更友善、更直觀的視覺化編程環境。

---

## 一、現況分析

### 1.1 後端功能侷限性

**問題描述:**
- 當前 `ActionType` 枚舉只實現了8種基本動作類型:
  - `MOVE_TO_POSITION` (移動到位置)
  - `RELATIVE_MOVE` (相對移動)
  - `SAVE_POSITION` (保存位置)
  - `HOME` (返回原點)
  - `FREEDRIVE` (自由拖動)
  - `WAIT` (等待)
  - `EMERGENCY_STOP` (緊急停止)
  - `CIRCULAR_MOTION` (圓周運動)

- 設計文檔中提及的高級功能尚未實現:
  - 力量控制 (Force Control)
  - 夾爪控制 (Gripper Control)
  - 循環標記 (Loop Markers)
  - 條件分支 (Conditional Branching)

**影響:**
- 非工程學生無法重現文檔中描述的豐富示例
- 限制了教學場景的複雜度和實用性
- 降低了學習者的參與度和成就感

**建議優先級:** 🔴 高

### 1.2 介面設計的侷限

**問題描述:**
- 採用傳統的 `QListWidget` 線性列表展示步驟序列
- 缺乏視覺化流程圖或區塊圖表示
- 步驟之間的關係和執行順序不夠直觀
- 無法表示分支、循環等控制流程

**影響:**
- 對首次使用者來說,理解程序流程需要較高的認知負荷
- 難以快速瀏覽和理解複雜的任務序列
- 不符合現代視覺化編程工具的使用習慣(如 Scratch、Blockly)

**建議優先級:** 🔴 高

### 1.3 參數編輯體驗

**問題描述:**
- 所有動作共用同一個 `ActionParameterDialog` 對話框
- 僅提供下拉選單和數字輸入框,缺乏視覺提示
- 沒有預覽功能,無法在執行前驗證參數效果
- 對於座標、關節角度等技術參數,缺乏友善的解釋

**影響:**
- 非工程學生需要理解笛卡爾座標系和關節空間概念
- 容易設定錯誤參數,導致機器人行為異常
- 缺少即時反饋,降低學習效率

**建議優先級:** 🟡 中

### 1.4 執行反饋機制

**問題描述:**
- 執行反饋僅限於文字狀態更新
- 無法視覺化顯示當前正在執行的步驟
- 缺少執行歷史記錄和回溯功能
- 進度條提供的資訊有限

**影響:**
- 使用者難以追蹤任務執行狀態
- 出錯時不易定位問題步驟
- 缺乏成就感和參與感

**建議優先級:** 🟡 中

---

## 二、核心改進建議

### 2.1 實現節點式視覺化編輯器

#### 2.1.1 設計理念

將傳統的列表視圖轉換為基於節點的流程圖編輯器,類似於視覺化編程工具(Scratch、Node-RED)。

#### 2.1.2 技術實現方案

**方案 A: 基於 QGraphicsView/QGraphicsScene**

```python
class ActionBlockItem(QGraphicsRectItem):
    """動作區塊圖形項目"""
    
    def __init__(self, action: Action):
        super().__init__()
        self.action = action
        self.setup_appearance()
        
    def setup_appearance(self):
        """設置外觀"""
        # 設置大小
        self.setRect(0, 0, 200, 80)
        
        # 根據動作類型設置顏色
        colors = {
            ActionType.MOVE_TO_POSITION: "#4CAF50",
            ActionType.WAIT: "#FF9800",
            ActionType.SAVE_POSITION: "#2196F3",
            # ... 其他類型
        }
        color = colors.get(self.action.action_type, "#9E9E9E")
        self.setBrush(QBrush(QColor(color)))
        
        # 添加圖標和文字
        self.icon_item = QGraphicsPixmapItem(self)
        self.text_item = QGraphicsTextItem(self.action.get_display_text(), self)
        
    def paint(self, painter, option, widget):
        """自定義繪製"""
        # 繪製陰影效果
        # 繪製邊框
        # 繪製連接點
        super().paint(painter, option, widget)


class BlockCanvasView(QGraphicsView):
    """區塊畫布視圖"""
    
    def __init__(self, sequential_controller):
        super().__init__()
        self.seq_controller = sequential_controller
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        
        # 啟用拖放
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setAcceptDrops(True)
        
    def add_action_block(self, action: Action, position=None):
        """添加動作區塊"""
        block = ActionBlockItem(action)
        
        if position:
            block.setPos(position)
        else:
            # 自動排列
            y_offset = len(self.scene.items()) * 100
            block.setPos(50, y_offset)
            
        self.scene.addItem(block)
        self.draw_connectors()
        
    def draw_connectors(self):
        """繪製連接線"""
        # 在區塊之間繪製箭頭連接線
        pass
```

**優點:**
- 完全可控的自定義渲染
- 良好的性能表現
- 豐富的交互可能性

**缺點:**
- 開發工作量較大
- 需要處理複雜的拖放邏輯

**方案 B: 使用 QML + Qt Quick**

```qml
// ActionBlock.qml
Rectangle {
    id: actionBlock
    width: 200
    height: 80
    radius: 8
    color: getColorForActionType(actionType)
    
    Row {
        anchors.centerIn: parent
        spacing: 10
        
        Image {
            source: getIconForActionType(actionType)
            width: 32
            height: 32
        }
        
        Text {
            text: actionDescription
            font.pixelSize: 14
            color: "white"
        }
    }
    
    // 拖動手柄
    MouseArea {
        anchors.fill: parent
        drag.target: parent
        onClicked: showParameterDialog()
    }
    
    // 連接點
    Rectangle {
        id: inputConnector
        width: 12
        height: 12
        radius: 6
        color: "white"
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
    }
    
    Rectangle {
        id: outputConnector
        width: 12
        height: 12
        radius: 6
        color: "white"
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
    }
}
```

**優點:**
- 更現代化的外觀
- 聲明式語法,開發效率高
- 動畫效果更流暢

**缺點:**
- 需要團隊熟悉 QML
- 與現有 PyQt5 代碼整合需要額外工作

**推薦方案:** 方案 A (QGraphicsView)

理由:
- 與現有 PyQt5 代碼庫一致性更好
- 不需要學習新的框架
- 更易於維護和除錯

#### 2.1.3 具體實現步驟

**第一階段: 基礎框架 (2-3 週)**

1. 創建 `BlockCanvasView` 類替換 `QListWidget`
2. 實現基本的區塊拖放功能
3. 添加區塊選中、移動、刪除功能
4. 實現自動排列算法

**第二階段: 視覺化增強 (2-3 週)**

1. 為每種動作類型設計獨特的圖標和顏色
2. 添加連接線和箭頭指示執行順序
3. 實現區塊展開/收縮功能(顯示/隱藏參數詳情)
4. 添加執行狀態動畫(當前執行區塊高亮、脈動效果)

**第三階段: 高級功能 (3-4 週)**

1. 實現循環區塊(repeat N times)
2. 實現條件分支區塊(if sensor > threshold)
3. 添加子流程/函數封裝功能
4. 實現區塊搜索和過濾

#### 2.1.4 預期效果

**改進前:**
```
1. 移動到位置: home
2. 等待: 3秒
3. 移動到位置: 左肩上方
4. 啟用壓力
5. 圓周運動: 半徑3cm, 30秒
```

**改進後:**
```
┌─────────────────┐
│  🏠 返回原點      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  ⏱️ 等待 3秒     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  📍 移動到        │
│  "左肩上方"       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  💪 啟用壓力      │
│  等級: 適中       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  🔄 圓周運動      │
│  半徑: 3cm       │
│  時間: 30秒      │
└─────────────────┘
```

### 2.2 重構動作庫介面

#### 2.2.1 分類系統設計

將動作分類為直觀的類別,降低認知負荷:

**類別結構:**

1. **移動類 (Movement) - 🚀**
   - 移動到預設位置
   - 相對移動
   - 返回原點
   - 圓周運動
   - 直線運動

2. **互動類 (Interaction) - 🤝**
   - 啟用壓力控制
   - 自由拖動模式
   - 夾爪開/關
   - 感測器讀取

3. **控制類 (Control Flow) - 🔀**
   - 等待
   - 重複 N 次
   - 如果...則...
   - 並行執行

4. **管理類 (Management) - 🛠️**
   - 保存當前位置
   - 載入位置
   - 設定速度
   - 設定加速度

5. **安全類 (Safety) - ⚠️**
   - 緊急停止
   - 啟用安全區域
   - 碰撞檢測開關

6. **自定義類 (Custom) - ⭐**
   - 使用者自定義動作
   - 腳本執行
   - 外部程式呼叫

#### 2.2.2 實現方案

```python
class CategorizedActionLibrary(QWidget):
    """分類動作庫"""
    
    CATEGORIES = {
        "movement": {
            "name": "移動",
            "icon": "🚀",
            "color": "#4CAF50",
            "actions": [
                ActionType.MOVE_TO_POSITION,
                ActionType.RELATIVE_MOVE,
                ActionType.HOME,
                ActionType.CIRCULAR_MOTION,
            ]
        },
        "interaction": {
            "name": "互動",
            "icon": "🤝",
            "color": "#2196F3",
            "actions": [
                ActionType.ENABLE_FORCE,
                ActionType.FREEDRIVE,
                # ActionType.GRIPPER_OPEN,
                # ActionType.GRIPPER_CLOSE,
            ]
        },
        # ... 其他類別
    }
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 類別選擇器(標籤頁或按鈕組)
        self.category_tabs = QTabWidget()
        
        for cat_id, cat_info in self.CATEGORIES.items():
            # 為每個類別創建一個標籤頁
            page = self.create_category_page(cat_info)
            icon_label = QLabel(cat_info["icon"])
            self.category_tabs.addTab(page, cat_info["name"])
            
        layout.addWidget(self.category_tabs)
        
    def create_category_page(self, category_info):
        """創建類別頁面"""
        page = QWidget()
        layout = QGridLayout(page)
        
        # 以卡片形式展示動作
        row, col = 0, 0
        for action_type in category_info["actions"]:
            card = self.create_action_card(action_type, category_info["color"])
            layout.addWidget(card, row, col)
            
            col += 1
            if col >= 2:  # 每行2個卡片
                col = 0
                row += 1
                
        return page
        
    def create_action_card(self, action_type: ActionType, color: str):
        """創建動作卡片"""
        metadata = ACTION_METADATA[action_type]
        
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {color};
                border-radius: 8px;
                padding: 15px;
            }}
            QFrame:hover {{
                background-color: {self.darken_color(color)};
                cursor: pointer;
            }}
        """)
        
        layout = QVBoxLayout(card)
        
        # 圖標
        icon_label = QLabel(metadata.get("icon", "⚙️"))
        icon_label.setStyleSheet("font-size: 36px;")
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)
        
        # 名稱
        name_label = QLabel(metadata.get("name", ""))
        name_label.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
        name_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(name_label)
        
        # 描述(可選)
        if metadata.get("description"):
            desc_label = QLabel(metadata["description"][:50] + "...")
            desc_label.setStyleSheet("color: white; font-size: 10px;")
            desc_label.setWordWrap(True)
            desc_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(desc_label)
        
        # 點擊事件
        card.mousePressEvent = lambda e: self.on_card_clicked(action_type)
        
        return card
        
    def on_card_clicked(self, action_type: ActionType):
        """卡片點擊事件"""
        # 觸發添加動作事件
        self.action_selected.emit(action_type)
```

#### 2.2.3 預期效果

**改進前:**
- 單一列表,需要上下滾動尋找動作
- 所有動作混在一起,難以快速定位

**改進後:**
- 分類標籤頁,一目了然
- 大圖標卡片,易於識別
- 顏色編碼,強化記憶

### 2.3 優化參數編輯對話框

#### 2.3.1 增加視覺提示

**現有問題:**
- 純文字標籤,缺乏直觀性
- 技術術語對初學者不友善

**改進方案:**

```python
class EnhancedActionParameterDialog(QDialog):
    """增強型參數編輯對話框"""
    
    def _add_position_selector_enhanced(self, layout):
        """增強版位置選擇器"""
        
        # 位置預覽圖
        preview_label = QLabel()
        preview_pixmap = QPixmap("resources/robot_positions/home.png")
        preview_label.setPixmap(preview_pixmap.scaled(200, 200, Qt.KeepAspectRatio))
        layout.addRow("位置示意圖:", preview_label)
        
        # 位置選擇器
        self.position_combo = QComboBox()
        positions = list(Config.PRESET_POSITIONS.keys())
        self.position_combo.addItems(positions)
        
        # 當選擇改變時,更新預覽圖
        self.position_combo.currentTextChanged.connect(
            lambda name: self.update_preview(preview_label, name)
        )
        
        layout.addRow("選擇位置:", self.position_combo)
        
        # 座標資訊(只讀,供參考)
        coord_label = QLabel()
        coord_label.setStyleSheet("color: gray; font-size: 11px;")
        self.update_coordinate_info(coord_label, self.position_combo.currentText())
        layout.addRow("座標參考:", coord_label)
        
        # 預覽按鈕
        preview_btn = QPushButton("🔍 預覽動作")
        preview_btn.clicked.connect(self.preview_action)
        layout.addRow("", preview_btn)
        
    def preview_action(self):
        """預覽動作(安全模式)"""
        # 調用機器人API以慢速、安全模式執行動作
        # 使用者可以看到機器人如何移動,但不會真正完成任務
        pass
        
    def _add_speed_selector_enhanced(self, layout):
        """增強版速度選擇器"""
        
        speed_group = QWidget()
        speed_layout = QHBoxLayout(speed_group)
        
        self.speed_buttons = QButtonGroup()
        speeds = [
            ("🐌 慢速", "slow", "適合精細操作"),
            ("🚶 中速", "medium", "一般任務"),
            ("🚀 快速", "fast", "熟悉後使用")
        ]
        
        for i, (label, value, tooltip) in enumerate(speeds):
            btn = QRadioButton(label)
            btn.setToolTip(tooltip)
            btn.setStyleSheet("""
                QRadioButton {
                    padding: 10px;
                    font-size: 13px;
                }
                QRadioButton:checked {
                    background-color: #E3F2FD;
                    border-radius: 4px;
                }
            """)
            self.speed_buttons.addButton(btn, i)
            speed_layout.addWidget(btn)
            
        layout.addRow("移動速度:", speed_group)
        
        # 添加說明文字
        info_label = QLabel("💡 初學者建議使用慢速,避免意外")
        info_label.setStyleSheet("color: #FF9800; font-size: 11px; padding: 5px;")
        layout.addRow("", info_label)
```

#### 2.3.2 增加預設值模板

**設計理念:**
提供自然語言描述的預設值組合,讓使用者無需理解技術細節即可開始。

**實現範例:**

```python
class ParameterPresets:
    """參數預設值庫"""
    
    PRESETS = {
        ActionType.MOVE_TO_POSITION: {
            "回到起始位置": {
                "position_name": "home",
                "speed": "medium",
                "description": "讓機器人返回安全的起始位置"
            },
            "移動到患者左肩": {
                "position_name": "patient_left_shoulder",
                "speed": "slow",
                "description": "緩慢移動到患者左肩上方,準備按摩"
            },
            "快速移動到等待區": {
                "position_name": "waiting_area",
                "speed": "fast",
                "description": "快速移動到等待區,不進行操作"
            }
        },
        ActionType.CIRCULAR_MOTION: {
            "肩部舒緩按摩": {
                "radius_cm": 3,
                "duration_sec": 30,
                "speed": "slow",
                "description": "小幅度圓周運動,適合肩部舒緩"
            },
            "背部大範圍按摩": {
                "radius_cm": 8,
                "duration_sec": 60,
                "speed": "medium",
                "description": "較大幅度圓周運動,適合背部放鬆"
            }
        }
    }
    
    @classmethod
    def get_presets(cls, action_type: ActionType):
        """取得特定動作類型的預設值"""
        return cls.PRESETS.get(action_type, {})


class EnhancedActionParameterDialog(QDialog):
    """增強型參數編輯對話框"""
    
    def add_preset_selector(self, layout, action_type: ActionType):
        """添加預設值選擇器"""
        presets = ParameterPresets.get_presets(action_type)
        
        if not presets:
            return
            
        preset_group = QGroupBox("🎯 快速設定模板")
        preset_layout = QVBoxLayout()
        
        for preset_name, preset_values in presets.items():
            btn = QPushButton(preset_name)
            btn.setToolTip(preset_values.get("description", ""))
            btn.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 10px;
                    background-color: #F5F5F5;
                    border: 1px solid #E0E0E0;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #E8F5E9;
                    border-color: #4CAF50;
                }
            """)
            btn.clicked.connect(
                lambda checked, pv=preset_values: self.apply_preset(pv)
            )
            preset_layout.addWidget(btn)
            
        preset_group.setLayout(preset_layout)
        layout.addRow("", preset_group)
        
    def apply_preset(self, preset_values: dict):
        """應用預設值"""
        # 根據 preset_values 自動填充對話框中的控件
        if "position_name" in preset_values:
            index = self.position_combo.findText(preset_values["position_name"])
            if index >= 0:
                self.position_combo.setCurrentIndex(index)
                
        if "speed" in preset_values:
            speed_map = {"slow": 0, "medium": 1, "fast": 2}
            self.speed_combo.setCurrentIndex(speed_map[preset_values["speed"]])
            
        # ... 其他參數
        
        QMessageBox.information(
            self, "已套用模板",
            f"已套用預設值,您可以直接使用或進行微調"
        )
```

#### 2.3.3 添加互動式幫助

**GIF 動畫示範:**

```python
class HelpAnimationWidget(QLabel):
    """幫助動畫 Widget"""
    
    def __init__(self, gif_path: str):
        super().__init__()
        self.movie = QMovie(gif_path)
        self.setMovie(self.movie)
        self.movie.start()
        self.setFixedSize(300, 200)
        self.setScaledContents(True)


class EnhancedActionParameterDialog(QDialog):
    """增強型參數編輯對話框"""
    
    def add_help_section(self, layout, action_type: ActionType):
        """添加幫助區段"""
        
        help_group = QGroupBox("📚 操作說明")
        help_layout = QVBoxLayout()
        
        # GIF 動畫
        gif_path = f"resources/help_animations/{action_type.value}.gif"
        if os.path.exists(gif_path):
            animation = HelpAnimationWidget(gif_path)
            help_layout.addWidget(animation)
            
        # 文字說明
        help_text = self.get_help_text(action_type)
        help_label = QLabel(help_text)
        help_label.setWordWrap(True)
        help_label.setStyleSheet("padding: 10px; background-color: #E3F2FD; border-radius: 4px;")
        help_layout.addWidget(help_label)
        
        # 展開/收起按鈕
        toggle_btn = QPushButton("收起說明 ▲")
        toggle_btn.clicked.connect(lambda: self.toggle_help(help_group, toggle_btn))
        help_layout.addWidget(toggle_btn)
        
        help_group.setLayout(help_layout)
        layout.addRow("", help_group)
        
    def get_help_text(self, action_type: ActionType) -> str:
        """取得幫助文字"""
        help_texts = {
            ActionType.MOVE_TO_POSITION: 
                "將機器人手臂移動到預先設定的位置。\n"
                "💡 提示: 使用「慢速」可以更安全地移動",
            ActionType.CIRCULAR_MOTION:
                "讓機器人手臂執行圓周運動。\n"
                "💡 提示: 半徑越小,運動越精細",
            # ... 其他說明
        }
        return help_texts.get(action_type, "")
```

### 2.4 擴充後端 ActionType

#### 2.4.1 新增動作類型

**待實現的動作類型:**

```python
class ActionType(str, Enum):
    """動作類型枚舉(擴充版)"""
    
    # === 現有動作 ===
    MOVE_TO_POSITION = "move_to_position"
    RELATIVE_MOVE = "relative_move"
    SAVE_POSITION = "save_position"
    HOME = "home"
    FREEDRIVE = "freedrive"
    WAIT = "wait"
    EMERGENCY_STOP = "emergency_stop"
    CIRCULAR_MOTION = "circular_motion"
    
    # === 新增: 力量控制 ===
    ENABLE_FORCE = "enable_force"
    DISABLE_FORCE = "disable_force"
    SET_FORCE_LEVEL = "set_force_level"
    
    # === 新增: 夾爪控制 ===
    GRIPPER_OPEN = "gripper_open"
    GRIPPER_CLOSE = "gripper_close"
    GRIPPER_MOVE = "gripper_move"  # 移動到特定開合度
    
    # === 新增: 進階運動 ===
    LINEAR_MOTION = "linear_motion"  # 直線運動
    ARC_MOTION = "arc_motion"  # 弧線運動
    SPIRAL_MOTION = "spiral_motion"  # 螺旋運動
    
    # === 新增: 控制流程 ===
    REPEAT_START = "repeat_start"  # 重複開始標記
    REPEAT_END = "repeat_end"  # 重複結束標記
    IF_CONDITION = "if_condition"  # 條件判斷
    PARALLEL_START = "parallel_start"  # 並行執行開始
    PARALLEL_END = "parallel_end"  # 並行執行結束
    
    # === 新增: 感測器 ===
    READ_SENSOR = "read_sensor"  # 讀取感測器
    WAIT_FOR_SENSOR = "wait_for_sensor"  # 等待感測器條件
    
    # === 新增: 進階功能 ===
    CALL_SCRIPT = "call_script"  # 呼叫外部腳本
    SEND_SIGNAL = "send_signal"  # 發送信號
    PLAY_SOUND = "play_sound"  # 播放聲音


# 更新元數據
ACTION_METADATA = {
    ActionType.MOVE_TO_POSITION: {
        "name": "移動到位置",
        "icon": "📍",
        "description": "將機器人移動到預設位置",
        "category": "movement",
        "parameters": ["position_name", "speed"],
        "difficulty": "beginner"
    },
    ActionType.ENABLE_FORCE: {
        "name": "啟用壓力",
        "icon": "💪",
        "description": "啟用力量控制,感知接觸力道",
        "category": "interaction",
        "parameters": ["force_level"],
        "difficulty": "intermediate"
    },
    ActionType.GRIPPER_OPEN: {
        "name": "打開夾爪",
        "icon": "🤲",
        "description": "完全打開機器人夾爪",
        "category": "interaction",
        "parameters": ["speed"],
        "difficulty": "beginner"
    },
    ActionType.REPEAT_START: {
        "name": "重複開始",
        "icon": "🔁",
        "description": "標記重複區塊的開始",
        "category": "control_flow",
        "parameters": ["repeat_count"],
        "difficulty": "intermediate"
    },
    ActionType.IF_CONDITION: {
        "name": "條件判斷",
        "icon": "❓",
        "description": "根據條件決定是否執行後續動作",
        "category": "control_flow",
        "parameters": ["condition_type", "threshold"],
        "difficulty": "advanced"
    },
    # ... 其他元數據
}
```

#### 2.4.2 實現策略

**階段性實現:**

**第一階段(立即實現):**
- ✅ `ENABLE_FORCE` - 使用現有 UR10e API
- ✅ `GRIPPER_OPEN/CLOSE` - 如果已有夾爪硬體
- ✅ `LINEAR_MOTION` - 使用 moveL API

**第二階段(2-4週):**
- 🔄 `REPEAT_START/END` - 純軟體邏輯
- 🔄 `READ_SENSOR` - 如果已有感測器整合
- 🔄 `SPIRAL_MOTION` - 組合現有運動API

**第三階段(長期規劃):**
- 📅 `IF_CONDITION` - 需要設計條件評估框架
- 📅 `PARALLEL_START/END` - 需要多執行緒管理
- 📅 `CALL_SCRIPT` - 安全性考量

**即使硬體未就緒,也應添加佔位實現:**

```python
class SequentialController:
    """順序控制器"""
    
    def execute_action(self, action: Action) -> bool:
        """執行動作"""
        
        if action.action_type == ActionType.GRIPPER_OPEN:
            if not self.hardware_available["gripper"]:
                logger.warning("夾爪硬體未連接,模擬執行")
                self.simulate_gripper_action("open")
                return True
            else:
                return self.real_gripper_open(action.parameters)
                
        # ... 其他動作
        
    def simulate_gripper_action(self, action_name: str):
        """模擬夾爪動作(用於教學)"""
        logger.info(f"[模擬模式] 執行夾爪動作: {action_name}")
        # 可以在 GUI 顯示動畫
        self.gui_signals.show_simulation_animation.emit("gripper", action_name)
```

**好處:**
- 讓學生能夠完整體驗編程流程
- 提早發現介面設計問題
- 硬體到位後可快速切換

### 2.5 實現引導式任務生成器

#### 2.5.1 設計理念

提供問答式介面,透過簡單的問題引導使用者自動生成任務序列。

#### 2.5.2 技術實現

```python
class GuidedModeWizard(QWizard):
    """引導模式精靈"""
    
    def __init__(self, sequential_controller: SequentialController, parent=None):
        super().__init__(parent)
        self.seq_controller = sequential_controller
        self.setWindowTitle("任務建立精靈")
        self.setWizardStyle(QWizard.ModernStyle)
        
        # 添加頁面
        self.addPage(WelcomePage())
        self.addPage(TaskTypePage())
        self.addPage(TargetLocationPage())
        self.addPage(OperationTypePage())
        self.addPage(SafetyCheckPage())
        self.addPage(SummaryPage())
        
    def accept(self):
        """完成精靈,生成任務"""
        task_config = self.collect_user_choices()
        actions = self.generate_actions_from_config(task_config)
        
        for action in actions:
            self.seq_controller.add_action(action)
            
        super().accept()


class TaskTypePage(QWizardPage):
    """任務類型選擇頁面"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("選擇您想要執行的任務類型")
        self.setSubTitle("選擇最接近您需求的任務類型,我們會為您生成基礎程式")
        
        layout = QVBoxLayout()
        
        self.task_group = QButtonGroup()
        
        tasks = [
            ("simple_massage", "🧘 簡單按摩", "讓機器人在一個位置進行輕柔按摩"),
            ("pick_and_place", "🔄 拿取與放置", "讓機器人從A點拿取物品放到B點"),
            ("patrol", "👀 巡邏檢查", "讓機器人依序移動到多個檢查點"),
            ("custom", "⚙️ 自定義任務", "從零開始建立自己的任務")
        ]
        
        for i, (task_id, task_name, task_desc) in enumerate(tasks):
            btn = QRadioButton(task_name)
            btn.setStyleSheet("QRadioButton { font-size: 14px; font-weight: bold; padding: 10px; }")
            
            desc_label = QLabel(task_desc)
            desc_label.setStyleSheet("QLabel { margin-left: 30px; color: gray; margin-bottom: 10px; }")
            
            layout.addWidget(btn)
            layout.addWidget(desc_label)
            
            self.task_group.addButton(btn, i)
            
        self.setLayout(layout)
        
    def validatePage(self):
        """驗證頁面"""
        if self.task_group.checkedId() < 0:
            QMessageBox.warning(self, "提示", "請選擇一個任務類型")
            return False
        return True


class TargetLocationPage(QWizardPage):
    """目標位置選擇頁面"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("設定目標位置")
        self.setSubTitle("告訴我們機器人應該在哪裡操作")
        
        layout = QVBoxLayout()
        
        # 位置選擇
        location_group = QGroupBox("選擇操作位置")
        location_layout = QVBoxLayout()
        
        self.location_combo = QComboBox()
        self.location_combo.addItems(list(Config.PRESET_POSITIONS.keys()))
        location_layout.addWidget(QLabel("從預設位置選擇:"))
        location_layout.addWidget(self.location_combo)
        
        # 或者教學新位置
        teach_btn = QPushButton("🎓 教學新位置")
        teach_btn.setToolTip("啟用自由拖動模式,手動移動機器人到目標位置")
        teach_btn.clicked.connect(self.teach_position)
        location_layout.addWidget(teach_btn)
        
        location_group.setLayout(location_layout)
        layout.addWidget(location_group)
        
        self.setLayout(layout)
        
    def teach_position(self):
        """教學位置"""
        reply = QMessageBox.question(
            self,
            "教學位置",
            "即將進入自由拖動模式。\n\n"
            "請:\n"
            "1. 手動移動機器人到目標位置\n"
            "2. 點擊「完成」按鈕\n\n"
            "準備好了嗎?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 啟用自由拖動
            # 顯示「完成」按鈕
            # 保存位置
            pass


class TaskTemplateGenerator:
    """任務範本生成器"""
    
    TEMPLATES = {
        "simple_massage": [
            # 1. 移動到目標位置
            Action(ActionType.MOVE_TO_POSITION, {
                "position_name": "{target_location}",
                "speed": "slow"
            }),
            # 2. 啟用力量控制
            Action(ActionType.ENABLE_FORCE, {
                "force_level": "gentle"
            }),
            # 3. 執行圓周運動
            Action(ActionType.CIRCULAR_MOTION, {
                "radius_cm": 3,
                "duration_sec": 30,
                "speed": "slow"
            }),
            # 4. 返回原點
            Action(ActionType.HOME, {}),
        ],
        
        "pick_and_place": [
            # 1. 移動到拾取位置
            Action(ActionType.MOVE_TO_POSITION, {
                "position_name": "{pickup_location}",
                "speed": "medium"
            }),
            # 2. 打開夾爪
            Action(ActionType.GRIPPER_OPEN, {}),
            # 3. 下降接近物品
            Action(ActionType.RELATIVE_MOVE, {
                "direction": "down",
                "distance_cm": 5,
                "speed": "slow"
            }),
            # 4. 關閉夾爪
            Action(ActionType.GRIPPER_CLOSE, {}),
            # 5. 上升
            Action(ActionType.RELATIVE_MOVE, {
                "direction": "up",
                "distance_cm": 10,
                "speed": "slow"
            }),
            # 6. 移動到放置位置
            Action(ActionType.MOVE_TO_POSITION, {
                "position_name": "{place_location}",
                "speed": "medium"
            }),
            # 7. 打開夾爪釋放物品
            Action(ActionType.GRIPPER_OPEN, {}),
            # 8. 返回原點
            Action(ActionType.HOME, {}),
        ],
        
        "patrol": [
            # 動態生成巡邏路徑
        ]
    }
    
    @classmethod
    def generate_from_template(cls, template_name: str, parameters: dict) -> list[Action]:
        """從範本生成動作序列"""
        template = cls.TEMPLATES.get(template_name, [])
        
        # 替換參數
        actions = []
        for action_template in template:
            params = action_template.parameters.copy()
            
            # 替換參數中的佔位符
            for key, value in params.items():
                if isinstance(value, str) and value.startswith("{"):
                    param_name = value.strip("{}")
                    params[key] = parameters.get(param_name, value)
                    
            actions.append(Action(action_template.action_type, params))
            
        return actions
```

#### 2.5.3 使用流程

1. 使用者點擊「引導模式」按鈕
2. 回答 4-6 個簡單問題:
   - 想要執行什麼類型的任務?
   - 目標位置在哪裡?
   - 需要什麼操作?(按摩/拿取/檢查)
   - 速度偏好?(慢/中/快)
3. 系統自動生成任務序列
4. 使用者可以在視覺化編輯器中微調

### 2.6 增強執行反饋機制

#### 2.6.1 視覺化執行狀態

**實現方案:**

```python
class BlockCanvasView(QGraphicsView):
    """區塊畫布視圖(增強版)"""
    
    def highlight_executing_block(self, step_index: int):
        """高亮正在執行的區塊"""
        for i, item in enumerate(self.scene.items()):
            if isinstance(item, ActionBlockItem):
                if i == step_index:
                    # 當前執行中 - 脈動動畫
                    item.set_state("executing")
                    self.start_pulse_animation(item)
                elif i < step_index:
                    # 已完成 - 綠色勾選
                    item.set_state("completed")
                else:
                    # 待執行 - 預設樣式
                    item.set_state("pending")
                    
    def start_pulse_animation(self, item: ActionBlockItem):
        """啟動脈動動畫"""
        animation = QPropertyAnimation(item, b"scale")
        animation.setDuration(1000)
        animation.setStartValue(1.0)
        animation.setEndValue(1.1)
        animation.setEasingCurve(QEasingCurve.InOutQuad)
        animation.setLoopCount(-1)  # 無限循環
        animation.start()
        
        self.current_animation = animation


class ActionBlockItem(QGraphicsRectItem):
    """動作區塊圖形項目(增強版)"""
    
    def set_state(self, state: str):
        """設置區塊狀態"""
        self.state = state
        
        if state == "pending":
            self.setBrush(QBrush(self.default_color))
            self.opacity = 0.7
        elif state == "executing":
            self.setBrush(QBrush(QColor("#FF9800")))
            self.opacity = 1.0
            # 添加邊框動畫
        elif state == "completed":
            self.setBrush(QBrush(QColor("#4CAF50")))
            self.opacity = 0.8
            # 添加勾選圖示
            self.show_checkmark()
        elif state == "error":
            self.setBrush(QBrush(QColor("#F44336")))
            self.opacity = 1.0
            # 添加錯誤圖示
            
    def show_checkmark(self):
        """顯示勾選圖示"""
        checkmark = QGraphicsTextItem("✓", self)
        checkmark.setDefaultTextColor(QColor("white"))
        checkmark.setFont(QFont("Arial", 24, QFont.Bold))
        checkmark.setPos(150, 25)
```

#### 2.6.2 執行歷史記錄

```python
class ExecutionHistoryPanel(QWidget):
    """執行歷史面板"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 標題
        title = QLabel("📜 執行歷史")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(title)
        
        # 歷史列表
        self.history_list = QListWidget()
        self.history_list.setStyleSheet("""
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #e0e0e0;
            }
        """)
        layout.addWidget(self.history_list)
        
        # 控制按鈕
        btn_layout = QHBoxLayout()
        
        clear_btn = QPushButton("清除歷史")
        clear_btn.clicked.connect(self.clear_history)
        btn_layout.addWidget(clear_btn)
        
        export_btn = QPushButton("匯出日誌")
        export_btn.clicked.connect(self.export_log)
        btn_layout.addWidget(export_btn)
        
        layout.addLayout(btn_layout)
        
    def add_history_entry(self, step_index: int, action_name: str,
                          status: str, timestamp: str, duration: float):
        """添加歷史記錄"""
        
        icon = {
            "completed": "✅",
            "error": "❌",
            "skipped": "⏭️"
        }.get(status, "❓")
        
        text = (f"{icon} 步驟 {step_index + 1}: {action_name}\n"
                f"   狀態: {status} | 耗時: {duration:.2f}秒 | {timestamp}")
        
        item = QListWidgetItem(text)
        
        if status == "error":
            item.setBackground(QColor("#FFCDD2"))
        elif status == "completed":
            item.setBackground(QColor("#C8E6C9"))
            
        self.history_list.addItem(item)
        
        # 自動滾動到最新記錄
        self.history_list.scrollToBottom()
```

#### 2.6.3 實時參數顯示

```python
class ExecutionMonitorWidget(QWidget):
    """執行監控 Widget"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 當前動作
        current_group = QGroupBox("🎯 當前執行")
        current_layout = QFormLayout()
        
        self.action_label = QLabel("無")
        self.action_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        current_layout.addRow("動作:", self.action_label)
        
        self.progress_label = QLabel("0 / 0")
        current_layout.addRow("進度:", self.progress_label)
        
        self.time_label = QLabel("00:00")
        current_layout.addRow("已用時間:", self.time_label)
        
        current_group.setLayout(current_layout)
        layout.addWidget(current_group)
        
        # 機器人狀態
        robot_group = QGroupBox("🤖 機器人狀態")
        robot_layout = QFormLayout()
        
        self.position_label = QLabel("N/A")
        robot_layout.addRow("當前位置:", self.position_label)
        
        self.speed_label = QLabel("N/A")
        robot_layout.addRow("當前速度:", self.speed_label)
        
        self.force_label = QLabel("N/A")
        robot_layout.addRow("接觸力:", self.force_label)
        
        robot_group.setLayout(robot_layout)
        layout.addWidget(robot_group)
        
    def update_robot_status(self, position: list, speed: float, force: float):
        """更新機器人狀態"""
        pos_str = f"[{position[0]:.2f}, {position[1]:.2f}, {position[2]:.2f}]"
        self.position_label.setText(pos_str)
        self.speed_label.setText(f"{speed:.2f} mm/s")
        self.force_label.setText(f"{force:.2f} N")
```

---

## 三、實施路線圖

### 階段一: 基礎視覺化 (4-6 週)

**目標:** 建立基本的區塊式編輯器

**任務清單:**
- [ ] 實現 `BlockCanvasView` 替代 `QListWidget`
- [ ] 創建 `ActionBlockItem` 圖形項目
- [ ] 實現基本拖放功能
- [ ] 添加區塊連接線繪製
- [ ] 重構動作庫為卡片式分類介面
- [ ] 測試與除錯

**驗收標準:**
- 能夠以區塊形式添加、移動、刪除動作
- 區塊之間有視覺化連接線
- 動作庫按類別分組顯示

### 階段二: 增強互動體驗 (4-6 週)

**目標:** 優化參數編輯和執行反饋

**任務清單:**
- [ ] 增強 `ActionParameterDialog` (添加圖像、預設值)
- [ ] 實現參數預覽功能
- [ ] 添加執行狀態高亮動畫
- [ ] 實現執行歷史面板
- [ ] 添加實時監控 Widget
- [ ] 測試與除錯

**驗收標準:**
- 參數對話框包含視覺提示和預設值
- 執行時區塊會高亮並有動畫效果
- 能夠查看執行歷史和實時狀態

### 階段三: 擴充動作類型 (6-8 週)

**目標:** 實現文檔中描述的高級功能

**任務清單:**
- [ ] 實現力量控制相關動作
- [ ] 實現夾爪控制(如有硬體)
- [ ] 實現循環和條件分支邏輯
- [ ] 添加感測器讀取動作
- [ ] 更新後端執行引擎支援新動作
- [ ] 創建測試案例

**驗收標準:**
- 至少新增 10 種動作類型
- 支援基本的循環和條件控制
- 所有新動作都有對應的 UI 元素

### 階段四: 引導式工具 (3-4 週)

**目標:** 降低入門門檻

**任務清單:**
- [ ] 實現任務建立精靈
- [ ] 創建任務範本庫
- [ ] 實現範本參數化系統
- [ ] 添加教學模式(逐步指引)
- [ ] 創建使用者文檔和影片教學

**驗收標準:**
- 非技術使用者能在 5 分鐘內創建第一個任務
- 至少提供 5 個常用任務範本
- 完整的中文使用說明

### 階段五: 優化與測試 (2-3 週)

**目標:** 確保系統穩定性和易用性

**任務清單:**
- [ ] 使用者測試(找 5-10 位非工程背景學生)
- [ ] 收集反饋並改進
- [ ] 性能優化
- [ ] 撰寫維護文檔
- [ ] 代碼審查與重構

**驗收標準:**
- 使用者滿意度評分 ≥ 4/5
- 無嚴重 Bug
- 代碼覆蓋率 ≥ 70%

---

## 四、技術決策建議

### 4.1 視覺化方案選擇

**推薦:** QGraphicsView/QGraphicsScene

**理由:**
- 與現有 PyQt5 代碼庫一致
- 豐富的圖形 API,易於自定義
- 良好的性能表現
- 團隊不需要學習新框架

### 4.2 動作執行架構

**當前問題:**
- 動作執行在主執行緒,可能阻塞 UI

**建議改進:**

```python
# 使用 QThread 進行非同步執行
class ActionExecutor(QThread):
    """動作執行器(非同步)"""
    
    action_started = pyqtSignal(int, str)
    action_completed = pyqtSignal(int, bool)
    progress_updated = pyqtSignal(int, int)
    
    def __init__(self, actions: list[Action], robot_interface):
        super().__init__()
        self.actions = actions
        self.robot = robot_interface
        self.is_paused = False
        self.should_stop = False
        
    def run(self):
        """執行動作序列"""
        for i, action in enumerate(self.actions):
            if self.should_stop:
                break
                
            while self.is_paused:
                self.msleep(100)
                
            self.action_started.emit(i, action.get_display_text())
            
            try:
                success = self.execute_single_action(action)
                self.action_completed.emit(i, success)
            except Exception as e:
                logger.error(f"Action execution failed: {e}")
                self.action_completed.emit(i, False)
                break
                
            self.progress_updated.emit(i + 1, len(self.actions))
```

### 4.3 資料持久化

**建議使用 JSON 格式:**
- 易於閱讀和編輯
- 支援版本控制
- 跨平台相容性好

**範例:**

```json
{
  "task_name": "shoulder_massage",
  "version": "1.0",
  "created_at": "2024-01-15T10:30:00",
  "description": "肩部舒緩按摩程序",
  "actions": [
    {
      "type": "move_to_position",
      "parameters": {
        "position_name": "left_shoulder",
        "speed": "slow"
      },
      "metadata": {
        "duration_estimate": 5.0,
        "safety_level": "high"
      }
    },
    {
      "type": "enable_force",
      "parameters": {
        "force_level": "gentle"
      }
    }
  ],
  "metadata": {
    "estimated_duration": 120,
    "difficulty": "beginner",
    "required_hardware": ["ur10e", "force_sensor"]
  }
}
```

### 4.4 錯誤處理策略

**建議實現分層錯誤處理:**

1. **動作層級:** 單個動作失敗時的處理
2. **序列層級:** 整個序列執行異常的處理
3. **系統層級:** 機器人連接失敗等系統錯誤

```python
class ErrorHandler:
    """錯誤處理器"""
    
    @staticmethod
    def handle_action_error(action: Action, error: Exception):
        """處理動作錯誤"""
        logger.error(f"Action {action.action_type} failed: {error}")
        
        # 決策樹
        if isinstance(error, RobotConnectionError):
            # 嘗試重新連接
            return ErrorHandler.retry_with_reconnect(action)
        elif isinstance(error, SafetyViolationError):
            # 立即停止並發出警告
            return ErrorHandler.emergency_stop()
        elif isinstance(error, ParameterValidationError):
            # 提示使用者修正參數
            return ErrorHandler.prompt_user_fix(action, error)
        else:
            # 記錄並跳過
            return ErrorHandler.log_and_skip(action, error)
```

---

## 五、使用者教育建議

### 5.1 互動式教學

**建議創建內建教學模式:**

```python
class InteractiveTutorial(QWidget):
    """互動式教學"""
    
    TUTORIAL_STEPS = [
        {
            "title": "歡迎使用順序控制器!",
            "content": "這是一個讓您輕鬆編程機器人的工具",
            "action": "show_overview",
            "next_trigger": "click_ok"
        },
        {
            "title": "步驟 1: 選擇動作",
            "content": "從左側的動作庫選擇「移動到位置」",
            "highlight": "action_library",
            "next_trigger": "action_selected"
        },
        {
            "title": "步驟 2: 設定參數",
            "content": "選擇「home」位置和「慢速」",
            "highlight": "parameter_dialog",
            "next_trigger": "parameters_set"
        },
        # ... 更多步驟
    ]
    
    def show_step(self, step_index: int):
        """顯示教學步驟"""
        step = self.TUTORIAL_STEPS[step_index]
        
        # 顯示提示框
        tooltip = self.create_tooltip(step)
        tooltip.show()
        
        # 高亮相關區域
        if step.get("highlight"):
            self.highlight_widget(step["highlight"])
```

### 5.2 範例庫

**建議預裝常用範例:**

- 🧘 **簡單按摩:** 單點圓周運動
- 🔄 **拿取放置:** 完整的抓取流程
- 👋 **揮手動作:** 關節空間運動示範
- 🎨 **繪畫路徑:** 複雜路徑規劃
- 🔁 **重複巡邏:** 循環控制示範

### 5.3 影片教學

**建議製作的影片主題:**

1. **5分鐘快速入門** - 創建第一個任務
2. **動作類型詳解** - 每種動作的用途和參數
3. **進階技巧** - 循環、條件、子流程
4. **故障排除** - 常見問題解決
5. **實際案例** - 真實應用場景示範

---

## 六、維護與擴展性考量

### 6.1 模組化設計原則

**當前結構:**
```
sequential_controller/
├── sequential_controller.py (核心邏輯)
├── sequential_controller_ui.py (UI)
└── sequential_controller_ui_page.py (頁面版本)
```

**建議重構為:**
```
sequential_controller/
├── core/
│   ├── action.py (動作定義)
│   ├── controller.py (控制器邏輯)
│   ├── executor.py (執行引擎)
│   └── serializer.py (序列化/反序列化)
├── ui/
│   ├── widgets/
│   │   ├── action_library.py
│   │   ├── block_canvas.py
│   │   ├── parameter_dialog.py
│   │   └── execution_panel.py
│   ├── dialogs/
│   │   ├── guided_wizard.py
│   │   └── settings_dialog.py
│   └── main_widget.py
├── templates/
│   ├── template_engine.py
│   └── presets/
│       ├── massage.json
│       ├── pick_and_place.json
│       └── ...
└── utils/
    ├── validators.py
    ├── error_handlers.py
    └── logger.py
```

### 6.2 插件系統(未來擴展)

**設計插件介面,允許第三方擴展:**

```python
class ActionPlugin(ABC):
    """動作插件基類"""
    
    @abstractmethod
    def get_action_type(self) -> ActionType:
        """返回動作類型"""
        pass
        
    @abstractmethod
    def get_metadata(self) -> dict:
        """返回元數據"""
        pass
        
    @abstractmethod
    def create_parameter_widget(self) -> QWidget:
        """創建參數編輯 Widget"""
        pass
        
    @abstractmethod
    def execute(self, parameters: dict, robot_interface) -> bool:
        """執行動作"""
        pass


class PluginManager:
    """插件管理器"""
    
    def __init__(self):
        self.plugins = {}
        
    def load_plugin(self, plugin_path: str):
        """載入插件"""
        # 動態載入插件模組
        pass
        
    def register_action_type(self, plugin: ActionPlugin):
        """註冊新動作類型"""
        action_type = plugin.get_action_type()
        self.plugins[action_type] = plugin
```

### 6.3 單元測試建議

**關鍵測試領域:**

```python
# tests/test_sequential_controller.py
class TestSequentialController(unittest.TestCase):
    
    def setUp(self):
        self.controller = SequentialController(mock_robot_interface)
        
    def test_add_action(self):
        """測試添加動作"""
        action = Action(ActionType.MOVE_TO_POSITION, {"position_name": "home"})
        self.controller.add_action(action)
        self.assertEqual(self.controller.get_action_count(), 1)
        
    def test_execute_sequence(self):
        """測試執行序列"""
        # ... 測試邏輯
        
    def test_parameter_validation(self):
        """測試參數驗證"""
        # ... 測試邏輯


# tests/test_action_block_item.py
class TestActionBlockItem(unittest.TestCase):
    
    def test_block_creation(self):
        """測試區塊創建"""
        # ... 測試邏輯
        
    def test_drag_and_drop(self):
        """測試拖放功能"""
        # ... 測試邏輯
```

---

## 七、性能優化建議

### 7.1 UI 渲染優化

**問題:** 大量區塊時渲染可能變慢

**解決方案:**
1. 使用虛擬化列表(只渲染可見區塊)
2. 延遲載入連接線
3. 使用 OpenGL 加速渲染

```python
class BlockCanvasView(QGraphicsView):
    """區塊畫布視圖(優化版)"""
    
    def __init__(self):
        super().__init__()
        
        # 啟用 OpenGL 渲染
        self.setViewport(QOpenGLWidget())
        
        # 啟用視口更新模式
        self.setViewportUpdateMode(QGraphicsView.BoundingRectViewportUpdate)
        
        # 啟用快取
        self.setCacheMode(QGraphicsView.CacheBackground)
```

### 7.2 記憶體管理

**避免記憶體洩漏:**

```python
class SequentialControllerWidget(QWidget):
    
    def __del__(self):
        """清理資源"""
        # 停止所有執行緒
        if hasattr(self, 'executor') and self.executor.isRunning():
            self.executor.stop()
            self.executor.wait()
            
        # 清除圖形場景
        if hasattr(self, 'canvas_view'):
            self.canvas_view.scene().clear()
```

---

## 八、總結

### 關鍵改進點總結

1. **🎨 視覺化編程介面**
   - 從列表改為區塊流程圖
   - 直觀的拖放操作
   - 即時視覺反饋

2. **📚 分類動作庫**
   - 清晰的類別劃分
   - 卡片式展示
   - 降低搜尋時間

3. **🛠️ 友善參數編輯**
   - 圖像提示和 GIF 示範
   - 自然語言預設值
   - 預覽功能

4. **🚀 擴充動作類型**
   - 實現文檔中的所有功能
   - 支援循環和分支
   - 模擬模式方便教學

5. **🧙 引導式建立精靈**
   - 問答式任務生成
   - 範本庫
   - 降低入門門檻

6. **📊 增強執行反饋**
   - 視覺化執行狀態
   - 歷史記錄
   - 實時監控

### 預期效果

**改進前:**
- 學習曲線陡峭,需要 2-3 小時才能創建第一個有意義的任務
- 工程背景學生友善,非工程背景學生困難
- 缺乏視覺反饋,除錯困難

**改進後:**
- 5-10 分鐘內完成第一個任務
- 適合所有背景的學生
- 直觀的視覺化介面
- 即時反饋和易於除錯
- 豐富的教學資源

### 開發工作量估算

| 階段 | 工作量(人週) | 優先級 |
|------|-------------|--------|
| 階段一: 基礎視覺化 | 4-6 週 | 🔴 高 |
| 階段二: 增強互動體驗 | 4-6 週 | 🔴 高 |
| 階段三: 擴充動作類型 | 6-8 週 | 🟡 中 |
| 階段四: 引導式工具 | 3-4 週 | 🟡 中 |
| 階段五: 優化與測試 | 2-3 週 | 🔴 高 |
| **總計** | **19-27 週** | |

### 下一步行動

**立即可以開始的工作:**

1. **[ ] 創建 UI 原型** (1 週)
   - 使用 Figma 或 Qt Designer 設計新介面
   - 與使用者(學生)確認設計方向

2. **[ ] 重構代碼架構** (1 週)
   - 將 UI 和邏輯分離
   - 建立模組化結構

3. **[ ] 實現基礎區塊視圖** (2-3 週)
   - 替換 QListWidget
   - 實現基本拖放功能

4. **[ ] 使用者測試** (持續進行)
   - 找 3-5 位學生測試原型
   - 收集反饋並迭代

---

## 附錄

### A. 參考資源

**視覺化編程工具參考:**
- Scratch (MIT) - 兒童編程教育
- Node-RED - 流程式編程工具
- Blockly (Google) - 區塊式編程庫
- LabVIEW - 圖形化系統設計平台

**機器人編程工具參考:**
- Universal Robots PolyScope - UR 機器人官方介面
- ABB RobotStudio - ABB 機器人模擬工具
- KUKA.Sim - KUKA 機器人模擬器

**PyQt 高級功能參考:**
- QGraphicsView 官方文檔
- Qt Animation Framework
- Model/View Programming

### B. 設計資源建議

**圖標庫:**
- Font Awesome
- Material Design Icons
- Feather Icons

**顏色方案:**
- Material Design Color Palette
- Coolors.co
- Adobe Color

**字體:**
- Roboto (英文)
- Noto Sans CJK TC (繁體中文)

### C. 團隊協作建議

**建議使用的工具:**
- **版本控制:** Git + GitHub/GitLab
- **專案管理:** Jira / Trello
- **設計協作:** Figma
- **文檔協作:** Notion / Confluence
- **通訊:** Slack / Microsoft Teams

**開發流程:**
1. 功能設計 → UI 原型 → 代碼審查
2. 每週進度會議
3. 每兩週一次使用者測試
4. 持續整合/持續部署 (CI/CD)

---

**文檔版本:** 1.0  
**最後更新:** 2024-01-15  
**作者:** Tetsu (R&D Associate Director)  
**審核狀態:** 待審核

---

## 變更記錄

| 日期 | 版本 | 變更內容 | 作者 |
|------|------|---------|------|
| 2024-01-15 | 1.0 | 初始版本創建 | Tetsu |

---

**回饋與建議:**  
如有任何問題或建議,請聯繫 R&D 團隊。
