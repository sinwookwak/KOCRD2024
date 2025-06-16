# main_window.py
import logging
from PyQt5.QtWidgets import QMainWindow, QWidget, QSplitter, QVBoxLayout, QMessageBox, QProgressBar
from PyQt5.QtCore import pyqtSignal, Qt
from document_ui_system import DocumentUISystem
from monitoring_ui_system import MonitoringUISystem
from menubar_manager import MenubarManager
from kocrd.config.config import text_manager, AppConfig # text_manager와 AppConfig import
from kocrd.managers.system_manager import SystemManager # 수정된 임포트 경로

class MainWindow(QMainWindow):
    command_processed = pyqtSignal(str, str)  # (Command Text, AI Response) 신호

    def __init__(self, system_manager: SystemManager, ocr_manager, event_manager): # 타입 힌트 추가
        super().__init__()
        self.system_manager = system_manager
        self.system_manager.main_window = self # SystemManager에 main_window 인스턴스 설정
        # model_manager는 SystemManager에서 가져오는 것이 좋습니다.
        self.model_manager = self.system_manager.get_ai_model_manager()
        self.ocr_manager = ocr_manager # OCRManager는 SystemManager에서 가져오는 것이 좋습니다.
        self.event_manager = event_manager # EventManager는 SystemManager에서 관리하는 것이 좋습니다.

        # TextManager는 config.py에서 전역 인스턴스로 이미 초기화되어 있으므로 직접 사용
        self.text_manager = text_manager # 전역 인스턴스를 참조

        # UI 설정은 AppConfig에서 가져옴 (ui.json의 기본값)
        # 텍스트는 text_manager에서 가져옴

        # 창 제목 설정 (text_manager 사용)
        self.setWindowTitle(self.text_manager.get_ui_text("main_window", "title"))

        # 창 크기 설정 (AppConfig에서 가져옴)
        main_window_size = AppConfig.UI_SETTINGS.get("main_window", {}).get("size", {})
        width = main_window_size.get("width", 1200)
        height = main_window_size.get("height", 800)
        self.setGeometry(100, 100, width, height)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        # UI 시스템 초기화 (SystemManager에서 관리하는 것이 더 일관성 있을 수 있습니다)
        # 현재는 MainWindow에서 직접 생성
        self.document_ui_system = DocumentUISystem(self, system_manager, ocr_manager)
        self.monitoring_ui_system = MonitoringUISystem(self, system_manager)

        # MenubarManager 초기화 (SystemManager에서 관리하는 것이 더 일관성 있을 수 있습니다)
        # 현재는 MainWindow에서 직접 생성
        self.menubar_manager = MenubarManager(self, system_manager)
        self.setMenuBar(self.menubar_manager.create_menubar())

        self.setup_ui() # setup_ui 메서드 구현 필요
        logging.info(self.text_manager.get_log_text("328")) # "Window configuration loaded successfully." (text_manager 사용)

    def setup_ui(self):
        """메인 윈도우 UI 레이아웃을 설정합니다."""
        # 이 메서드는 이전 코드에 없었지만, init_ui와 유사한 역할을 할 것으로 예상됩니다.
        # init_ui의 내용을 여기에 옮기거나 init_ui를 setup_ui로 변경하세요.
        self.init_ui() # 기존 init_ui 호출

    def init_ui(self):
        """UI 컴포넌트 레이아웃을 초기화합니다."""
        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.addWidget(self.document_ui_system.get_widget())
        main_splitter.addWidget(self.monitoring_ui_system.get_widget())

        self.setCentralWidget(main_splitter)

    def closeEvent(self, event):
        """창 닫기 이벤트를 처리합니다."""
        reply = QMessageBox.question(
            self,
            self.text_manager.get_general_text("16"), # text_manager 사용
            self.text_manager.get_general_text("16"), # text_manager 사용
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                # SystemManager에 데이터베이스 패키징 위임
                self.system_manager.database_packaging()
                logging.info(self.text_manager.get_log_text("333")) # "Database successfully packaged on close."와 같은 메시지로 변경 고려
            except Exception as e:
                logging.error(self.text_manager.get_error_text("501", e=e)) # text_manager 사용
            event.accept()
        else:
            event.ignore()

    def trigger_process(self, process_type, data=None):
        """SystemManager를 통해 프로세스를 트리거합니다."""
        self.system_manager.trigger_process(process_type, data) # SystemManager에 위임

    def handle_command(self, command_text):
        """GPT 명령을 처리합니다."""
        if not command_text.strip():
            logging.warning(self.text_manager.get_warning_text("405")) # "Command input field is empty."와 같은 메시지로 변경 고려
            return

        try:
            # AI 응답 생성은 MonitoringUISystem 또는 SystemManager의 AI 매니저에 위임
            # 현재 코드는 MonitoringUISystem에 위임하고 있으므로 유지
            response = self.monitoring_ui_system.generate_ai_response(command_text) # MonitoringUISystem에 generate_ai_response 메서드가 있다고 가정
            self.monitoring_ui_system.display_chat_response(response) # MonitoringUISystem에 display_chat_response 메서드가 있다고 가정
            self.command_processed.emit(command_text, response)
        except Exception as e:
            error_message = self.text_manager.get_error_text("517", error=e) # text_manager 사용
            logging.error(error_message)
            QMessageBox.critical(self, self.text_manager.get_error_text("501"), error_message) # text_manager 사용

    def process_ocr_event(self, file_path):
        """OCR 이벤트를 처리합니다."""
        try:
            # OCR 처리는 OCRManager에 위임
            text = self.ocr_manager.extract_text(file_path) # OCRManager에 extract_text 메서드가 있다고 가정
            log_message = self.text_manager.get_log_text("313", file_path=file_path, ocr_result=text[:100] + "...") # text_manager 사용 (결과 일부만 로깅)
            self.monitoring_ui_system.display_log(log_message) # MonitoringUISystem에 display_log 메서드가 있다고 가정
        except Exception as e:
            error_message = self.text_manager.get_error_text("518", error=e) # text_manager 사용
            logging.error(error_message)
            QMessageBox.critical(self, self.text_manager.get_error_text("501"), error_message) # text_manager 사용

    def handle_monitoring_event(self, event_type):
        """AI_Monitoring_event와 연동합니다."""
        try:
            # 이벤트 처리는 EventManager에 위임 (SystemManager에서 관리하는 것이 좋음)
            self.event_manager.handle_monitoring_event(event_type) # EventManager에 handle_monitoring_event 메서드가 있다고 가정
            logging.info(self.text_manager.get_log_text("333", event_type=event_type)) # text_manager 사용 (이벤트 타입 로깅)
        except Exception as e:
            error_message = self.text_manager.get_error_text("519", error=e) # text_manager 사용
            logging.error(error_message)
            QMessageBox.critical(self, self.text_manager.get_error_text("501"), error_message) # text_manager 사용

    def handle_chat(self, message):
        """사용자 메시지를 처리하고 AI 응답을 표시합니다."""
        try:
            if not message.strip():
                logging.warning(self.text_manager.get_warning_text("405")) # text_manager 사용
                return

            # AI 응답 생성 및 표시는 MonitoringUISystem 또는 SystemManager의 AI 매니저에 위임
            # 현재 코드는 MonitoringUISystem에 위임하고 있으므로 유지
            response = self.monitoring_ui_system.generate_ai_response(message) # MonitoringUISystem에 generate_ai_response 메서드가 있다고 가정
            self.monitoring_ui_system.display_chat_message(message, response) # MonitoringUISystem에 display_chat_message 메서드가 있다고 가정

        except Exception as e:
            logging.error(self.text_manager.get_error_text("520", error=e)) # text_manager 사용
            # 오류 메시지를 채팅 창에 표시
            self.monitoring_ui_system.display_chat_message(
                message,
                self.text_manager.get_error_text("520", error=e) # text_manager 사용
            )

    def display_document_content(self, text, source="AI"):
        """문서 내용을 모니터링 패널에 표시합니다."""
        try:
            # 내용 표시는 MonitoringUISystem에 위임
            self.monitoring_ui_system.display_log(self.text_manager.get_log_text("333", source=source, text=text[:100] + "...")) # text_manager 사용 (내용 일부만 로깅)
            logging.info(self.text_manager.get_log_text("333", source=source)) # text_manager 사용 (표시 정보 로깅)
        except Exception as e:
            logging.error(self.text_manager.get_error_text("521", error=e)) # text_manager 사용