import os

import numpy as np
import pydicom
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QComboBox,
    QSpinBox, QDialogButtonBox, QPushButton, QVBoxLayout, QFileDialog, QMessageBox, QTextEdit,
)


class PatientInfoDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
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
                self.image_path = selected_files[0]
                dicom_dataset = pydicom.dcmread(self.image_path)

                # --- 字符集处理 ---
                encoding = getattr(dicom_dataset, 'SpecificCharacterSet', 'GB18030')

                # --- 自动填充表单 ---
                # 姓名填充
                patient_name = str(dicom_dataset.PatientName)
                self.name_edit.setText(patient_name)

                # 性别填充
                sex_mapping = {'M': '男', 'F': '女'}
                patient_sex = sex_mapping.get(getattr(dicom_dataset, 'PatientSex', 'M'), '未知')
                index = self.gender_combo.findText(patient_sex)
                self.gender_combo.setCurrentIndex(index if index != -1 else 0)

                # 年龄填充
                age_str = getattr(dicom_dataset, 'PatientAge', '')
                age = self._parse_dicom_age(age_str)
                if age != "未知":
                    self.age_spin.setValue(int(age))

                # --- 提取CT数据 ---
                pixel_array = dicom_dataset.pixel_array
                slope = getattr(dicom_dataset, 'RescaleSlope', 1.0)
                intercept = getattr(dicom_dataset, 'RescaleIntercept', 0)
                self.hu_values = pixel_array * slope + intercept  # 转换为HU值
                self.mean_hu = np.mean(self.hu_values)  # 存储HU值
                self.mean_hu_edit.setText(f"{self.mean_hu:.2f}")  # 显示平均HU值
                self.ct_image_data = pixel_array  # 存储原始CT数据

                QMessageBox.information(self, "DICOM加载成功",
                                        f"患者信息已自动填充\nHU值范围：{self.hu_values.min()}~{self.hu_values.max()}")

            except Exception as e:
                QMessageBox.critical(self, "错误", f"DICOM解析失败：{str(e)}")

    def _parse_dicom_age(self, age_str):
        """返回整数年龄（非字符串）"""
        if not age_str:
            return None
        try:
            return int(''.join(filter(str.isdigit, age_str)))
        except:
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
