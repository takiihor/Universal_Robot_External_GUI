@echo off
REM UR10e 控制系統依賴安裝腳本 (Windows 版本)
REM 此腳本解決 PyQt5 安裝卡住的問題

echo ==========================================
echo   UR10e 控制系統依賴安裝腳本
echo ==========================================
echo.

REM 檢查是否在虛擬環境中
if not defined VIRTUAL_ENV (
    echo [警告] 您不在虛擬環境中
    echo 建議先創建並啟動虛擬環境:
    echo   python -m venv venv
    echo   venv\Scripts\activate
    echo.
    set /p continue="是否繼續安裝? (Y/N): "
    if /i not "%continue%"=="Y" exit /b 1
)

REM 步驟 1: 升級 pip 工具
echo 步驟 1/5: 升級 pip、setuptools 和 wheel...
python -m pip install --upgrade pip setuptools wheel
if errorlevel 1 (
    echo [錯誤] pip 升級失敗
    exit /b 1
)
echo [完成]
echo.

REM 步驟 2: 安裝 PyQt5
echo 步驟 2/5: 安裝 PyQt5 (使用預編譯二進制包)...
python -m pip install PyQt5==5.15.10 --only-binary=PyQt5
if errorlevel 1 (
    echo [錯誤] PyQt5 安裝失敗
    echo 請嘗試手動安裝: pip install PyQt5==5.15.10
    exit /b 1
)
echo [完成]
echo.

REM 步驟 3: 安裝數值計算庫
echo 步驟 3/5: 安裝 NumPy 和 SciPy...
python -m pip install numpy==1.24.3
python -m pip install scipy==1.10.1
if errorlevel 1 (
    echo [錯誤] NumPy/SciPy 安裝失敗
    exit /b 1
)
echo [完成]
echo.

REM 步驟 4: 安裝繪圖庫
echo 步驟 4/5: 安裝 pyqtgraph...
python -m pip install pyqtgraph==0.13.3
if errorlevel 1 (
    echo [錯誤] pyqtgraph 安裝失敗
    exit /b 1
)
echo [完成]
echo.

REM 步驟 5: 安裝 UR 機器人通訊庫
echo 步驟 5/5: 安裝 ur-rtde...
python -m pip install ur-rtde==1.5.7
if errorlevel 1 (
    echo [錯誤] ur-rtde 安裝失敗
    exit /b 1
)
echo [完成]
echo.

REM 驗證安裝
echo ==========================================
echo   驗證安裝
echo ==========================================
echo.

python -c "import PyQt5.QtCore; print('PyQt5 版本:', PyQt5.QtCore.PYQT_VERSION_STR)"
python -c "import pyqtgraph; print('pyqtgraph 版本:', pyqtgraph.__version__)"
python -c "import rtde; print('ur-rtde: 安裝成功')"
python -c "import numpy; print('NumPy 版本:', numpy.__version__)"
python -c "import scipy; print('SciPy 版本:', scipy.__version__)"

if errorlevel 1 (
    echo.
    echo [錯誤] 部分依賴驗證失敗
    exit /b 1
)

echo.
echo ==========================================
echo   安裝完成!
echo ==========================================
echo.
echo 您現在可以運行 UR10e 控制程序了
pause
