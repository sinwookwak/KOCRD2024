# file: system.py
import json
import logging
import os
import sys
import pytesseract
from typing import Dict, Any, Optional
from PyQt5.QtWidgets import QMessageBox

from managers.database_manager import DatabaseManager
from managers.ocr.ocr_manager import OCRManager
from Settings.settings_manager import SettingsManager
from managers.document.document_manager import DocumentManager
from managers.ai_managers.ai_model_manager import AIModelManager
from managers.temp_file_manager import TempFileManager
from managers.rabbitmq_manager import RabbitMQManager
from window.menubar.menubar_manager import MenubarManager
from utils.embedding_utils import EmbeddingUtils

logging.basicConfig(level=logging.DEBUG)

def process_message(process_func):
    """메시지를 처리하는 공통 함수"""
    def wrapper(channel, method, properties, body, manager):
        try:
            process_func(channel, method, properties, body, manager)
            channel.basic_ack(delivery_tag=method.delivery_tag)
        except json.JSONDecodeError as e:
            logging.error(f"JSON 파싱 오류: {e}")
            channel.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
        except Exception as e:
            logging.error(f"메시지 처리 중 오류 발생: {e}")
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    return wrapper

def process_document(channel, method, properties, body, document_manager):
    """문서 처리 함수"""
    message = json.loads(body.decode())
    file_paths = message.get("file_paths", [])
    if not file_paths:
        logging.warning(f"파일 경로 없음. 메시지 내용: {body.decode()}")
        return
    for file_path in file_paths:
        document_manager.load_document(file_path)
    logging.info(f"문서 처리 완료: {file_paths}")

def process_database_packaging(channel, method, properties, body, database_manager):
    """데이터베이스 패키징 함수"""
    database_manager.package_database()
    logging.info("데이터베이스 패키징 완료")

def process_ai_training(channel, method, properties, body, ai_manager):
    """AI 학습 처리 함수"""
    ai_manager.train_ai()
    logging.info("AI 학습 완료")

def process_temp_file_manager(channel, method, properties, body, temp_file_manager):
    """임시 파일 관리"""
    temp_file_manager.handle_message(channel, method, properties, body)
    logging.info("임시 파일 관리 작업 완료")

def process_ai_prediction(channel, method, properties, body, ai_prediction_manager):
    """AI 예측 수행"""
    ai_prediction_manager.handle_message(channel, method, properties, body)
    logging.info("AI 예측 작업 완료")

def process_ai_event(channel, method, properties, body, ai_event_manager):
    """AI 이벤트 핸들링"""
    ai_event_manager.handle_message(channel, method, properties, body)
    logging.info("AI 이벤트 작업 완료")

def process_ai_ocr_running(channel, method, properties, body, ai_ocr_running):
    """AI OCR 실행"""
    ai_ocr_running.handle_ocr_result(channel, method, properties, body)
    logging.info("AI OCR 실행 작업 완료")

def create_manager(manager_config, settings_manager):
    """설정 파일에서 매니저 인스턴스를 생성합니다."""
    module_name = manager_config["module"]
    class_name = manager_config["class"]
    kwargs = manager_config.get("kwargs", {})
    module = __import__(module_name, fromlist=[class_name])
    manager_class = getattr(module, class_name)
    return manager_class(settings_manager, **kwargs)

class SystemManager:
    def __init__(self, settings_manager: SettingsManager, main_window=None, tesseract_cmd=None, tessdata_dir=None):
        self.settings_manager = settings_manager
        self.main_window = main_window  # MainWindow 인스턴스 설정
        self.tesseract_cmd = tesseract_cmd
        self.tessdata_dir = tessdata_dir
        self.managers = {}
        self.uis = {}
        self.settings = self.load_development_settings()
        self._init_components(self.settings)
        self.initialize_managers()

    def initialize_managers(self):
        config = self.settings
        for manager_name, manager_config in config["managers"].items():
            self.managers[manager_name] = self.create_manager_instance(manager_config)

        self.managers["temp_file"] = self.create_temp_file_manager()
        self.managers["rabbitmq"] = self.create_rabbitmq_manager()
        self.managers["database"] = self.create_database_manager()
        self.managers["menubar"] = self.create_menubar_manager()
        self.managers["document"] = self.create_document_manager()
        self.managers["ocr"] = self.create_ocr_manager()
        self._configure_tesseract()

    def create_manager_instance(self, manager_config):
        manager_class = self.get_class(manager_config["module"], manager_config["class"])
        kwargs = manager_config.get("kwargs", {})
        dependencies = [self.managers[dep] for dep in manager_config.get("dependencies", [])]
        return manager_class(*dependencies, **kwargs)

    def create_temp_file_manager(self):
        return TempFileManager(self.settings_manager)

    def create_rabbitmq_manager(self):
        return RabbitMQManager(self.settings_manager)

    def create_database_manager(self):
        return DatabaseManager(self.settings_manager.get_setting("db_path"), self.settings_manager.get_setting("backup_path"))

    def get_temp_file_manager(self):
        return self.managers.get("temp_file")

    def get_database_manager(self):
        return self.managers.get("database")

    def get_rabbitmq_manager(self):
        return self.managers.get("rabbitmq")

    def create_menubar_manager(self):
        return MenubarManager(self.main_window)

    def create_document_manager(self):
        return DocumentManager(self.settings_manager)

    def create_ocr_manager(self):
        return OCRManager(self.settings_manager)

    def _configure_tesseract(self):
        pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
        if self.tessdata_dir:
            pytesseract.pytesseract.tessdata_dir = self.tessdata_dir
            logging.info(f"🟢 Tessdata 설정 완료: {self.tessdata_dir}")
        logging.info(f"🟢 Tesseract 설정 완료: {self.tesseract_cmd}")
        logging.info("🟢 SystemManager 초기화 완료.")

    def _init_components(self, settings: Dict[str, Any]) -> None:
        """설정 파일을 기반으로 매니저 및 UI 초기화"""
        for component_type, component_dict in settings.items():
            for component_name, component_settings in component_dict.items():
                try:
                    class_ = self.get_class(component_settings["module"], component_settings["class"])
                    dependencies = [self.managers[dep] for dep in component_settings.get("dependencies", [])]
                    kwargs = component_settings.get("kwargs", {})
                    component_dict[component_name] = class_(*dependencies, **kwargs)
                    logging.info(f"🟢 {component_type.capitalize()} '{component_name}' 초기화 완료.")
                except Exception as e:
                    logging.error(f"🔴 {component_type.capitalize()} '{component_name}' 초기화 실패: {e}")
                    sys.exit(1)

    def database_packaging(self):
        self.get_manager("database").package_database()  # get_manager 사용

    def trigger_process(self, process_type: str, data: Optional[Dict[str, Any]] = None):
        """AI 모델 실행 프로세스 트리거"""
        if process_type == "database_packaging":
            self.get_temp_file_manager().database_packaging()
        elif process_type == "document_processing":
            self.get_manager("document").request_document_processing(data)
        elif process_type == "ai_training":
            self.get_manager("ai_training").request_ai_training(data)
        elif process_type == "generate_text":
            ai_manager = self.get_ai_manager()
            if ai_manager:
                return ai_manager.generate_text(data.get("command", ""))
            else:
                logging.error("AIManager가 초기화되지 않았습니다.")
        else:
            logging.warning(f"🔴 알 수 없는 프로세스 유형: {process_type}")
            QMessageBox.warning(self.main_window, "오류", "알 수 없는 작업 유형입니다.")

    def handle_error(self, message, error_code=None):
        if error_code:
            logging.error(f"{message} (Error Code: {error_code})")
        else:
            logging.error(message)
        QMessageBox.critical(self.main_window, "Error", message)

    def run_embedding_generation(self):
        EmbeddingUtils.run_embedding_generation(self.settings_manager)

    def close_rabbitmq_connection(self):
        self.get_rabbitmq_manager().close_connection()

    def get_ai_manager(self):
        return self.managers.get("ai_prediction")

    def get_manager(self, manager_name: str) -> Optional[Any]:
        return self.managers.get(manager_name)

    def get_ui(self, ui_name: str) -> Optional[Any]:
        return self.uis.get(ui_name)

    def get_ai_model_manager(self):
        """AIModelManager 인스턴스 반환."""
        return self.managers.get("ai_model")

    def get_class(self, module_name: str, class_name: str):
        """모듈에서 클래스를 동적으로 가져옵니다."""
        module = __import__(module_name, fromlist=[class_name])
        return getattr(module, class_name)

def main():
    """메인 실행 함수"""
    settings_manager = SettingsManager()
    
    connection, channel = settings_manager.connect_to_rabbitmq()
    if connection is None:
        logging.error("RabbitMQ 연결 실패. 종료합니다.")
        return

    try:
        channel.basic_qos(prefetch_count=1)

        config = settings_manager.load_development_settings()
        queues = config["queues"].values()
        for queue in queues:
            channel.queue_declare(queue=queue, durable=True)

        channel.basic_consume(queue=config["queues"]["document_processing"], on_message_callback=process_message(process_document), auto_ack=False)
        channel.basic_consume(queue=config["queues"]["database_packaging"], on_message_callback=process_message(process_database_packaging), auto_ack=False)
        channel.basic_consume(queue=config["queues"]["ai_training_queue"], on_message_callback=process_message(process_ai_training), auto_ack=False)

        logging.info("메시지 대기 중... 종료하려면 CTRL+C를 누르세요.")
        channel.start_consuming()

    except KeyboardInterrupt:
        logging.info("작업 중지됨. RabbitMQ 연결 종료.")
        if connection and connection.is_open:
            connection.close()

if __name__ == "__main__":
    main()
