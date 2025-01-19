# file_name: MainApplication or OCR_AI_0_05.py
# main_window.py
import logging
from PyQt5.QtWidgets import QMainWindow, QWidget, QSplitter, QVBoxLayout, QHBoxLayout, QLabel, QMessageBox, QProgressBar

class MainWindow(QMainWindow):
    def __init__(self, system_manager): # SystemManager 인스턴스를 인자로 받음
        super().__init__()
        self.system_manager = system_manager # SystemManager 저장
        self.setWindowTitle("Document Processor")
        self.setGeometry(100, 100, 1200, 800)
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.init_ui()
        logging.info("MainWindow initialized.")

    def init_ui(self):
        # UI 관련 코드만 남김
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        central_widget.setLayout(QVBoxLayout())

        splitter = QSplitter(central_widget)
        central_widget.layout().addWidget(splitter)

        document_ui = self.system_manager.get_ui("document")
        splitter.addWidget(document_ui)

        monitoring_ui = self.system_manager.get_ui("monitoring")
        if isinstance(monitoring_ui, QWidget):
            if monitoring_ui.layout() is None:
                monitoring_layout = QVBoxLayout()
                monitoring_ui.setLayout(monitoring_layout)
            else:
                monitoring_layout = monitoring_ui.layout()
            monitoring_layout.addWidget(self.progress_bar)
        else:
            logging.error("Monitoring UI is not a QWidget. Cannot add progress bar.")

        splitter.setSizes([1000, 200])
        logging.info("MainWindow UI initialized.")

    def closeEvent(self, event):
        reply = QMessageBox.question(self, '프로그램 종료', '프로그램을 종료하시겠습니까?',
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                self.system_manager.database_packaging() # SystemManager에 위임
                logging.info("Database successfully packaged on close.")
            except Exception as e:
                logging.error(f"Error packaging database on close: {e}")
            event.accept()
        else:
            event.ignore()

    # 다른 UI 이벤트 핸들러들...
    def trigger_process(self, process_type, data=None):
        self.system_manager.trigger_process(process_type, data) # SystemManager에 위임

    def handle_command(self, command_text):
        self.system_manager.handle_command(command_text) # SystemManager에 위임
    # ... 다른 UI 관련 메서드들
