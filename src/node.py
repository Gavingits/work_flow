# -*- coding: utf-8 -*-
"""
Defines the graphical Node and Socket items for the workflow canvas.
"""
import uuid
import os
import json
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsTextItem, QGraphicsProxyWidget
from PyQt6.QtGui import QBrush, QPen, QColor, QPainterPath, QFont, QPolygonF
from PyQt6.QtCore import QRectF, Qt, QPointF

# --- Constants for Node Appearance ---
NODE_WIDTH = 180
NODE_HEIGHT = 100
HEADER_HEIGHT = 30
STATUS_BAR_HEIGHT = 5
SOCKET_SIZE = 10.0

# --- Status Colors ---
STATUS_COLORS = {
    'waiting': QColor("#808080"),   # Grey
    'running': QColor("#F1C40F"),   # Yellow
    'done': QColor("#2ECC71"),      # Green
    'skipped': QColor("#34495E"),   # Dark Blue/Grey
    'error': QColor("#E74C3C"),     # Red
}

class Socket(QGraphicsItem):
    """
    A Socket is a connection point on a Node.
    It has a name and a direction (input/output).
    """
    def __init__(self, parent_node, index, name, is_output=False):
        super().__init__(parent_node)
        self.node = parent_node
        self.index = index
        self.socket_name = name
        self.is_output = is_output
        self.connection = None # Holds the Connection item

        self.brush = QBrush(QColor("#D0D3D4"))
        self.pen = QPen(QColor("#2C3E50"), 1.5)

        # Arrow polygon for direction
        self.arrow = QPolygonF()
        if self.is_output:
            self.arrow.extend([QPointF(-SOCKET_SIZE/2, -SOCKET_SIZE/2), QPointF(SOCKET_SIZE/2, 0), QPointF(-SOCKET_size/2, SOCKET_SIZE/2)])
        else:
            self.arrow.extend([QPointF(SOCKET_SIZE/2, -SOCKET_SIZE/2), QPointF(-SOCKET_SIZE/2, 0), QPointF(SOCKET_SIZE/2, SOCKET_SIZE/2)])

        # Text label for the socket name
        self.label = QGraphicsTextItem(self.socket_name, self)
        font = QFont("Arial", 8)
        self.label.setFont(font)
        self.label.setDefaultTextColor(QColor("#F0F0F0"))

        label_width = self.label.boundingRect().width()
        label_height = self.label.boundingRect().height()
        if self.is_output:
            self.label.setPos(SOCKET_SIZE * -1.5 - label_width, -label_height/2)
        else:
            self.label.setPos(SOCKET_SIZE * 1.5, -label_height/2)

    def boundingRect(self):
        # Include label in bounding rect for interaction
        return self.childrenBoundingRect().united(self.shape().boundingRect())

    def shape(self):
        path = QPainterPath()
        path.addPolygon(self.arrow)
        return path

    def paint(self, painter, option, widget=None):
        painter.setBrush(self.brush)
        painter.setPen(self.pen)
        painter.drawPolygon(self.arrow)

class Node(QGraphicsItem):
    """
    A Node represents a tool instance in the workflow.
    """
    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.node_name = name
        self.id = str(uuid.uuid4().hex)
        self.config = {}

        self.inputs = []
        self.outputs = []
        self.status = 'waiting'

        # Make item movable, selectable, and notify on changes
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)

        # --- Create Child Items ---
        # Header Text
        self.header_text = QGraphicsTextItem(self.node_name, self)
        self.header_text.setDefaultTextColor(Qt.GlobalColor.white)
        font = QFont("Arial", 10, QFont.Weight.Bold)
        self.header_text.setFont(font)
        self.header_text.setPos(5, 5)

    def add_socket(self, name, is_output=False):
        """Adds an input or output socket to the node."""
        sockets = self.outputs if is_output else self.inputs
        index = len(sockets)
        socket = Socket(self, index, name, is_output)

        # Position the socket vertically
        y_pos = HEADER_HEIGHT + (index + 1) * (NODE_HEIGHT - HEADER_HEIGHT) / (len(sockets) + 2)
        x_pos = NODE_WIDTH if is_output else 0
        socket.setPos(x_pos, y_pos)

        sockets.append(socket)
        return socket

    def set_status(self, status):
        """Sets the visual status of the node."""
        if status in STATUS_COLORS:
            self.status = status
            self.update() # Trigger a repaint
        else:
            print(f"Warning: Unknown status '{status}'")

    def boundingRect(self):
        return QRectF(0, 0, NODE_WIDTH, NODE_HEIGHT)

    def paint(self, painter, option, widget=None):
        # Main Body
        body_path = QPainterPath()
        body_path.addRoundedRect(0, 0, NODE_WIDTH, NODE_HEIGHT, 5, 5)
        painter.setPen(Qt.GlobalColor.transparent)
        painter.setBrush(QColor("#2C3E50")) # Dark background
        painter.drawPath(body_path)

        # Header
        header_path = QPainterPath()
        header_path.addRoundedRect(0, 0, NODE_WIDTH, HEADER_HEIGHT, 5, 5)
        # Make bottom corners of header square
        header_path.addRect(0, HEADER_HEIGHT - 5, NODE_WIDTH, 5)
        painter.setBrush(QColor("#34495E")) # Slightly lighter header
        painter.drawPath(header_path)

        # Status Bar
        status_path = QPainterPath()
        status_path.addRoundedRect(0, HEADER_HEIGHT, NODE_WIDTH, STATUS_BAR_HEIGHT, 0, 0)
        painter.setBrush(STATUS_COLORS[self.status])
        painter.drawPath(status_path)

        # Selection Border
        if self.isSelected():
            pen = QPen(QColor("#5DADE2"), 2)
            painter.setPen(pen)
            painter.setBrush(Qt.GlobalColor.transparent)
            painter.drawRoundedRect(0, 0, NODE_WIDTH, NODE_HEIGHT, 5, 5)

    def itemChange(self, change, value):
        """On position change, update all connected connections."""
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for socket in self.inputs + self.outputs:
                if socket.connection:
                    socket.connection.update_path()
        return super().itemChange(change, value)

    def mouseDoubleClickEvent(self, event):
        """Triggers the config dialog via the view."""
        view = self.scene().views()[0]
        if hasattr(view, 'on_node_double_clicked'):
            view.on_node_double_clicked(self)
        super().mouseDoubleClickEvent(event)

    def serialize(self):
        """Returns a dictionary representation of the node for saving."""
        return {
            'id': self.id,
            'tool_name': self.node_name,
            'pos': [self.pos().x(), self.pos().y()],
        }

    def deserialize(self, data):
        """Sets the node's properties from a dictionary."""
        self.id = data['id']
        # self.node_name is set at creation, so no need to change
        self.setPos(QPointF(*data['pos']))

    def get_config_filepath(self, workflow_path):
        """Constructs the full path for this node's config file."""
        return os.path.join(workflow_path, "node_configs", f"{self.id}.json")

    def save_config(self, workflow_path):
        """Saves the node's config dictionary to its file."""
        filepath = self.get_config_filepath(workflow_path)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
            print(f"Saved config for node {self.id} to {filepath}")
        except IOError as e:
            print(f"Error saving config for node {self.id}: {e}")

    def load_config(self, workflow_path):
        """Loads the node's config dictionary from its file."""
        filepath = self.get_config_filepath(workflow_path)
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                print(f"Loaded config for node {self.id} from {filepath}")
            except (IOError, json.JSONDecodeError) as e:
                print(f"Error loading config for node {self.id}: {e}")
                self.config = {} # Reset to default on error
        else:
            self.config = {} # No config file exists yet
