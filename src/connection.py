# -*- coding: utf-8 -*-
"""
Defines the graphical Connection item for the workflow canvas.
"""

from PyQt6.QtWidgets import QGraphicsPathItem
from PyQt6.QtGui import QPen, QColor, QPainterPath
from PyQt6.QtCore import Qt, QPointF

class Connection(QGraphicsPathItem):
    """
    A Connection represents a link between two Sockets.
    """
    def __init__(self, start_socket, end_socket, parent=None):
        super().__init__(parent)
        self.start_socket = start_socket
        self.end_socket = end_socket

        # A connection can only be attached to one input and one output
        self.start_socket.connection = self
        self.end_socket.connection = self

        self.pen = QPen(QColor("#a9a9a9"), 2)
        self.pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        self.setPen(self.pen)

        # Draw below nodes but above background
        self.setZValue(-1.0)

        self.update_path()

    def update_path(self):
        """
        Calculates and sets the Bezier curve path between the start and end sockets.
        """
        start_pos = self.start_socket.mapToScene(self.start_socket.boundingRect().center())
        end_pos = self.end_socket.mapToScene(self.end_socket.boundingRect().center())

        path = QPainterPath(start_pos)

        # Control points for the Bezier curve
        dx = end_pos.x() - start_pos.x()
        dy = end_pos.y() - start_pos.y()

        ctrl1 = QPointF(start_pos.x() + dx * 0.5, start_pos.y())
        ctrl2 = QPointF(end_pos.x() - dx * 0.5, end_pos.y())

        path.cubicTo(ctrl1, ctrl2, end_pos)
        self.setPath(path)

    def terminate(self):
        """Removes the connection and cleans up references."""
        if self.start_socket:
            self.start_socket.connection = None
        if self.end_socket:
            self.end_socket.connection = None

        if self.scene():
            self.scene().removeItem(self)
