from PySide6.QtCore import QObject, Signal


class DetectionWorker(QObject):
    finished = Signal(object,list)  # 传递结果
    error = Signal(str)

    def __init__(self,process_func, image_path):
        super().__init__()
        self.image_path = image_path
        self.process_func = process_func

    def run(self):
        try:
            # 将原有 process_image 逻辑迁移到这里
            results,nodules = self.process_func(self.image_path)
            self.finished.emit(results,nodules)  # 传递结果
        except Exception as e:
            self.error.emit(str(e))
