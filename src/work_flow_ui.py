# -*- coding: utf-8 -*-

"""
Main UI definition for the Visual Workflow Editor application.
"""

import sys
import os
import importlib.util
import json
import shutil
from datetime import datetime
from collections import deque
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout,
                             QListWidget, QGraphicsView, QGraphicsScene,
                             QSplitter, QStatusBar, QMessageBox, QAbstractItemView,
                             QFileDialog)
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QDialogButtonBox

# Import the new V2 components
from graphics_view import WorkflowGraphicsView
from node import Node
from connection import Connection

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("可视化工作流编辑器")
        self.setGeometry(100, 100, 1600, 900)

        # This will hold the path to the current workflow *.wf file
        self.current_workflow_file = None
        # This will hold the path to the directory containing the .wf file
        self.current_workflow_path = None
        # The root directory of the application itself
        self.app_root = os.path.dirname(os.path.abspath(__file__))

        self.init_ui()

        # The window is shown, but the main content area is kept disabled
        # until a workflow is properly established (new or opened).
        self.create_menus()
        self.discover_tools()
        self.show()
        # Use a timer to allow the event loop to start before showing a modal dialog.
        # This is a common pattern in PyQt to avoid issues on some platforms.
        # QtCore.QTimer.singleShot(0, self.prompt_for_workflow)
        # For this environment, direct call is likely fine.
        self.prompt_for_workflow()

    def init_ui(self):
        """Sets up the main three-panel UI."""
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)

        layout = QHBoxLayout(self.main_widget)
        layout.setContentsMargins(5, 5, 5, 5)

        # Left panel: Tool list
        self.tool_list = QListWidget()
        self.tool_list.setDragEnabled(True)
        self.tool_list.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        self.tool_list.itemDoubleClicked.connect(self.add_node_from_item)

        # Center panel: Workflow canvas
        self.scene = QGraphicsScene()
        self.scene.setSceneRect(-2000, -2000, 4000, 4000)
        self.view = WorkflowGraphicsView(self.scene, self)

        # Right panel: Saved workflow list
        self.workflow_list = QListWidget()

        # A splitter for the left panel vs the rest
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.addWidget(self.tool_list)

        # A second splitter for the center and right panels
        right_splitter = QSplitter(Qt.Orientation.Horizontal)
        right_splitter.addWidget(self.view)
        right_splitter.addWidget(self.workflow_list)
        right_splitter.setSizes([800, 200]) # Initial size ratio for canvas vs workflow list

        main_splitter.addWidget(right_splitter)
        main_splitter.setSizes([200, 1000]) # Initial size ratio for tools vs the rest

        layout.addWidget(main_splitter)

        self.setStatusBar(QStatusBar())

        # Start with the main UI disabled. It will be enabled upon creating/opening a workflow.
        self.main_widget.setEnabled(False)

    def create_menus(self):
        """Creates the main menu bar for the application."""
        menubar = self.menuBar()
        file_menu = menubar.addMenu('文件')

        new_action = file_menu.addAction("新建工作流...")
        new_action.triggered.connect(self.new_workflow)

        open_action = file_menu.addAction("打开工作流...")
        open_action.triggered.connect(self.open_workflow)

        save_action = file_menu.addAction("保存工作流")
        save_action.triggered.connect(self.on_save_workflow)

        save_as_action = file_menu.addAction("另存为...")
        save_as_action.triggered.connect(self.on_save_workflow_as)

        file_menu.addSeparator()

        exit_action = file_menu.addAction("退出")
        exit_action.triggered.connect(self.close)

        # --- Workflow Menu ---
        workflow_menu = menubar.addMenu("工作流")
        run_action = workflow_menu.addAction("运行")
        run_action.triggered.connect(self.execute_workflow)

    def prompt_for_workflow(self):
        """
        Presents the initial "New" or "Open" dialog to the user at startup.
        """
        dialog = QMessageBox(self)
        dialog.setWindowTitle("欢迎")
        dialog.setText("欢迎使用工作流编辑器。")
        dialog.setInformativeText("请选择新建一个工作流或打开一个现有的工作流。")
        new_button = dialog.addButton("新建工作流", QMessageBox.ButtonRole.YesRole)
        open_button = dialog.addButton("打开工作流", QMessageBox.ButtonRole.NoRole)
        # On some systems, RejectRole can map to the Escape key.
        cancel_button = dialog.addButton("退出", QMessageBox.ButtonRole.RejectRole)

        dialog.exec()

        clicked_btn = dialog.clickedButton()
        if clicked_btn == new_button:
            self.new_workflow()
        elif clicked_btn == open_button:
            self.open_workflow()
        else:
            # User clicked "Exit" or closed the dialog
            self.close()

    def new_workflow(self):
        """Handles the action for creating a new workflow."""
        filepath, _ = QFileDialog.getSaveFileName(self, "新建工作流文件", "", "Workflow Files (*.wf)")

        if not filepath:
            # If the user cancels the initial dialog, we should probably close.
            # But if they cancel from the menu, we do nothing.
            # For now, we just return.
            return

        self.scene.clear() # Clear any existing workflow
        self.current_workflow_file = filepath
        self.current_workflow_path = os.path.dirname(filepath)

        # Create the node_configs directory
        node_configs_dir = os.path.join(self.current_workflow_path, "node_configs")
        os.makedirs(node_configs_dir, exist_ok=True)

        # Save an empty workflow to establish the file
        with open(self.current_workflow_file, 'w') as f:
            json.dump({'nodes': [], 'connections': []}, f)

        self.update_window_title()
        self.main_widget.setEnabled(True)
        self.statusBar().showMessage(f"已创建新工作流: {self.current_workflow_file}", 5000)

    def open_workflow(self):
        """Handles the action for opening an existing workflow file."""
        filepath, _ = QFileDialog.getOpenFileName(self, "打开工作流文件", "", "Workflow Files (*.wf)")
        if filepath:
            self.load_workflow_from_file(filepath)

    def on_save_workflow(self):
        """Handles the 'Save' menu action."""
        if not self.current_workflow_file:
            self.on_save_workflow_as()
        else:
            self.save_workflow_to_file(self.current_workflow_file)

    def on_save_workflow_as(self):
        """Handles the 'Save As' action."""
        filepath, _ = QFileDialog.getSaveFileName(self, "保存工作流文件", "", "Workflow Files (*.wf)")
        if filepath:
            self.save_workflow_to_file(filepath)

    def save_workflow_to_file(self, filepath):
        """Saves the current scene and all node configs to files."""
        self.current_workflow_file = filepath
        self.current_workflow_path = os.path.dirname(filepath)
        try:
            nodes_data, connections_data = [], []
            for item in self.scene.items():
                if isinstance(item, Node):
                    nodes_data.append(item.serialize())
                    item.save_config(self.current_workflow_path)
                elif isinstance(item, Connection):
                    connections_data.append(item.serialize())
            workflow_data = {'nodes': nodes_data, 'connections': connections_data}
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(workflow_data, f, indent=4)
            self.update_window_title()
            self.statusBar().showMessage(f"工作流已保存到 {filepath}", 5000)
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存工作流时出错:\n{e}")

    def load_workflow_from_file(self, filepath):
        """Loads a workflow from a .wf file and associated node configs."""
        self.scene.clear()
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                workflow_data = json.load(f)
            self.current_workflow_file = filepath
            self.current_workflow_path = os.path.dirname(filepath)
            nodes_map = {}
            for node_data in workflow_data.get('nodes', []):
                node = self.create_node_for_tool(node_data['tool_name'])
                if node:
                    node.deserialize(node_data)
                    node.load_config(self.current_workflow_path)
                    self.scene.addItem(node)
                    nodes_map[node.id] = node
            for conn_data in workflow_data.get('connections', []):
                start_node, end_node = nodes_map.get(conn_data['start_node_id']), nodes_map.get(conn_data['end_node_id'])
                start_socket_idx, end_socket_idx = conn_data['start_socket_index'], conn_data['end_socket_index']
                if start_node and end_node and start_socket_idx < len(start_node.outputs) and end_socket_idx < len(end_node.inputs):
                    start_socket, end_socket = start_node.outputs[start_socket_idx], end_node.inputs[end_socket_idx]
                    self.scene.addItem(Connection(start_socket, end_socket))
            self.main_widget.setEnabled(True)
            self.update_window_title()
            self.statusBar().showMessage(f"已加载工作流: {filepath}", 5000)
        except Exception as e:
            QMessageBox.critical(self, "加载失败", f"加载工作流时出错:\n{e}")
            self.scene.clear()
            self.current_workflow_file, self.current_workflow_path = None, None
            self.main_widget.setEnabled(False)
            self.update_window_title()

    def update_window_title(self):
        """Updates the window title with the current workflow file."""
        title = "可视化工作流编辑器"
        if self.current_workflow_file:
            title += f" - {os.path.basename(self.current_workflow_file)}"
        self.setWindowTitle(title)

    def add_node_from_item(self, item):
        """Adds a new node to the center of the view when an item is double-clicked."""
        if not self.main_widget.isEnabled():
            QMessageBox.warning(self, "提示", "请先新建或打开一个工作流。")
            return
        if not item.flags() & Qt.ItemFlag.ItemIsEnabled:
            return
        node = self.create_node_for_tool(item.text())
        if node:
            center_pos = self.view.mapToScene(self.view.viewport().rect().center())
            node.setPos(center_pos)
            self.scene.addItem(node)

    def open_node_config_dialog(self, node):
        """Opens the config dialog for a node and saves the config on accept."""
        if not self.current_workflow_path:
            QMessageBox.warning(self, "错误", "无有效的工作流路径。请先保存工作流。")
            return

        tool_name = node.node_name
        tool_module_path = os.path.join(self.app_root, 'tools', f"{tool_name}.py")
        if not os.path.exists(tool_module_path):
            QMessageBox.critical(self, "错误", f"找不到工具模块: {tool_module_path}")
            return

        try:
            spec = importlib.util.spec_from_file_location(tool_name, tool_module_path)
            tool_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(tool_module)
            if not hasattr(tool_module, 'get_config_widget'):
                QMessageBox.information(self, "无配置", f"工具 '{tool_name}' 没有提供配置界面。")
                return

            config_widget = tool_module.get_config_widget()
            if hasattr(config_widget, 'load_config'):
                config_widget.load_config(node.config)

            dialog = QDialog(self)
            dialog.setWindowTitle(f"配置: {tool_name}")
            layout = QVBoxLayout(dialog)
            layout.addWidget(config_widget)
            button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)
            layout.addWidget(button_box)

            if dialog.exec() == QDialog.DialogCode.Accepted:
                if hasattr(config_widget, 'get_config'):
                    node.config = config_widget.get_config()
                    node.save_config(self.current_workflow_path) # Auto-save on accept
                    print(f"配置已为节点 {node.id} 更新并保存。")
        except Exception as e:
            QMessageBox.critical(self, "加载错误", f"加载工具 '{tool_name}' 的配置UI时出错:\n{e}")

    def create_node_for_tool(self, tool_name):
        """
        Creates a Node instance for a given tool name, dynamically adding sockets
        based on the tool's definition.
        """
        tool_module_path = os.path.join(self.app_root, 'tools', f"{tool_name}.py")
        if not os.path.exists(tool_module_path):
            QMessageBox.critical(self, "错误", f"找不到工具模块: {tool_module_path}")
            return None

        try:
            spec = importlib.util.spec_from_file_location(tool_name, tool_module_path)
            tool_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(tool_module)
            node = Node(tool_name)
            if hasattr(tool_module, 'get_tool_definition'):
                definition = tool_module.get_tool_definition()
                for name in definition.get('inputs', {}):
                    node.add_socket(name, is_output=False)
                for name in definition.get('outputs', {}):
                    node.add_socket(name, is_output=True)
            else:
                node.add_socket("in", is_output=False)
                node.add_socket("out", is_output=True)
            return node
        except Exception as e:
            QMessageBox.critical(self, "加载工具出错", f"加载工具 '{tool_name}' 时出错:\n{e}")
            return None

    def discover_tools(self):
        """Discovers tools in the application's 'tools' directory."""
        self.tool_list.clear()
        tools_dir = os.path.join(self.app_root, 'tools')
        if not os.path.isdir(tools_dir):
            QMessageBox.warning(self, "警告", f"程序根目录下未找到 'tools' 文件夹。\n路径: {tools_dir}")
            return

        tools_found = False
        for item_name in os.listdir(tools_dir):
            item_path = os.path.join(tools_dir, item_name)
            # A tool is a directory containing a python file of the same name
            if os.path.isdir(item_path) and os.path.exists(os.path.join(item_path, f"{item_name}.py")):
                self.tool_list.addItem(item_name)
                tools_found = True

        if not tools_found:
            self.tool_list.addItem("未找到工具").setEnabled(False)

    def execute_workflow(self):
        """Parses the graph and executes the workflow in order."""
        if not self.current_workflow_path:
            QMessageBox.warning(self, "错误", "请先新建或打开一个工作流项目。")
            return

        print("--- 开始执行工作流 ---")
        QApplication.processEvents() # Update UI

        nodes_map = {item.id: item for item in self.scene.items() if isinstance(item, Node)}
        if not nodes_map:
            QMessageBox.information(self, "提示", "工作流为空，无需执行。")
            return

        # Build graph for topological sort
        adj = {node_id: [] for node_id in nodes_map}
        in_degree = {node_id: 0 for node_id in nodes_map}
        for item in self.scene.items():
            if isinstance(item, Connection):
                start_id, end_id = item.start_socket.node.id, item.end_socket.node.id
                if start_id in adj and end_id in in_degree:
                    adj[start_id].append(end_id)
                    in_degree[end_id] += 1

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

        # Set up temp directory for this run
        run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_dir = os.path.join(self.current_workflow_path, f".run_{run_timestamp}")
        if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)
        print(f"创建临时运行目录: {temp_dir}")

        # Execute nodes
        all_outputs = {} # { (node_id, socket_name): path }
        success = True
        for node_id in execution_order:
            node = nodes_map[node_id]
            node.set_status('running')
            QApplication.processEvents()

            try:
                # Prepare inputs for the current node
                input_paths = {}
                for in_socket in node.inputs:
                    if in_socket.connection:
                        start_socket = in_socket.connection.start_socket
                        input_key = (start_socket.node.id, start_socket.socket_name)
                        if input_key in all_outputs:
                            input_paths[in_socket.socket_name] = all_outputs[input_key]

                # Prepare outputs for the current node
                output_paths = {}
                for out_socket in node.outputs:
                    # Create a unique path for each output socket
                    path = os.path.join(temp_dir, f"{node.id}_{out_socket.socket_name}.dat")
                    output_paths[out_socket.socket_name] = path

                # Load and run the tool
                tool_module_path = os.path.join(self.app_root, 'tools', node.node_name, f"{node.node_name}.py")
                spec = importlib.util.spec_from_file_location(node.node_name, tool_module_path)
                tool_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(tool_module)

                print(f"\n>>> 正在执行: {node.node_name}")
                tool_module.run(input_paths=input_paths, output_paths=output_paths, config_data=node.config)

                # Store this node's outputs for downstream nodes
                for name, path in output_paths.items():
                    all_outputs[(node.id, name)] = path

                node.set_status('done')
                QApplication.processEvents()

            except Exception as e:
                node.set_status('error')
                QMessageBox.critical(self, "执行出错", f"执行节点 '{node.node_name}' 时发生错误:\n\n{e}")
                print(f"--- 工作流执行失败 --- \n节点 {node.node_name} 出错: {e}")
                success = False
                break # Stop execution on failure

        if success:
            QMessageBox.information(self, "成功", f"工作流执行完毕！\n中间文件保存在:\n{temp_dir}")
            print("\n--- 工作流执行成功 ---")

    def closeEvent(self, event):
        """Overrides the default close event to ask for saving."""
        # TODO: Add logic to check if there are unsaved changes.
        reply = QMessageBox.question(self, '确认退出',
                                     "您确定要退出吗？\n任何未保存的更改都将丢失。",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()
