# This Python file uses the following encoding: utf-8
import math
import sys
from collections import defaultdict

import cv2
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QGraphicsScene, QGraphicsPixmapItem, \
    QTableWidgetItem
from PySide6.QtGui import QPixmap, QPen, QColor
from PySide6.QtCore import Qt
from ultralytics import YOLO

from PatientInfoDialog import PatientInfoDialog
from ReportExportDialog import ReportExportDialog
from RiskConfigDialog import RiskConfigDialog
from MorphologyAnalyzer import MorphologyAnalyzer
from ui_form import Ui_MainWindow


# Important:
# You need to run the following command to generate the ui_form.py file
#     pyside6-uic form.ui -o ui_form.py, or
#     pyside2-uic form.ui -o ui_form.py


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._export_available = False
        self._detect_available = False
        self.nodules = None
        self.advice = None
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        # 新增患者信息存储
        self.patient_info = {
            'name': '未录入',
            'gender': '男',
            'age': 0,
            'medical_history': ''
        }

        # 初始化医学参数
        self.default_params = {
            'main_weight': 0.7,
            'n_status': "N0",
            'm_status': "M0",
            'mm_per_pixel': 0.5,
            'thresholds': {
                'low': 3,
                'medium': 5,
                'high': 7
            },
            # 患者特征参数
            'patient': {
                'age_weights': {'<45': 0.5, '45-54': 1.5, '55-69': 2.0, '≥70': 3.0},
                'gender_weights': {'男': 1.5, '女': 0.5},
                'history_keywords': {'吸烟': 2.0, '家族史': 1.5}
            },
            'nodules': {
                'size': [(5, 0), (10, 1), (20, 2), (30, 3), (float('inf'), 4)],
                'type': {'ggo': 1, 'part-solid': 2, 'solid': 3},
                'location': {'upper': 1, 'middle': 0.5, 'lower': 0},  # 上肺叶风险更高[6](@ref)
                'morphology': {'spiculation': 2, 'lobulation': 1.5}

            }
        }
        self.current_params = self.default_params.copy()

        header = self.ui.noduleTable.horizontalHeader()
        header.setMinimumSectionSize(80)  # 最小列宽
        header.setDefaultAlignment(Qt.AlignHCenter | Qt.AlignVCenter)  # 居中对齐
        header.setFixedHeight(36)  # 固定高度
        # 设置特定列宽
        self.ui.noduleTable.setColumnWidth(0, 60)  # 编号列
        self.ui.noduleTable.setColumnWidth(1, 100)  # 直径列
        self.ui.noduleTable.setColumnWidth(2, 80)  # 类型列
        self.ui.noduleTable.setColumnWidth(3, 80)  # 边界列
        header.setStretchLastSection(True)  # 最后一列自动拉伸

        # 按钮初始化状态
        self.current_image_path = None  # 当前加载的影像路径
        self.patient_info = None  # 存储患者信息
        self._update_ui_state()  # 更新UI状态

        # 新增按钮
        self.ui.startDetectionBtn.clicked.connect(self.start_detection)
        self.ui.addPatientBtn.clicked.connect(self.show_patient_dialog)
        self.ui.exportBtn.clicked.connect(self.show_export_dialog)
        self.ui.paramButton.clicked.connect(self.show_config_dialog)

    def _update_ui_state(self):
        """统一更新界面状态"""
        # 按钮状态初始化
        self.ui.startDetectionBtn.setEnabled(self._detect_available)
        self.ui.exportBtn.setEnabled(self._export_available)

        # 更新提示信息
        if not self._detect_available:
            self.ui.startDetectionBtn.setToolTip("请先加载医学影像")
        else:
            self.ui.startDetectionBtn.setToolTip("点击开始检测")

        #更新导出按钮提示
        if not self._export_available:
            self.ui.exportBtn.setToolTip("请先完成检测")
        else:
            self.ui.exportBtn.setToolTip("点击导出报告")

    def show_config_dialog(self):
        """显示参数配置对话框（更新版）"""
        dialog = RiskConfigDialog(self)

        # 加载当前参数到对话框
        dialog.load_params(self.current_params)

        if dialog.exec():
            # 获取新参数并验证
            new_params = dialog.get_params()
            # 阈值验证
            thresholds = new_params['thresholds']
            if not (thresholds['low'] < thresholds['medium'] < thresholds['high']):
                QMessageBox.warning(self, "参数错误", "阈值必须满足：低危 < 中危 < 高危")
                return

            # 年龄分段完整性验证
            age_weights = new_params['patient']['age_weights']
            required_age_keys = ['<45', '45-54', '55-69', '≥70']
            if any(k not in age_weights for k in required_age_keys):
                QMessageBox.warning(self, "参数错误", "年龄分段配置不完整")
                return

            # 更新参数并刷新UI
            self.current_params = new_params
            self.ui.label.setText(f"单位像素换算系数: {new_params['mm_per_pixel']} mm/px")
            QMessageBox.information(self, "成功", "参数更新完成")

    def show_patient_dialog(self):
        """显示患者信息对话框"""
        dialog = PatientInfoDialog(self)
        if dialog.exec():
            # 保存患者信息
            self.patient_info = dialog.get_patient_info()
            self.current_image_path = dialog.image_path
            # 显示原始图像
            self.show_image(self.current_image_path)
            self._detect_available = True
            self._update_ui_state()  # 更新UI状态
            QMessageBox.information(self, "就绪", "患者信息与影像加载完成，可开始检测")

    def start_detection(self):
        """开始检测按钮的新逻辑"""
        if not self.current_image_path:
            QMessageBox.critical(self, "错误", "尚未加载医学影像！")
            return
        try:
            # 执行原有处理流程
            self.process_image(self.current_image_path)
            self._export_available = True
            self._update_ui_state()  # 更新UI状态
        except Exception as e:
            QMessageBox.critical(self, "检测失败", f"影像处理错误：{str(e)}")
            self._export_available = False

    def show_export_dialog(self):
        """生成导出数据并显示导出对话框"""
        if self._export_available:
            report_data = {
                'patient_info': self.patient_info,
                'nodule_features': self.generate_features_text(self.nodules),
                'stage_prediction': self.predict_tnm_stage(self.nodules),
                'clinical_advice': self.advice
            }
            dialog = ReportExportDialog(report_data, self)
            dialog.exec()
            QMessageBox.information(self, "导出", "报告导出成功")
        else:
            QMessageBox.warning(self, "错误", "请先完成检测")

    def generate_features_text(self, nodules):
        """生成结构化结节特征报告（含主结节标注）"""
        # 统一输入格式（处理单个结节情况）
        if isinstance(nodules, dict):
            nodules = [nodules]
            is_single = True
        else:
            is_single = False
        if not nodules:
            return "未检测到明显结节"

        # 自动确定主结节（若输入为单个结节则自动标记）
        main_nodule = nodules[0] if is_single else max(
            nodules, key=lambda x: x['diameter_mm']
        )

        features = []
        for i, nodule in enumerate(nodules):
            # 直径分类标准（根据Lung-RADS 1.1）
            diameter = nodule['diameter_mm']
            if diameter < 6:
                size_desc = "微小结节（<6mm）"
            elif 6 <= diameter < 10:
                size_desc = "小结节（6-10mm）"
            elif 10 <= diameter < 30:
                size_desc = "中等结节（10-30mm）"
            else:
                size_desc = "高风险结节（≥30mm）"
            # 类型本地化映射（兼容TI-RADS分类）
            type_mapping = {
                'solid': '实性结节',
                'part-solid': '部分实性结节',
                'ggo': '磨玻璃结节',
            }
            type_desc = type_mapping.get(nodule['type'], '其他类型（需人工复核）')

            # 位置分类（基于CT影像坐标，假设图像高度为512px）
            y_pos = nodule['position'][1]
            if y_pos < 200:  # 上肺叶
                location = "上肺叶"
            else:  # 下肺叶
                location = "下肺叶"

            # 标注主结节
            prefix = "★主结节 " if nodule == main_nodule else f"结节{i + 1} "

            features.append(
                f"{prefix}| {size_desc} | "
                f"类型：{type_desc} | "
                f"位置：{location}"
            )

        # 添加医学分类说明
        if not is_single:
            features.append("\n注：结节分类依据Lung-RADS 1.1标准")
        return "\n".join(features)

    def process_image(self, file_path):

        # YOLO模型推理
        model = YOLO("best.pt")
        model.to('cuda')
        results = model(file_path, conf=0.5)

        # 显示推理时间
        self.show_inference_time(results)

        # 处理检测结果
        self.nodules = self.process_detections(results)

        # 显示检测结果
        self.show_detections(results[0], self.nodules)

        # 医学分析
        if self.nodules:
            self.medical_analysis(self.nodules)
        else:
            self.ui.riskLevelLabel.setText("恶性风险: 未检测到结节")
            self.ui.riskDetailLabel.setText("特征评估:无")
            self.ui.stageLabel.setText("肺癌分期: 无")
            self.ui.stageDetailLabel.setText("暂无描述")

    def medical_analysis(self, nodules):
        # 更新结节数量显示
        self.ui.noduleCountLabel.setText(f"检测到结节: {len(nodules)}个")

        # 更新结节特征表格
        self.update_nodule_table(nodules)

        # 恶性风险评估
        risk_level, percentage, main_nodule_detail_desc = self.assess_malignant_risk(nodules)

        self.ui.riskLevelLabel.setText(f"风险水平：{risk_level}")
        self.ui.riskDetailLabel.setText(f"特征评估: {main_nodule_detail_desc}")
        self.update_risk_progress(percentage)  # 风险进度条更新

        # TNM分期预测
        tnm_stage, stage_details = self.predict_tnm_stage(nodules)
        self.ui.stageLabel.setText(f"TNM分期：{tnm_stage}")
        self.ui.stageDetailLabel.setText(f"分期描述：\n{stage_details}")

    def assess_malignant_risk(self, nodules):
        """基于Lung-RADS 2022和C-TIRADS的恶性风险评估"""
        """动态参数化风险评估"""
        params = self.current_params

        # 主结节动态权重计算
        main_nodule = max(nodules, key=lambda x: x['diameter_mm'])
        main_score = self._score_single_nodule(main_nodule) * params['main_weight']

        # 其他结节加权计算
        other_weight = 1 - params['main_weight']
        other_scores = sum(
            self._score_single_nodule(n) * other_weight / (len(nodules) - 1)
            for n in nodules if n != main_nodule
        )

        # 综合风险生成
        total_score = main_score + other_scores
        risk_level = self._calc_risk_level(total_score)

        # 非线性映射到百分制（Sigmoid函数）[4](@ref)
        risk_thresholds = self.current_params['thresholds']

        sigmoid_params = self.calculate_sigmoid_params(risk_thresholds)
        percentage = self.risk_mapping(total_score, sigmoid_params)

        # 生成医学建议[6](@ref)
        self.advice = self._generate_advice(risk_level, main_nodule)
        main_nodule_detail_desc = self.generate_features_text(main_nodule)
        return risk_level, percentage, main_nodule_detail_desc

    def calculate_sigmoid_params(self, risk_thresholds):
        """动态计算Sigmoid参数，基于风险评估阈值"""
        # 默认临床映射参数（可配置）
        mid_point_percent = 50  # 中危阈值对应百分比
        high_risk_percent = 95  # 高危阈值预期百分比

        # 从配置中获取阈值
        low_thresh = risk_thresholds['low']
        mid_thresh = risk_thresholds['medium']
        high_thresh = risk_thresholds['high']

        # 计算Sigmoid中心点（x0 = 中危阈值）
        x0 = mid_thresh

        # 计算斜率k（确保高危阈值时达到high_risk_percent）
        # 使用方程：high_risk_percent = 100 / (1 + exp(-k*(high_thresh - x0)))
        k = -math.log((100 / high_risk_percent - 1)) / (high_thresh - x0)

        return {
            'x0': x0,
            'k': max(k, 0.1),  # 防止负斜率
            'output_scale': 100  # 输出百分比
        }

    def risk_mapping(self, total_score, sigmoid_params):
        """带参数的非线性风险映射"""
        x = total_score
        k = sigmoid_params['k']
        x0 = sigmoid_params['x0']
        scaled = 1 / (1 + math.exp(-k * (x - x0)))
        return min(scaled * sigmoid_params['output_scale'], 99.9)

    def _calc_risk_level(self, score):
        """动态阈值判断"""
        if score >= self.current_params['thresholds']['high']:
            return "高危"
        elif score >= self.current_params['thresholds']['medium']:
            return "中危"
        else:
            return "低危"

    def _score_single_nodule(self, nodule):
        """基于多模态医学标准的单结节评分（LU-RADS/TI-RADS）"""
        score = 0
        morphology_weights = defaultdict(int)

        # 动态参数配置（可界面调整）
        size_rules = self.current_params['nodules']['size']  # [(5,0),(10,1),(20,2),(30,3)]
        type_weights = self.current_params['nodules']['type']  # {'ggo':1,'part-solid':2,'solid':3}
        morph_rules = self.current_params['nodules']['morphology']  # {'spiculation':2,'lobulation':1.5}

        # 年龄评分
        age = self.patient_info.get('age', 50)
        age_weights = self.current_params['patient']['age_weights']
        if age < 45:
            score += age_weights['<45']
        elif 45 <= age < 55:
            score += age_weights['45-54']
        elif 55 <= age < 70:
            score += age_weights['55-69']
        else:
            score += age_weights['≥70']

        # 性别评分
        gender = self.patient_info.get('gender', '男')
        gender_weight = self.current_params['patient']['gender_weights'].get(gender, 1.0)
        score += gender_weight

        # 病史评分部分修改
        risk_factors = self.patient_info.get('risk_factors', {})
        for keyword, config in self.current_params['patient']['history_keywords'].items():
            if keyword in risk_factors:
                score += config['score'] if isinstance(config, dict) else config

        # 1. 大小评分优化
        diameter = nodule['diameter_mm']
        for threshold, points in sorted(size_rules, key=lambda x: x[0]):
            if diameter <= threshold:
                score += points
                break

        # 2. 类型评分细化
        nodule_type = nodule['type']
        score += type_weights.get(nodule_type, 0)

        # 3. 位置评分优化
        y_pos = nodule['position'][1]
        if y_pos < 100:  # 上肺叶高风险区
            score += 2
        elif y_pos < 200:  # 中肺叶中等风险
            score += 1
        else:  # 下肺叶低风险
            pass

        # 4. 形态特征检测（传统视觉实现）
        if 'morphology' in nodule:
            for feature in nodule['morphology']:
                weight = morph_rules.get(feature, 0)
                if weight > 0:
                    score += weight
                    # morphology_weights[feature] += 1

        return min(score, 10)  # 根据LU-RADS调整上限

    def _generate_advice(self, risk_level, main_nodule):
        """根据NCCN指南生成建议[6](@ref)"""
        advice_map = {
            "高危": [
                f"1.建议PET-CT检查（主结节直径{main_nodule['diameter_mm']}mm）",
                "2.需多学科会诊讨论治疗方案",
                "3.穿刺活检优先级：高"
            ],
            "中危": [
                "1.建议3个月后复查薄层CT",
                "2.戒烟干预建议",
                f"3.监测{main_nodule['type']}结节变化"
            ],
            "低危": [
                "1.年度低剂量CT筛查,建议年度常规体检",
                "2.健康教育及风险因素控制"
            ]
        }

        return "\n".join(advice_map[risk_level])

    def _format_morphology(self, features):
        """格式化形态学特征"""
        items = []
        if features['spiculation'] > 0:
            items.append(f"毛刺({features['spiculation']}处)")
        if features['lobulation'] >= 3:
            items.append(f"分叶({features['lobulation']}分叶)")
        return " | ".join(items) if items else "未见典型恶性征象"

    def predict_tnm_stage(self, nodules):
        """基于TNM第八版分期标准"""
        # 获取主结节信息
        main_nodule = max(nodules, key=lambda x: x['diameter_mm'])

        # 模拟N/M参数（需要根据实际检测结果调整）
        N_status = self.current_params['n_status']  # 假设N0（无淋巴结转移）
        M_status = self.current_params['m_status']  # 假设M0（无远端转移）

        # 根据直径确定T分期
        diameter = main_nodule['diameter_mm']
        if diameter <= 10:
            T_stage = "T1a"
        elif diameter <= 20:
            T_stage = "T1b"
        elif diameter <= 30:
            T_stage = "T1c"
        elif diameter <= 40:
            T_stage = "T2a"
        elif diameter <= 50:
            T_stage = "T2b"
        else:
            T_stage = "T3"

        # 完整TNM组合
        tnm_code = f"{T_stage}{N_status}{M_status}"

        # 扩展分期映射
        stage_map = {
            "TisN0M0": ("0期", "原位癌"),
            "T1aN0M0": ("IA1期", "微小浸润癌"),
            "T1bN0M0": ("IA2期", "早期浸润癌"),
            "T1cN0M0": ("IA3期", "局部浸润癌"),
            "T2aN0M0": ("IB期", "中等大小原发灶"),
            "T2bN0M0": ("IIA期", "较大原发灶"),
            "T1bN1M0": ("IIB期", "局部淋巴结转移"),
            "T2aN1M0": ("IIB期", "较大肿瘤伴淋巴结转移"),
            "T3N0M0": ("IIIA期", "局部进展期肿瘤"),
            "T3N1M0": ("IIIB期", "局部扩散伴淋巴结转移"),
            "T4N0M0": ("IIIC期", "侵犯邻近器官"),
            "TanyNanyM1a": ("IVA期", "单器官远端转移"),
            "TanyNanyM1b": ("IVB期", "多器官转移")
        }

        # 查找最匹配的分期
        stage_detail = stage_map.get(tnm_code, ("待评估", "需结合影像学检查"))

        # 处理转移情况
        if M_status == 'M1':
            return "IV期", "远端转移（M1）"

        return f"{stage_detail[0]} {tnm_code}", stage_detail[1]

    def _crop_roi(self, image, coords, padding=5):
        """带安全边界的ROI裁剪"""
        h, w = image.shape[:2]
        x1, y1, x2, y2 = [int(round(c)) for c in coords]
        x1 = max(0, x1 - padding)
        y1 = max(0, y1 - padding)
        x2 = min(w, x2 + padding)
        y2 = min(h, y2 + padding)
        return image[y1:y2, x1:x2]

    def process_detections(self, results):
        """处理检测结果并提取结节特征"""
        nodules = []
        for result in results:
            for box in result.boxes:
                # 获取检测框信息
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                cls = int(box.cls[0].item())
                conf = box.conf[0].item()
                # 计算实际尺寸
                width = x2 - x1
                height = y2 - y1
                diameter = max(width, height) * self.default_params['mm_per_pixel']
                # ROI特征分析
                roi = self._crop_roi(cv2.imread(self.current_image_path), (x1, y1, x2, y2))
                morphology = MorphologyAnalyzer().analyze(roi)
                nodules.append({
                    'diameter_mm': diameter,
                    'type': result.names[cls],
                    'confidence': round(conf, 2),
                    'position': ((x1 + x2) / 2, (y1 + y2) / 2),
                    'morphology': {
                        'spiculation': morphology['spiculation'],
                        'lobulation': morphology['lobulation']
                    },
                    'roi_shape': roi.shape[:2]  # 用于质量检查
                })
        return nodules

    def show_image(self, file_path):
        """显示原始图像"""
        pixmap = QPixmap(file_path)
        scene = QGraphicsScene()
        item = QGraphicsPixmapItem(pixmap)
        scene.addItem(item)
        self.ui.graphicsView.setScene(scene)
        self.ui.graphicsView.fitInView(item, Qt.KeepAspectRatio)

    def show_inference_time(self, results):
        """显示推理时间"""
        if results:
            inference_time = results[0].speed['inference']
            self.ui.inferenceTimeLabel.setText(
                f"推理时间: {inference_time:.1f}ms"
            )

    def show_detections(self, result, nodules):
        """可视化检测结果"""
        scene = self.ui.graphicsView.scene()

        # 清空先前标注
        for item in scene.items():
            if isinstance(item, QGraphicsPixmapItem): continue
            scene.removeItem(item)

        # 绘制新检测结果
        for box, nodule in zip(result.boxes, nodules):
            x1, y1, x2, y2 = box.xyxy[0].tolist()

            # 绘制边界框
            rect = scene.addRect(x1, y1, x2 - x1, y2 - y1)
            color = QColor(0, 255, 0) if nodule['diameter_mm'] < 30 else QColor(255, 0, 0)
            rect.setPen(QPen(color, 2))

            # 添加标注文本
            text = f"{nodule['type']} {nodule['diameter_mm']:.1f}mm"
            text_item = scene.addText(text)
            text_item.setDefaultTextColor(color)
            text_item.setPos(x1, y1 - 20)

    def update_risk_progress(self, percentage):
        """更新风险进度条"""
        # risk_map = {
        #     "高危": 85,
        #     "中危": 60,
        #     "低危": 30
        # }
        self.ui.riskProgressBar.setValue(int(percentage * 100))
        self.ui.riskProgressBar.setFormat("恶性概率：" + "%.02f %%" % percentage)

    def update_nodule_table(self, nodules):
        """更新结节特征表格"""
        # 清空现有数据
        self.ui.noduleTable.clearContents()
        self.ui.noduleTable.setRowCount(len(nodules))

        # 设置表格列数和表头
        self.ui.noduleTable.setColumnCount(5)
        self.ui.noduleTable.setHorizontalHeaderLabels([
            "编号", "直径(mm)", "类型", "形态", "位置"
        ])

        # 填充数据
        for i, nodule in enumerate(nodules):
            self.ui.noduleTable.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.ui.noduleTable.setItem(i, 1, QTableWidgetItem(f"{nodule['diameter_mm']:.1f}"))
            self.ui.noduleTable.setItem(i, 2, QTableWidgetItem(nodule['type']))
            morphology_desc = []
            if nodule['morphology']['spiculation'] > 0:
                morphology_desc.append("毛刺")
            if nodule['morphology']['lobulation'] > 0:
                morphology_desc.append("分叶")
            if not morphology_desc:
                morphology_desc.append("无")
            self.ui.noduleTable.setItem(i, 3, QTableWidgetItem(" | ".join(morphology_desc)))  # 位置格式化
            position_str = f"({nodule['position'][0]:.1f}, {nodule['position'][1]:.1f})"
            self.ui.noduleTable.setItem(i, 4, QTableWidgetItem(position_str))

            # 自动调整列宽
        self.ui.noduleTable.resizeColumnsToContents()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = MainWindow()
    widget.show()
    sys.exit(app.exec())
