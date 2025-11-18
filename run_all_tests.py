#!/usr/bin/env python3
"""
執行所有測試
"""
import subprocess
import sys

def run_test(test_file, test_name):
    """執行單一測試"""
    print(f"\n{'='*60}")
    print(f"執行測試: {test_name}")
    print('='*60)

    try:
        result = subprocess.run(
            [sys.executable, test_file],
            capture_output=True,
            text=True,
            timeout=10
        )

        print(result.stdout)

        if result.returncode == 0:
            print(f"✅ {test_name} 通過")
            return True
        else:
            print(f"❌ {test_name} 失敗")
            if result.stderr:
                print("錯誤訊息:")
                print(result.stderr)
            return False

    except subprocess.TimeoutExpired:
        print(f"⏰ {test_name} 超時")
        return False
    except Exception as e:
        print(f"❌ {test_name} 執行錯誤: {e}")
        return False

def main():
    """主測試函數"""
    print("="*60)
    print("UR10e 控制 UI - 自動化測試套件")
    print("="*60)

    tests = [
        ('test_imports.py', '模組導入測試'),
        ('test_config.py', 'Config 模組測試'),
        ('test_utils.py', 'Utils 模組測試'),
        ('test_ui_headless.py', 'UI 組件創建測試 (Headless)'),
    ]

    passed = 0
    failed = 0

    for test_file, test_name in tests:
        if run_test(test_file, test_name):
            passed += 1
        else:
            failed += 1

    # UI 測試提示
    print(f"\n{'='*60}")
    print("注意：完整 UI 顯示測試需要手動執行")
    print('='*60)
    print("如果你有圖形環境，執行命令：python3 test_ui_startup.py")
    print()

    # 總結
    print("="*60)
    print("測試總結")
    print("="*60)
    print(f"通過: {passed}")
    print(f"失敗: {failed}")

    if failed == 0:
        print("\n✅ 所有自動化測試通過！")
        print("程式碼可以正常運行，準備進入下一階段或連線實際機器人。")
    else:
        print("\n❌ 有測試失敗，請檢查錯誤訊息。")

    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
