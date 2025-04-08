import os

import cv2
import numpy as np
import pydicom
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QComboBox,
    QSpinBox, QDialogButtonBox, QPushButton, QVBoxLayout, QFileDialog, QMessageBox, QTextEdit,
)


class PatientInfoDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.mean_hu = None
        self.output_dir = "./yolo_dataset"  # 输出目录
        self.DICOM = None
        self.hu_values = None
        self.dicom_dataset = None
        self.setWindowTitle("患者信息录入")
        self.layout = QVBoxLayout()

        # 患者信息表单
        self.form_layout = QFormLayout()
        self.name_edit = QLineEdit()
        self.gender_combo = QComboBox()
        self.gender_combo.addItems(["男", "女"])
        self.age_spin = QSpinBox()
        self.age_spin.setRange(0, 120)
        self.mean_hu_edit = QLineEdit()
        self.history_edit = QTextEdit()
        self.history_edit.setPlaceholderText("请输入病史信息")

        self.form_layout.addRow("姓名:", self.name_edit)
        self.form_layout.addRow("性别:", self.gender_combo)
        self.form_layout.addRow("年龄:", self.age_spin)
        self.form_layout.addRow("HU平均值:", self.mean_hu_edit)
        self.form_layout.addRow("病史:", self.history_edit)

        # # 新增影像加载按钮
        # self.btn_load_image = QPushButton("导入医学影像")
        # self.btn_load_image.clicked.connect(self.load_medical_image)
        self.image_path = None

        # 预览标签
        # self.lbl_preview = QLabel()
        # self.lbl_preview.setFixedSize(200, 200)
        self.btn_load_photo = QPushButton("加载普通照片")
        self.btn_load_dicom = QPushButton("加载DICOM文件")
        self.btn_load_photo.clicked.connect(self.load_plain_image)
        self.btn_load_dicom.clicked.connect(self.load_dicom_file)

        # 按钮组
        self.btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.btn_box.accepted.connect(self.validate_input)
        self.btn_box.rejected.connect(self.reject)

        # 布局组合
        self.layout.addLayout(self.form_layout)
        # 调整布局
        self.layout.addWidget(self.btn_load_photo)
        self.layout.addWidget(self.btn_load_dicom)
        self.layout.addWidget(self.btn_box)

        self.setLayout(self.layout)

    def load_plain_image(self):
        """医学影像加载逻辑"""
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setNameFilters([
            "图像文件 (*.png *.jpg *.jpeg *.bmp)",
            "所有文件 (*.*)"
        ])

        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                self.image_path = selected_files[0]
                QMessageBox.information(self, "加载成功", f"已加载影像文件：{os.path.basename(self.image_path)}")

    def load_dicom_file(self):
        """医学影像加载逻辑（支持DICOM格式）"""
        """加载DICOM文件并自动填充表单"""
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setNameFilter("DICOM文件 (*.dcm)")

        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            if not selected_files:
                return

            try:
                # 读取DICOM文件
                self.DICOM = selected_files[0]
                dicom_dataset = pydicom.dcmread(self.DICOM)

                # --- 字符集处理 ---
                getattr(dicom_dataset, 'SpecificCharacterSet', 'GB18030')
                for tag in ['PatientName', 'PatientSex', 'PatientAge']:
                    if not hasattr(dicom_dataset, tag):
                        raise ValueError(f"DICOM文件缺少必要字段: {tag}")
                # --- 自动填充表单 ---
                # 姓名填充
                patient_name = str(dicom_dataset.PatientName)
                self.name_edit.setText(patient_name)

                # 性别填充
                sex_mapping = {'M': '男', 'F': '女'}
                patient_sex = sex_mapping.get(
                    getattr(dicom_dataset, 'PatientSex', ''),
                    '未知'
                )
                self.gender_combo.setCurrentText(patient_sex)

                # 年龄填充
                age = self._parse_dicom_age(dicom_dataset.PatientAge)
                if age is not None:
                    self.age_spin.setValue(age)
                else:
                    self.age_spin.clear()
                    print("年龄字段格式无效，已清空输入框")

                # --- 提取CT数据 ---
                pixel_array = dicom_dataset.pixel_array
                slope = getattr(dicom_dataset, 'RescaleSlope', 1.0)
                intercept = getattr(dicom_dataset, 'RescaleIntercept', 0)
                self.hu_values = pixel_array * slope + intercept  # 转换为HU值
                self.mean_hu = np.mean(self.hu_values)  # 存储HU值
                self.mean_hu_edit.setText(f"{self.mean_hu:.2f}")  # 显示平均HU值
                os.makedirs(self.output_dir, exist_ok=True)
                self.image_path = self._dicom_to_yolo_image(self.output_dir)  # 存储原始CT数据

                QMessageBox.information(self, "DICOM加载成功",
                                        f"患者信息已自动填充\nHU值范围：{self.hu_values.min()}~{self.hu_values.max()}")

            except Exception as e:
                QMessageBox.critical(self, "DICOM错误",
                                     f"解析失败: {str(e)}\n"
                                     f"建议检查：\n"
                                     "1. 文件是否完整\n"
                                     "2. PatientAge字段格式是否为'045Y'样式\n"
                                     "3. 必需字段(PatientName/Sex/Age)是否存在")

    def _simulate_nodule(self, hu_values, nodule_size=2, hu_value=800):
        """在CT图像中模拟磨玻璃结节"""
        # 随机生成结节中心坐标
        # 修正中心坐标生成方式（避免越界）
        center_y = np.random.randint(nodule_size, hu_values.shape[0] - nodule_size)
        center_x = np.random.randint(nodule_size, hu_values.shape[1] - nodule_size)

        # 创建圆形掩模
        y, x = np.ogrid[-center_y:hu_values.shape[0] - center_y,
               -center_x:hu_values.shape[1] - center_x]
        mask = x ** 2 + y ** 2 <= nodule_size ** 2
        hu_values[mask] = hu_value

        # 计算YOLO格式的归一化坐标[2](@ref)
        x_center = (center_x + nodule_size / 2) / hu_values.shape[1]
        y_center = (center_y + nodule_size / 2) / hu_values.shape[0]
        width = nodule_size / hu_values.shape[1]
        height = nodule_size / hu_values.shape[0]

        return hu_values, (x_center, y_center, width, height)

    def _dicom_to_yolo_image(self, output_dir):
        """DICOM转YOLO格式"""
        try:
            if self.hu_values is None:
                raise ValueError("HU值未初始化")
            # 模拟结节生成
            simulated_hu, bbox = self._simulate_nodule(self.hu_values.copy())

            # 窗宽窗位调整（肺窗设置）[4,5](@ref)
            window_center = -600
            window_width = 1500
            hu_min = window_center - window_width // 2
            hu_max = window_center + window_width // 2
            hu_clipped = np.clip(simulated_hu, hu_min, hu_max)
            normalized = ((hu_clipped - hu_min) / window_width) * 255
            image_8bit = normalized.astype(np.uint8)

            # 尺寸调整为YOLO推荐尺寸[6](@ref)
            resized = cv2.resize(image_8bit, (640, 640), interpolation=cv2.INTER_NEAREST)

            # 添加对比度增强
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(resized)

            # 保存处理后的图像
            output_path = os.path.join(output_dir, "yolo_ready.png")
            cv2.imwrite(output_path, enhanced)
            return output_path
        except Exception as e:
            QMessageBox.critical(self, "转换错误", f"DICOM处理失败：{str(e)}")
            return None

    def _parse_dicom_age(self, age_str):
        """更健壮的DICOM年龄解析方法"""
        try:
            # 处理空值或非字符串类型
            age_str = str(age_str) if age_str is not None else ""
            # 提取数字部分（兼容'045Y'、'60'等格式）
            digits = ''.join(filter(str.isdigit, age_str))
            if not digits:
                return None  # 明确返回None表示无效值
            return int(digits)
        except Exception as e:
            print(f"年龄解析错误: {str(e)}")
            return None

    def validate_input(self):
        """提交前的综合验证"""
        error = []
        if not self.name_edit.text().strip():
            error.append("患者姓名不能为空")
        if not self.image_path:
            error.append("请先导入医学影像")
        if self.age_spin.value() < 18:
            error.append("年龄需≥18岁")
        if not self.mean_hu_edit.text():
            error.append("HU值不能为空")
        if error:
            QMessageBox.warning(self, "输入错误", "\n".join(error))
            return False  # 保持对话框打开
        else:
            self.accept()  # 验证通过，关闭对话框
        return True

    def get_patient_info(self):
        """获取标准化患者信息字典"""
        return {
            # 基本信息
            'name': self.name_edit.text(),
            'gender': self.gender_combo.currentText(),
            'age': self.age_spin.value(),
            # 临床信息
            'medical_history': self._format_history(self.history_edit.toPlainText()),
            'risk_factors': self._parse_risk_factors(),
            'mean_hu': self.mean_hu_edit.text()
        }

    def _format_history(self, text):
        """病史文本格式化"""
        return '；'.join([line.strip() for line in text.split('\n') if line.strip()])

    def _parse_risk_factors(self):
        """从病史中解析危险因素（仅返回中文关键词列表）"""
        target_keywords = ['吸烟', '饮酒', '高血压', '糖尿病']
        history_text = self.history_edit.toPlainText().lower()
        return [kw for kw in target_keywords if kw in history_text]
