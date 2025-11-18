# 流程图可视化系统设计方案 - Sequential Controller

## 一、设计理念

### 1.1 核心价值
将**线性的动作列表**转换为**直观的流程图**，让非工程师用户能够：
- 🎯 **一目了然**：快速理解整体任务流程
- 🔄 **可视化逻辑**：清晰展示循环、分支、子程序调用
- 📊 **实时状态**：执行时动态显示进度和状态
- 🎨 **拖拽编辑**：通过流程图直接编辑任务序列

### 1.2 设计原则
- **双向同步**：列表视图 ⟷ 流程图视图实时同步
- **渐进增强**：从简单线性流程到复杂嵌套逻辑
- **视觉层次**：通过颜色、大小、形状区分不同类型节点
- **交互友好**：支持缩放、平移、自动布局

## 二、流程图架构设计

### 2.1 节点类型定义

```python
class FlowNodeType(Enum):
    """流程图节点类型"""
    # 基础节点
    START = "start"                    # 开始节点（圆形）
    END = "end"                        # 结束节点（圆形）
    ACTION = "action"                  # 动作节点（矩形）
    
    # 控制流节点
    CONDITION = "condition"            # 条件判断（菱形）
    LOOP_START = "loop_start"          # 循环开始（六边形）
    LOOP_END = "loop_end"              # 循环结束（六边形）
    
    # 特殊节点
    SUBPROGRAM = "subprogram"          # 子程序调用（圆角矩形）
    PARALLEL_START = "parallel_start"  # 并行开始（双线矩形）
    PARALLEL_END = "parallel_end"      # 并行结束（双线矩形）
    
    # 交互节点
    USER_INPUT = "user_input"          # 用户输入（平行四边形）
    WAIT = "wait"                      # 等待/延时（椭圆形）

class FlowNode:
    """流程图节点"""
    def __init__(self, node_id: str, node_type: FlowNodeType, 
                 action: Action = None):
        self.id = node_id
        self.type = node_type
        self.action = action  # 关联的动作
        self.position = QPointF(0, 0)  # 节点位置
        self.size = QSizeF(120, 60)    # 节点大小
        self.color = self.get_color_for_type()
        self.label = self.get_label()
        self.inputs = []   # 输入连接点
        self.outputs = []  # 输出连接点
        self.metadata = {} # 额外信息
        
    def get_color_for_type(self) -> QColor:
        """根据节点类型获取颜色"""
        color_map = {
            FlowNodeType.START: QColor("#4CAF50"),      # 绿色
            FlowNodeType.END: QColor("#F44336"),        # 红色
            FlowNodeType.ACTION: QColor("#2196F3"),     # 蓝色
            FlowNodeType.CONDITION: QColor("#FF9800"),  # 橙色
            FlowNodeType.LOOP_START: QColor("#9C27B0"), # 紫色
            FlowNodeType.SUBPROGRAM: QColor("#00BCD4"), # 青色
            FlowNodeType.WAIT: QColor("#FFC107"),       # 黄色
        }
        return color_map.get(self.type, QColor("#607D8B"))
```

### 2.2 连接线定义

```python
class FlowEdge:
    """流程图连接线"""
    def __init__(self, source_node: str, target_node: str, 
                 edge_type: str = "normal"):
        self.source = source_node
        self.target = target_node
        self.type = edge_type  # normal, true, false, loop_back
        self.label = ""        # 连接线标签（如：条件）
        self.style = self.get_style_for_type()
        self.control_points = []  # 贝塞尔曲线控制点
        
    def get_style_for_type(self) -> dict:
        """根据类型获取样式"""
        if self.type == "true":
            return {"color": "#4CAF50", "style": "solid", "label": "是"}
        elif self.type == "false":
            return {"color": "#F44336", "style": "dashed", "label": "否"}
        elif self.type == "loop_back":
            return {"color": "#9C27B0", "style": "solid", "arrow": "curved"}
        else:
            return {"color": "#333333", "style": "solid", "arrow": "straight"}
```

## 三、流程图生成器

### 3.1 序列转流程图转换器

```python
class SequenceToFlowChart:
    """将动作序列转换为流程图"""
    
    def __init__(self):
        self.nodes = {}
        self.edges = []
        self.layout_engine = AutoLayoutEngine()
        
    def convert(self, action_sequence: List[Action]) -> FlowChart:
        """转换主函数"""
        # 1. 创建开始节点
        start_node = FlowNode("start", FlowNodeType.START)
        self.nodes["start"] = start_node
        
        # 2. 处理动作序列
        prev_node_id = "start"
        node_stack = []  # 用于处理嵌套结构
        
        for i, action in enumerate(action_sequence):
            node_id = f"node_{i}"
            
            # 根据动作类型创建对应节点
            if action.type == ActionType.REPEAT_START:
                # 循环开始
                loop_node = FlowNode(node_id, FlowNodeType.LOOP_START, action)
                loop_node.label = f"循环 {action.parameters.get('count', 1)} 次"
                self.nodes[node_id] = loop_node
                
                # 连接前一个节点
                self.edges.append(FlowEdge(prev_node_id, node_id))
                
                # 压入栈
                node_stack.append({
                    "type": "loop",
                    "start_id": node_id,
                    "first_child": None
                })
                prev_node_id = node_id
                
            elif action.type == ActionType.REPEAT_END:
                # 循环结束
                if node_stack and node_stack[-1]["type"] == "loop":
                    loop_info = node_stack.pop()
                    loop_end = FlowNode(node_id, FlowNodeType.LOOP_END)
                    self.nodes[node_id] = loop_end
                    
                    # 连接到循环结束
                    self.edges.append(FlowEdge(prev_node_id, node_id))
                    
                    # 添加循环回边
                    self.edges.append(FlowEdge(
                        node_id, 
                        loop_info["first_child"] or loop_info["start_id"],
                        "loop_back"
                    ))
                    prev_node_id = node_id
                    
            elif action.type == ActionType.CALL_SUBPROGRAM:
                # 子程序调用
                sub_node = FlowNode(node_id, FlowNodeType.SUBPROGRAM, action)
                sub_node.label = action.parameters.get("name", "子程序")
                self.nodes[node_id] = sub_node
                
                self.edges.append(FlowEdge(prev_node_id, node_id))
                prev_node_id = node_id
                
            else:
                # 普通动作节点
                action_node = FlowNode(node_id, FlowNodeType.ACTION, action)
                action_node.label = ACTION_METADATA.get(
                    action.type, {}
                ).get("name", "未知动作")
                self.nodes[node_id] = action_node
                
                self.edges.append(FlowEdge(prev_node_id, node_id))
                
                # 如果在循环中，记录第一个子节点
                if node_stack and node_stack[-1]["first_child"] is None:
                    node_stack[-1]["first_child"] = node_id
                    
                prev_node_id = node_id
        
        # 3. 创建结束节点
        end_node = FlowNode("end", FlowNodeType.END)
        self.nodes["end"] = end_node
        self.edges.append(FlowEdge(prev_node_id, "end"))
        
        # 4. 自动布局
        self.layout_engine.layout(self.nodes, self.edges)
        
        return FlowChart(self.nodes, self.edges)
```

### 3.2 自动布局引擎

```python
class AutoLayoutEngine:
    """自动布局引擎 - 使用分层布局算法"""
    
    def __init__(self):
        self.layer_height = 100  # 层间距
        self.node_spacing = 150  # 节点间距
        self.margin = 50         # 边距
        
    def layout(self, nodes: dict, edges: list):
        """执行自动布局"""
        # 1. 拓扑排序，分层
        layers = self.topological_layers(nodes, edges)
        
        # 2. 计算每层位置
        y = self.margin
        for layer_nodes in layers:
            x = self.margin
            layer_width = len(layer_nodes) * self.node_spacing
            
            # 居中对齐
            start_x = (self.get_canvas_width() - layer_width) / 2
            
            for node_id in layer_nodes:
                node = nodes[node_id]
                node.position = QPointF(start_x + x, y)
                x += self.node_spacing
                
            y += self.layer_height
        
        # 3. 优化连接线路径
        self.optimize_edges(nodes, edges)
        
    def topological_layers(self, nodes, edges):
        """拓扑排序分层"""
        # 构建邻接表
        graph = {node_id: [] for node_id in nodes}
        in_degree = {node_id: 0 for node_id in nodes}
        
        for edge in edges:
            if edge.type != "loop_back":  # 忽略循环回边
                graph[edge.source].append(edge.target)
                in_degree[edge.target] += 1
        
        # BFS分层
        layers = []
        current_layer = [n for n in in_degree if in_degree[n] == 0]
        
        while current_layer:
            layers.append(current_layer[:])
            next_layer = []
            
            for node in current_layer:
                for neighbor in graph[node]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        next_layer.append(neighbor)
                        
            current_layer = next_layer
            
        return layers
    
    def optimize_edges(self, nodes, edges):
        """优化连接线路径，避免交叉"""
        for edge in edges:
            if edge.type == "loop_back":
                # 循环回边使用贝塞尔曲线
                self.create_bezier_path(edge, nodes)
            else:
                # 普通连接使用直线或折线
                self.create_orthogonal_path(edge, nodes)
```

## 四、流程图可视化组件

### 4.1 流程图画布

```python
class FlowChartCanvas(QGraphicsView):
    """流程图画布 - 支持缩放、平移、编辑"""
    
    node_clicked = pyqtSignal(FlowNode)
    node_double_clicked = pyqtSignal(FlowNode)
    connection_created = pyqtSignal(str, str)
    
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        
        # 设置渲染选项
        self.setRenderHint(QPainter.Antialiasing)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        
        # 节点和连接线图形项
        self.node_items = {}
        self.edge_items = []
        
        # 交互状态
        self.zoom_level = 1.0
        self.is_connecting = False
        self.connection_start = None
        
        # 网格背景
        self.draw_grid = True
        self.grid_size = 20
        
    def load_flowchart(self, flowchart: FlowChart):
        """加载流程图"""
        self.scene.clear()
        self.node_items.clear()
        self.edge_items.clear()
        
        # 创建节点图形项
        for node_id, node in flowchart.nodes.items():
            node_item = self.create_node_item(node)
            self.node_items[node_id] = node_item
            self.scene.addItem(node_item)
        
        # 创建连接线图形项
        for edge in flowchart.edges:
            edge_item = self.create_edge_item(edge)
            self.edge_items.append(edge_item)
            self.scene.addItem(edge_item)
        
        # 调整视图
        self.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)
        
    def create_node_item(self, node: FlowNode) -> QGraphicsItem:
        """创建节点图形项"""
        if node.type == FlowNodeType.START or node.type == FlowNodeType.END:
            # 圆形节点
            item = FlowChartCircleNode(node)
        elif node.type == FlowNodeType.CONDITION:
            # 菱形节点
            item = FlowChartDiamondNode(node)
        elif node.type == FlowNodeType.LOOP_START:
            # 六边形节点
            item = FlowChartHexagonNode(node)
        elif node.type == FlowNodeType.SUBPROGRAM:
            # 圆角矩形节点
            item = FlowChartRoundedRectNode(node)
        else:
            # 矩形节点
            item = FlowChartRectNode(node)
        
        # 设置位置和交互
        item.setPos(node.position)
        item.setFlag(QGraphicsItem.ItemIsSelectable)
        item.setFlag(QGraphicsItem.ItemIsMovable)
        
        # 连接信号
        item.clicked.connect(lambda: self.node_clicked.emit(node))
        item.double_clicked.connect(lambda: self.node_double_clicked.emit(node))
        
        return item
        
    def wheelEvent(self, event):
        """鼠标滚轮缩放"""
        factor = 1.2
        if event.angleDelta().y() > 0:
            self.scale(factor, factor)
            self.zoom_level *= factor
        else:
            self.scale(1/factor, 1/factor)
            self.zoom_level /= factor
    
    def drawBackground(self, painter, rect):
        """绘制网格背景"""
        if not self.draw_grid:
            return
            
        painter.setPen(QPen(QColor(200, 200, 200), 0.5))
        
        # 绘制网格线
        left = int(rect.left()) - (int(rect.left()) % self.grid_size)
        top = int(rect.top()) - (int(rect.top()) % self.grid_size)
        
        lines = []
        for x in range(left, int(rect.right()), self.grid_size):
            lines.append(QLineF(x, rect.top(), x, rect.bottom()))
        for y in range(top, int(rect.bottom()), self.grid_size):
            lines.append(QLineF(rect.left(), y, rect.right(), y))
            
        painter.drawLines(lines)
```

### 4.2 节点图形项

```python
class FlowChartNodeBase(QGraphicsItem):
    """流程图节点基类"""
    
    clicked = pyqtSignal()
    double_clicked = pyqtSignal()
    
    def __init__(self, node: FlowNode):
        super().__init__()
        self.node = node
        self.is_selected = False
        self.is_executing = False
        self.execution_progress = 0
        
        # 动画效果
        self.pulse_animation = QPropertyAnimation(self, b"scale")
        self.pulse_animation.setDuration(1000)
        self.pulse_animation.setLoopCount(-1)
        
    def paint(self, painter, option, widget):
        """绘制节点"""
        # 绘制阴影
        if self.is_selected:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(0, 0, 0, 50))
            painter.drawPath(self.shape().translated(3, 3))
        
        # 绘制主体
        painter.setPen(QPen(self.node.color.darker(), 2))
        painter.setBrush(self.node.color.lighter())
        painter.drawPath(self.shape())
        
        # 绘制执行状态
        if self.is_executing:
            self.draw_execution_state(painter)
        
        # 绘制文本
        painter.setPen(Qt.black)
        painter.setFont(QFont("Arial", 10))
        painter.drawText(self.boundingRect(), Qt.AlignCenter, self.node.label)
        
        # 绘制图标
        if self.node.action:
            self.draw_icon(painter)
    
    def draw_execution_state(self, painter):
        """绘制执行状态"""
        # 绘制进度环
        rect = self.boundingRect()
        center = rect.center()
        radius = min(rect.width(), rect.height()) / 2 + 10
        
        painter.setPen(QPen(QColor(76, 175, 80), 3))
        painter.drawArc(
            center.x() - radius, 
            center.y() - radius,
            radius * 2, 
            radius * 2,
            90 * 16,  # 起始角度
            -self.execution_progress * 360 * 16  # 扫描角度
        )
    
    def set_executing(self, is_executing: bool, progress: float = 0):
        """设置执行状态"""
        self.is_executing = is_executing
        self.execution_progress = progress
        
        if is_executing:
            # 启动脉冲动画
            self.pulse_animation.start()
        else:
            self.pulse_animation.stop()
            
        self.update()

class FlowChartRectNode(FlowChartNodeBase):
    """矩形节点"""
    
    def boundingRect(self):
        return QRectF(-60, -30, 120, 60)
    
    def shape(self):
        path = QPainterPath()
        path.addRect(self.boundingRect())
        return path

class FlowChartCircleNode(FlowChartNodeBase):
    """圆形节点"""
    
    def boundingRect(self):
        return QRectF(-30, -30, 60, 60)
    
    def shape(self):
        path = QPainterPath()
        path.addEllipse(self.boundingRect())
        return path

class FlowChartDiamondNode(FlowChartNodeBase):
    """菱形节点（条件判断）"""
    
    def boundingRect(self):
        return QRectF(-50, -35, 100, 70)
    
    def shape(self):
        path = QPainterPath()
        rect = self.boundingRect()
        points = [
            QPointF(rect.center().x(), rect.top()),
            QPointF(rect.right(), rect.center().y()),
            QPointF(rect.center().x(), rect.bottom()),
            QPointF(rect.left(), rect.center().y())
        ]
        path.addPolygon(QPolygonF(points))
        path.closeSubpath()
        return path
```

### 4.3 连接线图形项

```python
class FlowChartEdge(QGraphicsPathItem):
    """流程图连接线"""
    
    def __init__(self, edge: FlowEdge, start_pos: QPointF, end_pos: QPointF):
        super().__init__()
        self.edge = edge
        self.start_pos = start_pos
        self.end_pos = end_pos
        
        # 设置样式
        pen = QPen()
        pen.setColor(QColor(edge.style["color"]))
        pen.setWidth(2)
        if edge.style["style"] == "dashed":
            pen.setStyle(Qt.DashLine)
        self.setPen(pen)
        
        # 创建路径
        self.update_path()
        
    def update_path(self):
        """更新路径"""
        path = QPainterPath()
        
        if self.edge.type == "loop_back":
            # 循环回边 - 使用贝塞尔曲线
            path.moveTo(self.start_pos)
            
            # 计算控制点
            dx = abs(self.end_pos.x() - self.start_pos.x())
            dy = abs(self.end_pos.y() - self.start_pos.y())
            
            ctrl1 = QPointF(self.start_pos.x() + dx/3, self.start_pos.y() - dy)
            ctrl2 = QPointF(self.end_pos.x() - dx/3, self.end_pos.y() - dy)
            
            path.cubicTo(ctrl1, ctrl2, self.end_pos)
        else:
            # 普通连接 - 使用直线或折线
            path.moveTo(self.start_pos)
            
            if abs(self.start_pos.x() - self.end_pos.x()) < 10:
                # 垂直连接
                path.lineTo(self.end_pos)
            else:
                # 折线连接
                mid_y = (self.start_pos.y() + self.end_pos.y()) / 2
                path.lineTo(self.start_pos.x(), mid_y)
                path.lineTo(self.end_pos.x(), mid_y)
                path.lineTo(self.end_pos)
        
        self.setPath(path)
        
        # 添加箭头
        self.add_arrow()
        
        # 添加标签
        if self.edge.label:
            self.add_label()
    
    def add_arrow(self):
        """添加箭头"""
        arrow_size = 10
        path = self.path()
        
        # 获取最后一段的方向
        if path.elementCount() >= 2:
            last_point = QPointF(
                path.elementAt(path.elementCount() - 1).x,
                path.elementAt(path.elementCount() - 1).y
            )
            second_last = QPointF(
                path.elementAt(path.elementCount() - 2).x,
                path.elementAt(path.elementCount() - 2).y
            )
            
            # 计算箭头角度
            angle = math.atan2(
                last_point.y() - second_last.y(),
                last_point.x() - second_last.x()
            )
            
            # 创建箭头
            arrow_p1 = last_point - QPointF(
                arrow_size * math.cos(angle - math.pi/6),
                arrow_size * math.sin(angle - math.pi/6)
            )
            arrow_p2 = last_point - QPointF(
                arrow_size * math.cos(angle + math.pi/6),
                arrow_size * math.sin(angle + math.pi/6)
            )
            
            # 添加到路径
            path.moveTo(arrow_p1)
            path.lineTo(last_point)
            path.lineTo(arrow_p2)
            
            self.setPath(path)
```

## 五、交互功能设计

### 5.1 流程图编辑器

```python
class FlowChartEditor(QWidget):
    """流程图编辑器 - 完整的编辑界面"""
    
    def __init__(self, sequential_controller):
        super().__init__()
        self.controller = sequential_controller
        self.init_ui()
        self.connect_signals()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 工具栏
        toolbar = self.create_toolbar()
        layout.addWidget(toolbar)
        
        # 主分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：节点面板
        self.node_palette = self.create_node_palette()
        splitter.addWidget(self.node_palette)
        
        # 中间：流程图画布
        self.canvas = FlowChartCanvas()
        splitter.addWidget(self.canvas)
        
        # 右侧：属性面板
        self.property_panel = self.create_property_panel()
        splitter.addWidget(self.property_panel)
        
        splitter.setSizes([200, 800, 300])
        layout.addWidget(splitter)
        
        # 底部：状态栏
        self.status_bar = QStatusBar()
        layout.addWidget(self.status_bar)
        
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar()
        
        # 视图控制
        toolbar.addAction(QIcon("icons/zoom_in.png"), "放大", self.zoom_in)
        toolbar.addAction(QIcon("icons/zoom_out.png"), "缩小", self.zoom_out)
        toolbar.addAction(QIcon("icons/zoom_fit.png"), "适应窗口", self.zoom_fit)
        toolbar.addSeparator()
        
        # 布局控制
        toolbar.addAction(QIcon("icons/auto_layout.png"), "自动布局", self.auto_layout)
        toolbar.addAction(QIcon("icons/align_h.png"), "水平对齐", self.align_horizontal)
        toolbar.addAction(QIcon("icons/align_v.png"), "垂直对齐", self.align_vertical)
        toolbar.addSeparator()
        
        # 编辑操作
        toolbar.addAction(QIcon("icons/undo.png"), "撤销", self.undo)
        toolbar.addAction(QIcon("icons/redo.png"), "重做", self.redo)
        toolbar.addSeparator()
        
        # 视图切换
        view_toggle = QButtonGroup()
        
        list_btn = QPushButton("📝 列表视图")
        list_btn.setCheckable(True)
        list_btn.setChecked(True)
        view_toggle.addButton(list_btn, 0)
        toolbar.addWidget(list_btn)
        
        flow_btn = QPushButton("📊 流程图视图")
        flow_btn.setCheckable(True)
        view_toggle.addButton(flow_btn, 1)
        toolbar.addWidget(flow_btn)
        
        split_btn = QPushButton("📐 分割视图")
        split_btn.setCheckable(True)
        view_toggle.addButton(split_btn, 2)
        toolbar.addWidget(split_btn)
        
        view_toggle.buttonClicked[int].connect(self.switch_view)
        
        return toolbar
    
    def create_node_palette(self):
        """创建节点面板"""
        palette = QWidget()
        layout = QVBoxLayout(palette)
        
        # 标题
        title = QLabel("🎨 节点工具箱")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)
        
        # 节点类别
        categories = [
            ("基础节点", [
                ("▶️ 开始", FlowNodeType.START),
                ("⏹️ 结束", FlowNodeType.END),
                ("📦 动作", FlowNodeType.ACTION),
            ]),
            ("控制流", [
                ("❓ 条件", FlowNodeType.CONDITION),
                ("🔄 循环", FlowNodeType.LOOP_START),
                ("📞 子程序", FlowNodeType.SUBPROGRAM),
            ]),
            ("特殊节点", [
                ("⏱️ 等待", FlowNodeType.WAIT),
                ("📝 输入", FlowNodeType.USER_INPUT),
                ("⚡ 并行", FlowNodeType.PARALLEL_START),
            ])
        ]
        
        for category_name, nodes in categories:
            # 分类标签
            cat_label = QLabel(category_name)
            cat_label.setStyleSheet("color: #666; margin-top: 10px;")
            layout.addWidget(cat_label)
            
            # 节点按钮
            for node_name, node_type in nodes:
                btn = QPushButton(node_name)
                btn.setProperty("node_type", node_type)
                btn.setCursor(Qt.PointingHandCursor)
                btn.setStyleSheet("""
                    QPushButton {
                        text-align: left;
                        padding: 8px;
                        border: 1px solid #DDD;
                        background: white;
                        margin: 2px;
                    }
                    QPushButton:hover {
                        background: #F0F0F0;
                        border-color: #2196F3;
                    }
                """)
                
                # 支持拖拽
                btn.mousePressEvent = lambda e, t=node_type: self.start_drag_node(t)
                
                layout.addWidget(btn)
        
        layout.addStretch()
        return palette
    
    def create_property_panel(self):
        """创建属性面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # 标题
        title = QLabel("⚙️ 节点属性")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)
        
        # 属性表单
        self.property_form = QFormLayout()
        
        # 节点ID
        self.prop_id = QLineEdit()
        self.prop_id.setReadOnly(True)
        self.property_form.addRow("ID:", self.prop_id)
        
        # 节点类型
        self.prop_type = QLabel()
        self.property_form.addRow("类型:", self.prop_type)
        
        # 节点标签
        self.prop_label = QLineEdit()
        self.property_form.addRow("标签:", self.prop_label)
        
        # 关联动作
        self.prop_action = QComboBox()
        self.property_form.addRow("动作:", self.prop_action)
        
        # 条件设置（仅条件节点）
        self.prop_condition = QWidget()
        condition_layout = QVBoxLayout(self.prop_condition)
        self.condition_type = QComboBox()
        self.condition_type.addItems(["等于", "大于", "小于", "包含"])
        condition_layout.addWidget(self.condition_type)
        self.condition_value = QLineEdit()
        condition_layout.addWidget(self.condition_value)
        self.property_form.addRow("条件:", self.prop_condition)
        self.prop_condition.setVisible(False)
        
        # 循环设置（仅循环节点）
        self.prop_loop = QSpinBox()
        self.prop_loop.setMinimum(1)
        self.prop_loop.setMaximum(100)
        self.property_form.addRow("循环次数:", self.prop_loop)
        self.prop_loop.setVisible(False)
        
        layout.addLayout(self.property_form)
        
        # 应用按钮
        apply_btn = QPushButton("✅ 应用更改")
        apply_btn.clicked.connect(self.apply_properties)
        layout.addWidget(apply_btn)
        
        layout.addStretch()
        return panel
```

### 5.2 执行可视化

```python
class FlowChartExecutionVisualizer:
    """流程图执行可视化器"""
    
    def __init__(self, canvas: FlowChartCanvas):
        self.canvas = canvas
        self.current_node = None
        self.execution_path = []
        self.execution_timer = QTimer()
        self.execution_timer.timeout.connect(self.update_visualization)
        
    def start_execution(self):
        """开始执行可视化"""
        self.reset_visualization()
        self.current_node = "start"
        self.highlight_node(self.current_node)
        self.execution_timer.start(100)  # 100ms更新一次
        
    def update_visualization(self):
        """更新可视化状态"""
        # 从控制器获取当前执行的动作
        current_action_index = self.get_current_action_index()
        
        if current_action_index >= 0:
            # 找到对应的流程图节点
            node_id = f"node_{current_action_index}"
            
            if node_id != self.current_node:
                # 移动到新节点
                self.move_to_node(node_id)
                
        # 更新执行进度
        progress = self.get_execution_progress()
        if self.current_node in self.canvas.node_items:
            node_item = self.canvas.node_items[self.current_node]
            node_item.set_executing(True, progress)
    
    def move_to_node(self, node_id: str):
        """移动到指定节点"""
        # 取消当前节点高亮
        if self.current_node in self.canvas.node_items:
            self.canvas.node_items[self.current_node].set_executing(False)
        
        # 高亮新节点
        self.current_node = node_id
        if node_id in self.canvas.node_items:
            node_item = self.canvas.node_items[node_id]
            node_item.set_executing(True, 0)
            
            # 添加到执行路径
            self.execution_path.append(node_id)
            
            # 高亮执行路径
            self.highlight_execution_path()
            
            # 自动滚动到当前节点
            self.canvas.ensureVisible(node_item)
    
    def highlight_execution_path(self):
        """高亮执行路径"""
        for edge_item in self.canvas.edge_items:
            edge = edge_item.edge
            
            # 检查边是否在执行路径上
            if edge.source in self.execution_path and edge.target in self.execution_path:
                # 设置为执行样式
                pen = QPen(QColor(76, 175, 80), 3)
                edge_item.setPen(pen)
                edge_item.setZValue(1)  # 提高层级
    
    def stop_execution(self):
        """停止执行可视化"""
        self.execution_timer.stop()
        self.reset_visualization()
        
    def reset_visualization(self):
        """重置可视化状态"""
        # 清除所有高亮
        for node_item in self.canvas.node_items.values():
            node_item.set_executing(False)
            
        # 重置边样式
        for edge_item in self.canvas.edge_items:
            edge_item.setPen(QPen(QColor("#333333"), 2))
            edge_item.setZValue(0)
            
        self.execution_path.clear()
```

## 六、集成方案

### 6.1 与现有系统集成

```python
class IntegratedSequentialController(QWidget):
    """集成的顺序控制器 - 支持列表和流程图双视图"""
    
    def __init__(self, controller: SequentialController):
        super().__init__()
        self.controller = controller
        self.init_ui()
        self.setup_sync()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 视图切换工具栏
        toolbar = QToolBar()
        self.view_selector = QComboBox()
        self.view_selector.addItems(["列表视图", "流程图视图", "分割视图"])
        self.view_selector.currentIndexChanged.connect(self.switch_view)
        toolbar.addWidget(QLabel("视图模式:"))
        toolbar.addWidget(self.view_selector)
        layout.addWidget(toolbar)
        
        # 堆叠容器
        self.view_stack = QStackedWidget()
        
        # 列表视图
        self.list_view = SequentialListView(self.controller)
        self.view_stack.addWidget(self.list_view)
        
        # 流程图视图
        self.flowchart_view = FlowChartEditor(self.controller)
        self.view_stack.addWidget(self.flowchart_view)
        
        # 分割视图
        self.split_view = QSplitter(Qt.Horizontal)
        self.split_view.addWidget(SequentialListView(self.controller))
        self.split_view.addWidget(FlowChartCanvas())
        self.view_stack.addWidget(self.split_view)
        
        layout.addWidget(self.view_stack)
        
    def setup_sync(self):
        """设置双向同步"""
        # 列表到流程图同步
        self.controller.sequence_changed.connect(self.update_flowchart)
        
        # 流程图到列表同步
        self.flowchart_view.canvas.node_changed.connect(self.update_sequence)
        
    def update_flowchart(self):
        """更新流程图"""
        # 将序列转换为流程图
        converter = SequenceToFlowChart()
        flowchart = converter.convert(self.controller.action_sequence)
        
        # 更新流程图视图
        self.flowchart_view.canvas.load_flowchart(flowchart)
        
        # 如果在分割视图，也更新
        if self.view_stack.currentIndex() == 2:
            split_canvas = self.split_view.widget(1)
            split_canvas.load_flowchart(flowchart)
    
    def update_sequence(self, node: FlowNode):
        """从流程图更新序列"""
        if node.action:
            # 找到对应的动作并更新
            for i, action in enumerate(self.controller.action_sequence):
                if f"node_{i}" == node.id:
                    # 更新动作参数
                    action.parameters.update(node.action.parameters)
                    self.controller.sequence_changed.emit()
                    break
```

## 七、优势与特性

### 7.1 核心优势
- **直观理解**：图形化展示让非工程师一目了然
- **快速编辑**：拖拽节点即可调整流程
- **实时反馈**：执行时动态显示进度
- **错误定位**：失败节点红色高亮
- **逻辑清晰**：循环、分支、并行结构可视化

### 7.2 高级特性
- **自动布局**：智能排列节点位置
- **缩放平移**：支持大型流程图浏览
- **双向同步**：列表和图形实时同步
- **执行追踪**：绿色路径显示执行历史
- **导出功能**：支持SVG/PNG导出

### 7.3 交互特性
- **拖拽创建**：从工具箱拖拽节点
- **连线编辑**：点击拖动创建连接
- **批量操作**：框选多个节点
- **右键菜单**：快速访问常用操作
- **键盘快捷键**：提高操作效率

## 八、实施计划

### 第一阶段（1周）
1. 实现基础流程图数据结构
2. 开发序列到流程图转换器
3. 创建基础节点渲染

### 第二阶段（2周）
1. 实现流程图画布组件
2. 添加缩放平移功能
3. 开发自动布局算法

### 第三阶段（1周）
1. 实现双向同步机制
2. 添加执行可视化
3. 集成到主界面

### 第四阶段（1周）
1. 添加拖拽编辑功能
2. 实现导出功能
3. 性能优化

## 九、总结

流程图可视化将彻底改变Sequential Controller的用户体验：

1. **降低认知负担**：从阅读列表到看图理解
2. **提高编辑效率**：可视化编辑更直观
3. **增强调试能力**：执行路径一目了然
4. **支持复杂逻辑**：轻松处理嵌套和分支

这个方案让非工程师用户能够像使用Visio画流程图一样编程机器人，真正实现"所见即所得"的编程体验。

---
*设计版本：1.0*  
*创建日期：2024*