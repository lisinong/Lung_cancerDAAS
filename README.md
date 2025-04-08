# Lung_cancerDAAS

## 介绍
本科毕设项目，基于深度学习的肺癌风险评估系统。本项目旨在通过深度学习模型对医学影像进行分析，评估肺癌风险，并生成详细的报告。

## 运行环境
- 操作系统：Windows 10
- 编程语言：Python 3.8+
- 依赖库：
  - PySide6
  - numpy
  - pydicom
  - OpenCV
  - ultralytics
  - yaml

## 安装步骤
1. 克隆项目仓库：
   ```bash
   git clone https://gitee.com/Lisinong/lung_cancer-daas.git
    ```
2. 进入项目目录：
   ```bash
   cd lung_cancer-daas
    ```
3. 创建虚拟环境（可选）：
   ```bash
    python -m venv venv
    ```
4. 激活虚拟环境：
    - Windows:
      ```bash
      venv\Scripts\activate
        ```
    - Linux/MacOS:
      ```bash
      source venv/bin/activate
      ```
5. 安装依赖库：
   ```bash
    pip install -r requirements.txt
   ```  
6. 运行项目：
   ```bash
   python mainwindow.py
   ```

## 使用说明
1. 启动程序后，主界面将显示系统的基本信息和功能按钮。
2. 点击“导入医学影像”按钮，选择DICOM文件进行加载。
3. 填写患者信息，包括姓名、性别、年龄和病史信息。
4. 点击“开始检测”按钮，系统将对影像进行分析，并评估肺癌风险。
5. 检测完成后，可以点击“导出报告”按钮生成详细的评估报告。
6. 在报告中，系统将提供肺癌风险评估结果、影像分析结果和建议。

## 项目结构
```
Lung_cancerDAAS/
├── README.md
├── LICENSE
├── requirements.txt
├── mainwindow.py
├── ui_form.py
├── tools/
│   ├── __init__.py
│   ├── dicom.py
├── windows/
│   ├── __init__.py
│   ├── PatientInfoDialog.py
│   ├── ReportExportDialog.py
│   ├── RiskConfigDialog.py
│   ├── MorphologyAnalyzer.py
├── param/
│   ├── config.yaml
│   ├── Morphology.yaml
├── models/
│   ├── best.pt
└── resources/

```




