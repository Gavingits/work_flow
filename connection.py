from PyQt5.QtWidgets import QGraphicsPathItem
from PyQt5.QtGui import QPen, QColor, QPainterPath
from PyQt5.QtCore import Qt, QPointF

class Connection(QGraphicsPathItem):
    """
    代表两个节点端口之间的连接线。
    """
    def __init__(self, start_socket, end_socket, parent=None):
        super().__init__(parent)
        self.start_socket = start_socket
        self.end_socket = end_socket

        # 设置画笔样式
        self.pen = QPen(QColor("#bdc3c7"), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin) # Light grey color
        self.pen.setCosmetic(True) # Ensures the pen width is constant regardless of zoom
        self.setPen(self.pen)

        # 将连线绘制在节点下方
        self.setZValue(-1)

        # 将此连接注册到socket
        if self.start_socket:
            self.start_socket.connection = self
        if self.end_socket:
            self.end_socket.connection = self

        self.update_path()

    def update_path(self):
        """
        更新连接线的路径。
        使用贝塞尔曲线在起点和终点之间绘制。
        """
        if not self.start_socket or not self.end_socket:
            return

        path = QPainterPath()
        start_pos = self.start_socket.scenePos()
        end_pos = self.end_socket.scenePos()

        # 计算贝塞尔曲线的控制点，以创建平滑的S形曲线
        dx = end_pos.x() - start_pos.x()
        dy = end_pos.y() - start_pos.y()

        ctrl1 = QPointF(start_pos.x() + dx * 0.5, start_pos.y())
        ctrl2 = QPointF(end_pos.x() - dx * 0.5, end_pos.y())

        path.moveTo(start_pos)
        path.cubicTo(ctrl1, ctrl2, end_pos)

        self.setPath(path)

    def paint(self, painter, option, widget=None):
        self.update_path()
        super().paint(painter, option, widget)

    def terminate(self):
        """断开连接并从场景中移除"""
        if self.start_socket:
            self.start_socket.connection = None
        if self.end_socket:
            self.end_socket.connection = None
        if self.scene():
            self.scene().removeItem(self)
