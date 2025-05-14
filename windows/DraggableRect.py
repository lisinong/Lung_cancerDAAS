import os
import shutil
from PySide6.QtCore import Qt, QRectF, Signal, QObject, QPointF
from PySide6.QtGui import QPixmap, QPen, QColor, QTransform, QAction, QKeySequence
from PySide6.QtWidgets import (QMainWindow, QGraphicsView,
                               QGraphicsScene, QGraphicsRectItem, QWidget,
                               QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QFormLayout, QGraphicsItem, QPushButton,
                               QMenu, QFileDialog)


class ResizableRect(QGraphicsRectItem, QObject):
    rectModified = Signal()

    def __init__(self, x, y, w, h, orig_w, orig_h, scale_factor, offset_x, offset_y):
        QGraphicsRectItem.__init__(self, 0, 0, w, h)
        QObject.__init__(self)
        # 存储原始尺寸参数
        self.class_id = 0
        self.orig_x = x
        self.orig_y = y
        self.orig_w = w
        self.orig_h = h
        self.handle_type = None
        self.orig_width = orig_w
        self.orig_height = orig_h
        self.scale_factor = scale_factor
        self.offset_x = offset_x
        self.offset_y = offset_y
        # 设置显示尺寸限制
        self.display_min_size = 10  # 显示最小尺寸
        self.display_max_x = 512 - self.offset_x * 2  # 显示有效区域宽度
        self.display_max_y = 512 - self.offset_y * 2  # 显示有效区域高度

        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self.setPen(QPen(Qt.red, 2))
        self.setFlag(QGraphicsItem.ItemIsMovable, False)
        # 初始不可操作
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.handles = [SizeHandle(self, i) for i in range(8)]
        # 创建手柄后立即初始化位置
        self.setRect(QRectF(0, 0, w, h))  # 取消注释此行
        self.setPos(x, y)  # 确保在setRect之后设置位置

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            # 动态计算有效区域
            valid_width = self.orig_width * self.scale_factor
            valid_height = self.orig_height * self.scale_factor

            # 计算边界约束
            min_x = self.offset_x
            min_y = self.offset_y
            max_x = self.offset_x + valid_width - self.rect().width()
            max_y = self.offset_y + valid_height - self.rect().height()

            # 应用约束
            clamped_x = max(min_x, min(value.x(), max_x))
            clamped_y = max(min_y, min(value.y(), max_y))
            return QPointF(clamped_x, clamped_y)
        if change == QGraphicsItem.ItemSelectedChange:
            is_selected = bool(value)
            self.setFlag(QGraphicsItem.ItemIsMovable, is_selected)
            for handle in self.handles:
                handle.setVisible(is_selected)
                handle.setEnabled(is_selected)
        return super().itemChange(change, value)

    def get_original_coordinates(self):
        """转换回原始坐标系（用于保存）"""
        orig_x = (self.x() - self.offset_x) / self.scale_factor
        orig_y = (self.y() - self.offset_y) / self.scale_factor
        orig_w = self.rect().width() / self.scale_factor
        orig_h = self.rect().height() / self.scale_factor

        # 应用原始尺寸限制
        orig_x = max(0, min(orig_x, self.orig_width - orig_w))
        orig_y = max(0, min(orig_y, self.orig_height - orig_h))

        return orig_x, orig_y, orig_w, orig_h

    # def mouseMoveEvent(self, event):
    #     # 移动时需要转换坐标
    #     scene_pos = event.scenePos()
    #
    #     # 转换为原始坐标系的移动限制
    #     new_x = scene_pos.x() - self.offset_x
    #     new_y = scene_pos.y() - self.offset_y
    #
    #     # 计算原始坐标系中的最大允许位置
    #     orig_max_x = (self.orig_width - self.rect().width() / self.scale_factor) * self.scale_factor
    #     orig_max_y = (self.orig_height - self.rect().height() / self.scale_factor) * self.scale_factor
    #
    #     # 应用显示坐标系的限制
    #     display_x = max(self.offset_x, min(new_x, orig_max_x + self.offset_x))
    #     display_y = max(self.offset_y, min(new_y, orig_max_y + self.offset_y))
    #
    #     self.setPos(display_x, display_y)
    #     self.rectModified.emit()

    def setRect(self, rect):
        super().setRect(rect)
        for handle in self.handles:
            handle.updatePosition()  # 尺寸变化时更新手柄位置


class SizeHandle(QGraphicsRectItem):
    def __init__(self, parent, handle_type):
        super().__init__(-4, -4, 6, 6, parent)
        self.handle_type = handle_type
        self.setBrush(QColor(0, 0, 255))  # 蓝色
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.setVisible(False)  # 默认不可见

    def mouseMoveEvent(self, event):
        if not self.isEnabled():
            return

        parent = self.parentItem()
        if not isinstance(parent, ResizableRect):
            return

        # 获取当前矩形和鼠标位置
        rect = parent.rect()
        new_pos = parent.mapFromScene(event.scenePos())
        new_rect = QRectF(rect)  # 复制原始矩形

        # 根据手柄类型限制移动方向
        handle_type = self.handle_type
        if handle_type == 0:  # 左上：可自由调整
            new_rect.setTopLeft(new_pos)
        elif handle_type == 1:  # 上中：仅垂直调整高度
            new_rect.setTop(new_pos.y())
        elif handle_type == 2:  # 右上：可自由调整
            new_rect.setTopRight(new_pos)
        elif handle_type == 3:  # 左中：仅水平调整宽度
            new_rect.setLeft(new_pos.x())
        elif handle_type == 4:  # 右中：仅水平调整宽度
            new_rect.setRight(new_pos.x())
        elif handle_type == 5:  # 左下：可自由调整
            new_rect.setBottomLeft(new_pos)
        elif handle_type == 6:  # 下中：仅垂直调整高度
            new_rect.setBottom(new_pos.y())
        elif handle_type == 7:  # 右下：可自由调整
            new_rect.setBottomRight(new_pos)

        # 应用最小尺寸约束
        new_rect = new_rect.normalized()
        new_rect.setWidth(max(10, new_rect.width()))
        new_rect.setHeight(max(10, new_rect.height()))

        # 根据手柄类型同步位置（仅角部手柄需要移动父项）
        if handle_type in [0, 2, 5, 7]:
            dx = new_rect.x() - rect.x()
            dy = new_rect.y() - rect.y()
            parent.setPos(parent.x() + dx, parent.y() + dy)
            new_rect.moveTo(0, 0)  # 重置相对位置

        parent.setRect(new_rect)
        parent.rectModified.emit()
        event.accept()

    def updatePosition(self):
        rect = self.parentItem().rect()
        handle_type = self.handle_type
        pos_map = {
            0: rect.topLeft(),  # 左上
            1: QPointF(rect.center().x(), rect.top()),  # 上中
            2: rect.topRight(),  # 右上
            3: QPointF(rect.left(), rect.center().y()),  # 左中
            4: QPointF(rect.right(), rect.center().y()),  # 右中
            5: rect.bottomLeft(),  # 左下
            6: QPointF(rect.center().x(), rect.bottom()),  # 下中
            7: rect.bottomRight()  # 右下
        }
        self.setPos(pos_map[handle_type])  # 中心偏移5px


class AnnotationScene(QGraphicsScene):
    drawingFinished = Signal(QRectF)

    def __init__(self):
        super().__init__()
        self.drawing = False
        self.start_pos = QPointF()
        self.current_rect = None

    def mousePressEvent(self, event):
        # 优先处理已有项的选中
        if event.button() == Qt.LeftButton:
            items = self.items(event.scenePos())
            if len(items) > 0 and isinstance(items[0], (ResizableRect, SizeHandle)):
                # 如果有选中项则不开始绘制新矩形
                super().mousePressEvent(event)
                return

        # 无选中项时开始绘制新矩形
        if event.button() == Qt.LeftButton and not self.drawing:
            self.drawing = True
            self.start_pos = event.scenePos()
            self.current_rect = QGraphicsRectItem()
            self.current_rect.setPen(QPen(Qt.red, 2))
            self.addItem(self.current_rect)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.drawing:
            # 更新绘制中的矩形
            end_pos = event.scenePos()
            rect = QRectF(self.start_pos, end_pos).normalized()
            self.current_rect.setRect(rect)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.drawing:
            # 完成绘制并创建可调整的矩形
            self.drawing = False
            rect = self.current_rect.rect()
            self.removeItem(self.current_rect)
            self.drawingFinished.emit(rect)
        super().mouseReleaseEvent(event)


class YoloWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.coord_edits = None
        self.class_id_edit = None
        self.current_image_path = None
        self.h_edit = None
        self.w_edit = None
        self.y_edit = None
        self.scene = None
        self.view = None
        self.x_edit = None
        self.img_width = 0
        self.img_height = 0
        # 新增缩放相关属性
        self.orig_width = 0  # 原始图像宽度
        self.orig_height = 0  # 原始图像高度
        self.scale_factor = 1.0  # 缩放比例
        self.offset_x = 0  # X轴偏移量
        self.offset_y = 0  # Y轴偏移量
        self.class_id = 0
        self.center_x = 0
        self.center_y = 0
        self.width = 0
        self.height = 0
        self.rects = []
        self.index = 0
        # 新增删除相关功能
        self.delete_action = QAction("删除", self)
        self.delete_action.setShortcut(QKeySequence.Delete)
        self.delete_action.triggered.connect(self.delete_selected_rects)
        self.addAction(self.delete_action)
        self.initUI()

    def initUI(self):
        self.setWindowTitle("修正数据标注工具")
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        # 左侧视图区域
        self.view = QGraphicsView()
        self.scene = AnnotationScene()
        self.view.setScene(self.scene)
        layout.addWidget(self.view, 75)

        # 右侧控制面板
        panel = self.createControlPanel()
        layout.addWidget(panel, 25)

        # 信号连接
        self.scene.drawingFinished.connect(self.createResizableRect)
        self.view.wheelEvent = self.customWheelEvent
        self.scene.selectionChanged.connect(self.updateCoordDisplay)

    def createControlPanel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # 坐标显示
        form_layout = QFormLayout()
        self.x_edit = QLineEdit()
        self.y_edit = QLineEdit()
        self.w_edit = QLineEdit()
        self.h_edit = QLineEdit()
        self.class_id_edit = QLineEdit()
        self.coord_edits = [self.x_edit, self.y_edit, self.w_edit, self.h_edit]
        for edit in self.coord_edits + [self.class_id_edit]:
            edit.editingFinished.connect(self.on_input_changed)  # 焦点离开时触发
        form_layout.addRow(QLabel("X:"), self.x_edit)
        form_layout.addRow(QLabel("Y:"), self.y_edit)
        form_layout.addRow(QLabel("宽度:"), self.w_edit)
        form_layout.addRow(QLabel("高度:"), self.h_edit)
        form_layout.addRow(QLabel("类别:"), self.class_id_edit)

        layout.addLayout(form_layout)

        # 保存按钮
        save_button = QPushButton("保存标注")
        save_button.clicked.connect(self.saveLabels)
        layout.addWidget(save_button)
        # 添加删除按钮
        delete_btn = QPushButton("删除选中标注框")
        delete_btn.clicked.connect(self.delete_selected_rects)
        layout.addWidget(delete_btn)
        return panel

    def delete_selected_rects(self):
        """删除所有选中的标注框"""
        for item in self.scene.selectedItems():
            if isinstance(item, ResizableRect):
                # 先移除所有关联的手柄
                for handle in item.handles:
                    self.scene.removeItem(handle)
                # 再移除矩形本身
                self.scene.removeItem(item)
        self.updateCoordDisplay()  # 更新表单显示

    def contextMenuEvent(self, event):
        """右键菜单删除"""
        menu = QMenu(self)
        delete_action = menu.addAction("删除选中框")
        delete_action.triggered.connect(self.delete_selected_rects)
        menu.exec_(event.globalPos())

    def keyPressEvent(self, event):
        """快捷键支持"""
        if event.key() == Qt.Key_Delete:
            self.delete_selected_rects()
        super().keyPressEvent(event)

    def createResizableRect(self, rect):
        """简化坐标转换逻辑"""
        # 直接使用场景坐标系（临时方案）
        try:
            if self.class_id_edit.text() != "" or self.class_id_edit.text() is not None:
                self.class_id = int(self.class_id_edit.text())
            res_rect = ResizableRect(
                rect.x(), rect.y(),
                rect.width(), rect.height(),
                self.orig_width, self.orig_height,
                self.scale_factor,
                self.offset_x,
                self.offset_y,
            )
            res_rect.rectModified.connect(self.updateCoordDisplay)
            self.scene.addItem(res_rect)
        except Exception as e:
            print(f"创建矩形框失败: {str(e)}")

    def on_input_changed(self):
        """输入变更响应函数"""
        # 验证并获取新值
        try:
            new_x = float(self.x_edit.text())
            new_y = float(self.y_edit.text())
            new_w = float(self.w_edit.text())
            new_h = float(self.h_edit.text())
            class_id = int(self.class_id_edit.text())
        except ValueError:
            self.statusBar().showMessage("输入格式错误", 3000)
            return

        # 获取当前选中项
        selected = None
        for item in self.scene.items():
            if isinstance(item, ResizableRect):
                # 检查是否符合选中矩形框的坐标
                if item.isSelected():
                    selected = item
                    break

        if not selected:
            return

        rect_item = selected

        # 更新显示坐标系位置和尺寸
        rect_item.setPos(new_x, new_y)

        rect_item.setRect(QRectF(0, 0, new_w, new_h))

        # 更新存储数据
        rect_item.class_id = class_id

        # 刷新显示
        self.scene.update()

    def updateCoordDisplay(self):
        """更新坐标显示"""
        selected = self.scene.selectedItems()
        # 清空表单
        self.x_edit.clear()
        self.y_edit.clear()
        self.w_edit.clear()
        self.h_edit.clear()
        self.class_id_edit.clear()

        # 仅处理选中的ResizableRect
        rect_items = [item for item in selected if isinstance(item, ResizableRect)]
        if rect_items:
            rect_item = rect_items[0]
            # 获取原始坐标系参数
            x = rect_item.x()
            y = rect_item.y()
            w = rect_item.rect().width()
            h = rect_item.rect().height()
            # 获取类别
            class_id = rect_item.class_id
            # 更新表单
            self.x_edit.setText(f"{x:.1f}")
            self.y_edit.setText(f"{y:.1f}")
            self.w_edit.setText(f"{w:.1f}")
            self.h_edit.setText(f"{h:.1f}")
            self.class_id_edit.setText(str(class_id))

    def customWheelEvent(self, event):
        """支持Ctrl+滚轮缩放视图"""
        if event.modifiers() & Qt.ControlModifier:
            factor = 1.2 if event.angleDelta().y() > 0 else 1 / 1.2
            self.view.scale(factor, factor)
            self.scale_factor *= factor
        else:
            super().wheelEvent(event)

    def on_scale_changed(self, scale_factor):
        """处理视图缩放事件"""
        self.scale_factor = scale_factor
        self.view.setTransform(QTransform().scale(scale_factor, scale_factor))

    def loadImage(self, path, yolos):
        """加载医学影像及关联标注文件"""
        try:
            # 清空场景
            self.scene.clear()
            self.img_width = 0
            self.img_height = 0

            # 加载图片
            if not os.path.exists(path):
                raise FileNotFoundError(f"图片文件不存在: {path}")

            pixmap = QPixmap(path)
            if pixmap.isNull():
                raise ValueError("不支持的图片格式")

            if not yolos:
                raise ValueError("请提供YOLO格式的标注文件")
            # 存储原始尺寸
            self.orig_width = pixmap.width()
            self.orig_height = pixmap.height()

            # 计算缩放比例 (保持宽高比)
            target_size = 512
            self.scale_factor = min(target_size / self.orig_width,
                                    target_size / self.orig_height)
            # 生成缩放后的图像
            scaled_pixmap = pixmap.scaled(
                int(self.orig_width * self.scale_factor),
                int(self.orig_height * self.scale_factor),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.current_image_path = path
            # 计算居中偏移量
            self.offset_x = (target_size - scaled_pixmap.width()) // 2
            self.offset_y = (target_size - scaled_pixmap.height()) // 2

            # 创建带偏移量的场景
            self.scene.setSceneRect(0, 0, target_size, target_size)
            pixmap_item = self.scene.addPixmap(scaled_pixmap)
            pixmap_item.setPos(self.offset_x, self.offset_y)

            # 加载标签（需要坐标转换）
            for yolo in yolos:
                # 获取YOLO格式数据
                center_x = yolo['center_x'] * self.orig_width
                center_y = yolo['center_y'] * self.orig_height
                width = yolo['width'] * self.orig_width
                height = yolo['height'] * self.orig_height
                class_id = yolo['cls']
                index = yolo['index']
                # 转换为缩放后的显示坐标
                display_x = (center_x - width / 2) * self.scale_factor + self.offset_x
                display_y = (center_y - height / 2) * self.scale_factor + self.offset_y
                display_w = width * self.scale_factor
                display_h = height * self.scale_factor

                # 创建可调整矩形（使用显示坐标）
                rect_item = ResizableRect(
                    display_x, display_y,
                    display_w, display_h,
                    self.orig_width,
                    self.orig_height,
                    self.scale_factor,
                    self.offset_x,
                    self.offset_y
                )
                rect_item.setToolTip(f"类别: {class_id}")
                rect_item.class_id = class_id  # 存储类别信息
                self.class_id_edit.setText(str(class_id))  # 更新类别输入框
                rect_item.rectModified.connect(self.updateCoordDisplay)
                self.scene.addItem(rect_item)

            # 重置视图
            self.view.setFixedSize(512, 512)
            self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
            return True

        except Exception as e:
            print(f"加载失败: {str(e)}")
            self.statusBar().showMessage(f"错误: {str(e)}", 5000)
            return False

    def saveLabels(self):
        """保存为YOLO格式标签文件"""
        if not self.orig_width or not self.orig_height:
            self.statusBar().showMessage("未加载有效图片", 3000)
            return

        label_path = QFileDialog.getExistingDirectory(self, "选择存储位置")
        if not label_path:
            self.statusBar().showMessage("未选择存储位置", 3000)
            return

        try:
            # 创建 images 和 labels 文件夹
            images_folder = os.path.join(label_path, "images")
            labels_folder = os.path.join(label_path, "labels")
            os.makedirs(images_folder, exist_ok=True)
            os.makedirs(labels_folder, exist_ok=True)

            # 保存图片到 images 文件夹
            image_name = os.path.basename(self.current_image_path)
            image_dest_path = os.path.join(images_folder, image_name)
            if not os.path.exists(image_dest_path):
                shutil.copy(self.current_image_path, image_dest_path)

            # 保存标签到 labels 文件夹
            annotations = []
            for item in self.scene.items():
                if isinstance(item, ResizableRect):
                    # 获取原始坐标
                    x, y, w, h = item.get_original_coordinates()

                    # 转换为YOLO格式
                    x_center = (x + w / 2) / self.orig_width
                    y_center = (y + h / 2) / self.orig_height
                    width = w / self.orig_width
                    height = h / self.orig_height
                    if item.class_id is None:
                        self.statusBar().showMessage("类别ID不能为空", 3000)
                        return
                    line = f"{item.class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}"
                    annotations.append(line)

            label_file_path = os.path.join(labels_folder, os.path.splitext(image_name)[0] + ".txt")
            with open(label_file_path, 'w') as f:
                f.write("\n".join(annotations))

            self.statusBar().showMessage(f"成功保存{len(annotations)}个标注到{label_path}", 5000)
            return True

        except Exception as e:
            print(f"保存失败: {str(e)}")
            self.statusBar().showMessage(f"保存失败: {str(e)}", 5000)
            return False
