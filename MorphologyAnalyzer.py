import cv2
import numpy as np


class MorphologyAnalyzer:
    def __init__(self):
        # 形态特征阈值配置
        self.config = {
            'spiculation': {'min_length': 5, 'angle_var': 30},  # 毛刺特征
            'lobulation': {'min_peaks': 3, 'contour_thresh': 0.15},  # 分叶特征
            'calcification': {'min_white': 0.3, 'grain_size': 3}  # 钙化特征
        }

    def analyze(self, roi_image):
        """输入结节ROI图像，返回形态学特征"""
        # 预处理
        gray = cv2.cvtColor(roi_image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)

        # 特征检测
        features = {
            'spiculation': self._detect_spiculation(edges),
            'lobulation': self._detect_lobulation(gray),
            # 'calcification': self._detect_calcification(gray)
        }
        return features

    def _detect_spiculation(self, edge_map):
        """基于霍夫线变换的毛刺检测"""
        lines = cv2.HoughLinesP(edge_map, 1, np.pi / 180,
                                threshold=20, minLineLength=5)
        return len(lines) if lines is not None else 0

    def _detect_lobulation(self, gray_img):
        """基于轮廓波动的分叶检测"""
        contours, _ = cv2.findContours(cv2.adaptiveThreshold(gray_img, 255,
                                                             cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2),
                                       cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            main_contour = max(contours, key=cv2.contourArea)
            peri = cv2.arcLength(main_contour, True)
            approx = cv2.approxPolyDP(main_contour, 0.02 * peri, True)
            return len(approx)
        return 0
