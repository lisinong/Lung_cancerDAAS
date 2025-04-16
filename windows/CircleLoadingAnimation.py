from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import QWidget, QGraphicsBlurEffect


class CircleLoadingAnimation(QWidget):
    """加载动画
    progress = CircleProgressBar(600)
    progress.start()  # 开始显示加载动画
    # do something ...
    progress.stop()  # 停止显示
    """

    def __init__(self, size=100, color=QColor(24, 189, 155), clockwise=True, parent=None):
        super().__init__()
        self.setAttribute(Qt.WA_TranslucentBackground)  # 透明效果
        self.setWindowFlags(Qt.FramelessWindowHint  # 无边框
                            | Qt.BypassWindowManagerHint
                            | Qt.Tool  # 随父窗口关闭
                            | Qt.WindowStaysOnTopHint)  # 置顶
        self.setFixedSize(size, size)
        # self.setParent(parent)  # 设置父窗口
        self.angle = 0
        self.clockwise = clockwise  # 顺时针方向
        self.Color = color  # 圆圈颜色

        self.delta = 36
        self._timer = QTimer(self, timeout=self.update)  # 计时器，定时刷新界面

    def start(self):
        self._timer.start(100)  # 0.1s更新刷新一次界面
        self.show()  # 显示动画窗口

    def stop(self):
        self._timer.stop()  # 停止计时器
        self.close()  # 关闭动画窗口

    def paintEvent(self, event):
        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing)
        qp.translate(self.width() / 2, self.height() / 2)
        side = min(self.width(), self.height())
        qp.scale(side / 100.0, side / 100.0)
        qp.rotate(self.angle)
        qp.save()
        qp.setPen(Qt.NoPen)
        color = self.Color.toRgb()
        for i in range(11):
            color.setAlphaF(1.0 * i / 10)
            qp.setBrush(color)
            qp.drawEllipse(30, -10, 20, 20)
            qp.rotate(36)
        qp.restore()
        self.angle += self.delta if self.clockwise else -self.delta
        self.angle %= 360


class FrostedGlassWidget(QWidget):
    """实现磨砂玻璃效果的容器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.blur_radius = 50  # 模糊强度

    def paintEvent(self, event):
        # 绘制磨砂玻璃效果
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 创建透明层
        path = QPainterPath()
        path.addRoundedRect(self.rect(), 10, 10)  # 圆角半径

        # 半透明背景
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 255, 180))  # 基础透明度
        painter.drawPath(path)

        # 应用模糊效果（性能要求较高时可注释掉）
        blur = QGraphicsBlurEffect()
        blur.setBlurRadius(self.blur_radius)
        self.setGraphicsEffect(blur)
