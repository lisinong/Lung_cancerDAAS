import tkinter as tk
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
            'spiculation': {'thresh': 50, 'min_len': 20, 'max_gap': 5},
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

    def _create_slider(self, parent, label, param_key, category, range_vals, scale=1, odd=False):
        """通用滑动条创建方法"""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, padx=5, pady=2)

        ttk.Label(frame, text=label, width=12).pack(side=tk.LEFT)

        # 初始化值处理
        current_val = self.config[category][param_key] * scale

        slider = ttk.Scale(frame, from_=range_vals[0], to=range_vals[1],
                           value=current_val, orient=tk.HORIZONTAL,
                           command=lambda v: self._param_changed(category, param_key, v, scale, odd))
        slider.pack(side=tk.RIGHT, fill=tk.X, expand=True)

        # 实时数值显示
        value_label = ttk.Label(frame, text=f"{self.config[category][param_key]:.2f}")
        value_label.pack(side=tk.RIGHT, padx=5)
        slider.value_label = value_label

    def _create_spiculation_tab(self, notebook):
        """毛刺参数标签页"""
        tab = ttk.Frame(notebook)
        self._create_slider(tab, '阈值', 'thresh', 'spiculation', (1, 200))
        self._create_slider(tab, '最小长度', 'min_len', 'spiculation', (1, 100))
        self._create_slider(tab, '最大间隔', 'max_gap', 'spiculation', (1, 50))
        notebook.add(tab, text='毛刺参数')

    def _create_lobulation_tab(self, notebook):
        """分叶参数标签页"""
        tab = ttk.Frame(notebook)
        self._create_slider(tab, '轮廓精度', 'epsilon', 'lobulation', (1, 100), scale=100)
        self._create_slider(tab, '块大小', 'block', 'lobulation', (3, 255), odd=True)
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

    def _param_changed(self, category, param_key, value, scale=1, odd=False):
        """参数变化处理"""
        # 数值转换
        new_value = float(value) / scale
        if odd:  # 处理奇数参数
            new_value = int(new_value) | 1

        # 更新参数配置
        self.config[category][param_key] = new_value

        # 更新显示
        self.update_image()

        # 更新数值标签显示
        for widget in self.root.winfo_children():
            if isinstance(widget, ttk.Notebook):
                for child in widget.winfo_children():
                    if hasattr(child, 'value_label'):
                        child.value_label.config(text=f"{new_value:.2f}")

    def update_image(self):
        """更新显示图像"""
        display = self.original.copy()

        # 执行所有特征检测
        # self._detect_spiculation(display)  # 毛刺（红色）
        self._detect_lobulation(display)  # 分叶（绿色）
        # self._detect_vacuole(display)  # 空泡（黄色）
        # self._detect_calcification(display)  # 钙化（蓝色）

        # 更新显示
        self._update_canvas(display)

    def _detect_spiculation(self, img):
        """毛刺检测（增加参数验证）"""
        # 确保参数为整数
        params = {
            'threshold': int(self.config['spiculation']['thresh']),
            'minLineLength': int(self.config['spiculation']['min_len']),
            'maxLineGap': int(self.config['spiculation']['max_gap'])
        }

        # 调试输出参数值
        print(f"当前毛刺参数：{params}")

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, **params)

        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                cv2.line(img, (x1, y1), (x2, y2), (0, 0, 255), 1)

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
        _, mask = cv2.threshold(gray,params['hu_thresh'], 255, cv2.THRESH_BINARY)
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
    results = model("C:\\Users\\22662\\Desktop\\Graduation Project\\UI\\images\\0005.png", conf=0.5)
    nodules = []
    roi = []
    for result in results:
        for box in result.boxes:
            # 获取检测框信息
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            # 加载ROI图像（替换为你的实际路径）
            roi = _crop_roi(cv2.imread("C:\\Users\\22662\\Desktop\\Graduation Project\\UI\\images\\0005.png"),
                            (x1, y1, x2, y2))
    # 初始化分析器
    app = MorphologyAnalyzer(root, roi)
    root.mainloop()
