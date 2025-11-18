# 创建独立 Preset Manager 模块可行性分析

## 当前架构分析

### 1. 现有预设功能分布

#### **Config.py（配置模块）**
负责预设数据的存储和管理：
```python
# 预设数据存储
PRESET_POSITIONS = {
    'home': {'joints': [...], 'description': '原点位置'},
    'safe': {'joints': [...], 'description': '安全位置'},
    'vertical': {'joints': [...], 'description': '垂直向下位置'}
}

# 预设管理方法
- get_preset_position(name)      # 获取预设位置
- add_preset_position(name, joints, description)  # 添加预设
- remove_preset_position(name)   # 删除预设
```

#### **RobotController.py（控制模块）**
负责执行预设移动：
```python
def move_to_preset_position(position_name, speed, accel):
    joints = Config.get_preset_position(position_name)
    return self.move_joint(*joints, speed, accel)
```

#### **UI_MainWindow.py（界面模块）**
负责用户交互：
- 调用 `Config` 的方法管理预设数据
- 调用 `RobotController` 的方法执行移动

## 冲突风险评估

### ✅ **无冲突区域**

1. **数据结构独立性**
   - 现有的预设数据结构简单（仅包含joints和description）
   - 可以完全替换为更复杂的数据结构

2. **接口清晰度**
   - Config和RobotController之间的接口简单明确
   - 只通过 `get_preset_position()` 方法交互

3. **功能分离性**
   - 数据管理和执行控制已经分离
   - UI层只是调用者，不涉及核心逻辑

### ⚠️ **潜在冲突点**

1. **Config类的静态方法依赖**
   - 当前使用静态方法和类变量
   - 需要决定是否保留Config中的预设功能作为后备

2. **数据持久化**
   - Config.save_config() 包含预设数据
   - 需要协调新旧数据存储方式

3. **向后兼容性**
   - 现有的预设名称（'home', 'safe', 'vertical'）需要保留
   - 其他模块可能直接引用这些名称

## 创建 Preset Manager 的实施方案

### 方案A：完全替换（推荐）

```python
# preset_manager.py
class PresetManager:
    def __init__(self):
        self.presets = {}
        self.categories = {}
        self._load_legacy_presets()  # 导入Config中的预设
        
    def _load_legacy_presets(self):
        """导入Config.PRESET_POSITIONS中的预设"""
        for name, data in Config.PRESET_POSITIONS.items():
            self.add_preset(PresetData(
                name=name,
                joints=data['joints'],
                description=data['description'],
                category='系统预设',
                locked=True  # 防止删除系统预设
            ))
    
    def get_preset_for_execution(self, name):
        """为RobotController提供执行数据"""
        preset = self.presets.get(name)
        if preset:
            return preset.joints
        return None
```

**修改 RobotController:**
```python
def move_to_preset_position(self, position_name, speed=None, accel=None):
    # 优先使用PresetManager
    if hasattr(self, 'preset_manager'):
        joints = self.preset_manager.get_preset_for_execution(position_name)
    else:
        # 回退到Config（保持兼容性）
        joints = Config.get_preset_position(position_name)
    
    if joints is None:
        self.error_occurred.emit(f"预设位置不存在: {position_name}")
        return False
    
    return self.move_joint(*joints, speed=speed, accel=accel)
```

### 方案B：渐进式迁移

```python
# preset_manager.py
class PresetManager:
    def __init__(self, config_module=None):
        self.config = config_module or Config
        self.extended_presets = {}  # 新功能的预设
        
    def get_preset(self, name):
        # 先查找扩展预设
        if name in self.extended_presets:
            return self.extended_presets[name]
        # 回退到Config
        return self.config.get_preset_position(name)
    
    def add_preset(self, preset_data):
        if preset_data.is_advanced:
            self.extended_presets[preset_data.name] = preset_data
        else:
            # 简单预设仍存储在Config中
            self.config.add_preset_position(
                preset_data.name,
                preset_data.joints,
                preset_data.description
            )
```

## 实施步骤

### 第一阶段：创建PresetManager基础结构
1. ✅ 创建 `preset_manager.py`
2. ✅ 实现基本的PresetData类
3. ✅ 导入Config中的现有预设
4. ✅ 保持与现有接口的兼容性

### 第二阶段：增强功能
1. ⭕ 添加预设分类系统
2. ⭕ 实现预设验证器
3. ⭕ 添加预设序列功能
4. ⭕ 实现导入/导出功能

### 第三阶段：UI集成
1. ⏸️ 更新UI以使用PresetManager
2. ⏸️ 添加高级预设编辑界面
3. ⏸️ 实现3D预览功能

## 代码示例：无冲突的PresetManager

```python
# preset_manager.py
from typing import List, Dict, Optional
from dataclasses import dataclass
from config import Config
import json
import os

@dataclass
class PresetData:
    """增强的预设数据结构"""
    name: str
    joints: List[float]
    description: str = ""
    category: str = "默认"
    tcp_pose: Optional[List[float]] = None
    speed: float = Config.DEFAULT_JOINT_SPEED
    acceleration: float = Config.DEFAULT_JOINT_ACCEL
    blend_radius: float = 0.0
    locked: bool = False
    tags: List[str] = None
    safety_validated: bool = False
    
class PresetManager:
    """预设管理器 - 与现有系统兼容"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.presets: Dict[str, PresetData] = {}
            self.categories = ["系统", "工作区", "任务", "用户"]
            self._import_config_presets()
            self.initialized = True
    
    def _import_config_presets(self):
        """从Config导入现有预设（保持兼容性）"""
        for name, data in Config.PRESET_POSITIONS.items():
            self.presets[name] = PresetData(
                name=name,
                joints=data['joints'],
                description=data['description'],
                category="系统",
                locked=True,
                safety_validated=True
            )
    
    def get_preset(self, name: str) -> Optional[PresetData]:
        """获取预设（新接口）"""
        return self.presets.get(name)
    
    def get_preset_joints(self, name: str) -> Optional[List[float]]:
        """获取预设关节位置（兼容旧接口）"""
        preset = self.presets.get(name)
        return preset.joints if preset else None
    
    def add_preset(self, preset: PresetData) -> bool:
        """添加预设"""
        if preset.name in self.presets and self.presets[preset.name].locked:
            return False
        
        self.presets[preset.name] = preset
        self._sync_to_config(preset)  # 保持与Config同步
        return True
    
    def _sync_to_config(self, preset: PresetData):
        """同步到Config（保持向后兼容）"""
        Config.PRESET_POSITIONS[preset.name] = {
            'joints': preset.joints,
            'description': preset.description
        }
    
    def remove_preset(self, name: str) -> bool:
        """删除预设"""
        if name in self.presets:
            if self.presets[name].locked:
                return False
            del self.presets[name]
            # 同时从Config中删除
            if name in Config.PRESET_POSITIONS:
                del Config.PRESET_POSITIONS[name]
            return True
        return False
    
    def export_presets(self, filepath: str, category: str = None):
        """导出预设"""
        export_data = {}
        for name, preset in self.presets.items():
            if category is None or preset.category == category:
                export_data[name] = {
                    'joints': preset.joints,
                    'description': preset.description,
                    'category': preset.category,
                    'speed': preset.speed,
                    'acceleration': preset.acceleration,
                    'tags': preset.tags or []
                }
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)
    
    def import_presets(self, filepath: str):
        """导入预设"""
        with open(filepath, 'r') as f:
            import_data = json.load(f)
        
        for name, data in import_data.items():
            preset = PresetData(
                name=name,
                joints=data['joints'],
                description=data.get('description', ''),
                category=data.get('category', '用户'),
                speed=data.get('speed', Config.DEFAULT_JOINT_SPEED),
                acceleration=data.get('acceleration', Config.DEFAULT_JOINT_ACCEL),
                tags=data.get('tags', [])
            )
            self.add_preset(preset)
```

## 结论

### ✅ **创建独立的 PresetManager 是可行的**

**原因：**
1. 现有架构已经有良好的分离性
2. 接口简单，易于替换
3. 可以保持完全的向后兼容性

### 建议采用**方案A（完全替换）**，因为：
1. 更清晰的架构
2. 更容易添加新功能
3. 通过兼容层保持向后兼容

### 关键成功因素：
1. **保持接口兼容**：确保RobotController和UI的调用不需要大改
2. **数据迁移**：自动导入Config中的预设
3. **渐进式部署**：先创建PresetManager，逐步迁移功能
4. **保留回退机制**：在过渡期保留Config的预设功能

创建独立的PresetManager不会造成冲突，反而会让系统架构更清晰，功能更强大。
