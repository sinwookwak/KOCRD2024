# MonitoringUI.py
from PyQt5.QtWidgets import QWidget, QListWidget, QVBoxLayout, QTextEdit, QLineEdit, QProgressBar, QPushButton, QHBoxLayout
import logging

class MonitoringUI(QWidget):
    """모니터링 UI 생성 클래스."""
    def __init__(self):
        super().__init__()
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("메시지를 입력하세요...")
        self.chat_output = QTextEdit()  # 채팅 출력 영역 추가
        self.chat_output.setReadOnly(True)
        self.file_list_widget = QListWidget()

        self.setup_ui() # UI 구성 메서드 호출

    def setup_ui(self):
        """UI 구성."""
        layout = QVBoxLayout(self) # self에 레이아웃 설정
        layout.addWidget(self.log_display)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.chat_output) # 채팅 출력 영역 추가
        layout.addWidget(self.chat_input)

        send_button = QPushButton("전송")
        layout.addWidget(send_button)

        self.setLayout(layout)
        self.send_button = send_button # send_button 저장

    def set_send_callback(self, callback):
        """전송 버튼 콜백 설정 (MonitoringManager와 연결)."""
        self.send_button.clicked.connect(lambda: callback(self.chat_input.text().strip())) # MonitoringManager의 handle_chat과 연결

    def create_button_section(self, document_manager, ocr_manager):
        """버튼 섹션 생성."""
        button_section = QHBoxLayout()

        import_button = QPushButton("문서 가져오기")
        import_button.clicked.connect(document_manager.batch_import_documents) # DocumentManager의 batch_import_documents와 연결
        button_section.addWidget(import_button)

        reset_button = QPushButton("작업 초기화")
        reset_button.clicked.connect(ocr_manager.reset_work) # OCRManager의 reset_work와 연결
        button_section.addWidget(reset_button)

        scan_button = QPushButton("스캔")
        scan_button.clicked.connect(lambda: ocr_manager.scan_documents([])) # OCRManager의 scan_documents와 연결
        button_section.addWidget(scan_button)

        return button_section

    def update_progress(self, value, total):
        """진행 상태를 업데이트."""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(value)

    def display_log(self, message):
        """로그 영역에 메시지 출력."""
        self.log_display.append(message)

    def display_chat_message(self, message, response):
        """채팅 메시지 표시."""
        self.chat_output.append(f"사용자: {message}")
        self.chat_output.append(f"AI: {response}")

    def update_file_list(self, documents):
        """가져온 파일 목록을 업데이트."""
        self.file_list_widget.clear()
        for doc in documents:
            self.file_list_widget.addItem(f"{doc['name']} ({doc['date']})")