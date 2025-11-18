#!/usr/bin/env python3
"""
測試 config.py 的功能
"""
import config
import os
import json

def test_config():
    """測試設定模組"""

    print("=" * 60)
    print("測試 Config 模組")
    print("=" * 60)

    # 測試 1: 檢查預設參數
    print("\n測試 1: 預設參數")
    print(f"  DEFAULT_IP: {config.Config.DEFAULT_IP}")
    print(f"  DEFAULT_PORT: {config.Config.DEFAULT_PORT}")
    print(f"  DEFAULT_TCP_SPEED: {config.Config.DEFAULT_TCP_SPEED}")
    print(f"  TCP_STEP_SIZES: {config.Config.TCP_STEP_SIZES}")
    print("✅ 預設參數讀取成功")

    # 測試 2: 預設位置
    print("\n測試 2: 預設位置")
    home_pos = config.Config.get_preset_position('home')
    print(f"  Home 位置: {home_pos}")
    if home_pos and len(home_pos) == 6:
        print("✅ 預設位置格式正確")
    else:
        print("❌ 預設位置格式錯誤")
        return False

    # 測試 3: 儲存與載入設定
    print("\n測試 3: 設定檔儲存/載入")
    # 使用預設設定格式
    test_config_data = config.Config.get_default_config()
    # 修改一些值來測試
    test_config_data['connection']['ip'] = '192.168.1.200'
    test_config_data['motion']['tcp_speed'] = 0.15

    test_file = 'test_config.json'
    try:
        config.Config.save_config(test_config_data, test_file)
        print(f"  ✅ 設定儲存成功: {test_file}")

        loaded = config.Config.load_config(test_file)
        if loaded['connection']['ip'] == '192.168.1.200' and loaded['motion']['tcp_speed'] == 0.15:
            print("  ✅ 設定載入成功且內容正確")
        else:
            print("  ❌ 設定載入後內容不符")
            return False

        # 清理測試檔案
        os.remove(test_file)
        print("  ✅ 測試檔案清理完成")

    except Exception as e:
        print(f"  ❌ 設定檔操作失敗: {e}")
        return False

    print("\n" + "=" * 60)
    print("Config 模組測試通過 ✅")
    print("=" * 60)
    return True

if __name__ == "__main__":
    import sys
    success = test_config()
    sys.exit(0 if success else 1)
