#!/usr/bin/env python3
"""
測試所有模組是否可以正確導入
"""
import sys

def test_imports():
    """測試所有核心模組的導入"""

    print("=" * 60)
    print("開始模組導入測試")
    print("=" * 60)

    tests_passed = 0
    tests_failed = 0

    # 測試 1: 導入標準庫
    try:
        import logging
        import json
        import os
        print("✅ 標準庫導入成功")
        tests_passed += 1
    except ImportError as e:
        print(f"❌ 標準庫導入失敗: {e}")
        tests_failed += 1

    # 測試 2: 導入第三方庫
    try:
        import numpy as np
        print(f"✅ NumPy 導入成功 (版本: {np.__version__})")
        tests_passed += 1
    except ImportError as e:
        print(f"❌ NumPy 導入失敗: {e}")
        tests_failed += 1

    try:
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import QThread, pyqtSignal
        print("✅ PyQt5 導入成功")
        tests_passed += 1
    except ImportError as e:
        print(f"❌ PyQt5 導入失敗: {e}")
        tests_failed += 1

    try:
        import pyqtgraph as pg
        print(f"✅ PyQtGraph 導入成功")
        tests_passed += 1
    except ImportError as e:
        print(f"⚠️  PyQtGraph 導入失敗（第三階段才需要）: {e}")
        # 不計入失敗，因為階段一可能還不需要

    # 測試 3: 導入專案模組
    try:
        import config
        print("✅ config.py 導入成功")
        tests_passed += 1
    except Exception as e:
        print(f"❌ config.py 導入失敗: {e}")
        tests_failed += 1
        return False

    try:
        import utils
        print("✅ utils.py 導入成功")
        tests_passed += 1
    except Exception as e:
        print(f"❌ utils.py 導入失敗: {e}")
        tests_failed += 1
        return False

    try:
        import robot_controller
        print("✅ robot_controller.py 導入成功")
        tests_passed += 1
    except Exception as e:
        print(f"❌ robot_controller.py 導入失敗: {e}")
        tests_failed += 1
        return False

    try:
        import ui_mainwindow
        print("✅ ui_mainwindow.py 導入成功")
        tests_passed += 1
    except Exception as e:
        print(f"❌ ui_mainwindow.py 導入失敗: {e}")
        tests_failed += 1
        return False

    # 測試結果
    print("=" * 60)
    print(f"測試完成: {tests_passed} 通過, {tests_failed} 失敗")
    print("=" * 60)

    return tests_failed == 0

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
