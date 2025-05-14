import os
import tempfile
from pathlib import Path

from PySide6.QtCore import QUrl, QPoint
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QListWidget, QStackedWidget, QTextBrowser, QPushButton, \
    QApplication
from docx import Document


class HelpSystem(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.setWindowTitle("帮助中心")
        self.resize(800, 600)
        self._setup_ui()
        self._setup_styles()
        self.position_window()

    def _setup_ui(self):
        # 主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # 左侧导航
        self.nav_list = QListWidget()
        self.nav_list.setFixedWidth(200)
        layout.addWidget(self.nav_list)

        # 右侧内容区
        self.content_stack = QStackedWidget()
        layout.addWidget(self.content_stack)

        # 初始化帮助文档
        self._load_help_documents()

        # 下载按钮
        self.statusBar().setSizeGripEnabled(False)
        download_btn = QPushButton("下载完整手册")
        download_btn.setFixedSize(120, 32)
        download_btn.clicked.connect(self._download_manual)
        self.statusBar().addPermanentWidget(download_btn)

        # 连接信号
        self.nav_list.currentRowChanged.connect(self.content_stack.setCurrentIndex)

    def _setup_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f7;
                background-image: radial-gradient(circle at 1px 1px, #e0e0e0 1px, transparent 0);
                background-size: 8px 8px;
            }
            QListWidget {
                background: rgba(240,240,240,0.9);
                border-right: 1px solid #cccccc;
                font-size: 14px;
                padding: 8px 0;
            }
            QListWidget::item {
                height: 36px;
                padding-left: 16px;
            }
            QListWidget::item:selected {
                background: #e0e0e0;
                border-right: 3px solid #0078d4;
            }
            QTextBrowser {
                background: transparent;
                border: none;
                padding: 20px;
                font-size: 13px;
                line-height: 1.6;
            }
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 6px 12px;
                min-width: 120px;
            }
        """)

    def _load_help_documents(self):
        """加载所有Word格式的帮助文档"""
        doc_config = [
            ("操作指南", "操作指南.docx"),
            ("常见问题", "常见问题.docx"),
            ("隐私保护", "隐私保护.docx")
        ]

        parent_path = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))

        for title, filename in doc_config:
            self.nav_list.addItem(title)
            text_browser = self._create_text_browser(Path(os.path.join(parent_path, 'docx', filename)))
            self.content_stack.addWidget(text_browser)

    def _create_text_browser(self, doc_path):
        """创建并初始化文本浏览器"""
        browser = QTextBrowser()
        browser.setOpenLinks(False)

        if doc_path.exists():
            html_content = self._convert_docx_to_html(doc_path)
            browser.setHtml(html_content)
        else:
            browser.setHtml(f"<h3 style='color: #dc3545;'>文档缺失: {doc_path.name}</h3>")

        return browser

    def _convert_docx_to_html(self, doc_path):
        """将Word文档转换为HTML内容"""
        doc = Document(doc_path)
        html = ["<div style='font-family: 微软雅黑;'>"]

        # 样式映射
        style_map = {
            'Heading 1': ('h2', 'font-size: 18px; color: #2c3e50; margin: 20px 0 12px;'),
            'Heading 2': ('h3', 'font-size: 16px; color: #34495e; margin: 16px 0 10px;'),
            'Normal': ('p', 'margin: 8px 0;')
        }

        for para in doc.paragraphs:
            style = para.style.name
            tag, default_style = style_map.get(style, ('p', ''))

            # 处理段落文本
            para_html = []
            for run in para.runs:
                text = run.text.strip()
                if not text:
                    continue

                # 文本格式
                if run.bold:
                    text = f"<strong>{text}</strong>"
                if run.italic:
                    text = f"<em>{text}</em>"
                if run.underline:
                    text = f"<u>{text}</u>"

                para_html.append(text)

            # 添加段落
            if para_html:
                html.append(f"<{tag} style='{default_style}'>{' '.join(para_html)}</{tag}>")

        # 处理图片
        img_index = 0
        for rel in doc.part.rels.values():
            if "image" in rel.target_ref:
                img_path = self._save_image(rel.target_part.blob, img_index)
                html.append(
                    f"<div style='margin: 15px 0; text-align: center;'>"
                    f"<img src='{img_path}' style='max-width: 95%; height: auto; border-radius: 4px;'>"
                    f"</div>"
                )
                img_index += 1

        html.append("</div>")
        return "\n".join(html)

    def _save_image(self, image_data, index):
        """保存图片到临时目录并返回文件路径"""
        temp_path = Path(self.temp_dir.name) / f"img_{index}.png"
        with open(temp_path, "wb") as f:
            f.write(image_data)
        return QUrl.fromLocalFile(str(temp_path)).toString()

    def _download_manual(self):
        """下载完整手册"""
        parent_path = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))
        manual_path = QUrl.fromLocalFile(os.path.join(parent_path, 'resources', 'user_manual.pdf'))
        if manual_path.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(manual_path)))
        else:
            self.statusBar().showMessage("手册文件未找到", 3000)

    def position_window(self):
        """定位窗口在主界面右侧"""
        if self.parent():
            main_geo = self.parent().geometry()
            self.move(main_geo.right() + 20, main_geo.top())
