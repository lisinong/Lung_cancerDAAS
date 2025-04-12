import os

import cv2
import numpy as np
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
            'calcification': {  # 钙化
                'hu_thresh': 150,  # HU值阈值
                'hu_scale_factor': 2  # HU值缩放因子
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
            'calcification': ['hu_thresh', 'hu_scale_factor'],
            'physical_params': ['mm_per_pixel']
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
            'calcification': self._detect_calcification(gray, config['calcification'],
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

    def _detect_calcification(self, gray_img, params, mm_per_pixel):
        """钙化检测（模拟CT值）"""
        # 模拟HU值转换（假设原始图像已做标准化）
        pseudo_hu = (gray_img - gray_img.mean()) * params.get('hu_scale_factor', 2)
        calcified_area = np.sum(pseudo_hu > params.get('hu_thresh', 130)) * (mm_per_pixel ** 2)
        return calcified_area


class MorphologyAnalyzerbak:
    def __init__(self):
        # 形态特征阈值配置
        self.avg_HU = None  # 平均HU值
        self.dicom_metadata = {}  # 初始化DICOM元数据存储
        self.enhancement_data = None  # 增强CT数据
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
            'calcification': {  # 钙化
                'hu_thresh': 150,  # HU值阈值
                'hu_scale_factor': 2  # HU值缩放因子
            },
            'mm_per_pixel': 0.5  # 关键物理参数
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
        # 多尺度霍夫变换增强[1,7](@ref)
        lines_list = []
        for scale in params['scale_factors']:
            scaled_img = cv2.resize(edge_map, None, fx=scale, fy=scale,
                                    interpolation=cv2.INTER_AREA)
            lines = cv2.HoughLinesP(
                scaled_img,
                rho=1,
                theta=np.pi / 180,
                threshold=params['hough_threshold'],
                minLineLength=int(params['min_length'] * scale),
                maxLineGap=params['max_gap']
            )
            if lines is not None:
                lines_list.extend(lines * (1 / scale))

        # 放射状角度过滤[1](@ref)
        valid_lines = []
        center = (edge_map.shape[1] // 2, edge_map.shape[0] // 2)
        for line in lines_list:
            x1, y1, x2, y2 = line[0]
            vec = np.array([x2 - x1, y2 - y1])
            radial_vec = np.array([x1 - center[0], y1 - center[1]])
            angle = np.degrees(np.arccos(
                np.dot(vec, radial_vec) / (np.linalg.norm(vec) * np.linalg.norm(radial_vec) + 1e-5)
            ))
            if params['angle_range'][0] < angle < params['angle_range'][1]:
                valid_lines.append(line)
        return len(valid_lines)  # HU差异阈值[1](@ref)

    def _detect_lobulation(self, gray_img, params):
        # 动态轮廓近似[1](@ref)
        contour = max(self.safe_find_contours(gray_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE),
                      key=cv2.contourArea)
        epsilon = params['epsilon_ratio'] * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)

        # 深度比计算[1](@ref)
        depth_ratios = []
        for i in range(len(approx)):
            pt1 = approx[i][0]
            pt2 = approx[(i + 1) % len(approx)][0]
            chord = np.linalg.norm(pt2 - pt1)
            max_dist = 0
            for pt in contour:
                dist = (np.abs(np.cross(pt2 - pt1, pt1 - pt[0])) / chord)
                max_dist = max(max_dist, dist)
            depth_ratios.append(max_dist / chord)

        return sum(ratio > params['depth_ratio_threshold'] for ratio in depth_ratios)

    def _detect_vacuolation(self, gray_img, params, mm_per_pixel):
        # 结合患者平均HU值调整阈值
        if self.avg_HU is None:
            raise ValueError("缺失患者平均HU值")
        # 3D形态学滤波（网页4的3D洞填充思想）
        mask = cv2.inRange(gray_img, self.avg_HU - 50, self.avg_HU + 100)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        cleaned = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)  # 添加实际使用
        contours, _ = cv2.findContours(cleaned, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)  # 使用处理后的图像

        # 体积计算
        voxel_volume = (mm_per_pixel ** 2) * params.get('slice_thickness', 1.0)
        valid_contours = [c for c in contours if cv2.contourArea(c) * voxel_volume > params['min_volume']]
        return len(valid_contours)

    def calibrate_hu(self, ct_image):
        """实现网页10的HU动态校准"""
        if not self.dicom_metadata.get('rescale_slope'):
            raise ValueError("缺失DICOM元数据RescaleSlope/Intercept")
        return ct_image * self.dicom_metadata['rescale_slope'] + self.dicom_metadata['rescale_intercept']

    def safe_find_contours(self, image, mode, method):
        # 兼容OpenCV 2.x/3.x/4.x（网页5）
        if cv2.__version__.startswith('2'):
            _, contours, _ = cv2.findContours(image, mode, method)
        else:
            contours, _ = cv2.findContours(image, mode, method)
        return contours

    def _detect_calcification(self, gray_img, params, mm_per_pixel):
        # HU校准
        hu_image = self.calibrate_hu(gray_img)

        # 形态学预处理
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        morph_img = cv2.morphologyEx(gray_img, cv2.MORPH_OPEN, kernel)

        # 轮廓检测（网页5）
        contours = self.safe_find_contours(
            morph_img,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )
        if not contours:
            return 0

        # 形态学特征过滤
        valid_contours = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            circularity = 4 * np.pi * area / (cv2.arcLength(cnt, True) ** 2)
            if circularity > 0.7 and area > params['min_speckle']:
                valid_contours.append(cnt)

        # 多期相分析（需提前加载enhancement_data）
        if self.enhancement_data is not None:
            final_contours = []
            for cnt in valid_contours:
                # 创建轮廓掩膜
                mask = np.zeros_like(gray_img)
                # cv2.drawContours(mask, [cnt], -1, 255, -1)
                # 计算HU差异均值
                delta_hu = np.mean(np.abs(hu_image[mask == 255] - self.enhancement_data[mask == 255]))
                if delta_hu < params['enhancement_thresh']:
                    final_contours.append(cnt)
            valid_contours = final_contours

        return len(valid_contours) * (mm_per_pixel ** 2)
