import tkinter as tk
import traceback
from tkinter import ttk, filedialog

import cv2
import numpy as np
import pydicom
import yaml
from PIL import Image, ImageTk
from ultralytics import YOLO


class MorphologyAnalyzer:
    def __init__(self, root, roi_image, dicom_image=None):
        self.root = root
        self.root.title("单ROI形态学分析工具")

        # 初始化ROI图像
        self.original = roi_image.copy()
        self.processed_image = self.original.copy()
        self.dicom_image = dicom_image
        # 默认参数配置（包含全部四个特征）
        self.config = {
            'spiculation': {'hough_threshold': 50,
                            'min_length': 20,  # 单位：像素
                            'max_gap': 5,
                            'scale_factors': [1.0, 0.75, 0.5],  # 多尺度检测参数[1,7](@ref)
                            'angle_range': [15, 75]  # 放射状角度约束[1](@ref)}
                            },
            'lobulation': {'epsilon': 0.3, 'block': 11, 'c': 2},
            'vacuole': {'min_r': 0.95,  # 空泡直径下限1mm（网页8定义<5mm）
                        'max_r': 2,  # 直径上限5mm（网页8关键诊断标准）
                        'circularity': 18,  # 降低圆形度要求（允许卵圆形/不规则）
                        'contrast_thresh': 0.3  # 新增对比度阈值（排除血管干扰）
                        },
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

    def _create_slider(self, parent, label, param_key, category, range_vals, value_type='single', scale=1):
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
        self.root.update_idletasks()  # 强制刷新GUI

    def _create_spiculation_tab(self, notebook):
        """毛刺参数标签页优化"""
        tab = ttk.Frame(notebook)

        # 阈值参数
        self._create_slider(tab, 'Hough阈值', 'hough_threshold', 'spiculation',
                            (0, 100), scale=1.0)

        # 长度参数（带单位提示）
        length_frame = self._create_slider(tab, '最小长度(px)', 'min_length', 'spiculation',
                                           (0, 100), scale=1.0)
        ttk.Label(length_frame, text="5-50px").pack(side=tk.RIGHT, padx=5)

        # 角度范围（双滑动条）
        angle_frame = self._create_slider(tab, '角度范围(度)', 'angle_range', 'spiculation',
                                          (0, 100), value_type='range', scale=1.0)
        ttk.Label(angle_frame, text="0°-100°").pack(side=tk.RIGHT, padx=5)

        # 多尺度因子（动态添加按钮）
        scale_frame = ttk.Frame(tab)
        scale_frame.pack(fill=tk.X, pady=5)
        self._create_slider(scale_frame, '尺度因子', 'scale_factors', 'spiculation',
                            (0.1, 10.0), scale=1.0)

        notebook.add(tab, text='毛刺参数')

    def _create_lobulation_tab(self, notebook):
        """分叶参数标签页"""
        tab = ttk.Frame(notebook)
        self._create_slider(tab, '轮廓精度', 'epsilon', 'lobulation', (0, 100), scale=10)
        self._create_slider(tab, '块大小', 'block', 'lobulation', (1, 255))
        self._create_slider(tab, 'C值', 'c', 'lobulation', (1, 100))
        notebook.add(tab, text='分叶参数')

    def _create_vacuole_tab(self, notebook):
        """空泡参数标签页"""
        tab = ttk.Frame(notebook)
        self._create_slider(tab, '最小半径', 'min_r', 'vacuole', (0, 50))
        self._create_slider(tab, '最大半径', 'max_r', 'vacuole', (0, 50))
        self._create_slider(tab, '对比度阈值', 'contrast_thresh', 'vacuole', (0, 1), scale=1)
        self._create_slider(tab, '圆形度', 'circularity', 'vacuole', (0, 100), scale=1)
        notebook.add(tab, text='空泡参数')

    def _create_calcification_tab(self, notebook):
        """钙化参数标签页"""
        tab = ttk.Frame(notebook)
        self._create_slider(tab, 'HU阈值', 'hu_thresh', 'calcification', (0, 255))
        notebook.add(tab, text='钙化参数')

    def update_image(self):
        """更新显示图像"""
        # try:
        #     # 创建显示用图像的安全副本
        #     if self.original is None or self.original.size == 0:
        #         raise ValueError("原始图像数据异常")
        #
        #     if len(self.original.shape) == 3:
        #         # 如果original是3通道，转换为灰度
        #         gray = cv2.cvtColor(self.original, cv2.COLOR_BGR2GRAY)
        #     else:
        #         gray = self.original.copy()
        #     display = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        #     display = self._detect_spiculation(display)
        #     if display is not None:
        #         self._update_canvas(display)
        #     else:
        #         print("处理后的图像为空")
        #
        # except Exception as e:
        #     print(f"图像更新失败: {str(e)}")
        #     traceback.print_exc()
        display = self.original.copy()

        # 执行所有特征检测
        # self._detect_spiculation(display)  # 毛刺（红色）
        # self._detect_lobulation(display)  # 分叶（绿色）
        # display = self._detect_vacuole(display)  # 空泡（黄色）
        display = self._detect_calcification(display)  # 钙化（蓝色）

        # 更新显示
        self._update_canvas(display)

    def _detect_spiculation(self, img):
        """基于多尺度Hough变换的毛刺检测 """
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

        def polar_filter(img):
            center = (img.shape[1] // 2, img.shape[0] // 2)
            polar = cv2.linearPolar(img, center, maxRadius=200, flags=cv2.WARP_FILL_OUTLIERS)
            kernel = np.array([[-1, 2, -1]] * 3, dtype=np.float32)  # 垂直线增强模板
            filtered = cv2.filter2D(polar, -1, kernel)
            return cv2.linearPolar(filtered, center, maxRadius=200, flags=cv2.WARP_INVERSE_MAP)

        enhanced = clahe.apply(gray)
        enhanced = polar_filter(enhanced)  # 新增极坐标滤波

        median = np.median(enhanced)
        sigma = 0.33
        lower = int(max(0, (1.0 - sigma) * median))
        upper = int(min(255, (1.0 + sigma) * median))
        edges = cv2.Canny(enhanced, lower, upper)
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
        # 后处理：合并重叠线段
        # 线段合并使用原始灰度图像
        lsd = cv2.createLineSegmentDetector()
        if processing_img.size == 0 or processing_img.dtype != np.uint8:
            raise ValueError(f"无效的输入图像格式: shape={processing_img.shape}, dtype={processing_img.dtype}")

        lsd_lines, _, _, _ = lsd.detect(edges)
        # 合并结果：Hough线段 + LSD线段
        merged_lines = []
        if filtered:  # 当filtered非空时加入
            merged_lines.extend(filtered)
        if lsd_lines is not None:
            merged_lines.extend([line[0].tolist() for line in lsd_lines])  # 确保转换为列表

        # 绘制合并后的线段到显示图像
        for line in merged_lines:
            x1, y1, x2, y2 = map(int, line)
            color = (255, 0, 0) if line in filtered else (0, 255, 0)
            if line in filtered and line in lsd_lines:
                color = (0, 0, 255)  # 重叠部分红色高亮
            cv2.line(display_img, (x1, y1), (x2, y2), color, 2)

        print(f"[DEBUG] 检测到初始线段数: {len(all_lines)}")
        print(f"[DEBUG] 过滤后线段数: {len(filtered)}")
        print(f"[DEBUG] 合并后线段数: {len(merged_lines) if merged_lines is not None else 0}")

        def calc_spiculation_index(lines, img_area):
            total_length = sum(np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2) for line in lines)
            return round(total_length / img_area * 1e4, 2)  # 转换为0.01mm/px²

        print(f"[量化] 毛刺指数: {calc_spiculation_index(merged_lines, img.size)}")
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
            # 计算分叶指数
            lobulation_index = cv2.contourArea(approx) / cv2.contourArea(main_contour)
            print(f"[DEBUG] 分叶指数: {lobulation_index:.2f}")
            print(f"[DEBUG] 近似轮廓点数: {len(approx)}")

    def _detect_vacuole(self, img):
        """空泡检测（黄色圆圈）"""
        # 确保参数为整数
        params = {
            'min_r': int(self.config['vacuole']['min_r']),  # 空泡直径下限1mm
            'max_r': int(self.config['vacuole']['max_r']),  # 直径上限5mm
            'circularity': int(self.config['vacuole']['circularity']),  # 降低圆形度要求（允许卵圆形/不规则）
            'contrast_thresh': int(self.config['vacuole']['contrast_thresh'])  # 新增对比度阈值（排除血管干扰）
        }
        # 确保输入图像为灰度图像
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()
        # 显示用图像单独处理
        display_img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        # 动态阈值二值化
        binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY, 11, 2)
        # # 添加形态学开运算（消除小血管干扰）
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        # # 显示用图像单独处理
        #图像显示
        resize = cv2.resize(opened, (800, 600), interpolation=cv2.INTER_AREA)
        cv2.imshow("Opened Image", resize)

        circles = np.zeros((1, 0, 3), dtype=np.uint16)  # 初始形状 (1, 0, 3)
        hough_circles = cv2.HoughCircles(
            opened, cv2.HOUGH_GRADIENT,
            dp=1.2 if img.shape[1] > 512 else 1.0,  # 高分辨率图像增加dp,  # 提高检测灵敏度
            minDist=15,  # 防止密集区域重叠
            param1=30,  # 降低Canny阈值
            param2=params['circularity'],
            minRadius=params['min_r'],
            maxRadius=params['max_r']
        )
        if hough_circles is not None:
            circles = np.concatenate([circles, hough_circles], axis=1)
        print(f"[DEBUG] HoughCircles检测到圆形数量: {len(circles[0]) if circles is not None else 0}")
        # 第二阶段：轮廓筛选（排除管状结构）
        contours, _ = cv2.findContours(opened, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if params['min_r'] ** 2 * 3.14 < area < params['max_r'] ** 2 * 3.14:
                (x, y), radius = cv2.minEnclosingCircle(cnt)
                if params['min_r'] < radius < params['max_r']:
                    circles = np.append(circles if circles is not None else np.empty((0, 1, 3)),
                                        np.array([[[x, y, radius]]]), axis=1)
        # 对比度验证
        for circle in circles[0]:
            x, y, r = circle
            roi = gray[int(y - r):int(y + r), int(x - r):int(x + r)]
            if roi.size == 0:
                continue
            contrast = (np.max(roi) - np.min(roi)) / 255.0
            if contrast < params['contrast_thresh']:
                continue  # 排除低对比度伪影
        if circles is not None:
            circles = np.uint16(np.around(circles))
            for i in circles[0, :]:
                cv2.circle(display_img, (i[0], i[1]), i[2], (255, 0, 0), 1)
        print(f"[DEBUG] 检测到空泡数量: {len(circles[0]) if circles is not None else 0}")

        # 计算空泡指数
        def calc_vacuole_index(circles, img_area):
            total_area = sum(np.pi * (r ** 2) for _, _, r in circles[0])
            return round(total_area / img_area * 1e4, 2)

        print(f"[量化] 空泡指数: {calc_vacuole_index(circles, img.size)}")
        return display_img

    def _detect_calcification(self, img):
        """智能钙化检测（支持DICOM原始数据或预处理CT图像）"""
        # 类型检测分支
        if self.dicom_image is not None:  # 原始DICOM文件
            # 从DICOM提取HU值
            hu = self.dicom_image.pixel_array.astype(np.int16)
            hu = hu * int(self.dicom_image.RescaleSlope) + int(self.dicom_image.RescaleIntercept)

            # HU值归一化到0-255范围（基于预设窗宽）
            window_center = int(self.dicom_image.WindowCenter)  # 典型值400
            window_width = int(self.dicom_image.WindowWidth)  # 典型值1000
            hu = np.clip(hu, window_center - window_width // 2, window_center + window_width // 2)
            gray = cv2.normalize(hu, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
            if len(gray.shape) == 3:
                gray = cv2.cvtColor(gray, cv2.COLOR_BGR2GRAY)

        else:  # 预处理过的CT图像
            # 转换为灰度图并计算HU统计量
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
            mean_hu = np.mean(gray)
            std_hu = np.std(gray)
            max_hu = np.max(gray)

        # 公共处理流程
        def _common_processing(gray_img):
            # 动态阈值计算（DICOM模式使用绝对值阈值）
            if self.dicom_image is not None:
                hu_thresh = 200  # DICOM模式下直接使用200HU绝对值
            else:
                hu_thresh = max(200, min(max_hu, mean_hu + 3 * std_hu))

            # 二值化与形态学处理
            _, mask = cv2.threshold(gray_img, hu_thresh, 255, cv2.THRESH_BINARY)
            mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY) if len(mask.shape) == 3 else mask
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

            # 连通域过滤
            num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
            if num_labels >= 1:
                areas = stats[1:, cv2.CC_STAT_AREA]
                min_area = max(5, int(np.mean(areas))) if len(areas) > 0 else 5
                for label in range(1, num_labels):
                    if stats[label, cv2.CC_STAT_AREA] < min_area:
                        mask[labels == label] = 0
            return mask

        # 执行通用处理
        mask = _common_processing(gray)

        # 结果可视化（DICOM需要重建彩色图像）
        if self.dicom_image is not None:
            output = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        else:
            output = img.copy()
        output[mask == 255] = (255, 0, 0)  # 钙化区域标蓝

        return output

    def _update_canvas(self, img):
        """更新画布显示（改进版）"""
        # # 转换为RGB并调整尺寸
        # img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        # img = Image.fromarray(img)
        #
        # # 使用双线性插值进行高质量缩放
        # img = img.resize((800, 600), Image.Resampling.LANCZOS)
        #
        # self.tk_img = ImageTk.PhotoImage(img)
        # self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_img)
        # 删除旧图像项
        self.canvas.delete("all")

        # 转换图像格式
        # 保持图像引用
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.current_display = ImageTk.PhotoImage(
            Image.fromarray(img).resize((800, 600), Image.Resampling.LANCZOS)
        )

        self.canvas.create_image(0, 0, image=self.current_display, anchor=tk.NW)
        self.canvas.update_idletasks()  # 强制立即重绘

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
    dicom_dataset = pydicom.dcmread("C:\\Users\\22662\\Desktop\\Graduation Project\\UI\\tools\\multi_nodule_ct.dcm")
    # 初始化分析器
    app = MorphologyAnalyzer(root, roi, dicom_dataset)
    root.mainloop()
