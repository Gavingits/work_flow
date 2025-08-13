# -*- coding: utf-8 -*-
"""
Defines the custom QGraphicsView for the workflow canvas.
"""
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsLineItem
from PyQt6.QtGui import QPainter, QPen, QColor
from PyQt6.QtCore import Qt, QLineF

from node import Socket
from connection import Connection

class WorkflowGraphicsView(QGraphicsView):
    """
    Custom view for the workflow canvas that handles interactions like
    drag-and-drop to create nodes and drawing connections.
    """
    def __init__(self, scene: QGraphicsScene, parent=None):
        super().__init__(scene, parent)
        self.setAcceptDrops(True)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)

        self.line_to_draw = None
        self.start_socket = None

    def get_socket_at(self, pos):
        """Helper to find a socket at a given position."""
        items = self.items(pos)
        for item in items:
            if isinstance(item, Socket):
                return item
        return None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            socket = self.get_socket_at(event.pos())
            if socket:
                self.start_socket = socket
                self.line_to_draw = QGraphicsLineItem()
                self.line_to_draw.setPen(QPen(QColor("#a9a9a9"), 2, Qt.PenStyle.DashLine))
                self.scene().addItem(self.line_to_draw)

                start_pos = self.start_socket.mapToScene(self.start_socket.boundingRect().center())
                self.line_to_draw.setLine(QLineF(start_pos, start_pos))
                event.accept()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.line_to_draw:
            line = self.line_to_draw.line()
            line.setP2(self.mapToScene(event.pos()))
            self.line_to_draw.setLine(line)
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.line_to_draw and self.start_socket:
            if self.line_to_draw.scene():
                self.scene().removeItem(self.line_to_draw)
            self.line_to_draw = None

            end_socket = self.get_socket_at(event.pos())

            # --- Validate Connection ---
            # 1. Must end on a socket
            # 2. Sockets must not be on the same node
            # 3. Sockets must have different types (input vs output)
            # 4. Sockets must not already be connected
            if (end_socket and self.start_socket.node != end_socket.node and
                    self.start_socket.is_output != end_socket.is_output and
                    not self.start_socket.connection and not end_socket.connection):

                # Ensure connection is always from output to input
                start_sock = self.start_socket if self.start_socket.is_output else end_socket
                end_sock = end_socket if self.start_socket.is_output else self.start_socket

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

            main_win = self.window()
            if hasattr(main_win, 'create_node_for_tool'):
                node = main_win.create_node_for_tool(tool_name)
                if node:
                    self.scene().addItem(node)
                    node.setPos(drop_position)
                    print(f"通过拖拽添加了节点: {tool_name}")

            event.acceptProposedAction()
        else:
            super().dropEvent(event)
