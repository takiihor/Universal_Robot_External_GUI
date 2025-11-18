#!/usr/bin/env python3
"""
測試 utils.py 的功能
"""
import utils
import numpy as np

def test_utils():
    """測試工具模組"""

    print("=" * 60)
    print("測試 Utils 模組")
    print("=" * 60)

    # 測試 1: 角度轉換
    print("\n測試 1: 角度轉換")
    rad = utils.degrees_to_radians(90)
    deg = utils.radians_to_degrees(rad)
    print(f"  90° → {rad:.4f} rad → {deg:.4f}°")
    if abs(deg - 90.0) < 0.01:
        print("✅ 角度轉換正確")
    else:
        print("❌ 角度轉換錯誤")
        return False

    # 測試 2: 向量運算
    print("\n測試 2: 向量運算")
    vec = [3, 4, 0]
    mag = utils.vector_magnitude(vec)
    print(f"  向量 {vec} 的長度: {mag:.2f}")
    if abs(mag - 5.0) < 0.01:
        print("✅ 向量長度計算正確")
    else:
        print("❌ 向量長度計算錯誤")
        return False

    # 測試 3: Clamp 函數
    print("\n測試 3: Clamp 函數")
    val = utils.clamp(150, 0, 100)
    print(f"  clamp(150, 0, 100) = {val}")
    if val == 100:
        print("✅ Clamp 函數正確")
    else:
        print("❌ Clamp 函數錯誤")
        return False

    # 測試 4: 格式化輸出
    print("\n測試 4: 格式化輸出")
    pose = [0.5, -0.3, 0.2, 1.57, 0, 0]
    formatted = utils.format_pose(pose)
    print(f"  位姿格式化: {formatted}")
    print("✅ 格式化函數正常")

    # 測試 5: 工作空間檢查
    print("\n測試 5: 工作空間檢查")
    test_pose = [0.5, 0.5, 0.5, 0, 0, 0]
    limits = {
        'x_min': -0.8, 'x_max': 0.8,
        'y_min': -0.8, 'y_max': 0.8,
        'z_min': 0.0, 'z_max': 1.2
    }
    in_workspace = utils.check_pose_in_workspace(test_pose, limits)
    print(f"  位姿 {test_pose[:3]} 在工作空間內: {in_workspace}")
    if in_workspace:
        print("✅ 工作空間檢查正確")
    else:
        print("❌ 工作空間檢查錯誤")
        return False

    print("\n" + "=" * 60)
    print("Utils 模組測試通過 ✅")
    print("=" * 60)
    return True

if __name__ == "__main__":
    import sys
    success = test_utils()
    sys.exit(0 if success else 1)
