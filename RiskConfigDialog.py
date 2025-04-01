from PySide6.QtWidgets import QDialog, QFormLayout, QComboBox, QDoubleSpinBox, QSpinBox, QTableWidget, QTabWidget, \
    QWidget, QDialogButtonBox, QVBoxLayout, QGroupBox, QHeaderView, QLabel, QTableWidgetItem, QPushButton, QHBoxLayout


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
        self.gender_other = self.create_spinbox(0.0, 5.0)
        gender_layout.addRow("男性:", self.gender_male)
        gender_layout.addRow("女性:", self.gender_female)
        gender_layout.addRow("其他:", self.gender_other)
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
        """初始化结节参数页"""
        self.nodule_tab = QWidget()
        layout = QFormLayout()

        # 基础参数
        self.main_weight = self.create_spinbox(0.5, 0.9, 0.1)
        self.mm_per_pixel = self.create_spinbox(0.1, 2.0, 0.1)
        self.n_status = QComboBox()
        self.n_status.addItems(["N0", "N1"])
        self.m_status = QComboBox()
        self.m_status.addItems(["M0", "M1a","M1b"])
        # 阈值参数
        self.low_thresh = self.create_spinbox(0, 100)
        self.medium_thresh = self.create_spinbox(0, 100)
        self.high_thresh = self.create_spinbox(0, 100)

        # 类型权重表
        type_group = QGroupBox("结节类型权重")
        self.type_table = QTableWidget(0, 2)
        self.type_table.setHorizontalHeaderLabels(["类型", "分值"])
        table_buttons = QHBoxLayout()
        add_btn = QPushButton("新增类型")
        add_btn.clicked.connect(lambda: self.type_table.insertRow(self.type_table.rowCount()))
        del_btn = QPushButton("删除选中")
        del_btn.clicked.connect(lambda: self.type_table.removeRow(self.type_table.currentRow()))
        table_buttons.addWidget(add_btn)
        table_buttons.addWidget(del_btn)
        type_layout = QVBoxLayout()
        type_layout.addWidget(self.type_table)
        type_layout.addLayout(table_buttons)
        type_group.setLayout(type_layout)

        # 布局组合
        layout.addRow("N状态:", self.n_status)
        layout.addRow("M状态:", self.m_status)
        layout.addRow("主结节权重:", self.main_weight)
        layout.addRow("像素换算系数(mm/px):", self.mm_per_pixel)
        layout.addRow("低危阈值:", self.low_thresh)
        layout.addRow("中危阈值:", self.medium_thresh)
        layout.addRow("高危阈值:", self.high_thresh)
        layout.addRow(type_group)

        self.nodule_tab.setLayout(layout)

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
        nodule_params = params['nodules']
        self.main_weight.setValue(params['main_weight'])
        self.mm_per_pixel.setValue(params['mm_per_pixel'])
        self.n_status.setCurrentText(params['n_status'])
        self.m_status.setCurrentText(params['m_status'])
        self.low_thresh.setValue(params['thresholds']['low'])
        self.medium_thresh.setValue(params['thresholds']['medium'])
        self.high_thresh.setValue(params['thresholds']['high'])

        # 加载类型权重
        self.type_table.setRowCount(len(nodule_params['type']))
        for row, (t, score) in enumerate(nodule_params['type'].items()):
            self.type_table.setItem(row, 0, QTableWidgetItem(t))
            self.type_table.setItem(row, 1, QTableWidgetItem(str(score)))

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
                'size': [(5, 0), (10, 1), (20, 2), (30, 3), (float('inf'), 4)],
                'type': {'ggo': 1, 'part-solid': 2, 'solid': 3},
                'location': {'upper': 1, 'middle': 0.5, 'lower': 0},  # 上肺叶风险更高[6](@ref)
                'morphology': {'spiculation': 2, 'lobulation': 1.5}
            }
        }

        # 解析病史关键词
        for row in range(self.history_table.rowCount()):
            kw_item = self.history_table.item(row, 0)
            score_item = self.history_table.item(row, 1)
            if kw_item and score_item:
                params['patient']['history_keywords'][kw_item.text()] = float(score_item.text())

        # 解析类型权重
        for row in range(self.type_table.rowCount()):
            type_item = self.type_table.item(row, 0)
            score_item = self.type_table.item(row, 1)
            if type_item and score_item:
                params['nodule']['type'][type_item.text()] = float(score_item.text())

        return params
