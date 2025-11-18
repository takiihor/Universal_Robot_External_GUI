# UR10e 遠端控制 UI 系統

一個基於 Python + PyQt5 + ur_rtde 的 UR10e 機器手臂遠端控制圖形化介面系統。

## 專案概述

本系統提供友善的圖形化介面，讓使用者能夠輕鬆控制和監控 UR10e 機器手臂，包含：
- 即時連線管理
- TCP 位姿與關節角度監控
- 力感測器資料顯示
- 自由驅動模式控制
- 軟體急停功能

## 開發階段

**當前版本：第二階段 - 擴展控制功能** ✅

### Stage 1: Core Features ✅
- [x] 連線管理
- [x] 即時狀態監控
- [x] 自由驅動模式
- [x] 急停功能

### Stage 2: Expanded Control Features ✅
- [x] 手動 TCP 控制（6-DOF with adjustable steps)
- [x] 手動關節控制（Individual joint control)
- [x] 預設位置管理（Save/Load/Delete positions)
- [x] 力控制功能（Force mode with parameters)
- [x] 腳本執行功能（URScript execution)
- [x] I/O 控制（Digital & Analog I/O backend)

### Stage 3: Data Visualization & Logging ⏳
- [ ] 即時圖表顯示（PyQtGraph charts）
- [ ] 資料記錄與匯出（CSV/HDF5 format）
- [ ] 軌跡錄製與重播（Trajectory recording）

## 系統需求

- Python 3.7 或更高版本
- UR10e 機器手臂（支援 RTDE 協議）
- 網路連線（機器手臂與電腦在同一網段）

## 安裝步驟

### 1. 克隆或下載專案

```bash
cd /path/to/your/workspace
# 如果從 git 下載
git clone <repository_url>
cd ur10e_control_ui
```

### 2. 建立虛擬環境（建議）

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows
```

### 3. 安裝依賴套件

```bash
pip install -r requirements.txt
```

### 4. 驗證安裝

```bash
python -c "import PyQt5; import rtde_control; print('依賴套件安裝成功')"
```

## 使用方法

### 啟動應用程式

```bash
python main.py
```

### 連線到機器人

1. 確認 UR10e 已開機並處於可連線狀態
2. 在應用程式的「連線設定」區域輸入機器人的 IP 位址（例如：192.168.1.100）
3. 確認連接埠為 30004（RTDE 預設埠）
4. 點擊「連線」按鈕
5. 連線成功後，狀態指示器會變為綠色「● 已連線」

### 監控機器人狀態

連線成功後，以下資訊會即時更新：
- **TCP 位姿**：X, Y, Z 位置（公尺）及 Rx, Ry, Rz 姿態（弧度）
- **關節角度**：J1-J6 六個關節的當前角度（弧度）
- **力/力矩感測器**：Fx, Fy, Fz 力（牛頓）及 Tx, Ty, Tz 力矩（牛頓·公尺）

### 使用自由驅動模式

1. 確保已連線到機器人
2. 點擊「啟動自由驅動」按鈕
3. 確認對話框後，機器手臂進入自由驅動模式
4. 此時可以手動拖曳機器手臂到任意位置
5. 完成後點擊「停止自由驅動」按鈕

> ⚠️ **安全提示**：啟動自由驅動前，請確保機器手臂周圍無障礙物及人員。

### 急停功能

- 緊急情況下，點擊大紅色「⚠ 急停 ⚠」按鈕
- 機器手臂將立即停止所有運動
- 急停後需重新確認機器人狀態

### 斷開連線

- 點擊「斷線」按鈕可安全斷開與機器人的連線
- 關閉應用程式時會自動斷線

## 檔案結構

```
ur10e_control_ui/
├── main.py                  # 主程式入口
├── robot_controller.py      # 機器人控制核心
├── ui_mainwindow.py        # 主視窗 UI
├── config.py               # 設定管理
├── utils.py                # 工具函數
├── requirements.txt        # 依賴套件清單
├── README.md              # 本說明文件
├── scripts/               # URScript 腳本資料夾
├── logs/                  # 日誌檔案資料夾
└── assets/                # 資源檔案（圖示、樣式表等）
```

## 設定檔

應用程式會在首次運行後生成 `config.json` 設定檔，您可以編輯此檔案來調整預設參數。

主要設定項目：
- `connection.ip`：預設 IP 位址
- `connection.port`：預設連接埠
- `motion.tcp_speed`：TCP 移動速度（m/s）
- `motion.joint_speed`：關節移動速度（rad/s）
- `safety.workspace_limits`：工作空間限制

## 日誌系統

- 應用程式會自動記錄操作日誌到 `logs/` 資料夾
- 日誌包含所有重要操作、錯誤訊息及系統狀態
- UI 中的「系統訊息」區域也會顯示即時日誌

## 故障排除

### 無法連線到機器人

1. 檢查機器人 IP 位址是否正確
2. 確認電腦與機器人在同一網段
3. 使用 `ping <robot_ip>` 測試網路連線
4. 確認機器人已啟動且處於正常模式
5. 檢查防火牆設定是否阻擋 30004 埠

### 依賴套件安裝失敗

```bash
# 升級 pip
pip install --upgrade pip

# 如果 PyQt5 安裝失敗，可嘗試
pip install PyQt5 --no-cache-dir

# 如果 ur-rtde 安裝失敗
pip install ur-rtde --no-binary :all:
```

### UI 無法顯示或卡住

- 確認已正確安裝 PyQt5
- 檢查系統是否支援圖形化介面
- 查看 logs/ 中的日誌檔案以獲取詳細錯誤訊息

### 連線後資料不更新

- 確認 RTDE 服務在機器人上已啟用
- 檢查網路延遲（高延遲會導致更新緩慢）
- 重新連線嘗試

## 進階功能（後續階段）

第二階段將加入：
- 手動 TCP 移動控制（笛卡爾空間）
- 手動關節移動控制
- 預設位置管理
- 力控制模式
- 腳本執行功能

第三階段將加入：
- 即時資料曲線圖
- 資料記錄與匯出
- 3D 視覺化（可選）

## 安全注意事項

⚠️ **重要安全提示**

1. **人員安全**：操作機器手臂時，確保工作區域內無人員
2. **工作空間**：了解機器手臂的運動範圍，避免碰撞
3. **急停裝置**：確保機器人實體急停按鈕隨時可及
4. **測試環境**：初次使用時，建議在安全環境下測試所有功能
5. **備份設定**：修改重要設定前先備份
6. **網路安全**：建議在隔離的區域網路中使用，避免外部存取

## 授權

此專案僅供學習與研究使用。使用者需自行承擔操作機器手臂的所有責任。

## 技術支援

如遇到問題，請：
1. 查看 `logs/` 資料夾中的日誌檔案
2. 檢查本 README 的故障排除章節
3. 參考 ur_rtde 官方文件：https://sdurobotics.gitlab.io/ur_rtde/

## 版本歷史

- **v1.0.0 (2025-11-04)**：第一階段核心功能完成
  - 基礎連線管理
  - 即時狀態監控
  - 自由驅動模式
  - 急停功能

## 開發團隊

開發框架：Python + PyQt5 + ur_rtde
開發階段：第一階段（核心功能）

---

**祝使用愉快！** 🤖
