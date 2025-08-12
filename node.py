import uuid
from PyQt5.QtWidgets import QGraphicsItem, QGraphicsTextItem
from PyQt5.QtGui import QBrush, QPen, QColor, QPainterPath, QFont
from PyQt5.QtCore import QRectF, Qt

class Socket(QGraphicsItem):
    """代表节点上的一个输入/输出端口"""
    def __init__(self, parent, is_output=False):
        super().__init__(parent)
        self.radius = 6.0
        self.is_output = is_output
        self.brush = QBrush(QColor("#FFC300"))
        self.connection = None # 持有连接到此端口的Connection对象
        self.setAcceptHoverEvents(True)

    def boundingRect(self):
        return QRectF(-self.radius, -self.radius, self.radius * 2, self.radius * 2)

    def paint(self, painter, option, widget=None):
        painter.setBrush(self.brush)
        painter.setPen(QPen(QColor("#333"), 1))
        painter.drawEllipse(int(-self.radius), int(-self.radius), int(self.radius * 2), int(self.radius * 2))

    def hoverEnterEvent(self, event):
        self.brush = QBrush(QColor("#F1C40F")) # 悬停时更亮的黄色
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.brush = QBrush(QColor("#FFC300"))
        self.update()
        super().hoverLeaveEvent(event)


class Node(QGraphicsItem):
    """
    代表工作流画布上的一个可视化节点。
    """
    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.name = name
        self.id = str(uuid.uuid4().hex)

        # 设置标志，使节点可移动、可选择，并发送几何变化信号
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

        # 定义几何尺寸
        self.width = 150
        self.height = 80
        self.header_height = 30

        # 定义颜色
        self.header_color = QColor("#F39C12")  # 橙色
        self.body_color = QColor("#34495E")    # 深蓝灰色
        self.text_color = Qt.white
        self.border_color = QColor("#2C3E50")  # 稍深的蓝灰色
        self.selection_color = QColor("#5DADE2") # 选中时的蓝色

        # 创建用于显示标题的文本项
        self.header_text = QGraphicsTextItem(self.name, self)
        self.header_text.setDefaultTextColor(self.text_color)
        font = QFont()
        font.setBold(True)
        self.header_text.setFont(font)
        # 调整文本位置使其在头部居中
        text_width = self.header_text.boundingRect().width()
        self.header_text.setPos((self.width - text_width) / 2, 5)

        # 添加端口 (Sockets)
        self.socket_input = Socket(self, is_output=False)
        self.socket_output = Socket(self, is_output=True)

        # 定位端口
        input_y = self.header_height + (self.height - self.header_height) / 2
        output_y = input_y
        self.socket_input.setPos(0, input_y)
        self.socket_output.setPos(self.width, output_y)

    def boundingRect(self):
        """返回节点的边界矩形，需要比实际绘制范围稍大以容纳边框。"""
        return QRectF(0, 0, self.width, self.height).adjusted(-1, -1, 1, 1)

    def paint(self, painter, option, widget=None):
        """绘制节点的内容。"""
        # 整体边界
        bounds = QRectF(0, 0, self.width, self.height)

        # 绘制主体背景
        painter.setBrush(self.body_color)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(bounds, 5, 5)

        # 绘制头部背景
        header_rect = QRectF(0, 0, self.width, self.header_height)
        painter.setBrush(self.header_color)
        painter.drawRect(header_rect.adjusted(0, 0, 0, -5)) # top part
        # Manually create rounded top corners
        path = QPainterPath()
        path.addRoundedRect(header_rect, 5, 5)
        path.addRect(0, self.header_height - 5, self.width, 5) # remove bottom roundness
        painter.drawPath(path)


        # 绘制边框
        if self.isSelected():
            pen = QPen(self.selection_color, 2)
        else:
            pen = QPen(self.border_color, 1)

        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(bounds, 5, 5)

    def itemChange(self, change, value):
        """当节点位置变化时，更新与其相连的线"""
        if change == QGraphicsItem.ItemPositionHasChanged and self.scene():
            # 更新输入端的连接线
            if self.socket_input.connection:
                self.socket_input.connection.update_path()
            # 更新输出端的连接线
            if self.socket_output.connection:
                self.socket_output.connection.update_path()
        return super().itemChange(change, value)

    def mouseDoubleClickEvent(self, event):
        """处理双击事件，以打开配置对话框"""
        # 事件传播: Node -> View -> MainWindow -> Dialog
        # self.scene().views()返回此场景的所有视图列表
        view = self.scene().views()[0]
        if hasattr(view, 'on_node_double_clicked'):
            view.on_node_double_clicked(self)
        super().mouseDoubleClickEvent(event)
