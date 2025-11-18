# UR10e 控制系統依賴安裝指南

## 問題說明

原始的 `requirements.txt` 使用 `>=` 版本範圍會導致 pip 嘗試從源碼編譯 PyQt5，造成安裝過程卡在 "Preparing wheel metadata" 步驟。

## 解決方案

本次更新採用以下策略避免此問題：

1. **固定版本號**: 使用確定的版本號 (如 `PyQt5==5.15.10`) 而非範圍 (如 `PyQt5>=5.15.0`)
2. **預編譯包**: 優先使用預編譯的 wheel 包，避免從源碼編譯
3. **分步安裝**: 提供自動化腳本，按正確順序安裝依賴

## 安裝方法

### 方法 1: 使用自動化腳本 (推薦)

#### Linux/macOS:
```bash
# 1. 創建並啟動虛擬環境
python3 -m venv venv
source venv/bin/activate

# 2. 執行安裝腳本
chmod +x install_dependencies.sh
./install_dependencies.sh
```

#### Windows:
```cmd
REM 1. 創建並啟動虛擬環境
python -m venv venv
venv\Scripts\activate

REM 2. 執行安裝腳本
install_dependencies.bat
```

### 方法 2: 手動安裝

```bash
# 1. 升級 pip 工具
pip install --upgrade pip setuptools wheel

# 2. 安裝 PyQt5 (使用預編譯包)
pip install PyQt5==5.15.10 --only-binary=PyQt5

# 3. 安裝其他依賴
pip install -r requirements.txt
```

### 方法 3: 使用系統套件管理器 (備用方案)

如果方法 1 和 2 都失敗，可以使用系統套件管理器安裝 PyQt5：

#### Ubuntu/Debian:
```bash
# 1. 安裝系統級 PyQt5
sudo apt-get update
sudo apt-get install python3-pyqt5

# 2. 修改 requirements.txt，註解掉 PyQt5 相關行
# PyQt5==5.15.10
# PyQt5-Qt5==5.15.2
# PyQt5-sip==12.13.0

# 3. 安裝其他依賴
pip install pyqtgraph==0.13.3 ur-rtde==1.5.7 numpy==1.24.3 scipy==1.10.1
```

## 版本更改說明

| 套件 | 原版本 | 新版本 | 原因 |
|------|--------|--------|------|
| PyQt5 | >=5.15.0 | ==5.15.10 | 固定版本，使用穩定的預編譯包 |
| pyqtgraph | >=0.12.0 | ==0.13.3 | 使用最新穩定版 |
| ur-rtde | >=1.5.0 | ==1.5.7 | 使用最新穩定版 |
| numpy | >=1.21.0 | ==1.24.3 | 與 Python 3.8-3.11 兼容的穩定版 |
| scipy | >=1.7.0 | ==1.10.1 | 與 numpy 1.24.3 兼容 |

## 常見問題

### Q1: 為什麼固定版本號？
**A:** 固定版本號可以：
- 避免從源碼編譯
- 確保環境一致性
- 提高安裝成功率
- 方便問題排查

### Q2: 如果需要更新版本怎麼辦？
**A:** 可以手動更新到更新的版本：
```bash
pip install PyQt5==5.15.11 --only-binary=PyQt5
pip install pyqtgraph==0.13.4
```

### Q3: 安裝時出現權限錯誤
**A:** 
- 確保在虛擬環境中安裝
- 不要使用 `sudo pip install`
- 檢查目錄權限

### Q4: 在 ARM 架構 (如 Raspberry Pi) 上安裝失敗
**A:** ARM 架構可能沒有預編譯的 PyQt5 包，建議：
```bash
sudo apt-get install python3-pyqt5
# 然後安裝其他依賴
```

### Q5: 如何驗證安裝成功？
**A:** 運行以下命令：
```bash
python -c "import PyQt5; import pyqtgraph; import rtde; print('所有依賴已成功安裝')"
```

## Python 版本兼容性

| Python 版本 | 兼容性 | 說明 |
|-------------|--------|------|
| 3.7 | ❌ | 已停止支持 |
| 3.8 | ✅ | 完全支持 |
| 3.9 | ✅ | 完全支持 |
| 3.10 | ✅ | 完全支持 |
| 3.11 | ✅ | 完全支持 |
| 3.12 | ⚠️ | 部分支持，numpy/scipy 可能需要調整版本 |

## 技術細節

### 為什麼會卡在 "Preparing wheel metadata"？

1. **沒有預編譯包**: pip 嘗試從源碼構建 PyQt5
2. **需要編譯 C++ 代碼**: PyQt5 包含大量 C++ 擴展
3. **依賴系統庫**: 需要 Qt5 開發庫、編譯器等
4. **耗時長**: 完整編譯需要 10-30 分鐘，看起來像卡住

### `--only-binary` 標誌的作用

```bash
pip install PyQt5 --only-binary=PyQt5
```

這個標誌強制 pip：
- 只使用預編譯的 wheel 包
- 如果沒有 wheel 包就報錯，不嘗試從源碼編譯
- 大大加快安裝速度

## 其他資源

- [PyQt5 官方文檔](https://www.riverbankcomputing.com/static/Docs/PyQt5/)
- [ur-rtde 文檔](https://sdurobotics.gitlab.io/ur_rtde/)
- [pyqtgraph 文檔](https://pyqtgraph.readthedocs.io/)

## 更新日誌

- **v2.0** (2024-11): 修復 PyQt5 安裝卡住問題，固定所有依賴版本
- **v1.0** (初始版本): 使用版本範圍，存在安裝問題

---

**維護者**: Tetsu  
**最後更新**: 2024-11-13
