# UR10e 控制 UI 安裝指南

## 系統需求

### 硬體需求
- **電腦**: 支援 Python 3.7+ 的電腦（Linux/Windows/macOS）
- **記憶體**: 至少 2 GB RAM
- **網路**: 乙太網路連線（與 UR10e 同網段）

### 軟體需求
- **作業系統**:
  - Linux: Ubuntu 18.04+ / Debian 10+
  - Windows: Windows 10+
  - macOS: 10.14+
- **Python**: 3.7 或更高版本
- **顯示**: 支援圖形介面（X11/Wayland/Windows GUI）

### 機器人需求
- **UR10e** 機器手臂
- **韌體版本**: 支援 RTDE 協議（UR Software 3.0+）
- **網路設定**: 與電腦在同一網段

---

## 安裝步驟

### 1. 檢查 Python 版本

```bash
python3 --version
# 應該顯示 Python 3.7.x 或更高版本
```

如果版本過舊或未安裝 Python：

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

**Windows:**
- 從 [python.org](https://www.python.org/downloads/) 下載安裝
- 安裝時勾選 "Add Python to PATH"

**macOS:**
```bash
brew install python3
```

### 2. 取得專案檔案

**選項 A: 從 Git 克隆（推薦）**
```bash
git clone <repository_url>
cd ur10e_control_ui
```

**選項 B: 下載壓縮檔**
```bash
# 解壓縮後進入目錄
cd ur10e_control_ui
```

### 3. 建立虛擬環境（強烈建議）

**Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Windows (CMD):**
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

成功啟動後，命令提示符前會顯示 `(venv)`。

### 4. 升級 pip

```bash
pip install --upgrade pip
```

### 5. 安裝依賴套件

```bash
pip install -r requirements.txt
```

這會安裝以下套件：
- PyQt5 (GUI 框架)
- pyqtgraph (圖表庫)
- ur-rtde (UR 機器人通訊)
- numpy (數學運算)
- scipy (科學計算)

**預計安裝時間**: 5-10 分鐘（視網路速度而定）

### 6. 驗證安裝

```bash
python -c "import PyQt5; import rtde_control; import numpy; print('✅ 所有依賴套件安裝成功')"
```

如果沒有錯誤訊息，表示安裝成功！

---

## 常見安裝問題

### 問題 1: PyQt5 安裝失敗

**錯誤訊息**: `error: command 'gcc' failed` 或 `Qt platform plugin...`

**解決方法 (Linux):**
若出現 `Could not load the Qt platform plugin "xcb" ... even though it was found`，
表示 Qt 已找到插件，但可能缺少其依賴的系統函式庫。此專案在 Ubuntu 24.04
曾因缺少 `libxcb-xinerama.so.0` 無法啟動，可安裝對應的執行期套件：

```bash
sudo apt install libxcb-xinerama0
./start.sh
```

在 Wayland 桌面使用 `./start.sh` 時，啟動器會優先使用原生 Wayland，並保留
X11 (`xcb`) 作為備選。若已設定 `QT_QPA_PLATFORM`，啟動器會保留該設定。
直接執行 Python 時，也可以手動選擇 Wayland：

```bash
QT_QPA_PLATFORM=wayland .venv/bin/python main.py
```

**解決方法 (Windows):**
```cmd
# 確保使用官方 Python（非 Microsoft Store 版本）
pip install PyQt5 --no-cache-dir
```

### 問題 2: ur-rtde 安裝失敗

**錯誤訊息**: `error: command 'gcc' failed` 或編譯錯誤

**解決方法 (Linux):**
```bash
sudo apt install build-essential cmake libboost-all-dev
pip install ur-rtde --no-binary :all:
```

**解決方法 (Windows):**
- 安裝 [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/)
- 或使用預編譯的 wheel:
```cmd
pip install ur-rtde
```

### 問題 3: numpy/scipy 安裝失敗

**解決方法:**
```bash
# Linux
sudo apt install python3-numpy python3-scipy
pip install numpy scipy

# Windows/macOS
pip install numpy scipy --no-cache-dir
```

### 問題 4: 權限錯誤 (Permission Denied)

**解決方法:**
```bash
# 不要使用 sudo pip，而是使用虛擬環境
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 問題 5: 缺少系統依賴

**Ubuntu/Debian 完整依賴安裝:**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv \
                 build-essential cmake \
                 qt5-default libqt5gui5 libqt5widgets5 \
                 python3-pyqt5 python3-numpy python3-scipy
```

---

## 網路設定

### 1. 確認機器人 IP 位址

在 UR10e 示教器上：
1. 點擊 **Setup Robot**
2. 點擊 **Network**
3. 記下 **IP Address**（例如：192.168.1.100）

### 2. 設定電腦網路

確保電腦與機器人在同一網段：

**範例設定:**
- **機器人 IP**: 192.168.1.100
- **子網路遮罩**: 255.255.255.0
- **電腦 IP**: 192.168.1.50（任意 1-254，避開 100）

**Linux 設定:**
```bash
# 檢查網路介面
ip addr show

# 設定靜態 IP（以 eth0 為例）
sudo ip addr add 192.168.1.50/24 dev eth0
```

**Windows 設定:**
1. 控制台 → 網路和網際網路 → 網路連線
2. 右鍵乙太網路 → 內容
3. 選擇 IPv4 → 內容
4. 設定靜態 IP

### 3. 測試連線

```bash
ping 192.168.1.100
```

如果能 ping 通，表示網路設定正確。

### 4. 檢查防火牆

**Linux:**
```bash
# 允許 RTDE 連接埠
sudo ufw allow 30004/tcp
```

**Windows:**
- 控制台 → Windows Defender 防火牆
- 進階設定 → 輸入規則 → 新增規則
- 連接埠 30004，TCP

---

## 首次執行測試

### 1. 執行程式

```bash
python main.py
```

### 2. 檢查 UI 顯示

應該會看到主視窗，包含：
- 左側控制面板（連線設定、自由驅動、急停）
- 右側監控面板（TCP、關節、力感測器顯示）

### 3. 測試連線（可選）

如果有實際機器人：
1. 在「IP 位址」欄位輸入機器人 IP
2. 點擊「連線」
3. 觀察連線狀態是否變為綠色「● 已連線」

### 4. 檢查日誌

```bash
# 查看生成的日誌檔案
ls logs/
cat logs/ur10e_control_*.log
```

---

## 目錄結構確認

執行後應該會自動創建以下目錄：

```
ur10e_control_ui/
├── config.py
├── main.py
├── robot_controller.py
├── ui_mainwindow.py
├── utils.py
├── requirements.txt
├── README.md
├── scripts/          # URScript 腳本
├── logs/            # 日誌檔案（自動創建）
└── assets/          # 資源檔案（自動創建）
```

---

## 解除安裝

### 1. 停用虛擬環境

```bash
deactivate
```

### 2. 刪除虛擬環境

```bash
rm -rf venv/
```

### 3. 刪除專案檔案

```bash
cd ..
rm -rf ur10e_control_ui/
```

---

## 開發環境設定（可選）

如果您想要修改程式碼，建議安裝以下工具：

```bash
pip install black pylint mypy pytest
```

- **black**: 程式碼格式化
- **pylint**: 程式碼檢查
- **mypy**: 型別檢查
- **pytest**: 單元測試

---

## 效能優化建議

### Linux 建議設定

```bash
# 提高網路緩衝區大小（可選）
sudo sysctl -w net.core.rmem_max=8388608
sudo sysctl -w net.core.wmem_max=8388608

# 降低網路延遲（可選）
sudo ethtool -G eth0 rx 4096 tx 4096
```

### Windows 建議設定

- 關閉不必要的背景程式
- 確保網路卡驅動程式為最新版本
- 關閉 Windows Update 自動重啟

---

## 技術支援

如果遇到無法解決的問題：

1. **檢查日誌**: `logs/ur10e_control_*.log`
2. **查看文檔**: 閱讀 `README.md` 和 `QUICK_REFERENCE.md`
3. **測試依賴**: 執行驗證指令確認套件安裝正確
4. **網路診斷**: 使用 `ping` 和 `traceroute` 檢查連線

### 有用的診斷命令

```bash
# 檢查 Python 環境
python --version
pip list

# 檢查網路
ping <robot_ip>
netstat -an | grep 30004

# 檢查程式是否正在執行
ps aux | grep python
```

---

## 下一步

安裝完成後，請閱讀：
- **README.md**: 完整使用說明
- **QUICK_REFERENCE.md**: 快速參考
- **DEVELOPMENT_STAGE1_SUMMARY.md**: 開發階段總結

準備開始使用時：
```bash
python main.py
```

---

##from Taki
python -m venv ur10e-env
source ur10e-env/bin/activate  # Linux/macOS
# 或 ur10e-env\Scripts\activate  # Windows
pip install --upgrade pip
pip install wheel
pip install -r requirements.txt
