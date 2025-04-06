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
        self.history_edit = QTextEdit()
        self.history_edit.setPlaceholderText("请输入病史信息")

        self.form_layout.addRow("姓名:", self.name_edit)
        self.form_layout.addRow("性别:", self.gender_combo)
        self.form_layout.addRow("年龄:", self.age_spin)
        self.form_layout.addRow("病史:", self.history_edit)

        # 新增影像加载按钮
        self.btn_load_image = QPushButton("导入医学影像")
        self.btn_load_image.clicked.connect(self.load_medical_image)
        self.image_path = None

        # 预览标签
        # self.lbl_preview = QLabel()
        # self.lbl_preview.setFixedSize(200, 200)

        # 按钮组
        self.btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.btn_box.accepted.connect(self.validate_input)
        self.btn_box.rejected.connect(self.reject)

        # 布局组合
        self.layout.addLayout(self.form_layout)
        self.layout.addWidget(self.btn_load_image)
        # self.layout.addWidget(self.lbl_preview)
        self.layout.addWidget(self.btn_box)

        self.setLayout(self.layout)

    # def load_medical_image(self):
    #     """医学影像加载逻辑"""
    #     file_dialog = QFileDialog(self)
    #     file_dialog.setFileMode(QFileDialog.ExistingFile)
    #     file_dialog.setNameFilters([
    #         "图像文件 (*.png *.jpg *.jpeg *.bmp)",
    #         "所有文件 (*.*)"
    #     ])
    #
    #     if file_dialog.exec():
    #         selected_files = file_dialog.selectedFiles()
    #         if not selected_files:
    #             return
    #         self.image_path = selected_files[0]
    #         QMessageBox.information(self, "加载成功", f"已加载影像文件：{os.path.basename(self.image_path)}")
    def load_medical_image(self):
        """医学影像加载逻辑（支持DICOM格式）"""
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setNameFilters([
            "DICOM文件 (*.dcm)",
            "所有文件 (*.*)"
        ])

        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            if not selected_files:
                return

            try:
                # 读取DICOM文件
                self.image_path = selected_files[0]
                dicom_dataset = pydicom.dcmread(self.image_path)

                # 提取患者信息
                patient_info = {
                    'name': getattr(dicom_dataset, 'PatientName', '未知'),
                    'sex': getattr(dicom_dataset, 'PatientSex', '未知'),
                    'age': self._parse_dicom_age(getattr(dicom_dataset, 'PatientAge', '')),
                    'hu_values': None
                }

                # 获取HU值（可能需要Rescale Slope/Intercept）
                pixel_array = dicom_dataset.pixel_array
                slope = getattr(dicom_dataset, 'RescaleSlope', 1)
                intercept = getattr(dicom_dataset, 'RescaleIntercept', 0)
                hu_values = pixel_array * slope + intercept

                patient_info['hu_values'] = hu_values

                # 存储DICOM数据集供后续使用
                self.dicom_dataset = dicom_dataset

                # 显示加载信息
                info_message = (
                    f"成功加载DICOM文件：{os.path.basename(self.image_path)}\n"
                    f"患者姓名：{patient_info['name']}\n"
                    f"性别：{patient_info['sex']}\n"
                    f"年龄：{patient_info['age']}\n"
                    f"HU值范围：{np.min(hu_values)} ~ {np.max(hu_values)}"
                )

                QMessageBox.information(self, "加载成功", info_message)

            except Exception as e:
                QMessageBox.critical(self, "读取错误",
                                     f"DICOM文件解析失败：{str(e)}")
                return

    def _parse_dicom_age(self, age_str):
        """解析DICOM格式的年龄字符串（例如：'030Y' -> 30）"""
        if not age_str:
            return "未知"
        try:
            # 提取数字部分（DICOM格式通常为"###Y"）
            age = int(''.join(filter(str.isdigit, age_str)))
            return f"{age}岁"
        except:
            return "未知"

    def validate_input(self):
        """提交前的综合验证"""
        error = []
        if not self.name_edit.text().strip():
            error.append("患者姓名不能为空")
        if not self.image_path:
            error.append("请先导入医学影像")
        if self.age_spin.value() < 18:
            error.append("年龄需≥18岁")
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
            'risk_factors': self._parse_risk_factors()
        }

    def _format_history(self, text):
        """病史文本格式化"""
        return '；'.join([line.strip() for line in text.split('\n') if line.strip()])

    def _parse_risk_factors(self):
        """从病史中解析危险因素（仅返回中文关键词列表）"""
        target_keywords = ['吸烟', '饮酒', '高血压', '糖尿病']
        history_text = self.history_edit.toPlainText().lower()
        return [kw for kw in target_keywords if kw in history_text]
