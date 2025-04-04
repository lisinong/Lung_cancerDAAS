from tkinter import Tk, filedialog

import cv2
import numpy as np
import yaml
from ultralytics import YOLO

from MorphologyAnalyzer import MorphologyAnalyzer


class MorphologyTuner:
    """形态学参数调谐工具类"""

    def __init__(self, analyzer, sample_roi):
        self.analyzer = analyzer
        self.sample_roi = sample_roi.copy()
        self.current_roi = sample_roi.copy()
        self.root_tk = Tk()
        self.root_tk.withdraw()

        # 创建OpenCV窗口
        cv2.namedWindow('Morphology Tuning')
        cv2.resizeWindow('Morphology Tuning', 800, 600)
        self._create_trackbars()
        self._update_hints()
        self.update_display()

    def _create_trackbars(self):
        """创建带中文标签的滑动条（需要支持中文的OpenCV编译）"""
        cv2.createTrackbar('毛刺阈值', 'Morphology Tuning',
                           self.analyzer.config['spiculation']['hough_threshold'],
                           100, self._update_spiculation)
        cv2.createTrackbar('最小长度', 'Morphology Tuning',
                           self.analyzer.config['spiculation']['min_length'],
                           50, self._update_spiculation)
        cv2.createTrackbar('分叶精度(x100)', 'Morphology Tuning',
                           int(self.analyzer.config['lobulation']['contour_thresh'] * 100),
                           50, self._update_lobulation)

    def _update_spiculation(self, val):
        """毛刺参数更新回调"""
        self.analyzer.config['spiculation']['hough_threshold'] = cv2.getTrackbarPos('HoughThresh', 'Morphology Tuning')
        self.analyzer.config['spiculation']['min_length'] = cv2.getTrackbarPos('MinLength', 'Morphology Tuning')
        self.update_display()

    def _update_lobulation(self, val):
        """分叶参数更新回调"""
        self.analyzer.config['lobulation']['contour_thresh'] = cv2.getTrackbarPos(
            'ContourThresh(x100)', 'Morphology Tuning') / 100.0
        self.update_display()

    def _update_calcification(self, val):
        """钙化参数更新回调"""
        self.analyzer.config['calcification']['hu_thresh'] = cv2.getTrackbarPos(
            'HUThresh', 'Morphology Tuning')
        self.update_display()

    def _visualize_features(self, roi, features):
        """特征可视化叠加"""
        display = roi.copy()
        # 毛刺可视化（绘制检测到的线）
        edges = cv2.Canny(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY), 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180,
                                self.analyzer.config['spiculation']['hough_threshold'],
                                minLineLength=self.analyzer.config['spiculation']['min_length'],
                                maxLineGap=self.analyzer.config['spiculation']['max_gap'])
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                cv2.line(display, (x1, y1), (x2, y2), (0, 0, 255), 2)

        # 分叶可视化（绘制近似轮廓）
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY, self.analyzer.config['lobulation']['block_size'],
                                       self.analyzer.config['lobulation']['c'])
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            main_contour = max(contours, key=cv2.contourArea)
            epsilon = self.analyzer.config['lobulation']['contour_thresh'] * cv2.arcLength(main_contour, True)
            approx = cv2.approxPolyDP(main_contour, epsilon, True)
            cv2.drawContours(display, [approx], -1, (0, 255, 0), 2)

        # 信息叠加
        cv2.putText(display, f"Spiculations: {features['spiculation']}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        cv2.putText(display, f"Lobulations: {features['lobulation']}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        return display

    def _update_hints(self, message=None):
        """更新键盘操作提示"""
        self.current_roi = self.sample_roi.copy()
        hints = [
            "操作提示：",
            "S - 保存配置",
            "L - 加载配置",
            "ESC - 退出"
        ]
        y_start = self.current_roi.shape[0] - 30 * len(hints)
        for i, text in enumerate(hints):
            cv2.putText(self.current_roi, text, (10, y_start + 30 * i),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        if message:
            cv2.putText(self.current_roi, message, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    def handle_key_events(self, key):
        """处理键盘事件"""
        if key == ord('s'):
            self._save_config()
        elif key == ord('l'):
            self._load_config()

    def _save_config(self):
        """保存配置"""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".yaml",
            filetypes=[("YAML配置", "*.yaml")]
        )
        if filepath:
            try:
                with open(filepath, 'w') as f:
                    yaml.safe_dump(self.analyzer.config, f)
                self._update_hints(f"配置已保存至：{filepath}")
            except Exception as e:
                self._update_hints(f"保存失败：{str(e)}")

    def _load_config(self):
        """加载配置"""
        filepath = filedialog.askopenfilename(
            filetypes=[("YAML配置", "*.yaml")]
        )
        if filepath:
            try:
                with open(filepath, 'r') as f:
                    self.analyzer.config = yaml.safe_load(f)
                self._update_hints(f"配置已加载：{filepath}")
            except Exception as e:
                self._update_hints(f"加载失败：{str(e)}")

    def update_display(self):
        """更新显示并处理键盘事件"""
        # 合并参数提示
        param_text = [
            f"毛刺阈值: {self.analyzer.config['spiculation']['hough_threshold']}",
            f"最小长度: {self.analyzer.config['spiculation']['min_length']}",
            f"分叶精度: {self.analyzer.config['lobulation']['contour_thresh']:.2f}"
        ]
        display_img = self.current_roi.copy()
        for i, text in enumerate(param_text):
            cv2.putText(display_img, text, (10, 100 + 30 * i),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)

        cv2.imshow('Morphology Tuning', display_img)

    def _convert_config_types(self, config):
        """递归转换配置中的numpy类型为Python原生类型"""
        if isinstance(config, dict):
            return {k: self._convert_config_types(v) for k, v in config.items()}
        elif isinstance(config, (np.generic, np.ndarray)):
            return config.item()
        return config


def _crop_roi(image, coords, padding=5):
    """带安全边界的ROI裁剪"""
    h, w = image.shape[:2]
    x1, y1, x2, y2 = [int(round(c)) for c in coords]
    x1 = max(0, x1 - padding)
    y1 = max(0, y1 - padding)
    x2 = min(w, x2 + padding)
    y2 = min(h, y2 + padding)
    return image[y1:y2, x1:x2]


# 使用示例
if __name__ == "__main__":
    analyzer = MorphologyAnalyzer()
    # YOLO模型推理
    model = YOLO("C:/Users/22662/Desktop/Graduation Project/UI/best.pt")
    model.to('cuda')
    results = model("C:/Users/22662/Desktop/Graduation Project/UI/images/0005.png", conf=0.5)
    nodules = []
    for result in results:
        for box in result.boxes:
            # 获取检测框信息
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            cls = int(box.cls[0].item())
            conf = box.conf[0].item()
            # ROI特征分析
            roi = _crop_roi(cv2.imread("C:/Users/22662/Desktop/Graduation Project/UI/images/0005.png"),
                            (x1, y1, x2, y2))
            # 加载已有配置（可选）
            # analyzer.load_config("default_config.yaml")

            tuner = MorphologyTuner(analyzer, roi)

            while True:
                key = cv2.waitKey(1) & 0xFF
                if key == 27:  # ESC退出
                    break
                tuner.handle_key_events(key)
                tuner.update_display()

            cv2.destroyAllWindows()
            tuner.root_tk.destroy()
