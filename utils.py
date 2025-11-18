"""
UR10e 控制 UI 系統工具函數模組

提供座標轉換、向量運算、資料處理、安全檢查等通用函數。
"""

import numpy as np
import math
import os
from pathlib import Path
from typing import List, Tuple, Optional
from datetime import datetime
import logging

# 設定日誌
logger = logging.getLogger(__name__)


# ========================================
# 座標轉換函數
# ========================================

def pose_to_matrix(pose: List[float]) -> np.ndarray:
    """
    將位姿 [x, y, z, rx, ry, rz] 轉換為 4x4 變換矩陣

    Args:
        pose: [x, y, z, rx, ry, rz] (位置單位: m, 旋轉單位: rad)

    Returns:
        np.ndarray: 4x4 變換矩陣
    """
    x, y, z, rx, ry, rz = pose

    # 旋轉向量的模
    angle = math.sqrt(rx**2 + ry**2 + rz**2)

    if angle < 1e-6:
        # 旋轉角度接近零，使用單位旋轉矩陣
        rotation_matrix = np.eye(3)
    else:
        # 旋轉軸
        axis = np.array([rx, ry, rz]) / angle

        # 使用 Rodrigues 公式
        K = np.array([
            [0, -axis[2], axis[1]],
            [axis[2], 0, -axis[0]],
            [-axis[1], axis[0], 0]
        ])

        rotation_matrix = (np.eye(3) +
                          math.sin(angle) * K +
                          (1 - math.cos(angle)) * np.dot(K, K))

    # 組合成 4x4 變換矩陣
    transform = np.eye(4)
    transform[0:3, 0:3] = rotation_matrix
    transform[0:3, 3] = [x, y, z]

    return transform


def matrix_to_pose(matrix: np.ndarray) -> List[float]:
    """
    將 4x4 變換矩陣轉換為位姿 [x, y, z, rx, ry, rz]

    Args:
        matrix: 4x4 變換矩陣

    Returns:
        List[float]: [x, y, z, rx, ry, rz]
    """
    # 提取位置
    x, y, z = matrix[0:3, 3]

    # 提取旋轉矩陣
    R = matrix[0:3, 0:3]

    # 計算旋轉向量 (使用 Rodrigues 公式的逆運算)
    trace = np.trace(R)
    angle = math.acos(np.clip((trace - 1) / 2, -1, 1))

    if angle < 1e-6:
        # 旋轉角度接近零
        rx, ry, rz = 0, 0, 0
    else:
        # 旋轉軸
        axis = (1 / (2 * math.sin(angle))) * np.array([
            R[2, 1] - R[1, 2],
            R[0, 2] - R[2, 0],
            R[1, 0] - R[0, 1]
        ])
        rx, ry, rz = axis * angle

    return [x, y, z, rx, ry, rz]


def quaternion_to_euler(q: List[float]) -> List[float]:
    """
    四元數轉歐拉角 (ZYX順序)

    Args:
        q: [w, x, y, z] 四元數

    Returns:
        List[float]: [roll, pitch, yaw] (單位: rad)
    """
    w, x, y, z = q

    # Roll (X軸旋轉)
    sinr_cosp = 2 * (w * x + y * z)
    cosr_cosp = 1 - 2 * (x * x + y * y)
    roll = math.atan2(sinr_cosp, cosr_cosp)

    # Pitch (Y軸旋轉)
    sinp = 2 * (w * y - z * x)
    if abs(sinp) >= 1:
        pitch = math.copysign(math.pi / 2, sinp)
    else:
        pitch = math.asin(sinp)

    # Yaw (Z軸旋轉)
    siny_cosp = 2 * (w * z + x * y)
    cosy_cosp = 1 - 2 * (y * y + z * z)
    yaw = math.atan2(siny_cosp, cosy_cosp)

    return [roll, pitch, yaw]


def euler_to_quaternion(euler: List[float]) -> List[float]:
    """
    歐拉角轉四元數 (ZYX順序)

    Args:
        euler: [roll, pitch, yaw] (單位: rad)

    Returns:
        List[float]: [w, x, y, z] 四元數
    """
    roll, pitch, yaw = euler

    cy = math.cos(yaw * 0.5)
    sy = math.sin(yaw * 0.5)
    cp = math.cos(pitch * 0.5)
    sp = math.sin(pitch * 0.5)
    cr = math.cos(roll * 0.5)
    sr = math.sin(roll * 0.5)

    w = cr * cp * cy + sr * sp * sy
    x = sr * cp * cy - cr * sp * sy
    y = cr * sp * cy + sr * cp * sy
    z = cr * cp * sy - sr * sp * cy

    return [w, x, y, z]


# ========================================
# 向量運算
# ========================================

def vector_magnitude(vec: List[float]) -> float:
    """
    計算向量長度

    Args:
        vec: 向量

    Returns:
        float: 向量的模
    """
    return math.sqrt(sum(x**2 for x in vec))


def normalize_vector(vec: List[float]) -> List[float]:
    """
    向量正規化

    Args:
        vec: 向量

    Returns:
        List[float]: 單位向量
    """
    mag = vector_magnitude(vec)
    if mag < 1e-10:
        logger.warning("向量長度接近零，無法正規化")
        return vec
    return [x / mag for x in vec]


def dot_product(vec1: List[float], vec2: List[float]) -> float:
    """
    向量內積

    Args:
        vec1: 向量1
        vec2: 向量2

    Returns:
        float: 內積結果
    """
    if len(vec1) != len(vec2):
        raise ValueError(f"向量維度不匹配: {len(vec1)} vs {len(vec2)}")
    return sum(a * b for a, b in zip(vec1, vec2))


def cross_product(vec1: List[float], vec2: List[float]) -> List[float]:
    """
    向量外積 (僅適用於3D向量)

    Args:
        vec1: 向量1 [x, y, z]
        vec2: 向量2 [x, y, z]

    Returns:
        List[float]: 外積結果 [x, y, z]
    """
    if len(vec1) != 3 or len(vec2) != 3:
        raise ValueError("外積僅適用於 3D 向量")

    return [
        vec1[1] * vec2[2] - vec1[2] * vec2[1],
        vec1[2] * vec2[0] - vec1[0] * vec2[2],
        vec1[0] * vec2[1] - vec1[1] * vec2[0]
    ]


# ========================================
# 資料處理
# ========================================

def moving_average_filter(data: np.ndarray, window_size: int) -> np.ndarray:
    """
    移動平均濾波

    Args:
        data: 原始資料
        window_size: 視窗大小

    Returns:
        np.ndarray: 濾波後的資料
    """
    if window_size < 1:
        return data

    cumsum = np.cumsum(np.insert(data, 0, 0))
    return (cumsum[window_size:] - cumsum[:-window_size]) / window_size


def low_pass_filter(data: np.ndarray, cutoff_freq: float, sampling_freq: float) -> np.ndarray:
    """
    簡單的一階低通濾波器

    Args:
        data: 原始資料
        cutoff_freq: 截止頻率 (Hz)
        sampling_freq: 採樣頻率 (Hz)

    Returns:
        np.ndarray: 濾波後的資料
    """
    RC = 1.0 / (2 * math.pi * cutoff_freq)
    dt = 1.0 / sampling_freq
    alpha = dt / (RC + dt)

    filtered_data = np.zeros_like(data)
    filtered_data[0] = data[0]

    for i in range(1, len(data)):
        filtered_data[i] = alpha * data[i] + (1 - alpha) * filtered_data[i - 1]

    return filtered_data


def resample_trajectory(trajectory: List[List[float]], num_points: int) -> List[List[float]]:
    """
    軌跡重採樣

    Args:
        trajectory: 原始軌跡點列表
        num_points: 目標點數

    Returns:
        List[List[float]]: 重採樣後的軌跡
    """
    if len(trajectory) < 2:
        return trajectory

    trajectory_array = np.array(trajectory)
    original_indices = np.linspace(0, len(trajectory) - 1, len(trajectory))
    new_indices = np.linspace(0, len(trajectory) - 1, num_points)

    resampled = []
    for dim in range(trajectory_array.shape[1]):
        resampled_dim = np.interp(new_indices, original_indices, trajectory_array[:, dim])
        resampled.append(resampled_dim)

    return np.array(resampled).T.tolist()


# ========================================
# 檔案處理
# ========================================

def list_scripts(directory: str = "scripts") -> List[str]:
    """
    列出指定目錄下的所有 .script 檔案

    Args:
        directory: 目錄路徑

    Returns:
        List[str]: 腳本檔案路徑列表
    """
    try:
        path = Path(directory)
        if not path.exists():
            logger.warning(f"目錄不存在: {directory}")
            return []

        scripts = list(path.glob("*.script"))
        return [str(s) for s in sorted(scripts)]
    except Exception as e:
        logger.error(f"列出腳本檔案失敗: {e}")
        return []


def read_script_file(filepath: str) -> Optional[str]:
    """
    讀取腳本檔案內容

    Args:
        filepath: 檔案路徑

    Returns:
        Optional[str]: 檔案內容，失敗則返回 None
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        logger.info(f"成功讀取腳本: {filepath}")
        return content
    except Exception as e:
        logger.error(f"讀取腳本檔案失敗: {e}")
        return None


def save_trajectory(trajectory: List[List[float]], filepath: str) -> bool:
    """
    儲存軌跡到檔案 (CSV格式)

    Args:
        trajectory: 軌跡點列表
        filepath: 儲存路徑

    Returns:
        bool: 是否成功儲存
    """
    try:
        trajectory_array = np.array(trajectory)
        np.savetxt(filepath, trajectory_array, delimiter=',',
                   header='x,y,z,rx,ry,rz', comments='')
        logger.info(f"成功儲存軌跡: {filepath}")
        return True
    except Exception as e:
        logger.error(f"儲存軌跡失敗: {e}")
        return False


def load_trajectory(filepath: str) -> Optional[List[List[float]]]:
    """
    從檔案載入軌跡

    Args:
        filepath: 檔案路徑

    Returns:
        Optional[List[List[float]]]: 軌跡點列表，失敗則返回 None
    """
    try:
        trajectory_array = np.loadtxt(filepath, delimiter=',', skiprows=1)
        logger.info(f"成功載入軌跡: {filepath}")
        return trajectory_array.tolist()
    except Exception as e:
        logger.error(f"載入軌跡失敗: {e}")
        return None


# ========================================
# 安全檢查
# ========================================

def check_pose_in_workspace(pose: List[float], limits: dict) -> bool:
    """
    檢查位姿是否在工作空間內

    Args:
        pose: [x, y, z, rx, ry, rz]
        limits: 工作空間限制字典

    Returns:
        bool: 是否在工作空間內
    """
    x, y, z = pose[0:3]

    if not (limits['x_min'] <= x <= limits['x_max']):
        logger.warning(f"X 座標超出範圍: {x}")
        return False
    if not (limits['y_min'] <= y <= limits['y_max']):
        logger.warning(f"Y 座標超出範圍: {y}")
        return False
    if not (limits['z_min'] <= z <= limits['z_max']):
        logger.warning(f"Z 座標超出範圍: {z}")
        return False

    return True


def check_joint_limits(joints: List[float],
                       min_limits: List[float] = None,
                       max_limits: List[float] = None) -> bool:
    """
    檢查關節角度是否在安全範圍內

    Args:
        joints: 關節角度列表 [j1, j2, j3, j4, j5, j6]
        min_limits: 最小角度限制 (預設 ±2π)
        max_limits: 最大角度限制

    Returns:
        bool: 是否在安全範圍內
    """
    if len(joints) != 6:
        logger.error(f"關節數量錯誤: {len(joints)}")
        return False

    if min_limits is None:
        min_limits = [-2 * math.pi] * 6
    if max_limits is None:
        max_limits = [2 * math.pi] * 6

    for i, (joint, min_val, max_val) in enumerate(zip(joints, min_limits, max_limits)):
        if not (min_val <= joint <= max_val):
            logger.warning(f"關節 {i+1} 角度超出範圍: {joint}")
            return False

    return True


def calculate_safe_velocity(current_pose: List[float],
                           target_pose: List[float],
                           max_vel: float) -> float:
    """
    計算安全速度

    Args:
        current_pose: 當前位姿
        target_pose: 目標位姿
        max_vel: 最大速度

    Returns:
        float: 建議速度
    """
    # 計算距離
    distance = math.sqrt(sum((t - c)**2 for t, c in zip(target_pose[0:3], current_pose[0:3])))

    # 根據距離調整速度（距離越短，速度越慢）
    if distance < 0.01:  # 1cm
        return max_vel * 0.1
    elif distance < 0.05:  # 5cm
        return max_vel * 0.3
    elif distance < 0.1:  # 10cm
        return max_vel * 0.5
    else:
        return max_vel


# ========================================
# 時間與格式化
# ========================================

def timestamp() -> str:
    """
    返回當前時間戳字串

    Returns:
        str: 格式化的時間戳 (YYYY-MM-DD_HH-MM-SS)
    """
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def format_pose(pose: List[float], precision: int = 3) -> str:
    """
    格式化位姿顯示

    Args:
        pose: [x, y, z, rx, ry, rz]
        precision: 小數位數

    Returns:
        str: 格式化字串
    """
    format_str = f"{{:.{precision}f}}"
    return (f"X: {format_str.format(pose[0])} "
            f"Y: {format_str.format(pose[1])} "
            f"Z: {format_str.format(pose[2])} "
            f"Rx: {format_str.format(pose[3])} "
            f"Ry: {format_str.format(pose[4])} "
            f"Rz: {format_str.format(pose[5])}")


def format_force(force: List[float], precision: int = 2) -> str:
    """
    格式化力感測器資料顯示

    Args:
        force: [fx, fy, fz, tx, ty, tz]
        precision: 小數位數

    Returns:
        str: 格式化字串
    """
    format_str = f"{{:.{precision}f}}"
    return (f"Fx: {format_str.format(force[0])} "
            f"Fy: {format_str.format(force[1])} "
            f"Fz: {format_str.format(force[2])} "
            f"Tx: {format_str.format(force[3])} "
            f"Ty: {format_str.format(force[4])} "
            f"Tz: {format_str.format(force[5])}")


def format_joints(joints: List[float], precision: int = 3, in_degrees: bool = False) -> str:
    """
    格式化關節角度顯示

    Args:
        joints: [j1, j2, j3, j4, j5, j6]
        precision: 小數位數
        in_degrees: 是否顯示為角度 (預設為弧度)

    Returns:
        str: 格式化字串
    """
    format_str = f"{{:.{precision}f}}"
    unit = "°" if in_degrees else "rad"

    if in_degrees:
        joints = [radians_to_degrees(j) for j in joints]

    return " ".join([f"J{i+1}: {format_str.format(j)}{unit}"
                    for i, j in enumerate(joints)])


# ========================================
# 數學輔助
# ========================================

def clamp(value: float, min_val: float, max_val: float) -> float:
    """
    限制數值範圍

    Args:
        value: 輸入值
        min_val: 最小值
        max_val: 最大值

    Returns:
        float: 限制後的值
    """
    return max(min_val, min(max_val, value))


def interpolate_linear(start: float, end: float, t: float) -> float:
    """
    線性插值

    Args:
        start: 起始值
        end: 結束值
        t: 插值參數 (0~1)

    Returns:
        float: 插值結果
    """
    return start + (end - start) * clamp(t, 0.0, 1.0)


def degrees_to_radians(degrees: float) -> float:
    """
    角度轉弧度

    Args:
        degrees: 角度

    Returns:
        float: 弧度
    """
    return degrees * math.pi / 180.0


def radians_to_degrees(radians: float) -> float:
    """
    弧度轉角度

    Args:
        radians: 弧度

    Returns:
        float: 角度
    """
    return radians * 180.0 / math.pi


def is_nearly_equal(a: float, b: float, tolerance: float = 1e-6) -> bool:
    """
    檢查兩個浮點數是否近似相等

    Args:
        a: 數值1
        b: 數值2
        tolerance: 容差

    Returns:
        bool: 是否近似相等
    """
    return abs(a - b) < tolerance
