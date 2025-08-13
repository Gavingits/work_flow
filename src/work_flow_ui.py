# -*- coding: utf-8 -*-

"""
Main UI definition for the Visual Workflow Editor application.
"""

import sys
import os
import importlib.util
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout,
                             QListWidget, QGraphicsView, QGraphicsScene,
                             QSplitter, QStatusBar, QMessageBox, QAbstractItemView)
from PyQt6.QtCore import Qt

# Import the new V2 components
from graphics_view import WorkflowGraphicsView
from node import Node

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("可视化工作流编辑器")
        self.setGeometry(100, 100, 1600, 900)

        # This will hold the path to the current workflow *.wf file
        self.current_workflow_file = None
        # This will hold the path to the directory containing the .wf file
        self.current_workflow_path = None

        self.init_ui()

        # The window is shown, but the main content area is kept disabled
        # until a workflow is properly established (new or opened).
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
        print("Action: New Workflow")
        # TODO: Implement file dialog to create a new .wf file and set paths.
        # For now, just enable the UI to show it works.
        self.main_widget.setEnabled(True)
        self.statusBar().showMessage("新工作流已创建 (未保存)", 5000)

    def open_workflow(self):
        """Handles the action for opening an existing workflow."""
        print("Action: Open Workflow")
        # TODO: Implement file dialog to open an existing .wf file and load it.
        self.main_widget.setEnabled(True)
        self.statusBar().showMessage("工作流已加载 (模拟)", 5000)

    def add_node_from_item(self, item):
        """Adds a new node to the center of the view when an item is double-clicked."""
        if not item.flags() & Qt.ItemFlag.ItemIsEnabled:
            return
        node = self.create_node_for_tool(item.text())
        if node:
            center_pos = self.view.mapToScene(self.view.viewport().rect().center())
            node.setPos(center_pos)
            self.scene.addItem(node)

    def create_node_for_tool(self, tool_name):
        """
        Creates a Node instance for a given tool name, dynamically adding sockets
        based on the tool's definition.
        """
        # This will be implemented in the next phase (decoupling)
        # For now, we assume app_root is available.
        app_root = os.path.dirname(os.path.abspath(__file__))
        tool_module_path = os.path.join(app_root, 'tools', f"{tool_name}.py")

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
                # Add default sockets if no definition is provided
                node.add_socket("in", is_output=False)
                node.add_socket("out", is_output=True)

            return node

        except Exception as e:
            QMessageBox.critical(self, "加载工具出错", f"加载工具 '{tool_name}' 时出错:\n{e}")
            return None

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
