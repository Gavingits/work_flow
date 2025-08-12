import sys
import os
import json
import shutil
from datetime import datetime
import importlib.util
from collections import deque
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout,
                             QListWidget, QGraphicsView, QGraphicsScene,
                             QSplitter, QAction, QFileDialog, QMessageBox,
                             QAbstractItemView, QGraphicsLineItem, QDialog,
                             QVBoxLayout, QPushButton, QDialogButtonBox)
from PyQt5.QtCore import Qt, QLineF, QPointF
from PyQt5.QtGui import QPainter, QPen, QColor
from node import Node, Socket
from connection import Connection


class WorkflowGraphicsView(QGraphicsView):
    """
    自定义的QGraphicsView，用于接收从工具列表拖拽过来的节点，并处理连接线的绘制。
    """
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setAcceptDrops(True)
        self.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.RubberBandDrag)

        self.line_to_draw = None
        self.start_socket = None

    def get_socket_at(self, pos):
        """辅助函数，获取指定位置的Socket项"""
        # We need to check for items in a small area around the cursor, not just at a single point
        items = self.items(pos)
        for item in items:
            if isinstance(item, Socket):
                return item
        return None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            socket = self.get_socket_at(event.pos())
            if socket:
                # 开始绘制连接线
                self.start_socket = socket
                self.line_to_draw = QGraphicsLineItem()
                self.line_to_draw.setPen(QPen(QColor("#ecf0f1"), 2, Qt.DashLine))
                self.scene().addItem(self.line_to_draw)

                start_pos = self.start_socket.scenePos()
                self.line_to_draw.setLine(QLineF(start_pos, start_pos))
                event.accept()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.line_to_draw:
            # 更新临时线的位置
            line = self.line_to_draw.line()
            line.setP2(self.mapToScene(event.pos()))
            self.line_to_draw.setLine(line)
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.line_to_draw and self.start_socket:
            # 绘制结束
            # 清理临时线
            if self.line_to_draw.scene():
                self.scene().removeItem(self.line_to_draw)
            self.line_to_draw = None

            end_socket = self.get_socket_at(event.pos())

            # 检查连接是否有效
            if (end_socket and self.start_socket.parentItem() != end_socket.parentItem() and
                    self.start_socket.is_output != end_socket.is_output and
                    not self.start_socket.connection and not end_socket.connection):

                # 确保连接是从输出到输入
                start_sock = self.start_socket if self.start_socket.is_output else end_socket
                end_sock = end_socket if self.start_socket.is_output else self.start_socket

                # 创建永久连接
                conn = Connection(start_sock, end_sock)
                self.scene().addItem(conn)

            self.start_socket = None
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasText():
            tool_name = event.mimeData().text()
            drop_position = self.mapToScene(event.pos())

            node = Node(tool_name)
            node.setPos(drop_position)
            self.scene().addItem(node)

            event.acceptProposedAction()
        else:
            super().dropEvent(event)

    def on_node_double_clicked(self, node):
        """当节点被双击时，此方法由Node调用"""
        main_win = self.window()
        if isinstance(main_win, MainWindow):
            main_win.open_node_config_dialog(node)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.wfpath = None
        self.setWindowTitle("工作流编辑器 (Workflow Editor)")
        self.setGeometry(100, 100, 1200, 800)

        self.init_ui()
        self.create_menus()

    def init_ui(self):
        """初始化主界面UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # 使用QSplitter来分割工具列表和画布
        splitter = QSplitter(Qt.Horizontal)

        # 左侧：工具列表
        self.tools_list_widget = QListWidget()
        self.tools_list_widget.setDragEnabled(True)
        self.tools_list_widget.setDragDropMode(QAbstractItemView.DragOnly)
        splitter.addWidget(self.tools_list_widget)

        # 右侧：工作流画布
        self.scene = QGraphicsScene()
        self.scene.setSceneRect(-1000, -1000, 2000, 2000) # 给场景一个初始大小
        self.view = WorkflowGraphicsView(self.scene, self)
        splitter.addWidget(self.view)

        # 调整分割器的初始大小
        splitter.setSizes([200, 1000])

        main_layout.addWidget(splitter)

    def create_menus(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        file_menu = menubar.addMenu('文件 (&F)')

        # --- 设置工作流目录 Action ---
        set_dir_action = QAction('设置工作流目录 (&S)...', self)
        set_dir_action.setStatusTip('选择一个文件夹作为工作流的根目录')
        set_dir_action.triggered.connect(self.set_workflow_directory)
        file_menu.addAction(set_dir_action)

        file_menu.addSeparator()

        # --- 保存/加载 Action ---
        save_action = QAction('保存工作流 (&S)', self)
        save_action.triggered.connect(self.on_save_workflow)
        file_menu.addAction(save_action)

        load_action = QAction('加载工作流 (&L)', self)
        load_action.triggered.connect(self.on_load_workflow)
        file_menu.addAction(load_action)

        file_menu.addSeparator()

        # --- 退出 Action ---
        exit_action = QAction('退出 (&X)', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # --- 工作流菜单 ---
        workflow_menu = menubar.addMenu('工作流 (&W)')
        run_action = QAction('运行 (&R)', self)
        run_action.setStatusTip('执行当前画布上的工作流')
        run_action.triggered.connect(self.execute_workflow)
        workflow_menu.addAction(run_action)

    def set_workflow_directory(self):
        """弹出对话框让用户选择工作流目录"""
        directory = QFileDialog.getExistingDirectory(self, "选择工作流目录")
        if directory:
            self.wfpath = directory
            self.setWindowTitle(f"工作流编辑器 - {self.wfpath}")
            self.discover_tools()

    def discover_tools(self):
        """扫描tools文件夹并更新工具列表"""
        self.tools_list_widget.clear()
        if not self.wfpath:
            return

        tools_dir = os.path.join(self.wfpath, 'tools')
        if not os.path.isdir(tools_dir):
            # Optional: Offer to create the directory
            # reply = QMessageBox.question(self, '提示', f"在 {self.wfpath} 中未找到 'tools' 目录。\n是否要创建它？",
            #                            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            # if reply == QMessageBox.Yes:
            #     os.makedirs(tools_dir)
            # else:
            #     return
            return # Silently fail if tools dir doesn't exist yet.

        for filename in os.listdir(tools_dir):
            if filename.endswith('.py') and not filename.startswith('__'):
                tool_name = os.path.splitext(filename)[0]
                self.tools_list_widget.addItem(tool_name)

    def open_node_config_dialog(self, node):
        """打开指定节点的配置对话框"""
        if not self.wfpath:
            QMessageBox.warning(self, "错误", "工作流目录未设置。")
            return

        tool_name = node.name
        tool_module_path = os.path.join(self.wfpath, 'tools', f"{tool_name}.py")

        if not os.path.exists(tool_module_path):
            QMessageBox.critical(self, "错误", f"找不到工具模块: {tool_module_path}")
            return

        try:
            # 动态从文件路径加载模块
            spec = importlib.util.spec_from_file_location(tool_name, tool_module_path)
            tool_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(tool_module)

            if hasattr(tool_module, 'get_config_widget'):
                config_widget = tool_module.get_config_widget()

                # 创建对话框
                dialog = QDialog(self)
                dialog.setWindowTitle(f"配置: {tool_name}")

                layout = QVBoxLayout(dialog)
                layout.addWidget(config_widget)

                # 添加 OK 和 Cancel 按钮
                button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
                button_box.accepted.connect(dialog.accept)
                button_box.rejected.connect(dialog.reject)
                layout.addWidget(button_box)

                # TODO: 在此加载节点现有配置到config_widget
                # e.g., config_widget.load_settings(node.get_config())

                if dialog.exec_() == QDialog.Accepted:
                    # TODO: 在此从config_widget中获取设置并保存
                    # e.g., node.set_config(config_widget.get_settings())
                    print(f"配置已为节点 {node.id} 保存 (模拟)")
                else:
                    print(f"节点 {node.id} 的配置已取消")

            else:
                QMessageBox.information(self, "无配置", f"工具 '{tool_name}' 没有提供配置界面。")

        except Exception as e:
            QMessageBox.critical(self, "加载错误", f"加载工具 '{tool_name}' 时出错:\n{e}")

    def execute_workflow(self):
        """
        解析图，进行拓扑排序，并执行工作流。
        """
        print("--- 开始执行工作流 ---")

        if not self.wfpath:
            QMessageBox.warning(self, "错误", "请先设置工作流目录。")
            return

        # 1. 收集节点和连接
        nodes_map = {item.id: item for item in self.scene.items() if isinstance(item, Node)}
        connections = [item for item in self.scene.items() if isinstance(item, Connection)]

        if not nodes_map:
            QMessageBox.information(self, "提示", "工作流为空，无需执行。")
            return

        # 2. 构建图并进行拓扑排序
        adj = {node_id: [] for node_id in nodes_map}
        in_degree = {node_id: 0 for node_id in nodes_map}
        predecessors = {node_id: None for node_id in nodes_map}

        for conn in connections:
            start_node = conn.start_socket.parentItem()
            end_node = conn.end_socket.parentItem()
            if start_node and end_node and start_node.id in adj and end_node.id in in_degree:
                adj[start_node.id].append(end_node.id)
                in_degree[end_node.id] += 1
                predecessors[end_node.id] = start_node.id

        queue = deque([node_id for node_id in nodes_map if in_degree[node_id] == 0])
        execution_order = []
        while queue:
            node_id = queue.popleft()
            execution_order.append(node_id)
            for neighbor_id in adj[node_id]:
                in_degree[neighbor_id] -= 1
                if in_degree[neighbor_id] == 0:
                    queue.append(neighbor_id)

        if len(execution_order) != len(nodes_map):
            QMessageBox.critical(self, "错误", "工作流中存在循环，无法执行。")
            return

        # 3. 准备临时运行目录
        run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_dir = os.path.join(self.wfpath, f".run_{run_timestamp}")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)
        print(f"创建临时运行目录: {temp_dir}")

        # 4. 按顺序执行节点
        node_outputs = {}  # {node_id: output_path}
        try:
            for node_id in execution_order:
                node = nodes_map[node_id]
                print(f"\n>>> 正在执行节点: {node.name} (ID: {node.id})")

                pred_id = predecessors.get(node.id)
                input_path = node_outputs.get(pred_id) if pred_id else None
                output_path = os.path.join(temp_dir, f"{node.id}_output.dat")

                print(f"    输入路径: {input_path}")
                print(f"    输出路径: {output_path}")

                tool_module_path = os.path.join(self.wfpath, 'tools', f"{node.name}.py")
                spec = importlib.util.spec_from_file_location(node.name, tool_module_path)
                tool_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(tool_module)

                if hasattr(tool_module, 'run'):
                    tool_module.run(input_path=input_path, output_path=output_path)
                    node_outputs[node.id] = output_path
                    print(f"<<< 节点 {node.name} 执行成功")
                else:
                    raise RuntimeError(f"工具 '{node.name}' 没有 'run' 函数。")

            QMessageBox.information(self, "成功", f"工作流执行完毕！\n中间文件保存在:\n{temp_dir}")
            print("\n--- 工作流执行成功 ---")

        except Exception as e:
            QMessageBox.critical(self, "执行出错", f"执行节点 '{node.name}' 时发生错误:\n\n{e}")
            print(f"\n--- 工作流执行失败 --- \n节点 {node.name} 出错: {e}")

    def on_save_workflow(self):
        """打开文件对话框以保存工作流"""
        start_dir = self.wfpath if self.wfpath else os.getcwd()
        filepath, _ = QFileDialog.getSaveFileName(self, "保存工作流", start_dir, "Workflow Files (*.json)")
        if filepath:
            self.save_workflow(filepath)

    def on_load_workflow(self):
        """打开文件对话框以加载工作流"""
        start_dir = self.wfpath if self.wfpath else os.getcwd()
        filepath, _ = QFileDialog.getOpenFileName(self, "加载工作流", start_dir, "Workflow Files (*.json)")
        if filepath:
            self.load_workflow(filepath)

    def save_workflow(self, filepath):
        """将当前场景序列化为JSON文件"""
        try:
            nodes = [item for item in self.scene.items() if isinstance(item, Node)]
            connections = [item for item in self.scene.items() if isinstance(item, Connection)]

            workflow_data = {
                'nodes': [],
                'connections': []
            }

            for node in nodes:
                workflow_data['nodes'].append({
                    'id': node.id,
                    'name': node.name,
                    'pos': [node.pos().x(), node.pos().y()]
                })

            for conn in connections:
                start_node = conn.start_socket.parentItem()
                end_node = conn.end_socket.parentItem()
                workflow_data['connections'].append({
                    'start_node_id': start_node.id,
                    'end_node_id': end_node.id,
                })

            with open(filepath, 'w') as f:
                json.dump(workflow_data, f, indent=4)

            QMessageBox.information(self, "成功", f"工作流已成功保存到\n{filepath}")
            print(f"工作流已保存到 {filepath}")

        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存工作流时发生错误:\n{e}")
            print(f"错误: 保存工作流失败: {e}")

    def load_workflow(self, filepath):
        """从JSON文件加载工作流"""
        try:
            with open(filepath, 'r') as f:
                workflow_data = json.load(f)

            self.scene.clear()
            nodes_map = {}

            # 1. 加载所有节点
            for node_data in workflow_data.get('nodes', []):
                node = Node(name=node_data['name'])
                node.id = node_data['id'] # 恢复ID
                node.setPos(QPointF(*node_data['pos']))
                self.scene.addItem(node)
                nodes_map[node.id] = node

            # 2. 加载所有连接
            for conn_data in workflow_data.get('connections', []):
                start_node = nodes_map.get(conn_data['start_node_id'])
                end_node = nodes_map.get(conn_data['end_node_id'])

                if start_node and end_node:
                    # 假设输出端口是socket_output, 输入是socket_input
                    conn = Connection(start_node.socket_output, end_node.socket_input)
                    self.scene.addItem(conn)

            QMessageBox.information(self, "成功", f"工作流已从\n{filepath}\n成功加载")
            print(f"工作流已从 {filepath} 加载")

        except Exception as e:
            QMessageBox.critical(self, "加载失败", f"加载工作流时发生错误:\n{e}")
            print(f"错误: 加载工作流失败: {e}")


if __name__ == '__main__':
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
