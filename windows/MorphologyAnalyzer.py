import os

import cv2
import numpy as np
import pydicom
import yaml


class MorphologyAnalyzer:
    def __init__(self):
        # 形态特征阈值配置
        self.config = {
            'spiculation': {  # 毛刺
                'hough_threshold': 50,  # 霍夫变换阈值
                'min_length': 20,  # 最小线段长度
                'max_gap': 5  # 最大线段间隙
            },
            'lobulation': {  # 分叶
                'block_size': 11,  # 自适应阈值块大小
                'c': 2,  # 自适应阈值常数
                'contour_thresh': 0.03  # 轮廓近似阈值
            },
            'vacuolation': {  # 空泡征
                'intensity_thresh': 21.09375,  # 强度阈值
                'area_thresh': 5  # 面积阈值
            },
            'calcification': {'min_area': 10,
                              'max_area': 100  # 钙化
                              },
            'physical_params': {'mm_per_pixel': 0.5}  # 关键物理参数
        }

    def load_config(self, filepath):
        """从YAML文件加载配置"""
        try:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
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
            'calcification': ['min_area', 'max_area'],
            'physical_params': ['mm_per_pixel']
        }

        for section, keys in required_keys.items():
            if section not in config:
                raise ValueError(f"缺失配置段：{section}")
            if keys:
                for key in keys:
                    if key not in config[section]:
                        raise ValueError(f"段[{section}]中缺失参数：{key}")

    def analyze(self, roi_image, dicom_data):
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
            'calcification': self._detect_calcification(gray, dicom_data, config['calcification'],
                                                        config['physical_params']['mm_per_pixel']),
            'vacuolation': self._detect_vacuolation(gray, config['vacuolation'],
                                                    config['physical_params']['mm_per_pixel'])
        }
        return features

    def _detect_spiculation(self, edge_map, params):
        """毛刺检测（使用霍夫线变换）"""
        lines = cv2.HoughLinesP(
            edge_map,
            rho=1,
            theta=np.pi / 180,
            threshold=params.get('hough_threshold', 30),
            minLineLength=params.get('min_length', 10),
            maxLineGap=params.get('max_gap', 3)
        )
        # 线段过滤
        if lines is not None:
            filtered_lines = []
            for line in lines:
                x1, y1, x2, y2 = line[0]
                length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
                if length > params.get('min_length', 10):
                    filtered_lines.append(line)
            lines = filtered_lines
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

    # def _detect_calcification(self, gray_img, params, mm_per_pixel):
    #     """钙化检测（模拟CT值）"""
    #     # 模拟HU值转换（假设原始图像已做标准化）
    #     pseudo_hu = (gray_img - gray_img.mean()) * params.get('hu_scale_factor', 2)
    #     calcified_area = np.sum(pseudo_hu > params.get('hu_thresh', 130)) * (mm_per_pixel ** 2)
    #     return calcified_area
    def _detect_calcification(self, gray_img, dicom_data, params, mm_per_pixel):
        """智能钙化检测（支持DICOM原始数据或预处理CT图像）"""
        # 类型检测分支
        if dicom_data is not None:
            # 使用标准肺窗设置（窗宽1500，窗位-600）
            hu = dicom_data.pixel_array.astype(np.int16)
            hu = hu * int(dicom_data.RescaleSlope) + int(dicom_data.RescaleIntercept)

            # 调整窗宽窗位计算方式
            window_center = -600  # 肺窗中心
            window_width = 1500  # 肺窗宽度
            min_hu = window_center - window_width // 2
            max_hu = window_center + window_width // 2
            hu = np.clip(hu, min_hu, max_hu)

            # 优化归一化并增强对比度
            gray = cv2.normalize(hu, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
            gray = cv2.equalizeHist(gray)  # 直方图均衡化

        else:
            # 普通CT图像预处理
            if len(gray_img.shape) == 3:
                gray = cv2.cvtColor(gray_img, cv2.COLOR_BGR2GRAY)
            else:
                gray = gray_img.copy()

        # 公共处理流程
        def _common_processing(gray_img):
            # 动态阈值计算（DICOM模式使用绝对值阈值）
            # 动态阈值计算（DICOM模式使用绝对值阈值）
            if dicom_data is not None:
                # DICOM模式下：200HU对应的实际像素值需要重新计算
                # 原错误：直接使用200作为阈值，未考虑归一化映射
                window_range = window_width  # 1500（改进后代码中的窗宽）
                hu_thresh_pixel = int(255 * (200 - (window_center - window_width // 2)) / window_range)
                hu_thresh = max(50, min(hu_thresh_pixel, 200))  # 安全范围限制
            else:
                # 普通CT图像：确保阈值与输入图像匹配
                hu_thresh = 200 if np.max(gray_img) > 200 else np.max(gray_img) * 0.9

                # 修复阈值应用（原代码错误使用THRESH_BINARY导致阈值失效）
            _, mask = cv2.threshold(
                gray_img,
                hu_thresh,  # 实际使用的阈值
                255,
                cv2.THRESH_BINARY_INV if dicom_data else cv2.THRESH_BINARY  # DICOM需要反向阈值
            )

            # 连通域过滤增强
            contours, _ = cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            sum_area = 0
            for cnt in contours:
                area = cv2.contourArea(cnt) / mm_per_pixel
                if params.get('min_area', 10) < area < params.get('max_area', 100):  # 钙化结节典型尺寸
                    sum_area += 1
            return sum_area

        # 执行通用处理
        return _common_processing(gray)

        # #计算钙化面积
        # return np.sum(mask == 255) * (mm_per_pixel ** 2)
