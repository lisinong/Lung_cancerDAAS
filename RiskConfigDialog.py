from PySide6.QtWidgets import QDialog, QFormLayout, QComboBox, QDoubleSpinBox, QSpinBox, QTableWidget, QTabWidget, \
    QWidget, QDialogButtonBox, QVBoxLayout, QGroupBox, QHeaderView, QLabel, QTableWidgetItem, QPushButton, QHBoxLayout, \
    QScrollArea


class RiskConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("高级参数配置")
        self.setMinimumSize(800, 600)

        # 创建选项卡容器
        self.tabs = QTabWidget()

        # 初始化各参数页面
        self.init_patient_tab()
        self.init_nodule_tab()

        # 将页面添加到选项卡
        self.tabs.addTab(self.patient_tab, "患者参数")
        self.tabs.addTab(self.nodule_tab, "结节参数")

        # 创建按钮组
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        # 主布局
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.tabs)
        main_layout.addWidget(self.button_box)
        self.setLayout(main_layout)

    def init_patient_tab(self):
        """初始化患者参数页"""
        self.patient_tab = QWidget()
        layout = QVBoxLayout()

        # 年龄权重组
        age_group = QGroupBox("年龄权重系数")
        age_layout = QFormLayout()
        self.age_under45 = self.create_spinbox(0.0, 5.0)
        self.age_45_54 = self.create_spinbox(0.0, 5.0)
        self.age_55_69 = self.create_spinbox(0.0, 5.0)
        self.age_over70 = self.create_spinbox(0.0, 5.0)
        age_layout.addRow("<45岁:", self.age_under45)
        age_layout.addRow("45-54岁:", self.age_45_54)
        age_layout.addRow("55-69岁:", self.age_55_69)
        age_layout.addRow("≥70岁:", self.age_over70)
        age_group.setLayout(age_layout)

        # 性别权重组
        gender_group = QGroupBox("性别基础分")
        gender_layout = QFormLayout()
        self.gender_male = self.create_spinbox(0.0, 5.0)
        self.gender_female = self.create_spinbox(0.0, 5.0)

        gender_layout.addRow("男性:", self.gender_male)
        gender_layout.addRow("女性:", self.gender_female)
        gender_group.setLayout(gender_layout)

        # 病史规则表
        history_group = QGroupBox("病史关键词规则")
        self.history_table = QTableWidget(0, 2)
        self.history_table.setHorizontalHeaderLabels(["关键词", "危险分值"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table_buttons = QHBoxLayout()
        add_btn = QPushButton("新增规则")
        add_btn.clicked.connect(lambda: self.history_table.insertRow(self.history_table.rowCount()))
        del_btn = QPushButton("删除选中")
        del_btn.clicked.connect(lambda: self.history_table.removeRow(self.history_table.currentRow()))
        table_buttons.addWidget(add_btn)
        table_buttons.addWidget(del_btn)
        history_layout = QVBoxLayout()
        history_layout.addWidget(self.history_table)
        history_layout.addLayout(table_buttons)
        history_group.setLayout(history_layout)

        # 组合布局
        layout.addWidget(age_group)
        layout.addWidget(gender_group)
        layout.addWidget(history_group)
        self.patient_tab.setLayout(layout)

    def init_nodule_tab(self):
        """整合后的结节参数配置页"""
        self.nodule_tab = QWidget()
        main_layout = QVBoxLayout()

        # 基础参数组
        base_group = QGroupBox("基础设置")
        base_layout = QFormLayout()
        self.main_weight = QDoubleSpinBox()
        self.main_weight.setRange(0.1, 1.0)
        self.mm_per_pixel = QDoubleSpinBox()
        self.mm_per_pixel.setRange(0.1, 2.0)
        self.n_status = QComboBox()
        self.n_status.addItems(["N0", "N1"])
        self.m_status = QComboBox()
        self.m_status.addItems(["M0", "M1a", "M1b"])
        base_layout.addRow("主结节权重:", self.main_weight)
        base_layout.addRow("像素换算系数(mm/px):", self.mm_per_pixel)
        base_group.setLayout(base_layout)

        # 类型评分组
        type_group = QGroupBox("类型评分")
        type_layout = QFormLayout()
        self.type_ggo = QDoubleSpinBox()
        self.type_part_solid = QDoubleSpinBox()
        self.type_solid = QDoubleSpinBox()
        for spin in [self.type_ggo, self.type_part_solid, self.type_solid]:
            spin.setRange(0, 10)
        type_layout.addRow("磨玻璃 (GGO):", self.type_ggo)
        type_layout.addRow("部分实性:", self.type_part_solid)
        type_layout.addRow("实性:", self.type_solid)
        type_group.setLayout(type_layout)

        # 大小规则组
        size_group = QGroupBox("大小评分")
        size_layout = QFormLayout()
        self.size_5 = QDoubleSpinBox()  # <5mm
        self.size_10 = QDoubleSpinBox()  # 5-10mm
        self.size_20 = QDoubleSpinBox()  # 10-20mm
        self.size_30 = QDoubleSpinBox()  # 20-30mm
        self.size_inf = QDoubleSpinBox()  # ≥30mm
        for spin in [self.size_5, self.size_10, self.size_20, self.size_30, self.size_inf]:
            spin.setRange(0, 10)
        size_layout.addRow("<5mm:", self.size_5)
        size_layout.addRow("5-10mm:", self.size_10)
        size_layout.addRow("10-20mm:", self.size_20)
        size_layout.addRow("20-30mm:", self.size_30)
        size_layout.addRow("≥30mm:", self.size_inf)
        size_group.setLayout(size_layout)

        # 位置规则组
        location_group = QGroupBox("位置评分")
        location_layout = QFormLayout()
        self.upper_score = QDoubleSpinBox()
        self.middle_score = QDoubleSpinBox()
        self.lower_score = QDoubleSpinBox()
        for spin in [self.upper_score, self.middle_score, self.lower_score]:
            spin.setRange(0, 5)
            spin.setSingleStep(0.5)
        location_layout.addRow("上肺叶:", self.upper_score)
        location_layout.addRow("中肺叶:", self.middle_score)
        location_layout.addRow("下肺叶:", self.lower_score)
        location_group.setLayout(location_layout)

        # 形态规则组
        morph_group = QGroupBox("形态评分")
        morph_layout = QFormLayout()
        self.morph_spic = QDoubleSpinBox()  # 毛刺征
        self.morph_lob = QDoubleSpinBox()  # 分叶征
        for spin in [self.morph_spic, self.morph_lob]:
            spin.setRange(0, 5)
        morph_layout.addRow("毛刺征:", self.morph_spic)
        morph_layout.addRow("分叶征:", self.morph_lob)
        morph_group.setLayout(morph_layout)

        # 阈值设置组
        threshold_group = QGroupBox("风险阈值")
        threshold_layout = QFormLayout()
        self.low_thresh = QSpinBox()
        self.medium_thresh = QSpinBox()
        self.high_thresh = QSpinBox()
        for spin in [self.low_thresh, self.medium_thresh, self.high_thresh]:
            spin.setRange(0, 100)
        threshold_layout.addRow("低危:", self.low_thresh)
        threshold_layout.addRow("中危:", self.medium_thresh)
        threshold_layout.addRow("高危:", self.high_thresh)
        threshold_group.setLayout(threshold_layout)

        # 组合所有组件
        scroll = QScrollArea()
        content = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(base_group)
        layout.addWidget(type_group)
        layout.addWidget(size_group)
        layout.addWidget(location_group)
        layout.addWidget(morph_group)
        layout.addWidget(threshold_group)
        content.setLayout(layout)
        scroll.setWidget(content)
        scroll.setWidgetResizable(True)

        main_layout.addWidget(scroll)
        self.nodule_tab.setLayout(main_layout)

    def create_spinbox(self, min_val, max_val, step=0.1):
        """创建标准化数值输入框"""
        spinbox = QDoubleSpinBox() if step < 1 else QSpinBox()
        spinbox.setMinimum(min_val)
        spinbox.setMaximum(max_val)
        spinbox.setSingleStep(step)
        return spinbox

    def load_params(self, params):
        """加载参数到界面"""
        # 患者参数
        age_weights = params['patient']['age_weights']
        self.age_under45.setValue(age_weights['<45'])
        self.age_45_54.setValue(age_weights['45-54'])
        self.age_55_69.setValue(age_weights['55-69'])
        self.age_over70.setValue(age_weights['≥70'])

        gender_weights = params['patient']['gender_weights']
        self.gender_male.setValue(gender_weights['男'])
        self.gender_female.setValue(gender_weights['女'])

        # 加载病史规则
        self.history_table.setRowCount(len(params['patient']['history_keywords']))
        for row, (kw, score) in enumerate(params['patient']['history_keywords'].items()):
            self.history_table.setItem(row, 0, QTableWidgetItem(kw))
            self.history_table.setItem(row, 1, QTableWidgetItem(str(score)))

        # 结节参数
        self.main_weight.setValue(params['main_weight'])
        self.mm_per_pixel.setValue(params['mm_per_pixel'])
        self.n_status.setCurrentText(params['n_status'])
        self.m_status.setCurrentText(params['m_status'])
        self.low_thresh.setValue(params['thresholds']['low'])
        self.medium_thresh.setValue(params['thresholds']['medium'])
        self.high_thresh.setValue(params['thresholds']['high'])

        # 类型评分
        self.type_ggo.setValue(params['nodules']['type']['ggo'])
        self.type_part_solid.setValue(params['nodules']['type']['part-solid'])
        self.type_solid.setValue(params['nodules']['type']['solid'])

        # 位置评分
        self.upper_score.setValue(params['nodules']['location']['upper'])
        self.middle_score.setValue(params['nodules']['location']['middle'])
        self.lower_score.setValue(params['nodules']['location']['lower'])
        # 大小评分
        for (max_size, score) in params['nodules']['size']:
            if max_size == 5:
                self.size_5.setValue(score)
            elif max_size == 10:
                self.size_10.setValue(score)
            elif max_size == 20:
                self.size_20.setValue(score)
            elif max_size == 30:
                self.size_30.setValue(score)
            elif max_size == float('inf'):
                self.size_inf.setValue(score)
        # 形态评分
        morph = params['nodules']['morphology']
        self.morph_spic.setValue(morph.get('spiculation', 0))
        self.morph_lob.setValue(morph.get('lobulation', 0))

    def get_params(self):
        """从界面获取参数"""
        params = {
            'main_weight': self.main_weight.value(),
            'mm_per_pixel': self.mm_per_pixel.value(),
            'n_status': self.n_status.currentText(),
            'm_status': self.m_status.currentText(),
            'thresholds': {
                'low': self.low_thresh.value(),
                'medium': self.medium_thresh.value(),
                'high': self.high_thresh.value()
            },
            'patient': {
                'age_weights': {
                    '<45': self.age_under45.value(),
                    '45-54': self.age_45_54.value(),
                    '55-69': self.age_55_69.value(),
                    '≥70': self.age_over70.value()
                },
                'gender_weights': {
                    '男': self.gender_male.value(),
                    '女': self.gender_female.value(),
                },
                'history_keywords': {}
            },
            'nodules': {
                'type': {
                    'ggo': self.type_ggo.value(),
                    'part-solid': self.type_part_solid.value(),
                    'solid': self.type_solid.value()
                },
                'location': {
                    'upper': self.upper_score.value(),
                    'middle': self.middle_score.value(),
                    'lower': self.lower_score.value()
                },
                'size': [
                    (5, self.size_5.value()),
                    (10, self.size_10.value()),
                    (20, self.size_20.value()),
                    (30, self.size_30.value()),
                    (float('inf'), self.size_inf.value())
                ],
                'morphology': {
                    'spiculation': self.morph_spic.value(),
                    'lobulation': self.morph_lob.value(),
                }
            }
        }

        # 解析病史关键词
        for row in range(self.history_table.rowCount()):
            kw_item = self.history_table.item(row, 0)
            score_item = self.history_table.item(row, 1)
            if kw_item and score_item:
                params['patient']['history_keywords'][kw_item.text()] = float(score_item.text())

        return params
