import logging
import os
import json
from PyQt5.QtWidgets import QMainWindow, QWidget, QSplitter, QVBoxLayout, QMessageBox, QProgressBar
from PyQt5.QtCore import pyqtSignal
from window.document_ui_system import DocumentUISystem
from window.monitoring_ui_system import MonitoringUISystem
from kocrd.window.menubar_manager import MenubarManager
from kocrd.config.messages import messages

class MainWindow(QMainWindow):
    command_processed = pyqtSignal(str, str)  # (Command Text, AI Response) 신호

    def __init__(self, system_manager, ocr_manager, event_manager):
        super().__init__()
        self.system_manager = system_manager
        self.system_manager.main_window = self  # SystemManager에 MainWindow 인스턴스 설정
        self.model_manager = self.system_manager.get_ai_model_manager()  # SystemManager를 통해 AIModelManager 접근
        self.ocr_manager = ocr_manager
        self.event_manager = event_manager

        self.config = self.load_config()
        self.setWindowTitle(self.messages["main_window"]["title"])
        self.setGeometry(100, 100, self.messages["main_window"]["size"]["width"], self.messages["main_window"]["size"]["height"])

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        self.document_ui_system = DocumentUISystem(self)  # DocumentUISystem 인스턴스 생성
        self.monitoring_ui_system = MonitoringUISystem(self)  # MonitoringUISystem 인스턴스 생성
        self.menubar_manager = MenubarManager(system_manager)  # MenubarManager 인스턴스 생성
        self.setMenuBar(self.menubar_manager.get_ui())  # Menubar UI 설정

        self.messages = messages["messages"]
        self.error_messages = messages["error"]

        self.init_ui()
        logging.info("MainWindow initialized.")

    def init_ui(self):
        self.document_ui_system.init_ui()
        self.monitoring_ui_system.init_ui()

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self, 
            self.get_message("16"), 
            self.get_message("16"),
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                self.system_manager.database_packaging() # SystemManager에 위임
                logging.info("Database successfully packaged on close.")
            except Exception as e:
                logging.error(f"Error packaging database on close: {e}")
            event.accept()
        else:
            event.ignore()

    def trigger_process(self, process_type, data=None):
        self.system_manager.trigger_process(process_type, data) # SystemManager에 위임

    def handle_command(self, command_text):
        """GPT 명령 처리."""
        if not command_text.strip():
            logging.warning("Command input field is empty.")
            return

        try:
            response = self.monitoring_ui_system.generate_ai_response(command_text)
            self.monitoring_ui_system.display_chat_response(response)
            self.command_processed.emit(command_text, response)
        except Exception as e:
            logging.error(self.get_error_message("02").format(error=e))
            QMessageBox.critical(self, "Command Error", self.get_error_message("02").format(error=e))

    def process_ocr_event(self, file_path):
        """OCR 이벤트 처리."""
        try:
            text = self.ocr_manager.extract_text(file_path)
            log_message = f"Extracted Text: {text}"
            self.monitoring_ui_system.display_log(log_message)
        except Exception as e:
            logging.error(self.get_error_message("03").format(error=e))
            QMessageBox.critical(self, "OCR Error", self.get_error_message("03").format(error=e))

    def handle_monitoring_event(self, event_type):
        """AI_Monitoring_event와 연동."""
        try:
            self.event_manager.handle_monitoring_event(event_type)
            logging.info(f"Monitoring event '{event_type}' handled successfully.")
        except Exception as e:
            logging.error(self.get_error_message("04").format(error=e))
            QMessageBox.critical(self, "Monitoring Event Error", self.get_error_message("04").format(error=e))

    def handle_chat(self, message):
        """사용자 메시지 처리."""
        try:
            if not message.strip():
                logging.warning("Empty message received.")
                return

            response = self.monitoring_ui_system.generate_ai_response(message)
            self.monitoring_ui_system.display_chat_message(message, response)

        except Exception as e:
            logging.error(self.get_error_message("05"))
            self.monitoring_ui_system.display_chat_message(message, self.get_error_message("05"))

    def display_document_content(self, text, source="AI"):
        """문서 내용 표시."""
        try:
            self.monitoring_ui_system.display_log(f"[{source}]:\n{text}\n")
            logging.info(f"Displayed content from {source}.")
        except Exception as e:
            logging.error(self.get_error_message("06").format(error=e))

    def load_config(self):
        """설정 파일을 로드하거나 기본 설정을 생성합니다."""
        print(messages["601"])  # Window configuration loaded successfully.
        return messages

    def get_message(self, key):
        """메시지 키를 통해 메시지를 가져옵니다."""
        return self.messages.get(key, "메시지를 찾을 수 없습니다.")

    def get_error_message(self, key):
        """에러 메시지 키를 통해 에러 메시지를 가져옵니다."""
        return self.error_messages.get(key, "에러 메시지를 찾을 수 없습니다.")

# system_manager 모듈을 나중에 임포트
from system import SystemManager
