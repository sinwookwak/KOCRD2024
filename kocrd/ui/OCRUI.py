#OCR_UI.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QProgressBar, QPushButton, QHBoxLayout

class OCRUI:
    """OCR 관련 UI 요소 생성 클래스."""
    def create_button_layout(self, parent, system_manager):
        """OCR 관련 버튼 생성."""
        button_layout = QHBoxLayout()

        # 스캔 버튼
        scan_button = QPushButton("스캔", parent)
        scan_button.clicked.connect(lambda: system_manager.ocr_manager.scan_documents(parent.get_selected_files()))
        button_layout.addWidget(scan_button)

        return button_layout
    def setup_widget(self):
        """모니터링 창 생성."""
        monitoring_window = QWidget()
        layout = QVBoxLayout(monitoring_window)

        # 로그 출력
        log_display = QTextEdit()
        log_display.setReadOnly(True)
        layout.addWidget(log_display)

        # 진행 상태 Progress Bar
        progress_bar = QProgressBar()
        progress_bar.setMaximum(100)
        layout.addWidget(progress_bar)

        return monitoring_window
