#!/bin/bash
# UR10e 控制系統依賴修復腳本 v2
# 解決 numpy 損壞和 ur-rtde 導入問題

set -e

echo "=========================================="
echo "  UR10e 依賴修復腳本 v2"
echo "=========================================="
echo ""

# 檢查是否在虛擬環境中
if [ -z "$VIRTUAL_ENV" ]; then
    echo "❌ 錯誤: 請先啟動虛擬環境"
    echo "   source venv/bin/activate"
    exit 1
fi

echo "虛擬環境路徑: $VIRTUAL_ENV"
SITE_PACKAGES="$VIRTUAL_ENV/lib/python3.8/site-packages"
echo "套件目錄: $SITE_PACKAGES"
echo ""

# 步驟 1: 徹底清理損壞的 numpy
echo "步驟 1/5: 徹底清理損壞的 numpy..."

# 先卸載 numpy
pip uninstall -y numpy 2>/dev/null || true

# 清理所有異常的 numpy 目錄
echo "正在清理異常的 numpy 目錄..."
cd "$SITE_PACKAGES"

# 使用 find 命令查找並刪除所有異常的 numpy 目錄
find . -maxdepth 1 -type d \( -name "*umpy*" -o -name "~*numpy*" -o -name "-*numpy*" \) -exec rm -rf {} + 2>/dev/null || true

# 清理 dist-info
find . -maxdepth 1 -type d \( -name "*umpy*.dist-info" -o -name "~*numpy*.dist-info" -o -name "-*numpy*.dist-info" \) -exec rm -rf {} + 2>/dev/null || true

# 驗證清理
REMAINING=$(ls -d *umpy* 2>/dev/null | wc -l)
if [ "$REMAINING" -eq 0 ]; then
    echo "✓ 所有異常 numpy 目錄已清理"
else
    echo "⚠ 仍有 $REMAINING 個異常目錄，手動清理中..."
    ls -d *umpy* 2>/dev/null | xargs rm -rf
fi
echo ""

# 步驟 2: 清理 pip 緩存
echo "步驟 2/5: 清理 pip 緩存..."
pip cache purge
echo "✓ 完成"
echo ""

# 步驟 3: 重新安裝 numpy
echo "步驟 3/5: 重新安裝 numpy..."
pip install --no-cache-dir numpy==1.24.3
echo "✓ 完成"
echo ""

# 驗證 numpy
python3 << 'EOF'
try:
    import numpy as np
    print(f"✓ NumPy 安裝成功: {np.__version__}")
    print(f"  路徑: {np.__file__}")
except Exception as e:
    print(f"✗ NumPy 驗證失敗: {e}")
    exit(1)
EOF

if [ $? -ne 0 ]; then
    echo "❌ NumPy 安裝失敗，請檢查錯誤信息"
    exit 1
fi
echo ""

# 步驟 4: 安裝系統依賴並重新安裝 ur-rtde
echo "步驟 4/5: 安裝 ur-rtde..."

# 先檢查是否需要系統依賴
echo "檢查系統依賴..."
if ! dpkg -l | grep -q "build-essential"; then
    echo "安裝系統構建工具..."
    sudo apt-get update
    sudo apt-get install -y build-essential cmake libboost-all-dev python3-dev
fi

# 卸載舊的 ur-rtde
echo "卸載舊的 ur-rtde..."
pip uninstall -y ur-rtde 2>/dev/null || true

# 重新安裝 ur-rtde
echo "安裝 ur-rtde==1.5.7..."
pip install --no-cache-dir ur-rtde==1.5.7

echo "✓ 完成"
echo ""

# 驗證 ur-rtde
echo "驗證 ur-rtde 安裝..."
python3 << 'EOF'
import sys
import traceback

try:
    import rtde
    print(f"✓ ur-rtde 模塊導入成功")
    print(f"  路徑: {rtde.__file__}")
    
    # 測試關鍵接口
    errors = []
    try:
        from rtde import RTDEControlInterface
        print(f"✓ RTDEControlInterface 可用")
    except ImportError as e:
        errors.append(f"RTDEControlInterface: {e}")
    
    try:
        from rtde import RTDEReceiveInterface
        print(f"✓ RTDEReceiveInterface 可用")
    except ImportError as e:
        errors.append(f"RTDEReceiveInterface: {e}")
    
    try:
        from rtde import RTDEIOInterface
        print(f"✓ RTDEIOInterface 可用")
    except ImportError as e:
        errors.append(f"RTDEIOInterface: {e}")
    
    if errors:
        print("\n⚠ 部分接口不可用:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)
    
    sys.exit(0)
    
except ImportError as e:
    print(f"✗ ur-rtde 導入失敗: {e}")
    print("\n完整錯誤追蹤:")
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"✗ 未知錯誤: {e}")
    traceback.print_exc()
    sys.exit(1)
EOF

RTDE_STATUS=$?
echo ""

# 步驟 5: 完整驗證所有依賴
echo "步驟 5/5: 完整驗證所有依賴..."
echo "=========================================="

python3 << 'EOF'
import sys

def check_module(name, import_name=None, show_version=True):
    if import_name is None:
        import_name = name
    
    try:
        module = __import__(import_name)
        if show_version:
            version = getattr(module, '__version__', 'unknown')
            print(f"✓ {name:20s} 版本: {version}")
        else:
            if name == "PyQt5":
                from PyQt5.QtCore import PYQT_VERSION_STR
                print(f"✓ {name:20s} 版本: {PYQT_VERSION_STR}")
            else:
                print(f"✓ {name:20s} 已安裝")
        return True
    except ImportError as e:
        print(f"✗ {name:20s} 導入失敗: {e}")
        return False
    except Exception as e:
        print(f"⚠ {name:20s} 部分問題: {e}")
        return False

print("檢查所有套件:")
all_ok = True
all_ok &= check_module("PyQt5", "PyQt5.QtCore", show_version=False)
all_ok &= check_module("pyqtgraph")
all_ok &= check_module("numpy")
all_ok &= check_module("scipy")
all_ok &= check_module("ur-rtde", "rtde")

print("=" * 60)

if all_ok:
    print("\n✅ 所有依賴驗證成功!")
    sys.exit(0)
else:
    print("\n❌ 部分依賴仍有問題")
    sys.exit(1)
EOF

VERIFY_STATUS=$?
echo ""

# 最終結果
echo "=========================================="
if [ $RTDE_STATUS -eq 0 ] && [ $VERIFY_STATUS -eq 0 ]; then
    echo "  ✅ 修復完成!"
    echo "=========================================="
    echo ""
    echo "所有依賴已正常工作，可以運行 UR10e 控制程序了"
    echo ""
    echo "建議運行完整測試："
    echo "  python test_dependencies.py"
    exit 0
else
    echo "  ⚠ 部分問題仍存在"
    echo "=========================================="
    echo ""
    
    if [ $RTDE_STATUS -ne 0 ]; then
        echo "❌ ur-rtde 仍無法正常工作"
        echo ""
        echo "請嘗試以下診斷步驟:"
        echo "1. 檢查詳細錯誤:"
        echo "   python -c 'import rtde; print(rtde.__file__)'"
        echo ""
        echo "2. 檢查共享庫依賴:"
        echo "   find $VIRTUAL_ENV -name '*.so' -path '*/rtde/*' -exec ldd {} \;"
        echo ""
        echo "3. 嘗試從源碼安裝:"
        echo "   pip uninstall -y ur-rtde"
        echo "   pip install ur-rtde==1.5.7 --no-binary :all:"
        echo ""
    fi
    
    echo "或參考詳細排查文檔:"
    echo "  cat TROUBLESHOOTING.md"
    
    exit 1
fi