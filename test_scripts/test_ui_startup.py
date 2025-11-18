#!/usr/bin/env python3
"""
測試 UI 是否可以正常啟動（不連線機器人）
這個測試會啟動 UI 視窗 3 秒後自動關閉
"""
import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
import ui_mainwindow

def test_ui_startup():
    """測試 UI 啟動"""

    print("=" * 60)
    print("測試 UI 啟動")
    print("=" * 60)

    try:
        # 創建應用程式
        app = QApplication(sys.argv)

        print("✅ QApplication 創建成功")

        # 創建主視窗
        window = ui_mainwindow.MainWindow()
        print("✅ MainWindow 創建成功")

        # 顯示視窗
        window.show()
        print("✅ 視窗顯示成功")

        # 設定 3 秒後自動關閉
        def auto_close():
            print("\n⏰ 測試時間到，自動關閉視窗")
            print("=" * 60)
            print("UI 啟動測試通過 ✅")
            print("=" * 60)
            print("\n提示：如果視窗顯示正常，表示 UI 程式碼沒有問題！")
            window.close()
            app.quit()

        timer = QTimer()
        timer.timeout.connect(auto_close)
        timer.start(3000)  # 3 秒

        print("\n🖥️  UI 視窗已開啟，將在 3 秒後自動關閉...")
        print("請檢查視窗是否正常顯示：")
        print("  - 視窗標題：UR10e 控制系統")
        print("  - 連線面板（IP、Port 輸入框）")
        print("  - 自由驅動按鈕")
        print("  - 急停按鈕（紅色）")
        print("  - TCP 位姿顯示區域")
        print("  - 關節角度顯示區域")
        print("  - 力感測器顯示區域")
        print("  - 系統訊息區域")

        # 執行應用程式
        sys.exit(app.exec_())

    except Exception as e:
        print(f"❌ UI 啟動失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_ui_startup()
