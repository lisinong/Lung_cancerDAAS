import pydicom
from pydicom.dataset import Dataset, FileDataset
import numpy as np
from datetime import datetime


# 创建测试用DICOM文件
def create_sample_dcm(output_path):
    # 创建基础数据集
    file_meta = Dataset()
    file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.2'  # CT Image Storage
    file_meta.MediaStorageSOPInstanceUID = '1.2.3.4.5.6.7.8.9'
    file_meta.TransferSyntaxUID = '1.2.840.10008.1.2.1'  # Little Endian Explicit

    ds = FileDataset(output_path, {}, file_meta=file_meta, preamble=b"\0" * 128)

    # 添加患者信息
    ds.PatientName = "张^三"
    ds.PatientSex = "M"
    ds.PatientAge = "045Y"  # DICOM格式的年龄表示
    ds.PatientID = "12345678"

    # 添加设备信息
    ds.Modality = "CT"
    ds.BodyPartExamined = "CHEST"
    ds.SliceThickness = "1.0"
    ds.KVP = 120  # 管电压

    # 设置扫描参数
    ds.RescaleSlope = 1.0
    ds.RescaleIntercept = -1024.0  # 将原始数据转换为HU值

    # 创建10x10的测试像素数据（CT值范围）
    pixel_data = np.array([
        [-1000, -200, 0, 40, 1000],
        [30, 50, 70, 100, 200],
        [300, 400, 500, 600, 700],
        [800, 900, 1000, 1100, 1200],
        [1300, 1400, 1500, 1600, 1700]
    ], dtype=np.int16)

    ds.PixelData = pixel_data.tobytes()
    ds.Rows, ds.Columns = pixel_data.shape
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 1  # signed integer

    # 设置必要的时间标签
    ds.ContentDate = datetime.now().strftime('%Y%m%d')
    ds.ContentTime = datetime.now().strftime('%H%M%S')

    # 保存文件
    ds.save_as(output_path)
    return ds


# 使用示例
if __name__ == "__main__":
    create_sample_dcm("sample_ct.dcm")
    print("测试DICOM文件已生成：sample_ct.dcm")