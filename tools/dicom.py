import pydicom
from pydicom.dataset import Dataset, FileDataset
import numpy as np
from datetime import datetime


def add_nodules(base_hu, nodule_count=3, size_range=(5, 10), hu_range=(-400, 600)):
    """在基础HU矩阵中添加随机结节"""
    rows, cols = base_hu.shape
    nodules = []

    for _ in range(nodule_count):
        # 随机生成结节参数
        size = np.random.randint(*size_range)
        hu = np.random.randint(*hu_range)
        center_y = np.random.randint(size, rows - size)
        center_x = np.random.randint(size, cols - size)

        # 生成圆形掩模
        y, x = np.ogrid[-center_y:rows - center_y, -center_x:cols - center_x]
        mask = x ** 2 + y ** 2 <= size ** 2

        # 检查与已有结节的重叠
        if np.all(base_hu[mask] == -950):  # 仅检查是否为肺实质区域
            base_hu[mask] = hu
            nodules.append((center_x / cols, center_y / rows,
                            (2 * size) / cols, (2 * size) / rows))

    return base_hu, nodules


def create_dynamic_matrix(matrix_size=256):
    # 生成肺实质模拟背景（中心区域HU=-950，外周逐渐降低）
    mask = np.zeros((matrix_size, matrix_size))
    y, x = np.ogrid[-matrix_size//2:matrix_size//2, -matrix_size//2:matrix_size//2]
    mask = x**2 + y**2 <= (matrix_size//3)**2  # 中心圆形区域
    base_hu = np.where(mask, -950, -1000)     # 肺实质HU=-950，背景空气HU=-1000
    return base_hu.astype(np.int16)


def auto_window_settings(hu_values):
    """自动计算最佳窗宽窗位"""
    valid_hu = hu_values[hu_values > -900]
    center = np.median(valid_hu)
    width = np.ptp(valid_hu) * 1.2  # 增加20%余量
    return round(center), round(width)


def create_sample_dcm(output_path, matrix_size=256, nodule_count=3):
    """创建包含多结节的DICOM文件"""
    # 创建基础数据集
    file_meta = Dataset()
    file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.2'
    file_meta.MediaStorageSOPInstanceUID = pydicom.uid.generate_uid()
    file_meta.TransferSyntaxUID = '1.2.840.10008.1.2.1'

    ds = FileDataset(output_path, {}, file_meta=file_meta, preamble=b"\0" * 128)

    # 生成动态矩阵
    pixel_data = create_dynamic_matrix(matrix_size)
    pixel_data, bboxes = add_nodules(pixel_data, nodule_count=nodule_count)

    # 自动设置窗宽窗位
    wc, ww = auto_window_settings(pixel_data)
    # 添加设备坐标系信息
    ds.ImagePositionPatient = ['0', '0', '0']  # 起始扫描位置
    ds.ImageOrientationPatient = ['1', '0', '0', '0', '1', '0']  # 轴向扫描

    # 增强DICOM-SR兼容性（参考LIDC-IDRI标准）
    ds.StudyDescription = "Simulated Lung Nodule Study"
    ds.SeriesDescription = "CT Nodule Phantom"
    ds.ProtocolName = "Lung_Nodule_Detection_v1.2"
    ds.SpecificCharacterSet = "GB18030"  # 设置字符集为 GB18030（适用于中文）
    # 关键DICOM标签配置
    ds.PatientName = "张三"
    ds.PatientID = "SIM20240409"
    ds.PatientAge = "045Y"  # 45岁
    ds.PatientSex = "M"  # 男性
    ds.Modality = "CT"
    ds.BodyPartExamined = "LUNG"
    ds.SliceThickness = "1.0"
    ds.WindowCenter = str(wc)
    ds.WindowWidth = str(ww)
    ds.RescaleSlope = 1.0
    ds.RescaleIntercept = -1024
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    # 像素数据设置
    ds.PixelData = pixel_data.tobytes()
    ds.Rows, ds.Columns = pixel_data.shape
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 1

    # 时间标签
    now = datetime.now()
    ds.ContentDate = now.strftime('%Y%m%d')
    ds.ContentTime = now.strftime('%H%M%S')

    # 保存文件
    ds.save_as(output_path)
    return ds, bboxes


# 使用示例
if __name__ == "__main__":
    ds, bboxes = create_sample_dcm("multi_nodule_ct.dcm",
                                   matrix_size=256,
                                   nodule_count=5)
    print(f"生成成功，包含{len(bboxes)}个结节")
    print("YOLO格式标注：", bboxes)
