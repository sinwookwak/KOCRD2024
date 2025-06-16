# main_window.py
import logging
from PyQt5.QtWidgets import QMainWindow, QWidget, QSplitter, QVBoxLayout, QMessageBox, QProgressBar
from PyQt5.QtCore import pyqtSignal, Qt
from document_ui_system import DocumentUISystem
from monitoring_ui_system import MonitoringUISystem
from menubar_manager import MenubarManager
from kocrd.config.config import text_manager, AppConfig # text_manager와 AppConfig import

class MainWindow(QMainWindow):
    command_processed = pyqtSignal(str, str)  # (Command Text, AI Response) 신호

    def __init__(self, system_manager, ocr_manager, event_manager):
        super().__init__()
        self.system_manager = system_manager
        self.system_manager.main_window = self
        self.model_manager = self.system_manager.get_ai_model_manager()
        self.ocr_manager = ocr_manager
        self.event_manager = event_manager

        # TextManager는 config.py에서 전역 인스턴스로 이미 초기화되어 있으므로 직접 사용
        self.text_manager = text_manager # 전역 인스턴스를 참조

        # UI 설정은 AppConfig에서 가져옴 (ui.json의 기본값)
        # 텍스트는 text_manager에서 가져옴
        # 창 제목 설정
        self.setWindowTitle(self.text_manager.get_text("ui", "main_window", "title"))

        # 창 크기 설정 (AppConfig에서 가져옴)
        main_window_size = AppConfig.UI_SETTINGS.get("main_window", {}).get("size", {})
        width = main_window_size.get("width", 1200)
        height = main_window_size.get("height", 800)
        self.setGeometry(100, 100, width, height)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        self.document_ui_system = DocumentUISystem(self, system_manager, ocr_manager)
        self.monitoring_ui_system = MonitoringUISystem(self, system_manager)

        self.menubar_manager = MenubarManager(self, system_manager)
        self.setMenuBar(self.menubar_manager.create_menubar())

        self.setup_ui()
        logging.info(self.text_manager.get_text("log", "MSG_328")) # "Window configuration loaded successfully."

    def init_ui(self):
        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.addWidget(self.document_ui_system.get_widget())
        main_splitter.addWidget(self.monitoring_ui_system.get_widget())

        self.setCentralWidget(main_splitter)

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self,
            # self.get_message("16"), # 이전 코드
            # self.get_message("16"), # 이전 코드
            self.text_manager.get_text("general", "16"), # 수정: text_manager 사용
            self.text_manager.get_text("general", "16"), # 수정: text_manager 사용
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
            # logging.error(self.get_error_message("02").format(error=e)) # 이전 코드
            # QMessageBox.critical(self, "Command Error", self.get_error_message("02").format(error=e)) # 이전 코드
            error_message = self.text_manager.get_text("error", "02", error=e) # 수정: text_manager 사용
            logging.error(error_message)
            QMessageBox.critical(self, "Command Error", error_message) # 수정: text_manager 사용
    def process_ocr_event(self, file_path):
        """OCR 이벤트 처리."""
        try:
            text = self.ocr_manager.extract_text(file_path)
            log_message = f"Extracted Text: {text}"
            self.monitoring_ui_system.display_log(log_message)
        except Exception as e:
            # logging.error(self.get_error_message("03").format(error=e)) # 이전 코드
            # QMessageBox.critical(self, "OCR Error", self.get_error_message("03").format(error=e)) # 이전 코드
            error_message = self.text_manager.get_text("error", "03", error=e) # 수정: text_manager 사용
            logging.error(error_message)
            QMessageBox.critical(self, "OCR Error", error_message) # 수정: text_manager 사용

    def handle_monitoring_event(self, event_type):
        """AI_Monitoring_event와 연동."""
        try:
            self.event_manager.handle_monitoring_event(event_type)
            logging.info(f"Monitoring event '{event_type}' handled successfully.")
        except Exception as e:
            # logging.error(self.get_error_message("04").format(error=e)) # 이전 코드
            # QMessageBox.critical(self, "Monitoring Event Error", self.get_error_message("04").format(error=e)) # 이전 코드
            error_message = self.text_manager.get_text("error", "04", error=e) # 수정: text_manager 사용
            logging.error(error_message)
            QMessageBox.critical(self, "Monitoring Event Error", error_message) # 수정: text_manager 사용

    def handle_chat(self, message):
        """사용자 메시지 처리."""
        try:
            if not message.strip():
                logging.warning(self.text_manager.get_text("log", "MSG_EMPTY_MESSAGE"))
                return

            response = self.monitoring_ui_system.generate_ai_response(message)
            self.monitoring_ui_system.display_chat_message(message, response)

        except Exception as e:
            logging.error(self.text_manager.get_text("log", "MSG_CHAT_ERROR", error=e))
            self.monitoring_ui_system.display_chat_message(message, self.text_manager.get_text("log", "MSG_CHAT_ERROR", error=e))

    def display_document_content(self, text, source="AI"):
        """문서 내용 표시."""
        try:
            self.monitoring_ui_system.display_log(self.text_manager.get_text("log", "MSG_DISPLAY_CONTENT", source=source, text=text))
            logging.info(self.text_manager.get_text("log", "MSG_DISPLAYED_CONTENT_INFO", source=source))
        except Exception as e:
            logging.error(self.text_manager.get_text("log", "MSG_DISPLAY_CONTENT_ERROR", error=e))


# system_manager 모듈을 나중에 임포트
from kocrd.system import SystemManager