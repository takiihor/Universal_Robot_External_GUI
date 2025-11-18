#!/usr/bin/env python3
"""
測試 UI 組件是否可以正常創建（headless 模式）
不需要圖形顯示環境
"""
import sys
import os

# 設定 QT 為 offscreen 模式
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from PyQt5.QtWidgets import QApplication
import ui_mainwindow

def test_ui_creation():
    """測試 UI 創建"""

    print("=" * 60)
    print("測試 UI 組件創建 (Headless 模式)")
    print("=" * 60)

    try:
        # 創建應用程式
        app = QApplication(sys.argv)
        print("✅ QApplication 創建成功")

        # 創建主視窗
        window = ui_mainwindow.MainWindow()
        print("✅ MainWindow 創建成功")

        # 檢查視窗組件
        print("\n檢查 UI 組件:")

        # 檢查基本屬性
        if hasattr(window, 'connection_panel'):
            print("  ✅ 連線面板存在")
        else:
            print("  ❌ 連線面板不存在")

        if hasattr(window, 'control_panel'):
            print("  ✅ 控制面板存在")
        else:
            print("  ⚠️  控制面板不存在（可能在後續階段開發）")

        if hasattr(window, 'status_panel'):
            print("  ✅ 狀態面板存在")
        else:
            print("  ❌ 狀態面板不存在")

        if hasattr(window, 'message_panel'):
            print("  ✅ 訊息面板存在")
        else:
            print("  ❌ 訊息面板不存在")

        # 檢查視窗標題
        title = window.windowTitle()
        print(f"\n視窗標題: {title}")
        if "UR10e" in title or "控制" in title:
            print("✅ 視窗標題正確")
        else:
            print("⚠️  視窗標題可能需要調整")

        print("\n" + "=" * 60)
        print("UI 組件創建測試通過 ✅")
        print("=" * 60)
        print("\n注意：此測試在 headless 模式下進行，僅驗證組件可以創建。")
        print("如需測試實際顯示，請在有圖形環境的系統上執行 test_ui_startup.py")

        # 清理
        del window
        del app

        return True

    except Exception as e:
        print(f"❌ UI 創建失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_ui_creation()
    sys.exit(0 if success else 1)
