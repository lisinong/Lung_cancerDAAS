from pathlib import Path
import cv2
import numpy as np
import pydicom
import xml.etree.ElementTree as ET
from typing import List, Dict, Tuple


class DICOMProcessor:
    def __init__(self, xml_path: Path):

        self.ns = {'ns': 'http://www.nih.gov'}
        self.annotations = self._parse_xml(xml_path)

    def _parse_xml(self, xml_path: Path) -> Dict[str, List[Tuple]]:
        """解析XML注释文件，返回按SOP Instance UID分组的标注"""
        tree = ET.parse(xml_path)
        root = tree.getroot()

        annotations = {}
        for session in root.findall('ns:readingSession', self.ns):
            for nodule in session.findall('ns:unblindedReadNodule', self.ns):
                for roi in nodule.findall('ns:roi', self.ns):
                    sop_uid = roi.find('ns:imageSOP_UID', self.ns).text
                    points = []
                    for edge in roi.findall('ns:edgeMap', self.ns):
                        x = int(edge.find('ns:xCoord', self.ns).text)
                        y = int(edge.find('ns:yCoord', self.ns).text)
                        points.append((x, y))

                    if points:
                        # 计算边界框
                        x_coords = [p[0] for p in points]
                        y_coords = [p[1] for p in points]
                        x_min, x_max = min(x_coords), max(x_coords)
                        y_min, y_max = min(y_coords), max(y_coords)

                        # 保存归一化后的坐标
                        if sop_uid not in annotations:
                            annotations[sop_uid] = []
                        annotations[sop_uid].append(
                            (x_min, y_min, x_max, y_max)
                        )
        return annotations

    def _dicom_to_hu(self, dicom: pydicom.Dataset) -> np.ndarray:
        """将DICOM像素值转换为HU值"""
        pixel_array = dicom.pixel_array
        return pixel_array * dicom.RescaleSlope + dicom.RescaleIntercept

    def _get_yolo_bbox(self,
                       coords: Tuple[int, int, int, int],
                       img_width: int,
                       img_height: int) -> Tuple[float, float, float, float]:
        """将原始坐标转换为YOLO格式的归一化坐标"""
        x_min, y_min, x_max, y_max = coords

        # 计算中心点
        x_center = (x_min + x_max) / 2 / img_width
        y_center = (y_min + y_max) / 2 / img_height

        # 计算宽高
        width = (x_max - x_min) / img_width
        height = (y_max - y_min) / img_height

        return x_center, y_center, width, height

    def process_dicom(self,
                      dcm_path: Path,
                      output_dir: Path,
                      class_id: int = 0) -> Tuple[str, str]:
        """处理单个DICOM文件"""
        try:
            # 读取DICOM文件
            dicom = pydicom.dcmread(dcm_path)
            sop_uid = dicom.SOPInstanceUID

            # 获取HU值
            hu_values = self._dicom_to_hu(dicom)
            original_height, original_width = hu_values.shape

            # 获取对应标注
            bboxes = self.annotations.get(sop_uid, [])

            # 窗宽窗位调整（肺窗）
            window_center = -600
            window_width = 1500
            hu_min = window_center - window_width // 2
            hu_max = window_center + window_width // 2
            hu_clipped = np.clip(hu_values, hu_min, hu_max)

            # 标准化到0-255范围
            normalized = ((hu_clipped - hu_min) / window_width) * 255
            image_8bit = normalized.astype(np.uint8)

            # 保持宽高比的缩放
            scale = 640 / max(original_height, original_width)
            resized_w = int(original_width * scale)
            resized_h = int(original_height * scale)
            resized = cv2.resize(image_8bit, (resized_w, resized_h))

            # 填充黑边至640x640
            padded = np.full((640, 640), 0, dtype=np.uint8)
            pad_top = (640 - resized_h) // 2
            pad_left = (640 - resized_w) // 2
            padded[pad_top:pad_top + resized_h, pad_left:pad_left + resized_w] = resized

            # 创建输出目录
            images_dir = output_dir / "images"
            labels_dir = output_dir / "labels"
            images_dir.mkdir(parents=True, exist_ok=True)
            labels_dir.mkdir(parents=True, exist_ok=True)

            # 保存图像
            img_filename = f"{dcm_path.stem}.jpg"
            img_path = images_dir / img_filename
            cv2.imwrite(str(img_path), padded)

            # 生成并保存标签
            label_path = labels_dir / f"{dcm_path.stem}.txt"
            with open(label_path, 'w') as f:
                for bbox in bboxes:
                    # 转换坐标到缩放后的坐标系
                    x_min = (bbox[0] * scale) + pad_left
                    y_min = (bbox[1] * scale) + pad_top
                    x_max = (bbox[2] * scale) + pad_left
                    y_max = (bbox[3] * scale) + pad_top

                    # 转换为YOLO格式
                    yolo_bbox = self._get_yolo_bbox(
                        (x_min, y_min, x_max, y_max),
                        640, 640
                    )
                    f.write(f"{class_id} {' '.join(f'{v:.6f}' for v in yolo_bbox)}\n")

            return str(img_path), str(label_path)

        except Exception as e:
            print(f"处理文件 {dcm_path.name} 失败: {str(e)}")
            return "None", "None"


if __name__ == "__main__":
    # 配置路径
    input_dir = Path("C:/Users/22662/Desktop/Graduation Project/yolo_data/LIDC-IDRI-1001/")
    xml_path = Path("C:/Users/22662/Desktop/Graduation Project/yolo_data/LIDC-IDRI-1001/104.xml")  # 您的XML文件路径
    output_dir = Path("C:/Users/22662/Desktop/Graduation Project/yolo_data/")

    # 初始化处理器
    processor = DICOMProcessor(xml_path)

    # 处理所有DICOM文件
    for dcm_file in input_dir.glob("*.dcm"):
        img_path, label_path = processor.process_dicom(dcm_file, output_dir)
        if img_path and label_path:
            print(f"成功生成: {img_path} | {label_path}")
