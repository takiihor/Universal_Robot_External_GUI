# 快速參考卡 - UR10e 控制 UI

## 檔案功能速查

| 檔案 | 主要功能 | 關鍵類別/函數 |
|------|----------|---------------|
| **config.py** | 設定管理 | `Config` 類別、所有預設參數 |
| **utils.py** | 工具函數 | 座標轉換、向量運算、安全檢查 |
| **robot_controller.py** | 機器人控制 | `RobotController`、`DataReceiverThread` |
| **main.py** | 程式入口 | `main()`、日誌設定 |
| **ui_mainwindow.py** | UI 介面 | `MainWindow`、所有 UI 元件 |

## 快速命令

```bash
# 安裝依賴
pip install -r requirements.txt

# 執行程式
python main.py

# 檢查依賴
python -c "import PyQt5; import rtde_control; print('OK')"
```

## 主要類別速查

### RobotController 關鍵方法

```python
# 連線管理
.connect(ip, port)           # 連線到機器人
.disconnect()                # 斷線
.is_connected()             # 檢查連線狀態

# 狀態讀取
.get_tcp_pose()             # 獲取 TCP 位姿
.get_joint_positions()      # 獲取關節角度
.get_tcp_force()            # 獲取力感測器資料

# 運動控制
.move_tcp(x, y, z, ...)     # TCP 移動
.move_joint(q1, q2, ...)    # 關節移動
.stop_motion()              # 停止運動

# 特殊模式
.enable_freedrive()         # 啟動自由驅動
.disable_freedrive()        # 停止自由驅動
.emergency_stop()           # 急停
```

### Config 常用參數

```python
Config.DEFAULT_IP            # 預設 IP (192.168.1.100)
Config.DEFAULT_PORT          # 預設 Port (30004)
Config.DEFAULT_TCP_SPEED     # TCP 速度 (0.1 m/s)
Config.WORKSPACE_LIMITS      # 工作空間限制
Config.PRESET_POSITIONS      # 預設位置字典
```

### Utils 常用函數

```python
format_pose(pose)           # 格式化位姿顯示
format_force(force)         # 格式化力資料顯示
check_pose_in_workspace()   # 檢查工作空間
degrees_to_radians()        # 角度轉弧度
radians_to_degrees()        # 弧度轉角度
```

## 信號與槽對應

| 控制器信號 | UI 槽函數 | 作用 |
|-----------|----------|------|
| `tcp_pose_updated` | `update_tcp_display` | 更新 TCP 顯示 |
| `joint_positions_updated` | `update_joint_display` | 更新關節顯示 |
| `force_data_updated` | `update_force_display` | 更新力顯示 |
| `connection_status_changed` | `on_connection_status_changed` | 連線狀態變更 |
| `error_occurred` | `show_error_message` | 顯示錯誤 |
| `info_message` | `show_info_message` | 顯示資訊 |

## 預設位置

| 名稱 | 關節角度 (rad) | 說明 |
|------|---------------|------|
| **home** | [0, -1.57, 1.57, -1.57, -1.57, 0] | 原點位置 |
| **safe** | [0, -2.0, 2.0, -1.57, -1.57, 0] | 安全位置（較高） |
| **vertical** | [0, -1.57, 0, -1.57, -1.57, 0] | 垂直向下 |

## 安全參數

```python
# 工作空間限制 (m)
X: -0.8 ~ 0.8
Y: -0.8 ~ 0.8
Z: 0.0 ~ 1.2

# 力閾值
最大力: 50 N
最大力矩: 10 Nm

# 速度限制
最大 TCP 速度: 1.0 m/s
最大關節速度: 2.0 rad/s
```

## 故障排除速查

| 問題 | 可能原因 | 解決方法 |
|------|---------|---------|
| 無法連線 | IP 錯誤 | 檢查 IP 位址、ping 測試 |
| UI 無反應 | 執行緒阻塞 | 檢查 logs/ 日誌 |
| 資料不更新 | RTDE 問題 | 重新連線 |
| 依賴安裝失敗 | pip 版本舊 | `pip install --upgrade pip` |

## 日誌位置

- **檔案日誌**: `logs/ur10e_control_*.log`
- **UI 日誌**: 主視窗「系統訊息」區域
- **控制台日誌**: 終端機輸出

## 開發進度

- ✅ **第一階段**: 核心功能（連線、監控、自由驅動、急停）
- ⏳ **第二階段**: 擴展控制（手動移動、力控制、腳本執行）
- ⏳ **第三階段**: 資料記錄與視覺化（圖表、記錄器）

## 重要提醒

⚠️ **安全第一**
- 首次使用請在安全環境測試
- 確保工作區域無人員
- 實體急停按鈕隨時可及

⚠️ **網路要求**
- 機器人與電腦同一網段
- 防火牆允許 30004 埠

⚠️ **功能限制**
- 當前版本僅支援監控與自由驅動
- 手動移動功能將在第二階段實現

---

**版本**: v1.0.0 (第一階段)
**更新日期**: 2025-11-04
