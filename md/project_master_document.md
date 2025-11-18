# UR10e Sequential Controller 開發總覽文檔
## Project Handoff & Continuation Guide

**文檔版本:** 2.0  
**最後更新:** 2024-01-15  
**項目負責人:** Tetsu (Associate R&D Director, RV Automation Technology)  
**目的:** 這份文檔讓任何 LLM 在新對話中都能快速理解項目現狀並繼續開發

---

## 📋 執行摘要 (30 秒速讀)

**項目目標:** 為 UR10e 機器人開發一個**非工程背景學生也能使用**的順序控制器介面

**當前狀態:** 已完成初步設計，準備開始實施  

**開發策略:** 採用 **Quick Wins 增量式開發** (8-12 週)，而非大規模重構 (19-27 週)

**第一優先:** 實施 **Hand Guiding Tool** (位置教學工具) - 2-3 週

**核心設計理念:** 
- ✅ 教學(Hand Guiding) 與 編程(Sequential Controller) **完全分離**
- ✅ 增量改進現有系統，而非推倒重來
- ✅ 每 1-2 週交付一個可用改進

---

## 🎯 項目背景

### 使用場景
- **用戶:** 香港小學生、非工程背景學生
- **機器人:** Universal Robots UR10e
- **應用:** 按摩機器人、拾取放置、教學演示
- **環境:** 醫院、學校、展示場合

### 現有系統問題
1. ❌ 動作庫是扁平列表，難以找到特定動作
2. ❌ 參數編輯只有文字輸入框，技術門檻高
3. ❌ 缺少視覺化執行反饋
4. ❌ 缺少力量控制、夾爪控制、循環等功能
5. ❌ 沒有位置教學工具，學生難以設定位置

### 項目目標
1. ✅ 5-10 分鐘內讓新用戶創建第一個任務
2. ✅ 降低技術門檻，無需理解座標系和關節空間
3. ✅ 提供直觀的位置教學工具
4. ✅ 增加必要的動作類型(力量、夾爪、循環)
5. ✅ 改善執行反饋和除錯能力

---

## 🏗️ 系統架構

### 當前技術棧
```
語言: Python 3.8+
GUI 框架: PyQt5
機器人: Universal Robots UR10e
平台: Ubuntu 24
機器人控制: UR Python API (直接通訊，不使用 ROS)
```

### 現有代碼結構
```
ur10e_control/
├── sequential_controller.py          # 核心控制邏輯
│   ├── ActionType (枚舉)              # 8 種動作類型
│   ├── Action (類)                    # 動作數據結構
│   ├── SequentialController (類)     # 主控制器
│   └── ACTION_METADATA (字典)        # 動作元數據
│
├── sequential_controller_ui.py       # 主 UI Widget
│   ├── ActionParameterDialog         # 參數編輯對話框
│   └── SequentialControllerWidget    # 主介面
│
├── sequential_controller_ui_page.py  # 頁面版本 UI
│   └── SequentialControllerPageWidget
│
├── config.py                          # 配置文件
│   └── PRESET_POSITIONS (字典)       # 預設位置庫
│
└── main_window.py                     # 主視窗 (推測)
```

### 當前動作類型 (8 種)
```python
class ActionType(str, Enum):
    MOVE_TO_POSITION = "move_to_position"      # 移動到預設位置
    RELATIVE_MOVE = "relative_move"            # 相對移動
    SAVE_POSITION = "save_position"            # 保存當前位置
    HOME = "home"                               # 返回原點
    FREEDRIVE = "freedrive"                     # 自由拖動模式
    WAIT = "wait"                               # 等待
    EMERGENCY_STOP = "emergency_stop"           # 緊急停止
    CIRCULAR_MOTION = "circular_motion"         # 圓周運動 (可能存在)
```

### 機器人介面 (假設的 API)
```python
# 假設的 robot_interface 方法:
robot.enable_freedrive_mode() -> bool
robot.disable_freedrive_mode() -> bool
robot.get_current_pose() -> list[float]  # [x, y, z, rx, ry, rz]
robot.move_to_pose(pose, speed, acceleration) -> bool
robot.move_relative(direction, distance, speed) -> bool
robot.open_gripper() -> bool
robot.close_gripper() -> bool
robot.set_force_mode(level) -> bool
robot.emergency_stop() -> bool
```

---

## 🎯 開發策略：Quick Wins 方案

### 為什麼選擇 Quick Wins？

| 比較項目 | Quick Wins (選擇) | 完整重構 |
|---------|------------------|---------|
| 開發時間 | 8-12 週 | 19-27 週 |
| 風險 | 低（增量改進） | 高（推倒重來） |
| 價值交付 | 快速（每 1-2 週） | 延遲（需完整系統） |
| 用戶反饋 | 及早且頻繁 | 延後 |
| 可中止性 | 任何時候 | 困難 |

### 被拒絕的方案
❌ **完整視覺化區塊編輯器** (類似 Scratch)
- 開發時間: 6-12 個月
- 對簡單任務過於複雜
- 維護成本高

❌ **ROS + MoveIt 整合**
- 增加不必要的複雜度
- 現有 UR API 已足夠
- 適合多機器人協作，但不適合教學場景

❌ **3D 仿真與拖拽**
- 開發成本太高
- Hand Guiding Tool 已解決位置教學需求

---

## 📅 開發計劃：6 個優先級

### Priority 0: Hand Guiding Tool ⭐ **← 從這裡開始**
**時間:** 2-3 週  
**狀態:** 📝 待開始  

**核心概念 (非常重要!):**
```
❌ 錯誤理解: Hand Guiding 是程式的一個步驟
   程式:
   1. Enable hand guiding
   2. Move to position1
   3. Save position1

✅ 正確理解: Hand Guiding 是準備階段的獨立工具
   
   教學階段 (Hand Guiding Tool):
   1. 開啟 Hand Guiding Tool (獨立視窗)
   2. 啟用自由拖動模式
   3. 手動移動機器人到 position1
   4. 保存為 "position1"
   5. 手動移動到 position2
   6. 保存為 "position2"
   7. 測試夾爪開關
   8. 停止自由拖動
   
   編程階段 (Sequential Controller):
   1. Move to "position1"  ← 使用剛才保存的位置名稱
   2. Open gripper
   3. Move to "position2"  ← 使用剛才保存的位置名稱
   4. Close gripper
```

**實施內容:**
1. ✅ 創建新文件: `hand_guiding_tool.py`
2. ✅ 獨立視窗，不是對話框
3. ✅ 三個主要區域:
   - 控制面板 (啟用/停止 freedrive, 保存位置, 夾爪測試)
   - 位置列表 (顯示所有保存的位置)
   - 操作指南 (中文步驟說明)
4. ✅ 整合到主選單: Tools → Hand Guiding (Ctrl+H)
5. ✅ 與 Config.PRESET_POSITIONS 共享位置庫
6. ✅ 安全確認對話框
7. ❌ **不要** 把 ENABLE_FREEDRIVE/DISABLE_FREEDRIVE 加入 Sequential Controller 動作庫

**驗收標準:**
- [ ] Hand Guiding Tool 可作為獨立視窗開啟
- [ ] 能啟用/停止 freedrive 模式
- [ ] 即時顯示機器人位置 (X, Y, Z)
- [ ] 能保存位置並命名
- [ ] 保存的位置出現在 Sequential Controller 的位置下拉選單
- [ ] 能測試移動到保存的位置
- [ ] 能刪除保存的位置
- [ ] 夾爪測試按鈕可用
- [ ] 所有安全確認都到位
- [ ] 中文界面文字

**參考文檔:** `hand_guiding_tool_design_zh.md`

---

### Priority 1: 分類動作庫 (Categorized Action Library)
**時間:** 2-3 週  
**狀態:** 📝 待開始 (Priority 0 完成後)

**問題:** 所有 8 個動作在單一列表中，難以找到

**解決方案:** 創建分類標籤頁 + 卡片式展示

**類別結構:**
```python
ACTION_CATEGORIES = {
    "movement": {
        "name": "移動",
        "icon": "🚀",
        "color": "#4CAF50",
        "actions": [MOVE_TO_POSITION, RELATIVE_MOVE, HOME]
    },
    "interaction": {
        "name": "互動", 
        "icon": "🤝",
        "color": "#2196F3",
        "actions": [ENABLE_FORCE, GRIPPER_OPEN, GRIPPER_CLOSE]
    },
    "timing": {
        "name": "時間",
        "icon": "⏱️", 
        "color": "#FF9800",
        "actions": [WAIT]
    },
    "management": {
        "name": "管理",
        "icon": "🛠️",
        "color": "#9C27B0", 
        "actions": [SAVE_POSITION]
    },
    "safety": {
        "name": "安全",
        "icon": "⚠️",
        "color": "#F44336",
        "actions": [EMERGENCY_STOP]
    }
}
```

**實施任務:**
1. 創建 `categorized_action_library.py`
2. 實現 `ActionCard` widget (卡片)
3. 實現 `CategorizedActionLibrary` widget (標籤頁容器)
4. 替換 `sequential_controller_ui.py` 中的 `QListWidget`
5. 測試卡片點擊事件

**驗收標準:**
- [ ] 動作按類別分組顯示
- [ ] 每個類別有獨立標籤頁
- [ ] 動作以卡片形式展示 (圖標 + 名稱 + 描述)
- [ ] 卡片有懸停效果
- [ ] 點擊卡片能添加動作到序列
- [ ] 顏色編碼清晰

**參考文檔:** `SEQUENTIAL_CONTROLLER_QUICK_WINS.md` - Priority 1

---

### Priority 2: 增強參數對話框 (Enhanced Parameter Dialogs)
**時間:** 1-2 週  
**狀態:** 📝 待開始 (Priority 1 完成後)

**問題:** 
- 所有動作共用同一個通用對話框
- 只有下拉選單和數字輸入框
- 缺少視覺提示和預設值

**解決方案:** 為每種參數類型創建專用 Widget

**實施內容:**
1. 創建 `parameter_widgets.py`
2. 實現專用 Widget:
   - `PresetButtonGroup` - 預設值按鈕組
   - `DirectionSelector` - 方向選擇器 (圖形化)
   - `SpeedSelector` - 速度選擇器 (圖示 + 說明)
   - `PositionSelector` - 位置選擇器 (帶預覽)
3. 重構 `ActionParameterDialog` 使用新 Widget
4. 添加參數預設值庫 (`PARAMETER_PRESETS`)
5. 添加參數說明文字和提示

**範例:**
```python
PARAMETER_PRESETS = {
    "wait_time": {
        "label": "等待時間",
        "presets": [
            {"label": "短暫 (3秒)", "value": 3},
            {"label": "適中 (5秒)", "value": 5},
            {"label": "較長 (10秒)", "value": 10}
        ]
    },
    "distance": {
        "label": "移動距離",
        "presets": [
            {"label": "微調 (1cm)", "value": 1},
            {"label": "小幅 (5cm)", "value": 5},
            {"label": "中等 (10cm)", "value": 10}
        ]
    }
}
```

**驗收標準:**
- [ ] 每種參數有直觀的輸入方式
- [ ] 提供常用預設值快速選擇
- [ ] 有清晰的中文說明文字
- [ ] 方向選擇有圖形化指示
- [ ] 速度選擇有圖示 (🐌/🚶/🚀)
- [ ] 新手用戶無需查看文檔就能理解

**參考文檔:** `SEQUENTIAL_CONTROLLER_QUICK_WINS.md` - Priority 2

---

### Priority 3: 力量控制動作 (Force Control Actions)
**時間:** 2-3 週  
**狀態:** 📝 待開始 (Priority 2 完成後)

**問題:** 
- 按摩機器人需要力量控制
- 當前只有 ENABLE_FORCE 佔位符，沒有實際實現

**解決方案:** 實現完整的力量控制功能

**新增動作類型:**
```python
class ActionType(str, Enum):
    # ... 現有動作 ...
    
    # 新增:
    ENABLE_FORCE = "enable_force"           # 啟用力量控制
    DISABLE_FORCE = "disable_force"         # 停用力量控制
    SET_FORCE_LEVEL = "set_force_level"     # 設定力量等級
```

**實施內容:**
1. 在 `sequential_controller.py` 添加力量控制動作
2. 實現 `execute_enable_force()` 方法
3. 實現 `execute_disable_force()` 方法
4. 實現 `execute_set_force_level()` 方法
5. 添加力量等級參數對話框
6. 整合到動作庫 (Interaction 類別)
7. 如果硬體未就緒，提供模擬模式

**力量等級定義:**
```python
FORCE_LEVELS = {
    "gentle": {
        "name": "輕柔",
        "force_threshold": 10.0,  # N
        "description": "適合敏感部位"
    },
    "medium": {
        "name": "適中",
        "force_threshold": 20.0,
        "description": "一般按摩力道"
    },
    "strong": {
        "name": "強力",
        "force_threshold": 30.0,
        "description": "深層按摩"
    }
}
```

**驗收標準:**
- [ ] 可以在程式中啟用力量控制
- [ ] 可以設定三個力量等級
- [ ] 力量控制狀態在 UI 上可見
- [ ] 執行時正確呼叫機器人 API
- [ ] 如硬體未連接，有模擬模式提示
- [ ] 安全機制到位 (超過閾值停止)

**參考文檔:** `SEQUENTIAL_CONTROLLER_QUICK_WINS.md` - Priority 3

---

### Priority 4: 執行歷史面板 (Execution History Panel)
**時間:** 1 週  
**狀態:** 📝 待開始 (與 Priority 3 可並行)

**問題:**
- 執行時只有進度條和狀態文字
- 無法回顧已執行的步驟
- 錯誤發生時難以追蹤

**解決方案:** 添加執行歷史記錄面板

**實施內容:**
1. 創建 `execution_history_panel.py`
2. 實現 `ExecutionHistoryPanel` widget
3. 記錄每個步驟:
   - 步驟編號
   - 動作名稱
   - 狀態 (完成/錯誤/跳過)
   - 時間戳
   - 執行時長
4. 整合到主 UI (右側或底部)
5. 提供清除和匯出功能

**顯示格式:**
```
✅ 步驟 1: 移動到位置 "home"
   狀態: 完成 | 耗時: 3.2秒 | 14:32:15

✅ 步驟 2: 等待 5秒
   狀態: 完成 | 耗時: 5.0秒 | 14:32:18

❌ 步驟 3: 移動到位置 "invalid_pos"
   狀態: 錯誤 - 位置不存在 | 14:32:23
   
⏭️ 步驟 4: (已跳過)
```

**驗收標準:**
- [ ] 執行時即時記錄每個步驟
- [ ] 顏色編碼狀態 (綠色=成功, 紅色=錯誤)
- [ ] 顯示執行時長
- [ ] 可清除歷史記錄
- [ ] 可匯出日誌到文件
- [ ] 自動滾動到最新記錄

**參考文檔:** `SEQUENTIAL_CONTROLLER_QUICK_WINS.md` - Priority 4

---

### Priority 5: 基本循環支援 (Basic Loop Support)
**時間:** 2-3 週  
**狀態:** 📝 待開始 (Priority 4 完成後)

**問題:**
- 無法重複執行一組動作
- 必須手動複製貼上步驟

**解決方案:** 添加循環標記動作

**新增動作類型:**
```python
class ActionType(str, Enum):
    # ... 現有動作 ...
    
    # 新增:
    REPEAT_START = "repeat_start"    # 重複開始
    REPEAT_END = "repeat_end"        # 重複結束
```

**使用範例:**
```
1. Move to "home"
2. REPEAT_START (3 times)      ← 開始重複
3.   Move to "left_shoulder"
4.   Circular motion
5.   Wait 2 seconds
6. REPEAT_END                   ← 結束重複
7. Move to "home"

執行結果:
1. Move to "home"
2. Move to "left_shoulder"     ← 第 1 次
3. Circular motion
4. Wait 2 seconds
5. Move to "left_shoulder"     ← 第 2 次
6. Circular motion
7. Wait 2 seconds
8. Move to "left_shoulder"     ← 第 3 次
9. Circular motion
10. Wait 2 seconds
11. Move to "home"
```

**實施內容:**
1. 在 `sequential_controller.py` 添加循環動作類型
2. 實現 `expand_loops()` 方法 (展開循環)
3. 實現巢狀循環支援
4. 添加循環驗證 (檢查開始/結束配對)
5. 在序列列表中顯示縮排
6. 添加循環計數參數對話框
7. 整合到動作庫 (Control Flow 類別)

**驗收標準:**
- [ ] 可以添加 REPEAT_START 和 REPEAT_END
- [ ] 重複次數可設定 (1-100)
- [ ] 巢狀循環支援
- [ ] 序列列表顯示縮排和次數
- [ ] 執行前驗證循環配對
- [ ] 執行歷史顯示所有迭代
- [ ] 顏色編碼循環標記

**參考文檔:** `SEQUENTIAL_CONTROLLER_QUICK_WINS.md` - Priority 5

---

## 📊 進度追蹤

### 整體時程表

```
週次    優先級         任務                              狀態
─────────────────────────────────────────────────────────
1-3     Priority 0    Hand Guiding Tool                📝 待開始
4-6     Priority 1    Categorized Action Library       📝 待開始  
7-8     Priority 2    Enhanced Parameter Dialogs       📝 待開始
9-11    Priority 3    Force Control Actions            📝 待開始
9-10    Priority 4    Execution History Panel          📝 待開始
11-14   Priority 5    Basic Loop Support               📝 待開始
─────────────────────────────────────────────────────────
總計: 14 週
```

### 當前狀態
- **開始日期:** 待定
- **當前優先級:** Priority 0 (Hand Guiding Tool)
- **下一個里程碑:** Hand Guiding Tool 完成 (2-3 週)
- **完成百分比:** 0% (設計階段完成 100%)

### 成功指標

追蹤這些指標來評估改進效果:

| 指標 | 當前 | 目標 |
|-----|------|------|
| 新用戶創建首個任務時間 | N/A | < 10 分鐘 |
| 平均任務步驟數 | N/A | > 5 步 |
| 使用的動作類型多樣性 | N/A | > 4 種 |
| 任務執行成功率 | N/A | > 90% |
| 用戶滿意度 | N/A | > 4/5 |

---

## 🔧 技術實施指南

### 開發環境設置

```bash
# Python 環境
Python 3.8+
PyQt5
UR Robot Driver/SDK

# 推薦 IDE
VS Code with Python extension
PyCharm Professional

# 版本控制
Git
```

### 代碼規範

**Python 風格:**
```python
# 遵循 PEP 8
# 使用 type hints
# 英文註解，中文 UI 文字

class ExampleClass:
    """Class docstring in English."""
    
    def example_method(self, param: str) -> bool:
        """Method docstring in English.
        
        Args:
            param: Description
            
        Returns:
            Success status
        """
        # Implementation comments in English
        print("UI text in Chinese: 執行成功")
        return True
```

**PyQt5 風格:**
```python
# 使用 camelCase 命名 Qt slots
# 使用 snake_case 命名 Python 方法
# Signal 命名: <action>_<past_tense>

class MyWidget(QWidget):
    # Signals
    action_completed = pyqtSignal(bool)
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        """Initialize UI components."""
        # Setup code
        
    def on_button_clicked(self):
        """Button click handler."""
        # Handle click
```

### 測試策略

**每個 Priority 完成後:**
1. ✅ 單元測試 (如適用)
2. ✅ 整合測試
3. ✅ 手動測試
4. ✅ 用戶測試 (3-5 位非工程學生)
5. ✅ 收集反饋
6. ✅ 快速迭代

**測試清單範本:**
```markdown
## Priority X 測試清單

### 功能測試
- [ ] 功能 A 可正常使用
- [ ] 功能 B 邊界情況處理正確
- [ ] 錯誤訊息清晰易懂

### 整合測試  
- [ ] 與現有系統整合無問題
- [ ] 不影響現有功能

### 用戶測試
- [ ] 3 位學生可獨立完成任務
- [ ] 平均完成時間 < X 分鐘
- [ ] 無困惑點或已記錄

### 效能測試
- [ ] UI 響應流暢 (< 100ms)
- [ ] 無記憶體洩漏
```

---

## 📚 重要文檔索引

### 設計文檔

| 文檔名稱 | 用途 | 優先級 |
|---------|------|--------|
| `hand_guiding_tool_design_zh.md` | Hand Guiding Tool 完整設計規格 | Priority 0 |
| `SEQUENTIAL_CONTROLLER_QUICK_WINS.md` | Priority 1-5 詳細實施指南 | Priority 1-5 |
| `sequential_controller_improvements_zh.md` | 長期改進提案 (參考用) | 未來 |
| `claude_code_implementation_prompt.md` | LLM 實施提示詞範本 | 參考 |

### 參考文檔 (已分析但未採用)

| 文檔 | 結論 | 原因 |
|-----|------|------|
| 完整視覺化區塊編輯器 | ❌ 暫不採用 | 開發時間太長 (6-12 月) |
| ROS + MoveIt 整合 | ❌ 暫不採用 | 對教學場景過度設計 |
| 3D 仿真拖拽 | ❌ 暫不採用 | 成本高，Hand Guiding 已解決需求 |

---

## 🚀 快速開始指南

### 如果你是 LLM，剛接手這個項目:

**第一步: 理解核心概念**
```
最重要的概念:
Hand Guiding Tool ≠ Sequential Controller 的一部分
Hand Guiding Tool = 獨立的位置教學工具

工作流程:
教學階段 → Hand Guiding Tool → 保存位置
編程階段 → Sequential Controller → 使用位置名稱
```

**第二步: 查看當前優先級**
```
當前應該實施: Priority 0 - Hand Guiding Tool
參考文檔: hand_guiding_tool_design_zh.md
預計時間: 2-3 週
```

**第三步: 確認現有代碼**
```python
# 需要看到這些文件:
- sequential_controller.py
- sequential_controller_ui.py  
- sequential_controller_ui_page.py
- config.py
- main_window.py (可能)

# 確認機器人介面 API
robot.enable_freedrive_mode()
robot.get_current_pose()
# ... 等等
```

**第四步: 開始實施**
```
1. 創建 hand_guiding_tool.py
2. 實現 HandGuidingTool 類
3. 整合到主視窗
4. 測試
5. 收集反饋
```

### 如果你是人類開發者:

**設置開發環境:**
```bash
# 1. Clone 專案
git clone <repository>
cd ur10e_control

# 2. 創建虛擬環境
python3 -m venv venv
source venv/bin/activate

# 3. 安裝依賴
pip install PyQt5
pip install ur-rtde  # 或其他 UR 驅動

# 4. 運行現有系統
python main_window.py
```

**開始開發:**
```bash
# 1. 創建新分支
git checkout -b feature/hand-guiding-tool

# 2. 閱讀設計文檔
cat docs/hand_guiding_tool_design_zh.md

# 3. 創建新文件
touch hand_guiding_tool.py

# 4. 開始編碼...
```

---

## 💬 常見問題 (FAQ)

### Q1: 為什麼不用 ROS?
**A:** 現有系統用 UR Python API 直接通訊，已經足夠。ROS 適合多機器人協作和複雜規劃，但對教學場景是過度設計。如果未來需要多機器人協作，可以考慮整合。

### Q2: 為什麼 Hand Guiding 不是 Sequential Controller 的一部分?
**A:** 
```
Hand Guiding = 教學工具 (準備階段)
Sequential Controller = 執行工具 (運行階段)

類比:
Hand Guiding = 寫菜譜
Sequential Controller = 按菜譜做菜

你不會在做菜過程中寫菜譜對吧？
```

### Q3: 為什麼選擇列表式介面而不是視覺化區塊?
**A:** 
- ✅ 列表式可以在 2-3 週改進
- ✅ 對簡單任務(按摩、拾取放置)足夠
- ✅ 容易維護
- ❌ 視覺化區塊需要 6-12 個月
- 📋 未來可以根據反饋再考慮

### Q4: 如果硬體還沒準備好怎麼辦?
**A:** 實現模擬模式:
```python
if not hardware_available:
    logger.warning("硬體未連接，使用模擬模式")
    # 模擬執行
    return True
```

### Q5: 怎麼處理多語言?
**A:** 目前只支援中文 UI + 英文代碼。未來如需國際化:
```python
# 使用 Qt 的翻譯系統
from PyQt5.QtCore import QTranslator
translator = QTranslator()
translator.load("translations/zh_TW.qm")
app.installTranslator(translator)
```

### Q6: 如何確保安全性?
**A:** 
- ✅ 所有運動操作前都有確認對話框
- ✅ 顯眼的急停按鈕
- ✅ 軟限位檢查
- ✅ 速度限制
- ✅ 碰撞檢測 (如硬體支援)
- ✅ 詳細的日誌記錄

### Q7: 測試策略是什麼?
**A:** 
```
開發 → 單元測試 → 整合測試 → 手動測試 → 用戶測試 → 收集反饋 → 迭代
      (如適用)                              (3-5 位學生)
```

### Q8: 如果時間不夠怎麼辦?
**A:** Quick Wins 方案的優點就是可以隨時停止:
- ✅ Priority 0 完成就有位置教學工具
- ✅ Priority 1 完成就有分類動作庫
- ✅ 每個優先級都是獨立可用的改進

### Q9: 如何與團隊協作?
**A:** 
```
- 代碼審查: 所有 PR 需要審查
- 文檔同步: 更新這份文檔
- 每週同步: 進度、阻礙、計劃
- 用戶反饋: 共享測試結果
```

### Q10: 下一步是什麼?
**A:** 
```
如果 Quick Wins 成功 (8-12 週後):

Option A: 繼續 MVP 方式
- 添加更多動作類型
- 更多參數預設值
- 任務範本庫

Option B: 視覺化區塊編輯器
- 實施 QGraphicsView 區塊畫布
- 保留列表視圖作為備選

Option C: 引導模式
- 任務建立精靈
- 新手教學
- 範本庫

根據用戶反饋決定!
```

---

## 📞 聯絡資訊

**項目負責人:** Tetsu  
**職位:** Associate R&D Director  
**公司:** RV Automation Technology Company Ltd  
**經驗:** 12+ 年機器人自動化和系統整合  
**專長:** UR10e, 醫療機器人, 工廠自動化

**工作地點:** 香港和中國  
**語言:** 英語、粵語、普通話

---

## 🔄 文檔維護

### 如何更新這份文檔

**當你完成一個 Priority:**
1. 更新狀態: 📝 待開始 → 🟡 進行中 → ✅ 已完成
2. 更新進度追蹤表
3. 添加實施筆記 (遇到的問題、解決方案)
4. 更新測試結果

**當遇到設計變更:**
1. 記錄變更原因
2. 更新相關章節
3. 通知相關人員

**定期審查:**
- 每個 Priority 完成後審查
- 每月審查一次進度
- 根據反饋調整計劃

### 版本歷史

| 版本 | 日期 | 變更內容 | 作者 |
|-----|------|---------|------|
| 2.0 | 2024-01-15 | 完整項目總覽文檔創建 | Claude (Sonnet 4) |
| 1.0 | 2024-01-15 | 初始設計文檔 | Tetsu + Claude |

---

## 🎯 最後提醒

### 給 LLM:
如果你在新對話中接手這個項目:
1. ✅ 閱讀「執行摘要」(30 秒)
2. ✅ 查看「當前優先級」
3. ✅ 理解「Hand Guiding ≠ Sequential Controller」概念
4. ✅ 閱讀對應的設計文檔
5. ✅ 開始實施

### 給人類開發者:
1. ✅ 從 Priority 0 開始
2. ✅ 不要跳過測試
3. ✅ 經常收集用戶反饋
4. ✅ 保持簡單
5. ✅ 享受開發過程！

### 核心原則:
```
1. 增量改進 > 推倒重來
2. 快速交付 > 完美設計
3. 用戶反饋 > 個人假設
4. 實用主義 > 理論完整
5. 可工作的軟體 > 詳盡的文檔
```

---

**準備好了嗎？開始 Priority 0 - Hand Guiding Tool！** 🚀

**記住:** 
- Hand Guiding = 教學工具 (獨立)
- Sequential Controller = 編程工具 (使用教學結果)
- 保持簡單，快速迭代，收集反饋！

