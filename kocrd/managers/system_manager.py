# system_manager.py
import logging
import json
import sys
import os
import time
import threading
import uuid
import pika
import pytesseract
from typing import Dict, Any, Optional
from PyQt5.QtWidgets import QMessageBox, QApplication


from managers.ocr.ocr_manager import OCRManager
from managers.temp_file_manager import TempFileManager
from managers.monitoring_manager import MonitoringManager
from managers.database_manager import DatabaseManager
from managers.menubar_manager import MenubarManager
from managers.document.document_manager import DocumentManager
from managers.ai_managers.AI_model_manager import AIModelManager
from managers.ai_managers.ai_prediction_manager import AIPredictionManager
from managers.ai_managers.AI_data_manager import AIDataManager
from managers.rabbitmq_manager import RabbitMQManager
from managers.settings_manager import SettingsManager
from managers.ai_managers.ai_training_manager import AITrainingManager
from managers.analysis_manager import AnalysisManager
from managers.ai_managers.ai_event_manager import AIEventManager
from managers.ai_managers.ai_ocr_running import AIOCRRunning
from managers.ai_managers.ai_event_manager import AIEventManager

from utils.embedding_utils import generate_document_type_embeddings

# UI 임포트
from ui.menubar_ui import MenubarUI
from ui.document_ui import DocumentUI
from ui.monitoring_ui import MonitoringUI

# config/development.py 임포트
try:
    from config import development
except ImportError as e:
    logging.error(f"config.development 임포트 오류: {e}")
    sys.exit(1)

class SystemManager:
    def __init__(self, settings_manager, main_window, tesseract_cmd, tessdata_dir):
        self.settings_manager = settings_manager
        self.main_window = main_window
        self.tesseract_cmd = tesseract_cmd
        self.tessdata_dir = tessdata_dir
        self.rabbitmq_manager = RabbitMQManager()
        self.managers = {}
        self.uis = {}
        self.settings = self.settings_manager.config # 변수명 변경: self.config -> self.settings
        self.init_components(self.settings) # 변수명 변경

        # Tesseract 설정
        pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
        if self.tessdata_dir:
            pytesseract.pytesseract.tessdata_dir = self.tessdata_dir
            logging.info(f"🟢 Tessdata 설정 완료: {self.tessdata_dir}")

        logging.info(f"🟢 Tesseract 설정 완료: {self.tesseract_cmd}")
        logging.info("🟢 SystemManager 초기화 완료.")


    def _init_components(self, settings: Dict[str, Any]) -> None:
        """설정 파일을 기반으로 매니저 및 UI 초기화"""
        components = {"managers": self.managers, "uis": self.uis}

        for component_type, component_dict in components.items():
            for component_name, component_settings in settings.get(component_type, {}).items():
                try:
                    class_name = component_settings["class"]
                    dependencies = {dep: self.managers.get(dep) for dep in component_settings.get("dependencies", [])}
                    kwargs = component_settings.get("kwargs", {})

                    # 필수 의존성 주입
                    if component_settings.get("inject_settings", False):
                        kwargs["settings_manager"] = self.settings_manager
                    if component_settings.get("inject_main_window", False):
                        kwargs["main_window"] = self.main_window
                    if component_settings.get("inject_system_manager", False):
                        kwargs["system_manager"] = self

                    # 클래스 동적 로드
                    module_name = component_settings.get("module") # module 정보 가져오기
                    if module_name: # module 정보가 있는 경우에만 동적 import
                        try:
                            module = __import__(module_name, fromlist=[class_name])
                        except ModuleNotFoundError as e:
                            logging.error(f"모듈 {module_name}를 찾을 수 없습니다: {e}")
                            sys.exit(1)
                    else: # module 정보가 없는 경우 managers에서 찾도록 수정
                        module_name = f"managers.{component_name}"
                        module = __import__(module_name, fromlist=[class_name])
                    
                    class_ = getattr(module, class_name)
                    component_dict[component_name] = class_(**dependencies, **kwargs)

                    logging.info(f"🟢 {component_type.capitalize()} '{component_name}' 초기화 완료.")
                except Exception as e:
                    logging.error(f" {component_type.capitalize()} '{component_name}' 초기화 실패: {e}")
                    sys.exit(1)

    def database_packaging(self):
        self.get_manager("database").package_database() # get_manager 사용
    def trigger_process(self, process_type: str, data: Optional[Dict[str, Any]] = None):
        """AI 모델 실행 프로세스 트리거"""
        manager = self.get_manager("document")
        if process_type == "document_processing":
            manager.request_document_processing(data)
        elif process_type == "database_packaging":
            self.get_manager("database").request_database_packaging()
        elif process_type == "ai_training":
            manager.request_ai_training(data)
        else:
            logging.warning(f"🔴 알 수 없는 프로세스 유형: {process_type}")
            QMessageBox.warning(self.main_window, "오류", "알 수 없는 작업 유형입니다.")

    def handle_command(self, command_text: str):
        """사용자 명령어 처리"""
        monitoring_manager = self.get_manager("monitoring")
        response = monitoring_manager.generate_ai_response(command_text)
        monitoring_manager.monitoring_ui.display_chat_response("Command", response)
        monitoring_manager.command_processed.emit(command_text, response)

    def train_ai_model(self, training_data):
        if not training_data or not isinstance(training_data, dict):
            self.handle_error("유효하지 않은 학습 데이터를 제공했습니다.", error_code="AI_TRAIN_ERR_001")
            return
        try:
            self.get_ai_manager().train_model(training_data)
            logging.info("AI model training completed.")
        except Exception as e:
            self.handle_error(f"Error during AI model training: {e}", error_code="AI_TRAIN_ERR_002")

    def handle_error(self, message, error_code=None):
        if error_code:
            logging.error(f"{message} (Error Code: {error_code})")
        else:
            logging.error(message)
        QMessageBox.critical(self.parent, "Error", message)

    def start_consuming(self):
        """RabbitMQ 메시지 소비 시작"""
        def consume_messages():
            queues_to_consume = {
                self.settings_manager.get_queue_name("document_processing"): self.get_manager("document").handle_message,
                self.settings_manager.get_queue_name("database_packaging"): self.get_manager("database").handle_message,
                self.settings_manager.get_queue_name("temp_file_queue"): self.get_manager("temp_file").handle_message,
                self.settings_manager.get_queue_name("ai_training_queue"): self.get_manager("ai_trainer").handle_message,
            }

            while True:
                try:
                    if not self.rabbitmq_manager.channel or self.rabbitmq_manager.channel.is_closed:
                        self.rabbitmq_manager.connect_to_rabbitmq()
                    channel = self.rabbitmq_manager.channel

                    for queue, callback in queues_to_consume.items():
                        channel.basic_consume(queue=queue, on_message_callback=callback, auto_ack=False)

                    logging.info("📩 메시지 대기 중... (종료: CTRL+C)")
                    channel.start_consuming()

                except Exception as e:
                    logging.error(f"🔴 RabbitMQ 소비 오류: {e}")
                    time.sleep(5)

        thread = threading.Thread(target=consume_messages, daemon=True)
        thread.start()

    def send_temp_file_message(self, message_type, file_path=None, file_paths=None, callback=None):
        max_retries = 3
        retry_delay = 1

        for attempt in range(max_retries):
            try:
                connection = self.rabbitmq_manager.connection
                if connection is None or connection.is_closed:
                    self.rabbitmq_manager.connect_to_rabbitmq()
                    connection = self.rabbitmq_manager.connection
                channel = connection.channel()

                message = {"type": message_type}
                if file_path:
                    message["file_path"] = file_path
                if file_paths:
                    message["file_paths"] = file_paths

                if callback:
                    callback_queue = str(uuid.uuid4())
                    channel.queue_declare(queue=callback_queue, exclusive=True)
                    channel.basic_consume(queue=callback_queue, on_message_callback=callback, auto_ack=True)
                    channel.basic_publish(
                        exchange='',
                        routing_key=self.settings_manager.get_queue_name("temp_file_queue"),  # 큐 이름을 settings_manager에서 가져옴
                        properties=pika.BasicProperties(reply_to=callback_queue),
                        body=json.dumps(message).encode()
                    )
                else:
                    channel.basic_publish(exchange='', routing_key=development.RABBITMQ_QUEUES["temp_file_queue"], body=json.dumps(message).encode()) # 큐 이름 변경
                return

            except pika.exceptions.AMQPConnectionError as e:
                logging.error(f"RabbitMQ 연결 오류 (시도 {attempt+1}/{max_retries}): {e}")
                QApplication.instance().invoke(lambda: QMessageBox.critical(self.main_window, "RabbitMQ 연결 오류", str(e)))
                time.sleep(retry_delay * (2**attempt))
                continue
            except pika.exceptions.AMQPChannelError as e:
                logging.error(f"RabbitMQ 채널 오류 (시도 {attempt+1}/{max_retries}): {e}")
                QApplication.instance().invoke(lambda: QMessageBox.critical(self.main_window, "RabbitMQ 채널 오류", str(e)))
                time.sleep(retry_delay)
                self.rabbitmq_manager.connect_to_rabbitmq()
                continue
            except pika.exceptions.AMQPError as e:
                logging.error(f"기타 RabbitMQ 오류 (시도 {attempt+1}/{max_retries}): {e}")
                QApplication.instance().invoke(lambda: QMessageBox.critical(self.main_window, "RabbitMQ 오류", str(e)))
                break
            except Exception as e:
                logging.error(f"메시지 전송 중 일반 오류 (시도 {attempt+1}/{max_retries}): {e}")
                QApplication.instance().invoke(lambda: QMessageBox.critical(self.main_window, "오류", f"메시지 전송 중 일반 오류: {e}"))
                break

        logging.error(f"메시지 전송 실패 (최대 {max_retries}회 시도): {message_type}")
        QApplication.instance().invoke(lambda: QMessageBox.critical(self.main_window, "오류", f"메시지 전송에 실패했습니다: {message_type}"))
    def run_embedding_generation(self):
        try:
            settings_manager = self.managers["settings_manager"]
            generate_document_type_embeddings(settings_manager)
            logging.info("임베딩 생성 작업 완료.")
        except KeyError:
            logging.error("SettingsManager가 초기화되지 않았습니다. config 파일을 확인해주세요.")
        except Exception as e:
            logging.exception(f"임베딩 생성 작업 중 오류 발생: {e}")

    def close_rabbitmq_connection(self):
        self.rabbitmq_manager.close_connection()
    def get_ai_manager(self):
        return self.managers.get("ai_prediction")
    def get_manager(self, manager_name: str) -> Optional[Any]:
        return self.managers.get(manager_name)

    def get_ui(self, ui_name: str) -> Optional[Any]:
        return self.uis.get(ui_name)

    def cleanup_temp_dir(self):
        if self.get_manager("temp_file"):
            self.get_manager("temp_file").cleanup_temp_dir()
            logging.info("Temporary directory cleaned through SystemManager.")
