# file_name: main_window.py
import logging
from PyQt5.QtWidgets import QMainWindow, QWidget, QSplitter, QVBoxLayout, QHBoxLayout, QLabel, QMessageBox, QProgressBar, QTextEdit
from PyQt5.QtCore import pyqtSignal
from window.document_ui_system import DocumentUISystem
from window.monitoring_ui_system import MonitoringUISystem
from window.menubar.menubar_manager import MenubarManager

class MainWindow(QMainWindow):
    command_processed = pyqtSignal(str, str)  # (Command Text, AI Response) 신호

    def __init__(self, system_manager, ocr_manager, event_manager):
        super().__init__()
        self.system_manager = system_manager
        self.system_manager.main_window = self  # SystemManager에 MainWindow 인스턴스 설정
        self.model_manager = self.system_manager.get_ai_model_manager()  # SystemManager를 통해 AIModelManager 접근
        self.ocr_manager = ocr_manager
        self.event_manager = event_manager
        self.setWindowTitle("Document Processor")
        self.setGeometry(100, 100, 1200, 800)
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.document_ui_system = DocumentUISystem(self)  # DocumentUISystem 인스턴스 생성
        self.monitoring_ui_system = MonitoringUISystem(self)  # MonitoringUISystem 인스턴스 생성
        self.menubar_manager = MenubarManager(system_manager)  # MenubarManager 인스턴스 생성
        self.setMenuBar(self.menubar_manager.get_ui())  # Menubar UI 설정
        self.init_ui()
        logging.info("MainWindow initialized.")

    def init_ui(self):
        self.document_ui_system.init_ui()
        self.monitoring_ui_system.init_ui()

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
        """GPT 명령 처리."""
        if not command_text.strip():
            logging.warning("Command input field is empty.")
            return

        try:
            response = self.monitoring_ui_system.generate_ai_response(command_text)
            self.monitoring_ui_system.display_chat_response(response)
            self.command_processed.emit(command_text, response)
        except Exception as e:
            logging.error(f"Error handling command '{command_text}': {e}")
            QMessageBox.critical(self, "Command Error", f"Error handling command: {str(e)}")

    def process_ocr_event(self, file_path):
        """OCR 이벤트 처리."""
        try:
            text = self.ocr_manager.extract_text(file_path)
            log_message = f"Extracted Text: {text}"
            self.monitoring_ui_system.display_log(log_message)
        except Exception as e:
            logging.error(f"Error processing OCR event: {e}")
            QMessageBox.critical(self, "OCR Error", f"OCR 처리 중 오류가 발생했습니다: {e}")

    def handle_monitoring_event(self, event_type):
        """AI_Monitoring_event와 연동."""
        try:
            self.event_manager.handle_monitoring_event(event_type)
            logging.info(f"Monitoring event '{event_type}' handled successfully.")
        except Exception as e:
            logging.error(f"Error handling monitoring event: {e}")
            QMessageBox.critical(self, "Monitoring Event Error", f"Monitoring event 처리 중 오류가 발생했습니다: {e}")

    def handle_chat(self, message):
        """사용자 메시지 처리."""
        try:
            if not message.strip():
                logging.warning("Empty message received.")
                return

            response = self.monitoring_ui_system.generate_ai_response(message)
            self.monitoring_ui_system.display_chat_message(message, response)

        except Exception as e:
            logging.error(f"Error in chat handling: {e}")
            self.monitoring_ui_system.display_chat_message(message, "AI 응답 처리 중 오류가 발생했습니다.")

    def display_document_content(self, text, source="AI"):
        """문서 내용 표시."""
        try:
            self.monitoring_ui_system.display_log(f"[{source}]:\n{text}\n")
            logging.info(f"Displayed content from {source}.")
        except Exception as e:
            logging.error(f"Error displaying content: {e}")

# system_manager 모듈을 나중에 임포트
from system import SystemManager
