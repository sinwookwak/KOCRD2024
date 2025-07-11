# filename: monitoring_ui_system.py
import json
import logging
from PyQt5.QtWidgets import QProgressBar, QTextEdit, QLineEdit, QListWidget, QVBoxLayout, QWidget
from kocrd.config.config import AppConfig, text_manager

class MonitoringUISystem(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # self.config = load_config("config/ui.json") # load_config 호출 제거
        # self.messages_config = load_config("config/messages.json") # load_config 호출 제거
        # AppConfig와 text_manager는 config.py에서 전역으로 초기화되므로 직접 참조
        self.app_config = AppConfig
        self.text_manager = text_manager
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Progress Bar
        self.progress_bar = QProgressBar(self)
        layout.addWidget(self.progress_bar)

        # Log Display
        self.log_display = QTextEdit(self)
        self.log_display.setReadOnly(True)
        layout.addWidget(self.log_display)

        # Chat Output
        self.chat_output = QTextEdit(self)
        self.chat_output.setReadOnly(True)
        layout.addWidget(self.chat_output)

        # Chat Input
        self.chat_input = QLineEdit(self)
        layout.addWidget(self.chat_input)

        # File List Widget
        self.file_list_widget = QListWidget(self)
        layout.addWidget(self.file_list_widget)

        self.setLayout(layout)
        self.load_ui_config()

    def load_ui_config(self):
        """UI 설정을 로드하고 적용합니다."""
        try:
            # self.config 대신 AppConfig.UI_SETTINGS 사용
            components = self.app_config.UI_SETTINGS.get("components", {}).get("monitoring", {}).get("widgets", [])
            for component in components:
                if component.get("name") == "progress_bar":
                    self.progress_bar.setValue(0)
                elif component.get("name") == "log_display":
                    self.log_display.setPlainText("")
                elif component.get("name") == "chat_output":
                    self.chat_output.setPlainText("")
                elif component.get("name") == "chat_input":
                    self.chat_input.setText("")
                elif component.get("name") == "file_list_widget":
                    self.file_list_widget.clear()
            # get_message 대신 text_manager.get_text 사용 (로그 메시지 키 확인 필요)
            # main_window.py에서 MSG_328을 사용하므로 동일하게 적용
            logging.info(self.text_manager.get_text("log", "MSG_328"))
        except KeyError as e:
            logging.error(f"Error loading UI configuration: {e}")

    def update_progress(self, value):
        """진행률을 업데이트합니다."""
        self.progress_bar.setValue(value)

    def append_log(self, message):
        """로그 메시지를 추가합니다."""
        self.log_display.append(message)

    def append_chat_output(self, message):
        """채팅 출력을 추가합니다."""
        self.chat_output.append(message)

    def generate_ai_response(self, message):
        """AI 응답 생성."""
        try:
            # ...existing code...
            return self.tokenizer.decode(output[0], skip_special_tokens=True)
        except Exception as e:
            logging.error(f"Error generating AI response: {e}")
            # get_message 대신 text_manager.get_text 사용 (오류 메시지 키 확인 필요)
            # 임시로 "error" 카테고리와 "520" 키 사용
            return self.text_manager.get_text("error", "520", default=f"Error generating response: {e}")

    def update_file_list(self, documents):
        """가져온 파일 목록을 업데이트."""
        self.file_list_widget.clear()
        for doc in documents:
            self.file_list_widget.addItem(f"{doc['name']} ({doc['date']})")

    def init_ui(self):
        layout = QVBoxLayout(self) # self를 부모로 설정

        # ProgressBar 추가 (이미 __init__에서 생성됨)
        layout.addWidget(self.progress_bar)

        # Log Display 추가 (이미 __init__에서 생성됨)
        layout.addWidget(self.log_display)

        # Chat Output 추가 (이미 __init__에서 생성됨)
        layout.addWidget(self.chat_output)

        # Chat Input 추가 (이미 __init__에서 생성됨)
        layout.addWidget(self.chat_input)

        # File List Widget 추가 (이미 __init__에서 생성됨)
        layout.addWidget(self.file_list_widget)
