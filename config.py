"""
UR10e 控制 UI 系統設定管理模組

此模組負責管理所有系統參數、連線設定、預設位置等。
提供設定檔的載入與儲存功能。
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

from force_control.config import ForceConfig

# 設定日誌
logger = logging.getLogger(__name__)


class Config:
    """系統設定管理類別"""

    # ========================================
    # 連線參數
    # ========================================
    DEFAULT_IP = os.environ.get("ROBOT_IP", "").strip() or "192.168.1.10"
    DEFAULT_PORT = 30004
    DEFAULT_RTDE_FREQUENCY = 125  # Hz

    # ========================================
    # 運動控制參數
    # ========================================
    # TCP 運動參數
    DEFAULT_TCP_SPEED = 0.05  # m/s
    DEFAULT_TCP_ACCEL = 0.5  # m/s²
    MIN_TCP_SPEED = 0.01  # m/s
    MAX_TCP_SPEED = 0.5  # m/s
    MIN_TCP_ACCEL = 0.1  # m/s²
    MAX_TCP_ACCEL = 2.0  # m/s²

    # 關節運動參數
    DEFAULT_JOINT_SPEED = 0.1  # rad/s
    DEFAULT_JOINT_ACCEL = 1.0  # rad/s²
    MIN_JOINT_SPEED = 0.05  # rad/s
    MAX_JOINT_SPEED = 0.4  # rad/s
    MIN_JOINT_ACCEL = 0.1  # rad/s²
    MAX_JOINT_ACCEL = 3.0  # rad/s²

    # 移動步長選項
    TCP_STEP_SIZES = [0.001, 0.005, 0.01, 0.05]  # m (1mm, 5mm, 10mm, 50mm)
    JOINT_STEP_SIZES = [0.017453, 0.087266, 0.174533, 0.785398]  # rad (1°, 5°, 10°, 45°)
    ROTATION_STEP_SIZES = [0.017453, 0.087266, 0.174533, 0.261799]  # rad (1°, 5°, 10°, 15°)

    # ========================================
    # 安全參數
    # ========================================
    # 工作空間限制 (相對於基座標系)
    WORKSPACE_LIMITS = {
        'x_min': -0.8,
        'x_max': 0.8,
        'y_min': -0.8,
        'y_max': 0.8,
        'z_min': 0.0,
        'z_max': 1.2
    }

    # 力感測器閾值 - Normal Mode
    MAX_FORCE_THRESHOLD = 50.0  # N
    MAX_TORQUE_THRESHOLD = 10.0  # Nm
    COLLISION_FORCE_SPIKE = 20.0  # N (sudden force change)

    # 力感測器閾值 - Freedrive Mode (relaxed limits for hand-guiding)
    FREEDRIVE_MAX_FORCE_THRESHOLD = 80.0  # N (higher limit for manual guiding)
    FREEDRIVE_MAX_TORQUE_THRESHOLD = 15.0  # Nm
    FREEDRIVE_COLLISION_FORCE_SPIKE = 35.0  # N (higher spike threshold)

    # 速度限制
    MAX_VELOCITY = 1.0  # m/s

    # 自由驅動超時
    FREEDRIVE_TIMEOUT = 300  # 秒 (5分鐘)

    # ========================================
    # 預設位置 (關節角度，單位：rad)
    # ========================================
    PRESET_POSITIONS = {
        'home': {
            'joints': [0.0, -1.5708, 1.5708, -1.5708, -1.5708, 0.0],
            'description': '原點位置'
        },
        'safe': {
            'joints': [0.0, -2.0, 2.0, -1.5708, -1.5708, 0.0],
            'description': '安全位置 (較高)'
        },
        'vertical': {
            'joints': [0.0, -1.5708, 0.0, -1.5708, -1.5708, 0.0],
            'description': '垂直向下位置'
        }
    }

    # ========================================
    # 資料記錄參數
    # ========================================
    LOG_FREQUENCY = 100  # Hz
    LOG_BUFFER_SIZE = 10000  # 最大緩衝區大小
    DEFAULT_LOG_DIR = "logs"
    DEFAULT_DATA_FORMAT = "csv"  # csv 或 hdf5

    # ========================================
    # UI 參數
    # ========================================
    # 圖表更新頻率
    CHART_UPDATE_RATE = 30  # Hz
    CHART_HISTORY_LENGTH = 1000  # 顯示的歷史資料點數

    # 狀態更新頻率
    STATUS_UPDATE_RATE = 10  # Hz

    # ========================================
    # 檔案路徑
    # ========================================
    CONFIG_FILE = "config.json"
    SCRIPTS_DIR = "scripts"
    LOGS_DIR = "logs"
    ASSETS_DIR = "assets"

    # ========================================
    # 方法
    # ========================================

    @staticmethod
    def load_config(filepath: str = None) -> Dict[str, Any]:
        """
        從 JSON 檔案載入設定

        Args:
            filepath: 設定檔路徑，若為 None 則使用預設路徑

        Returns:
            Dict[str, Any]: 設定字典
        """
        if filepath is None:
            filepath = Config.CONFIG_FILE

        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    config_dict = json.load(f)
                logger.info(f"成功載入設定檔: {filepath}")
                return config_dict
            else:
                logger.warning(f"設定檔不存在: {filepath}，使用預設設定")
                return Config.get_default_config()
        except json.JSONDecodeError as e:
            logger.error(f"設定檔 JSON 格式錯誤: {e}")
            return Config.get_default_config()
        except Exception as e:
            logger.error(f"載入設定檔失敗: {e}")
            return Config.get_default_config()

    @staticmethod
    def save_config(config_dict: Dict[str, Any], filepath: str = None) -> bool:
        """
        儲存設定到 JSON 檔案

        Args:
            config_dict: 設定字典
            filepath: 儲存路徑，若為 None 則使用預設路徑

        Returns:
            bool: 是否成功儲存
        """
        if filepath is None:
            filepath = Config.CONFIG_FILE

        try:
            # 驗證設定
            if not Config.validate_config(config_dict):
                logger.error("設定驗證失敗，取消儲存")
                return False

            # 確保目錄存在
            os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else '.', exist_ok=True)

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=4, ensure_ascii=False)
            logger.info(f"成功儲存設定檔: {filepath}")
            return True
        except Exception as e:
            logger.error(f"儲存設定檔失敗: {e}")
            return False

    @staticmethod
    def get_default_config() -> Dict[str, Any]:
        """
        獲取預設設定

        Returns:
            Dict[str, Any]: 預設設定字典
        """
        return {
            'connection': {
                'ip': Config.DEFAULT_IP,
                'port': Config.DEFAULT_PORT,
                'rtde_frequency': Config.DEFAULT_RTDE_FREQUENCY
            },
            'motion': {
                'tcp_speed': Config.DEFAULT_TCP_SPEED,
                'tcp_accel': Config.DEFAULT_TCP_ACCEL,
                'joint_speed': Config.DEFAULT_JOINT_SPEED,
                'joint_accel': Config.DEFAULT_JOINT_ACCEL
            },
            'force_control': {
                'target_force': ForceConfig.DEFAULT_TARGET_FORCE,
                'force_type': ForceConfig.DEFAULT_FORCE_TYPE,
                'linear_speed': ForceConfig.DEFAULT_LINEAR_SPEED,
                'angular_speed': ForceConfig.DEFAULT_ANGULAR_SPEED,
                'timeout': ForceConfig.DEFAULT_TIMEOUT
            },
            'safety': {
                'workspace_limits': Config.WORKSPACE_LIMITS,
                'max_force_threshold': Config.MAX_FORCE_THRESHOLD,
                'max_torque_threshold': Config.MAX_TORQUE_THRESHOLD
            },
            'preset_positions': Config.PRESET_POSITIONS,
            'logging': {
                'frequency': Config.LOG_FREQUENCY,
                'buffer_size': Config.LOG_BUFFER_SIZE,
                'log_dir': Config.DEFAULT_LOG_DIR
            }
        }

    @staticmethod
    def validate_config(config_dict: Dict[str, Any]) -> bool:
        """
        驗證設定參數的有效性

        Args:
            config_dict: 設定字典

        Returns:
            bool: 設定是否有效
        """
        try:
            # 檢查必要的頂層鍵
            required_keys = ['connection', 'motion', 'force_control', 'safety']
            for key in required_keys:
                if key not in config_dict:
                    logger.error(f"設定缺少必要鍵: {key}")
                    return False

            # 驗證連線參數
            conn = config_dict['connection']
            if not isinstance(conn.get('port'), int) or not (1 <= conn['port'] <= 65535):
                logger.error(f"無效的 port: {conn.get('port')}")
                return False

            # 驗證運動參數
            motion = config_dict['motion']
            if not (Config.MIN_TCP_SPEED <= motion.get('tcp_speed', 0) <= Config.MAX_TCP_SPEED):
                logger.error(f"TCP 速度超出範圍: {motion.get('tcp_speed')}")
                return False

            if not (Config.MIN_JOINT_SPEED <= motion.get('joint_speed', 0) <= Config.MAX_JOINT_SPEED):
                logger.error(f"關節速度超出範圍: {motion.get('joint_speed')}")
                return False

            # 驗證力控制參數
            force = config_dict['force_control']
            if not (ForceConfig.MIN_TARGET_FORCE <= force.get('target_force', 0) <= ForceConfig.MAX_TARGET_FORCE):
                logger.error(f"目標力超出範圍: {force.get('target_force')}")
                return False

            logger.info("設定驗證通過")
            return True

        except Exception as e:
            logger.error(f"設定驗證過程發生錯誤: {e}")
            return False

    @staticmethod
    def get_preset_position(name: str) -> Optional[List[float]]:
        """
        取得預設位置的關節角度

        Args:
            name: 位置名稱

        Returns:
            Optional[List[float]]: 關節角度列表，若不存在則返回 None
        """
        if name in Config.PRESET_POSITIONS:
            return Config.PRESET_POSITIONS[name]['joints']
        else:
            logger.warning(f"預設位置不存在: {name}")
            return None

    @staticmethod
    def add_preset_position(name: str, joints: List[float], description: str = "") -> bool:
        """
        新增預設位置

        Args:
            name: 位置名稱
            joints: 關節角度列表 [j1, j2, j3, j4, j5, j6]
            description: 位置描述

        Returns:
            bool: 是否成功新增
        """
        try:
            if len(joints) != 6:
                logger.error(f"關節角度數量錯誤: {len(joints)}，應為 6")
                return False

            Config.PRESET_POSITIONS[name] = {
                'joints': joints,
                'description': description
            }
            logger.info(f"成功新增預設位置: {name}")
            return True
        except Exception as e:
            logger.error(f"新增預設位置失敗: {e}")
            return False

    @staticmethod
    def remove_preset_position(name: str) -> bool:
        """
        移除預設位置

        Args:
            name: 位置名稱

        Returns:
            bool: 是否成功移除
        """
        if name in Config.PRESET_POSITIONS:
            del Config.PRESET_POSITIONS[name]
            logger.info(f"成功移除預設位置: {name}")
            return True
        else:
            logger.warning(f"預設位置不存在: {name}")
            return False

    @staticmethod
    def create_directories():
        """創建必要的資料夾"""
        directories = [Config.SCRIPTS_DIR, Config.LOGS_DIR, Config.ASSETS_DIR]
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
        logger.info("已創建必要的資料夾")


# 在模組載入時自動創建必要的資料夾
Config.create_directories()
