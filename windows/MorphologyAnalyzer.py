import os

import cv2
import numpy as np
import yaml


class MorphologyAnalyzer:
    def __init__(self):
        # 形态特征阈值配置
        self.config = {
            'spiculation': {  #毛刺
                'hough_threshold': 50,  # 霍夫变换阈值
                'min_length': 20,  # 最小线段长度
                'max_gap': 5  # 最大线段间隙
            },
            'lobulation': {  #分叶
                'block_size': 11,  # 自适应阈值块大小
                'c': 2,  # 自适应阈值常数
                'contour_thresh': 0.03  # 轮廓近似阈值
            },
            'vacuolation': {  #空泡征
                'intensity_thresh': 21.09375,  # 强度阈值
                'area_thresh': 5  # 面积阈值
            },
            'calcification': {  #钙化
                'hu_thresh': 150,  # HU值阈值
                'hu_scale_factor': 2  # HU值缩放因子
            },
            'mm_per_pixel': 0.5  # 关键物理参数
        }

    def load_config(self, filepath):
        """从YAML文件加载配置"""
        try:
            with open(filepath, 'r',encoding='utf-8-sig') as f:
                loaded_config = yaml.safe_load(f)
                self._validate_config(loaded_config)
                self.config = loaded_config
            print(f"成功加载配置：{filepath}")
            return True
        except Exception as e:
            print(f"配置加载失败：{str(e)}")
            return False

    def _validate_config(self, config):
        """验证配置结构有效性"""
        required_keys = {
            'spiculation': ['hough_threshold', 'min_length', 'max_gap'],
            'lobulation': ['block_size', 'c', 'contour_thresh'],
            'vacuolation': ['intensity_thresh', 'area_thresh'],
            'calcification': ['hu_thresh', 'hu_scale_factor'],
            'mm_per_pixel': None
        }

        for section, keys in required_keys.items():
            if section not in config:
                raise ValueError(f"缺失配置段：{section}")
            if keys:
                for key in keys:
                    if key not in config[section]:
                        raise ValueError(f"段[{section}]中缺失参数：{key}")

    def analyze(self, roi_image):
        """输入结节ROI图像和配置字典，返回形态学特征"""
        # 检查输入图像
        if roi_image is None or not isinstance(roi_image, np.ndarray):
            raise ValueError("Invalid input image")
        parent_path = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))
        self.load_config(os.path.join(parent_path, 'param', 'Morphology.yaml'))
        config = self.config
        # 预处理
        gray = cv2.cvtColor(roi_image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)

        # 特征检测
        features = {
            'spiculation': self._detect_spiculation(edges, config['spiculation']),
            'lobulation': self._detect_lobulation(gray, config['lobulation']),
            'calcification': self._detect_calcification(gray, config['calcification'], config['mm_per_pixel']),
            'vacuolation': self._detect_vacuolation(gray, config['vacuolation'], config['mm_per_pixel'])
        }
        return features

    def _detect_spiculation(self, edge_map, params):
        """毛刺检测（使用霍夫线变换）"""
        lines = cv2.HoughLinesP(
            edge_map,
            rho=1,
            theta=np.pi / 180,
            threshold=params.get('hough_threshold', 20),
            minLineLength=params.get('min_length', 5),
            maxLineGap=params.get('max_gap', 5)
        )
        return len(lines) if lines is not None else 0

    def _detect_lobulation(self, gray_img, params):
        """分叶检测（基于轮廓波动）"""
        # 自适应阈值处理
        binary = cv2.adaptiveThreshold(
            gray_img, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            params.get('block_size', 11),
            params.get('c', 2)
        )

        # 轮廓近似
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return 0

        main_contour = max(contours, key=cv2.contourArea)
        epsilon = params.get('contour_thresh', 0.02) * cv2.arcLength(main_contour, True)
        approx = cv2.approxPolyDP(main_contour, epsilon, True)
        return len(approx)

    def _detect_vacuolation(self, gray_img, params, mm_per_pixel):
        """空泡征检测（基于强度阈值）"""
        _, thresh = cv2.threshold(
            gray_img,
            params.get('intensity_thresh', 150),
            255,
            cv2.THRESH_BINARY_INV
        )

        # 连通区域分析
        contours, _ = cv2.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        area_threshold = params.get('area_thresh', 5) / (mm_per_pixel ** 2)
        valid_contours = [c for c in contours if cv2.contourArea(c) > area_threshold]
        return len(valid_contours)

    def _detect_calcification(self, gray_img, params, mm_per_pixel):
        """钙化检测（模拟CT值）"""
        # 模拟HU值转换（假设原始图像已做标准化）
        pseudo_hu = (gray_img - gray_img.mean()) * params.get('hu_scale_factor', 2)
        calcified_area = np.sum(pseudo_hu > params.get('hu_thresh', 130)) * (mm_per_pixel ** 2)
        return calcified_area
