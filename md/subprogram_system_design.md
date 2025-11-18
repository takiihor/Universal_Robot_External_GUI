# 子程序系统设计方案 - Sequential Controller 升级

## 一、问题分析

### 1.1 当前架构限制

```
当前模式：线性列表 + 全局循环
┌─────────────────────────┐
│ 1. 移动到位置A          │
│ 2. 打开夹爪             │
│ 3. 移动到位置B          │
│ 4. 关闭夹爪             │
│ 5. REPEAT_START (3次)    │
│ 6.   移动到螺丝位置1    │
│ 7.   下压               │
│ 8.   旋转               │
│ 9. REPEAT_END           │
│ 10. 移动到位置C         │
└─────────────────────────┘
```

**问题：**
- ❌ 重复动作序列导致列表冗长
- ❌ 无法复用常见操作模式
- ❌ 难以维护和修改
- ❌ 嵌套循环不直观
- ❌ 缺乏模块化思维

### 1.2 理想架构

```
升级模式：层级化程序 + 子程序库
┌─────────────────────────┐     ┌──────────────────┐
│ 主程序                  │     │ 子程序库         │
├─────────────────────────┤     ├──────────────────┤
│ 1. 取料()              │ --> │ • 取料           │
│ 2. LOOP 3次 {          │     │ • 锁螺丝         │
│ 3.   锁螺丝(位置[i])   │ --> │ • 品质检查       │
│ 4. }                   │     │ • 放置成品       │
│ 5. 品质检查()          │     │ • ...            │
│ 6. 放置成品()          │     └──────────────────┘
└─────────────────────────┘
```

## 二、子程序系统架构设计

### 2.1 核心概念

```python
@dataclass
class SubProgram:
    """子程序定义"""
    id: str                          # 唯一标识
    name: str                        # 名称
    description: str                 # 描述
    icon: str                       # 图标
    category: str                   # 分类
    parameters: List[Parameter]     # 参数定义
    actions: List[Action]           # 动作序列
    version: str                    # 版本
    created_date: str              # 创建时间
    modified_date: str             # 修改时间
    usage_count: int               # 使用次数
    tags: List[str]                # 标签

@dataclass
class Parameter:
    """子程序参数"""
    name: str                       # 参数名
    type: str                       # 类型: number, string, position, speed
    default_value: Any             # 默认值
    required: bool                 # 是否必需
    description: str               # 描述
    constraints: Dict              # 约束条件
```

### 2.2 系统组件

```
┌────────────────────────────────────────────────┐
│                  主界面                         │
├────────────┬────────────┬──────────────────────┤
│            │            │                      │
│ 子程序库   │ 主流程编辑 │ 子程序编辑器        │
│            │            │                      │
│ [取料]     │ 1.取料()   │ 子程序: 锁螺丝      │
│ [锁螺丝]   │ 2.Loop 3   │ 1. 移动到位置      │
│ [检查]     │   锁螺丝() │ 2. 下压            │
│ [+新建]    │ 3.检查()   │ 3. 旋转            │
│            │            │                      │
└────────────┴────────────┴──────────────────────┘
```

## 三、详细功能设计

### 3.1 子程序管理器

```python
class SubProgramManager(QObject):
    """子程序管理器"""
    
    subprogram_added = pyqtSignal(SubProgram)
    subprogram_updated = pyqtSignal(SubProgram)
    subprogram_deleted = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.subprograms = {}  # id -> SubProgram
        self.load_subprograms()
    
    def create_subprogram(self, name: str, actions: List[Action]) -> SubProgram:
        """创建新子程序"""
        subprogram = SubProgram(
            id=self.generate_id(),
            name=name,
            actions=actions,
            parameters=self.extract_parameters(actions),
            created_date=datetime.now(),
            usage_count=0
        )
        
        self.subprograms[subprogram.id] = subprogram
        self.save_subprogram(subprogram)
        self.subprogram_added.emit(subprogram)
        return subprogram
    
    def extract_parameters(self, actions: List[Action]) -> List[Parameter]:
        """从动作序列中提取可参数化的值"""
        parameters = []
        
        for action in actions:
            # 识别可参数化的值
            if action.type == ActionType.MOVE_TO_POSITION:
                # 位置可以参数化
                param = Parameter(
                    name=f"position_{action.id}",
                    type="position",
                    default_value=action.parameters.get("position"),
                    description=f"动作{action.id}的目标位置"
                )
                parameters.append(param)
                
            elif action.type == ActionType.WAIT:
                # 等待时间可以参数化
                param = Parameter(
                    name=f"wait_time_{action.id}",
                    type="number",
                    default_value=action.parameters.get("duration"),
                    description=f"等待时间(秒)"
                )
                parameters.append(param)
        
        return parameters
    
    def instantiate_subprogram(self, subprogram_id: str, 
                              parameter_values: Dict = None) -> List[Action]:
        """实例化子程序，应用参数值"""
        subprogram = self.subprograms[subprogram_id]
        instantiated_actions = []
        
        for action in subprogram.actions:
            new_action = copy.deepcopy(action)
            
            # 应用参数值
            if parameter_values:
                for param_name, param_value in parameter_values.items():
                    # 更新对应的动作参数
                    if param_name in new_action.parameters:
                        new_action.parameters[param_name] = param_value
            
            instantiated_actions.append(new_action)
        
        return instantiated_actions
```

### 3.2 子程序库界面

```python
class SubProgramLibrary(QWidget):
    """子程序库面板"""
    
    subprogram_selected = pyqtSignal(SubProgram)
    
    def __init__(self, manager: SubProgramManager):
        super().__init__()
        self.manager = manager
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 搜索栏
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 搜索子程序...")
        search_layout.addWidget(self.search_input)
        
        # 新建按钮
        self.new_btn = QPushButton("➕ 新建子程序")
        self.new_btn.clicked.connect(self.create_new_subprogram)
        search_layout.addWidget(self.new_btn)
        
        layout.addLayout(search_layout)
        
        # 分类标签页
        self.category_tabs = QTabWidget()
        self.category_tabs.addTab(self.create_category_view("常用"), "⭐ 常用")
        self.category_tabs.addTab(self.create_category_view("取放"), "🤏 取放")
        self.category_tabs.addTab(self.create_category_view("装配"), "🔧 装配")
        self.category_tabs.addTab(self.create_category_view("检测"), "🔍 检测")
        self.category_tabs.addTab(self.create_category_view("全部"), "📚 全部")
        
        layout.addWidget(self.category_tabs)
    
    def create_category_view(self, category: str) -> QWidget:
        """创建分类视图"""
        scroll = QScrollArea()
        content = QWidget()
        grid = QGridLayout(content)
        
        # 子程序卡片
        subprograms = self.manager.get_by_category(category)
        for i, sp in enumerate(subprograms):
            card = self.create_subprogram_card(sp)
            grid.addWidget(card, i // 2, i % 2)
        
        scroll.setWidget(content)
        return scroll
    
    def create_subprogram_card(self, subprogram: SubProgram) -> QWidget:
        """创建子程序卡片"""
        card = QFrame()
        card.setFrameStyle(QFrame.StyledPanel)
        card.setCursor(Qt.PointingHandCursor)
        
        layout = QVBoxLayout(card)
        
        # 标题行
        title_layout = QHBoxLayout()
        
        # 图标
        icon = QLabel(subprogram.icon or "📦")
        icon.setStyleSheet("font-size: 24px;")
        title_layout.addWidget(icon)
        
        # 名称和使用次数
        info_layout = QVBoxLayout()
        name = QLabel(subprogram.name)
        name.setStyleSheet("font-weight: bold; font-size: 13px;")
        info_layout.addWidget(name)
        
        usage = QLabel(f"使用 {subprogram.usage_count} 次")
        usage.setStyleSheet("color: #888; font-size: 10px;")
        info_layout.addWidget(usage)
        
        title_layout.addLayout(info_layout)
        title_layout.addStretch()
        
        # 编辑按钮
        edit_btn = QPushButton("✏️")
        edit_btn.setFixedSize(24, 24)
        edit_btn.clicked.connect(lambda: self.edit_subprogram(subprogram))
        title_layout.addWidget(edit_btn)
        
        layout.addLayout(title_layout)
        
        # 描述
        desc = QLabel(subprogram.description or "无描述")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(desc)
        
        # 步骤数和参数信息
        info = QLabel(f"📊 {len(subprogram.actions)} 步骤 | "
                     f"⚙️ {len(subprogram.parameters)} 参数")
        info.setStyleSheet("color: #999; font-size: 10px; margin-top: 5px;")
        layout.addWidget(info)
        
        # 点击事件
        card.mousePressEvent = lambda e: self.subprogram_selected.emit(subprogram)
        
        # 样式
        card.setStyleSheet("""
            QFrame {
                background: white;
                border: 2px solid #E0E0E0;
                border-radius: 8px;
                padding: 10px;
                margin: 5px;
            }
            QFrame:hover {
                border-color: #2196F3;
                background: #F5F9FF;
            }
        """)
        
        return card
```

### 3.3 调用子程序动作

```python
class CallSubProgramAction(Action):
    """调用子程序动作"""
    
    def __init__(self, subprogram_id: str, 
                 parameter_values: Dict = None,
                 loop_count: int = 1):
        super().__init__(
            action_type=ActionType.CALL_SUBPROGRAM,
            parameters={
                "subprogram_id": subprogram_id,
                "parameter_values": parameter_values or {},
                "loop_count": loop_count,
                "error_handling": "stop"  # stop, skip, retry
            }
        )
    
    def get_display_text(self) -> str:
        """获取显示文本"""
        sp = SubProgramManager.get_instance().get(self.subprogram_id)
        if sp:
            loop_text = f" × {self.loop_count}" if self.loop_count > 1 else ""
            return f"📦 {sp.name}(){loop_text}"
        return "📦 未知子程序"
```

### 3.4 子程序编辑器

```python
class SubProgramEditor(QWidget):
    """子程序编辑器 - 独立的编辑界面"""
    
    def __init__(self, subprogram: SubProgram = None):
        super().__init__()
        self.subprogram = subprogram or SubProgram()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 顶部工具栏
        toolbar = QToolBar()
        
        # 子程序信息
        info_widget = QWidget()
        info_layout = QHBoxLayout(info_widget)
        
        # 名称
        info_layout.addWidget(QLabel("名称:"))
        self.name_edit = QLineEdit(self.subprogram.name)
        self.name_edit.setPlaceholderText("例如: 锁螺丝")
        info_layout.addWidget(self.name_edit)
        
        # 图标选择
        self.icon_btn = QPushButton(self.subprogram.icon or "📦")
        self.icon_btn.clicked.connect(self.select_icon)
        info_layout.addWidget(self.icon_btn)
        
        # 分类
        info_layout.addWidget(QLabel("分类:"))
        self.category_combo = QComboBox()
        self.category_combo.addItems(["取放", "装配", "检测", "其他"])
        info_layout.addWidget(self.category_combo)
        
        toolbar.addWidget(info_widget)
        layout.addWidget(toolbar)
        
        # 主编辑区 - 分割视图
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：动作序列编辑（复用现有的序列编辑器）
        self.sequence_editor = SequenceEditor()
        self.sequence_editor.load_actions(self.subprogram.actions)
        splitter.addWidget(self.sequence_editor)
        
        # 右侧：参数配置面板
        self.parameter_panel = SubProgramParameterPanel(self.subprogram)
        splitter.addWidget(self.parameter_panel)
        
        splitter.setSizes([600, 300])
        layout.addWidget(splitter)
        
        # 底部按钮
        button_layout = QHBoxLayout()
        
        # 测试运行
        self.test_btn = QPushButton("🧪 测试运行")
        self.test_btn.clicked.connect(self.test_subprogram)
        button_layout.addWidget(self.test_btn)
        
        button_layout.addStretch()
        
        # 保存按钮
        self.save_btn = QPushButton("💾 保存子程序")
        self.save_btn.clicked.connect(self.save_subprogram)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background: #4CAF50;
                color: white;
                padding: 8px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
        """)
        button_layout.addWidget(self.save_btn)
        
        # 取消按钮
        self.cancel_btn = QPushButton("取消")
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
```

### 3.5 参数配置面板

```python
class SubProgramParameterPanel(QWidget):
    """子程序参数配置面板"""
    
    def __init__(self, subprogram: SubProgram):
        super().__init__()
        self.subprogram = subprogram
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 标题
        title = QLabel("⚙️ 参数配置")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)
        
        # 说明
        info = QLabel("将动作中的固定值转换为可配置参数，"
                     "让子程序更灵活")
        info.setWordWrap(True)
        info.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(info)
        
        # 参数列表
        self.parameter_list = QListWidget()
        layout.addWidget(self.parameter_list)
        
        # 添加参数按钮
        add_btn = QPushButton("➕ 添加参数")
        add_btn.clicked.connect(self.add_parameter)
        layout.addWidget(add_btn)
        
        # 自动识别按钮
        auto_btn = QPushButton("🔍 自动识别可参数化的值")
        auto_btn.clicked.connect(self.auto_detect_parameters)
        layout.addWidget(auto_btn)
        
        # 加载现有参数
        self.load_parameters()
    
    def add_parameter(self):
        """添加新参数"""
        dialog = ParameterEditDialog()
        if dialog.exec_():
            param = dialog.get_parameter()
            self.subprogram.parameters.append(param)
            self.refresh_list()
    
    def auto_detect_parameters(self):
        """自动检测可参数化的值"""
        suggestions = []
        
        for i, action in enumerate(self.subprogram.actions):
            if action.type == ActionType.MOVE_TO_POSITION:
                suggestions.append({
                    "name": f"position_{i+1}",
                    "type": "position",
                    "description": f"步骤{i+1}的目标位置",
                    "action_index": i,
                    "parameter_key": "position"
                })
                
                suggestions.append({
                    "name": f"speed_{i+1}",
                    "type": "speed",
                    "description": f"步骤{i+1}的移动速度",
                    "action_index": i,
                    "parameter_key": "speed"
                })
            
            elif action.type == ActionType.WAIT:
                suggestions.append({
                    "name": f"wait_time_{i+1}",
                    "type": "number",
                    "description": f"步骤{i+1}的等待时间",
                    "action_index": i,
                    "parameter_key": "duration"
                })
        
        # 显示建议对话框
        dialog = ParameterSuggestionDialog(suggestions)
        if dialog.exec_():
            selected = dialog.get_selected_suggestions()
            for sug in selected:
                param = Parameter(
                    name=sug["name"],
                    type=sug["type"],
                    description=sug["description"],
                    action_binding={
                        "action_index": sug["action_index"],
                        "parameter_key": sug["parameter_key"]
                    }
                )
                self.subprogram.parameters.append(param)
            self.refresh_list()
```

## 四、执行引擎升级

### 4.1 层级执行器

```python
class HierarchicalExecutor(QThread):
    """层级化执行器 - 支持子程序调用"""
    
    execution_started = pyqtSignal()
    execution_step = pyqtSignal(str, int, int)  # context, current, total
    execution_completed = pyqtSignal()
    execution_error = pyqtSignal(str)
    
    def __init__(self, controller, subprogram_manager):
        super().__init__()
        self.controller = controller
        self.subprogram_manager = subprogram_manager
        self.call_stack = []  # 调用栈
        self.current_context = "main"
    
    def execute_action(self, action: Action):
        """执行单个动作"""
        if action.type == ActionType.CALL_SUBPROGRAM:
            return self.execute_subprogram(action)
        else:
            # 执行普通动作
            return self.controller.execute_single_action(action)
    
    def execute_subprogram(self, call_action: Action):
        """执行子程序调用"""
        subprogram_id = call_action.parameters["subprogram_id"]
        parameter_values = call_action.parameters.get("parameter_values", {})
        loop_count = call_action.parameters.get("loop_count", 1)
        error_handling = call_action.parameters.get("error_handling", "stop")
        
        # 获取子程序
        subprogram = self.subprogram_manager.get(subprogram_id)
        if not subprogram:
            self.execution_error.emit(f"子程序不存在: {subprogram_id}")
            return False
        
        # 压入调用栈
        self.call_stack.append({
            "name": subprogram.name,
            "context": f"subprogram_{subprogram_id}",
            "return_point": self.current_context
        })
        
        self.current_context = f"subprogram_{subprogram_id}"
        
        # 执行循环
        for loop_idx in range(loop_count):
            if loop_count > 1:
                self.execution_step.emit(
                    f"执行 {subprogram.name} (第{loop_idx+1}/{loop_count}次)",
                    loop_idx + 1, loop_count
                )
            
            # 实例化子程序动作
            actions = self.subprogram_manager.instantiate_subprogram(
                subprogram_id, parameter_values
            )
            
            # 执行子程序动作序列
            for i, action in enumerate(actions):
                # 发送执行状态
                context_text = f"{subprogram.name} > {action.get_display_text()}"
                self.execution_step.emit(context_text, i+1, len(actions))
                
                # 执行动作
                success = self.execute_action(action)
                
                if not success:
                    # 错误处理
                    if error_handling == "stop":
                        self.execution_error.emit(
                            f"子程序 {subprogram.name} 执行失败于步骤 {i+1}"
                        )
                        return False
                    elif error_handling == "skip":
                        break  # 跳过剩余步骤
                    elif error_handling == "retry":
                        # 重试逻辑
                        retry_count = 3
                        for retry in range(retry_count):
                            if self.execute_action(action):
                                break
                        else:
                            return False
        
        # 弹出调用栈
        self.call_stack.pop()
        if self.call_stack:
            self.current_context = self.call_stack[-1]["context"]
        else:
            self.current_context = "main"
        
        return True
```

### 4.2 执行历史增强

```python
class EnhancedExecutionHistory(QWidget):
    """增强的执行历史 - 显示层级关系"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 使用树形视图显示层级
        self.history_tree = QTreeWidget()
        self.history_tree.setHeaderLabels(
            ["时间", "层级", "动作", "状态", "耗时"]
        )
        
        layout.addWidget(self.history_tree)
    
    def add_execution_record(self, timestamp, context, action, 
                           status, duration):
        """添加执行记录"""
        # 解析上下文层级
        context_parts = context.split(" > ")
        
        if len(context_parts) == 1:
            # 主程序动作
            item = QTreeWidgetItem(self.history_tree)
            item.setText(0, timestamp)
            item.setText(1, "主程序")
            item.setText(2, action)
            item.setText(3, status)
            item.setText(4, f"{duration:.2f}s")
            
            # 状态颜色
            if status == "成功":
                item.setBackground(3, QColor("#E8F5E9"))
            elif status == "失败":
                item.setBackground(3, QColor("#FFEBEE"))
                
        else:
            # 子程序动作
            parent = self.find_or_create_parent(context_parts[0])
            item = QTreeWidgetItem(parent)
            item.setText(0, timestamp)
            item.setText(1, "  └─ 子步骤")
            item.setText(2, action)
            item.setText(3, status)
            item.setText(4, f"{duration:.2f}s")
    
    def find_or_create_parent(self, subprogram_name):
        """查找或创建父节点"""
        # 查找最近的子程序节点
        for i in range(self.history_tree.topLevelItemCount() - 1, -1, -1):
            item = self.history_tree.topLevelItem(i)
            if subprogram_name in item.text(2):
                return item
        
        # 创建新的子程序节点
        item = QTreeWidgetItem(self.history_tree)
        item.setText(1, "📦 子程序")
        item.setText(2, subprogram_name)
        return item
```

## 五、UI集成方案

### 5.1 主界面布局调整

```python
class EnhancedSequentialController(QWidget):
    """增强的顺序控制器主界面"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 顶部标签页切换
        self.mode_tabs = QTabWidget()
        self.mode_tabs.setTabPosition(QTabWidget.North)
        
        # 主程序编辑页
        self.main_program_page = self.create_main_program_page()
        self.mode_tabs.addTab(self.main_program_page, "📝 主程序")
        
        # 子程序库页
        self.subprogram_library_page = self.create_subprogram_library_page()
        self.mode_tabs.addTab(self.subprogram_library_page, "📦 子程序库")
        
        # 执行监控页
        self.execution_monitor_page = self.create_execution_monitor_page()
        self.mode_tabs.addTab(self.execution_monitor_page, "📊 执行监控")
        
        layout.addWidget(self.mode_tabs)
    
    def create_main_program_page(self):
        """创建主程序编辑页"""
        page = QWidget()
        layout = QHBoxLayout(page)
        
        # 左侧：动作库（包含子程序）
        action_lib = QWidget()
        lib_layout = QVBoxLayout(action_lib)
        
        # 切换按钮：基础动作 / 子程序
        toggle_group = QButtonGroup()
        toggle_layout = QHBoxLayout()
        
        basic_btn = QPushButton("🔧 基础动作")
        basic_btn.setCheckable(True)
        basic_btn.setChecked(True)
        toggle_group.addButton(basic_btn, 0)
        toggle_layout.addWidget(basic_btn)
        
        subprog_btn = QPushButton("📦 子程序")
        subprog_btn.setCheckable(True)
        toggle_group.addButton(subprog_btn, 1)
        toggle_layout.addWidget(subprog_btn)
        
        lib_layout.addLayout(toggle_layout)
        
        # 堆叠部件：基础动作库 / 子程序选择器
        self.lib_stack = QStackedWidget()
        self.lib_stack.addWidget(self.create_basic_action_library())
        self.lib_stack.addWidget(self.create_subprogram_selector())
        
        toggle_group.buttonClicked[int].connect(self.lib_stack.setCurrentIndex)
        
        lib_layout.addWidget(self.lib_stack)
        layout.addWidget(action_lib, 2)
        
        # 中间：主程序序列
        self.main_sequence_editor = MainSequenceEditor()
        layout.addWidget(self.main_sequence_editor, 3)
        
        # 右侧：控制面板
        self.control_panel = ExecutionControlPanel()
        layout.addWidget(self.control_panel, 2)
        
        return page
```

### 5.2 子程序选择器

```python
class SubProgramSelector(QWidget):
    """子程序选择器 - 用于添加到主程序"""
    
    subprogram_selected = pyqtSignal(SubProgram)
    
    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 搜索
        search = QLineEdit()
        search.setPlaceholderText("🔍 搜索子程序...")
        layout.addWidget(search)
        
        # 子程序列表
        self.list_widget = QListWidget()
        
        for sp in self.manager.get_all():
            item = QListWidgetItem()
            widget = self.create_mini_card(sp)
            item.setSizeHint(widget.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)
        
        layout.addWidget(self.list_widget)
        
        # 快速创建按钮
        create_btn = QPushButton("➕ 从当前序列创建子程序")
        create_btn.clicked.connect(self.create_from_selection)
        layout.addWidget(create_btn)
    
    def create_mini_card(self, subprogram):
        """创建迷你卡片"""
        card = QWidget()
        layout = QHBoxLayout(card)
        
        # 图标和名称
        icon = QLabel(subprogram.icon or "📦")
        layout.addWidget(icon)
        
        info_layout = QVBoxLayout()
        name = QLabel(subprogram.name)
        name.setStyleSheet("font-weight: bold;")
        info_layout.addWidget(name)
        
        stats = QLabel(f"{len(subprogram.actions)} 步骤")
        stats.setStyleSheet("color: #888; font-size: 10px;")
        info_layout.addWidget(stats)
        
        layout.addLayout(info_layout)
        layout.addStretch()
        
        # 添加按钮
        add_btn = QPushButton("添加")
        add_btn.clicked.connect(
            lambda: self.add_to_main_sequence(subprogram)
        )
        layout.addWidget(add_btn)
        
        card.setStyleSheet("""
            QWidget {
                background: white;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 5px;
            }
            QWidget:hover {
                background: #F5F9FF;
                border-color: #2196F3;
            }
        """)
        
        return card
    
    def add_to_main_sequence(self, subprogram):
        """添加子程序调用到主序列"""
        # 显示参数配置对话框
        dialog = SubProgramCallDialog(subprogram)
        if dialog.exec_():
            params = dialog.get_parameters()
            loop_count = dialog.get_loop_count()
            
            # 创建调用动作
            call_action = CallSubProgramAction(
                subprogram.id,
                params,
                loop_count
            )
            
            # 添加到主序列
            self.parent().main_sequence_editor.add_action(call_action)
```

## 六、实施路线图

### 第一阶段：基础架构（1周）
1. ✅ 实现 SubProgram 数据模型
2. ✅ 实现 SubProgramManager
3. ✅ 添加 CALL_SUBPROGRAM 动作类型
4. ✅ 基础文件存储（JSON格式）

### 第二阶段：UI组件（2周）
1. 🔄 开发子程序库界面
2. 🔄 实现子程序编辑器
3. 🔄 创建参数配置面板
4. 🔄 集成到主界面

### 第三阶段：执行引擎（1周）
1. 📋 升级执行器支持子程序调用
2. 📋 实现调用栈管理
3. 📋 添加错误处理策略
4. 📋 增强执行历史显示

### 第四阶段：高级功能（2周）
1. 💡 参数化子程序
2. 💡 嵌套子程序调用
3. 💡 条件执行
4. 💡 子程序版本管理

## 七、关键优势

### 7.1 对非工程师用户
- ✅ **直观理解**：子程序就像"功能积木"
- ✅ **快速组装**：拖拽预制模块构建复杂流程
- ✅ **减少重复**：一次定义，多处使用
- ✅ **易于维护**：修改子程序自动更新所有引用

### 7.2 对系统能力
- ✅ **模块化**：清晰的程序结构
- ✅ **可复用**：建立企业动作库
- ✅ **可扩展**：轻松添加新功能
- ✅ **可维护**：独立测试和调试

### 7.3 典型应用场景

```
示例：PCB组装线

主程序:
1. 初始化设备
2. LOOP 10块板 {
   3. 取板()                 -> 子程序：标准取放动作
   4. LOOP 5个元件 {
      5. 贴装元件(位置[i])    -> 子程序：精确贴装流程
   }
   6. 质检()                 -> 子程序：视觉检测流程
   7. 放置成品()             -> 子程序：分类存放
}
8. 生成报告()

每个子程序都可独立维护、测试和优化
```

## 八、总结

通过引入子程序系统，Sequential Controller将从"线性列表工具"进化为"模块化编程平台"：

1. **保持简单性**：对用户而言，子程序只是"可重用的动作组"
2. **提升能力**：支持复杂的嵌套和循环逻辑
3. **增强维护性**：修改一处，处处生效
4. **促进协作**：团队可共享子程序库

这是一个**渐进式升级**方案，可以在不破坏现有功能的基础上逐步实施，让非工程师用户也能构建复杂的自动化任务。

---
*设计版本：1.0*  
*创建日期：2024*