import tkinter as tk
import traceback
from tkinter import ttk, filedialog

import cv2
import numpy as np
import yaml
from PIL import Image, ImageTk
from ultralytics import YOLO


class MorphologyAnalyzer:
    def __init__(self, root, roi_image):
        self.root = root
        self.root.title("单ROI形态学分析工具")

        # 初始化ROI图像
        self.original = roi_image.copy()
        self.processed_image = self.original.copy()

        # 默认参数配置（包含全部四个特征）
        self.config = {
            'spiculation': {'hough_threshold': 50,
                            'min_length': 20,  # 单位：像素
                            'max_gap': 5,
                            'scale_factors': [1.0, 0.75, 0.5],  # 多尺度检测参数[1,7](@ref)
                            'angle_range': [15, 75]  # 放射状角度约束[1](@ref)}
                            },
            'lobulation': {'epsilon': 0.03, 'block': 11, 'c': 2},
            'vacuole': {'min_r': 5, 'circularity': 5},
            'calcification': {'hu_thresh': 150}
        }

        # 界面初始化
        self._init_ui()
        self.update_image()

    def _init_ui(self):
        """初始化用户界面组件"""
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 图像显示区域（左侧）
        self.canvas = tk.Canvas(main_frame, width=800, height=600)
        self.canvas.pack(side=tk.LEFT, padx=10, pady=10)

        # 参数控制面板（右侧）
        control_frame = ttk.Notebook(main_frame)
        self._create_control_tabs(control_frame)
        control_frame.pack(side=tk.RIGHT, padx=10)

        # 操作按钮（底部）
        btn_frame = ttk.Frame(main_frame)
        ttk.Button(btn_frame, text="保存配置", command=self.save_config).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="加载配置", command=self.load_config).pack(side=tk.LEFT)
        btn_frame.pack(side=tk.BOTTOM, pady=10)

    def _create_control_tabs(self, notebook):
        """创建包含所有参数的标签页"""
        self._create_spiculation_tab(notebook)  # 毛刺参数
        self._create_lobulation_tab(notebook)  # 分叶参数
        self._create_vacuole_tab(notebook)  # 空泡参数
        self._create_calcification_tab(notebook)  # 钙化参数

    def _create_slider(self, parent, label, param_key, category, range_vals, value_type='single', scale=1.0):
        """增强型参数滑动条组件"""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, padx=5, pady=2, expand=True)

        # 参数标签
        ttk.Label(frame, text=label, width=14, anchor='w').pack(side=tk.LEFT)

        # 参数值显示
        value_frame = ttk.Frame(frame)
        value_frame.pack(side=tk.RIGHT, padx=5)

        # 根据参数类型初始化
        config_value = self.config[category][param_key]

        if value_type == 'range':
            # 范围型参数（如angle_range）
            min_val = float(config_value[0]) * scale
            max_val = float(config_value[1]) * scale
            current_values = [min_val, max_val]
        elif isinstance(config_value, list):
            # 多值参数（如scale_factors）
            current_values = [float(v) * scale for v in config_value]
        else:
            # 单值参数
            current_values = [float(config_value) * scale]

        # 生成滑动条组件
        sliders = []
        for i, val in enumerate(current_values):
            slider_frame = ttk.Frame(value_frame)
            slider_frame.pack(fill=tk.X, pady=2)

            # 数值标签
            value_label = ttk.Label(slider_frame, width=6)
            value_label.pack(side=tk.RIGHT)

            # 滑动条
            slider = ttk.Scale(
                slider_frame,
                from_=range_vals[0],
                to=range_vals[1],
                value=val,
                orient=tk.HORIZONTAL,
                command=lambda v, pk=param_key, idx=i: self._update_param_value(v, pk, category, idx, scale,
                                                                                value_label)
            )
            slider.pack(side=tk.RIGHT, fill=tk.X, expand=True)

            # 初始值显示
            raw_value = val / scale
            value_label.config(text=f"{raw_value:.2f}" if isinstance(raw_value, float) else f"{raw_value}")
            sliders.append((slider, value_label))

        return frame

    def _update_param_value(self, value, param_key, category, index, scale, label):
        """参数更新回调"""
        raw_value = float(value) / scale

        # 更新配置值
        if isinstance(self.config[category][param_key], list):
            if param_key == 'angle_range' and len(self.config[category][param_key]) >= 2:
                # 角度范围校验
                if index == 0:
                    self.config[category][param_key][0] = min(raw_value, self.config[category][param_key][1] - 1)
                else:
                    self.config[category][param_key][1] = max(raw_value, self.config[category][param_key][0] + 1)
            else:
                self.config[category][param_key][index] = raw_value
        else:
            self.config[category][param_key] = raw_value

        # 更新标签显示
        display_value = raw_value if not isinstance(raw_value, float) or raw_value.is_integer() else f"{raw_value:.2f}"
        label.config(text=str(display_value))

        # 触发实时更新
        self.update_image()

    def _create_spiculation_tab(self, notebook):
        """毛刺参数标签页优化"""
        tab = ttk.Frame(notebook)

        # 阈值参数
        self._create_slider(tab, 'Hough阈值', 'hough_threshold', 'spiculation',
                            (10, 100), scale=1.0)

        # 长度参数（带单位提示）
        length_frame = self._create_slider(tab, '最小长度(px)', 'min_length', 'spiculation',
                                           (5, 50), scale=1.0)
        ttk.Label(length_frame, text="5-50px").pack(side=tk.RIGHT, padx=5)

        # 角度范围（双滑动条）
        angle_frame = self._create_slider(tab, '角度范围(度)', 'angle_range', 'spiculation',
                                          (0, 90), value_type='range', scale=1.0)
        ttk.Label(angle_frame, text="15°-75°").pack(side=tk.RIGHT, padx=5)

        # 多尺度因子（动态添加按钮）
        scale_frame = ttk.Frame(tab)
        scale_frame.pack(fill=tk.X, pady=5)
        ttk.Button(scale_frame, text="+", width=3,
                   command=lambda: self._add_scale_factor()).pack(side=tk.RIGHT, padx=5)
        self._create_slider(scale_frame, '尺度因子', 'scale_factors', 'spiculation',
                            (0.1, 2.0), scale=1.0)

        notebook.add(tab, text='毛刺参数')

    def _add_scale_factor(self):
        """动态添加尺度因子"""
        if len(self.config['spiculation']['scale_factors']) < 5:  # 最大允许5个尺度
            self.config['spiculation']['scale_factors'].append(1.0)

    def _create_lobulation_tab(self, notebook):
        """分叶参数标签页"""
        tab = ttk.Frame(notebook)
        self._create_slider(tab, '轮廓精度', 'epsilon', 'lobulation', (1, 100), scale=100)
        self._create_slider(tab, '块大小', 'block', 'lobulation', (3, 255))
        self._create_slider(tab, 'C值', 'c', 'lobulation', (1, 50))
        notebook.add(tab, text='分叶参数')

    def _create_vacuole_tab(self, notebook):
        """空泡参数标签页"""
        tab = ttk.Frame(notebook)
        self._create_slider(tab, '最小半径', 'min_r', 'vacuole', (1, 50))
        self._create_slider(tab, '圆形度', 'circularity', 'vacuole', (0, 100))
        notebook.add(tab, text='空泡参数')

    def _create_calcification_tab(self, notebook):
        """钙化参数标签页"""
        tab = ttk.Frame(notebook)
        self._create_slider(tab, 'HU阈值', 'hu_thresh', 'calcification', (0, 255))
        notebook.add(tab, text='钙化参数')

    def update_image(self):
        """更新显示图像"""
        try:
            # 创建显示用图像的安全副本
            if self.original is None or self.original.size == 0:
                raise ValueError("原始图像数据异常")

            if len(self.original.shape) == 3:
                # 如果original是3通道，转换为灰度
                gray = cv2.cvtColor(self.original, cv2.COLOR_BGR2GRAY)
            else:
                gray = self.original.copy()
            display = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
            display = self._detect_spiculation(display)
            self._update_canvas(display)

        except Exception as e:
            print(f"图像更新失败: {str(e)}")
            traceback.print_exc()
        # display = self.original.copy()
        #
        # # 执行所有特征检测
        # self._detect_spiculation(display)  # 毛刺（红色）
        # self._detect_lobulation(display)  # 分叶（绿色）
        # self._detect_vacuole(display)  # 空泡（黄色）
        # self._detect_calcification(display)  # 钙化（蓝色）

        # 更新显示
        # self._update_canvas(display)

    def _detect_spiculation(self, img):
        """
           基于多尺度Hough变换的毛刺检测
           :param image: 输入图像(灰度图)
           :param config: 形态学参数字典
           :param center_point: 病灶中心坐标(tuple)
           :return: 检测线段列表[[x1,y1,x2,y2],...]
           """
        # 参数初始化
        params = {
            'hough_threshold': self.config['spiculation']['hough_threshold'],
            'min_length': self.config['spiculation']['min_length'],
            'max_gap': self.config['spiculation']['max_gap'],
            'scale_factors': self.config['spiculation']['scale_factors'],
            'angle_range': self.config['spiculation']['angle_range']
        }
        # 验证处理图像的有效性
        processing_img = self.original.copy()
        if processing_img.size == 0:
            raise ValueError("处理图像为空，请检查ROI裁剪参数")

        # 强制转换为8位灰度图像
        if processing_img.dtype != np.uint8:
            processing_img = processing_img.astype(np.uint8)
        if len(processing_img.shape) == 3:
            processing_img = cv2.cvtColor(processing_img, cv2.COLOR_BGR2GRAY)

        # 显示用图像单独处理
        display_img = cv2.cvtColor(processing_img, cv2.COLOR_GRAY2BGR)
        # 确保输入为灰度图像
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()

        # 添加CLAHE增强对比度
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # 使用Canny边缘检测优化线段检测
        edges = cv2.Canny(enhanced, 50, 150, apertureSize=3)

        all_lines = []

        # 多尺度检测
        for scale in params['scale_factors']:
            # 尺度缩放使用INTER_AREA插值
            scaled = cv2.resize(edges, None, fx=scale, fy=scale,
                                interpolation=cv2.INTER_AREA)

            # 执行Hough变换前验证图像格式
            if scaled.dtype != np.uint8:
                scaled = scaled.astype(np.uint8)
            # Hough线段检测
            lines = cv2.HoughLinesP(
                scaled,
                rho=1,
                theta=np.pi / 180,
                threshold=int(params['hough_threshold']),
                minLineLength=int(params['min_length'] * scale),  # 尺度自适应长度阈值
                maxLineGap=int(params['max_gap'])
            )

            # 坐标还原
            # 坐标还原（添加边界保护）
            if lines is not None:
                lines = lines.reshape(-1, 4).clip(min=0) / scale
                all_lines.extend(lines.tolist())

        # 角度过滤
        def _angle_filter(lines):
            valid_lines = []
            cx, cy = (img.shape[1] // 2, img.shape[0] // 2)  # 假设中心在图像中心
            min_angle, max_angle = params['angle_range']

            for x1, y1, x2, y2 in lines:
                # 计算线段相对中心的角度
                vec = np.array([x2 - cx, cy - y2])  # 图像坐标系转换
                angle = np.degrees(np.arctan2(vec[1], vec[0]))

                if min_angle <= abs(angle) <= max_angle:
                    valid_lines.append([x1, y1, x2, y2])
            return valid_lines

        filtered = _angle_filter(all_lines)
        # # 在显示图像上绘制结果（确保显示图像是BGR格式）
        # for x1, y1, x2, y2 in filtered:
        #     cv2.line(img, (int(x1), int(y1)), (int(x2), int(y2)), (0, 0, 255), 1)

        # 后处理：合并重叠线段
        # 线段合并使用原始灰度图像
        lsd = cv2.createLineSegmentDetector()
        if processing_img.size == 0 or processing_img.dtype != np.uint8:
            raise ValueError(f"无效的输入图像格式: shape={processing_img.shape}, dtype={processing_img.dtype}")

        lines, _, _, _ = lsd.detect(processing_img)

        # 绘制合并后的线段到显示图像
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                cv2.line(display_img, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 0), 1)

                # 更新显示图像
        self._update_canvas(display_img)
        return display_img

    def _detect_lobulation(self, img):
        """分叶检测（绿色轮廓）"""
        # 确保参数为整数
        params = {
            'block': int(self.config['lobulation']['block']),
            'c': int(self.config['lobulation']['c']),
            'epsilon': float(self.config['lobulation']['epsilon'])
        }

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY_INV,
                                       params['block'],
                                       params['c'])
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            main_contour = max(contours, key=cv2.contourArea)
            epsilon = params['epsilon'] * cv2.arcLength(main_contour, True)
            approx = cv2.approxPolyDP(main_contour, epsilon, True)
            cv2.drawContours(img, [approx], -1, (0, 255, 0), 1)

    def _detect_vacuole(self, img):
        """空泡检测（黄色圆圈）"""
        # 确保参数为整数
        params = {
            'min_r': int(self.config['vacuole']['min_r']),
            'circularity': int(self.config['vacuole']['circularity'])
        }
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.medianBlur(gray, 5)
        circles = cv2.HoughCircles(blurred, cv2.HOUGH_GRADIENT, 1, 20,
                                   param1=50,
                                   param2=params['circularity'],
                                   minRadius=params['min_r'],
                                   maxRadius=50)
        if circles is not None:
            circles = np.uint16(np.around(circles))
            for i in circles[0, :]:
                cv2.circle(img, (i[0], i[1]), i[2], (255, 255, 0), 1)

    def _detect_calcification(self, img):
        """钙化检测（蓝色区域）"""
        # 确保参数为整数
        params = {
            'hu_thresh': int(self.config['calcification']['hu_thresh'])
        }
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray, params['hu_thresh'], 255, cv2.THRESH_BINARY)
        img[mask == 255] = (255, 0, 0)

    def _update_canvas(self, img):
        """更新画布显示（改进版）"""
        # 转换为RGB并调整尺寸
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(img)

        # 使用双线性插值进行高质量缩放
        img = img.resize((800, 600), Image.Resampling.LANCZOS)

        self.tk_img = ImageTk.PhotoImage(img)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_img)

    def save_config(self):
        """保存当前配置"""
        path = filedialog.asksaveasfilename(defaultextension=".yaml")
        if path:
            with open(path, 'w') as f:
                yaml.safe_dump(self.config, f)

    def load_config(self):
        """加载配置文件"""
        path = filedialog.askopenfilename(filetypes=[("YAML配置", "*.yaml")])
        if path:
            with open(path, 'r') as f:
                self.config = yaml.safe_load(f)
            self.update_image()


def _crop_roi(image, coords, padding=5):
    """带安全边界的ROI裁剪"""
    h, w = image.shape[:2]
    x1, y1, x2, y2 = [int(round(c)) for c in coords]
    x1 = max(0, x1 - padding)
    y1 = max(0, y1 - padding)
    x2 = min(w, x2 + padding)
    y2 = min(h, y2 + padding)
    return image[y1:y2, x1:x2]


if __name__ == "__main__":
    # 使用示例
    root = tk.Tk()
    model = YOLO("C:\\Users\\22662\\Desktop\\Graduation Project\\UI\\models\\best.pt")
    model.to('cuda')
    results = model("C:\\Users\\22662\\Desktop\\Graduation Project\\UI\\resources\\0005.png", conf=0.5)
    nodules = []
    roi = []
    for result in results:
        for box in result.boxes:
            # 获取检测框信息
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            # 加载ROI图像（替换为你的实际路径）
            roi = _crop_roi(cv2.imread("C:\\Users\\22662\\Desktop\\Graduation Project\\UI\\resources\\0005.png"),
                            (x1, y1, x2, y2))
    # 初始化分析器
    app = MorphologyAnalyzer(root, roi)
    root.mainloop()
