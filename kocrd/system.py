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
from managers.temp_file_manager import TempFileManager
from kocrd.window.menubar_manager import MenubarManager
from utils.embedding_utils import EmbeddingUtils
from kocrd.config.config import ConfigManager
from kocrd.managers.system_manager import SystemManager

logging.basicConfig(level=logging.DEBUG)

def process_message(process_func):
    """메시지를 처리하는 공통 함수"""
    def wrapper(channel, method, properties, body, system_manager: SystemManager):  # system_manager 타입 힌트 추가
        try:
            process_func(channel, method, properties, body, system_manager)  # system_manager 전달
            channel.basic_ack(delivery_tag=method.delivery_tag)
        except json.JSONDecodeError as e:
            logging.error(system_manager.get_message("error", "512").format(e=e, body=body))  # system_manager.get_message 호출
            channel.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
        except Exception as e:
            logging.error(system_manager.get_message("error", "513").format(e=e, body=body))  # system_manager.get_message 호출
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    return wrapper

def handle_process(channel, method, properties, body, system_manager: SystemManager, process_func):  # system_manager 인자 추가
    """공통 메시지 처리 함수"""
    message = json.loads(body.decode())
    process_func(system_manager, message)  # system_manager 전달
    logging.info(system_manager.get_message("log", "333").format(message=message))  # system_manager.get_message 호출


def process_document(system_manager: SystemManager, message):  # system_manager 인자 추가
    """문서 처리 함수"""
    file_paths = message.get("file_paths", [])
    if not file_paths:
        logging.warning(system_manager.get_message("warning", "403").format(message=message))  # system_manager.get_message 호출
        return
    for file_path in file_paths:
        system_manager.get_manager("document").load_document(file_path) # system_manager를 통해 document manager 접근
    logging.info(system_manager.get_message("log", "324").format(file_paths=file_paths))  # system_manager.get_message 호출


def process_database_packaging(system_manager: SystemManager, message):
    """데이터베이스 패키징 함수"""
    system_manager.get_manager("database").package_database()
    logging.info(system_manager.get_message("log", "330"))

def process_ai_training(system_manager: SystemManager, message):
    """AI 학습 처리 함수"""
    system_manager.get_manager("ai_training").train_ai()
    logging.info(system_manager.get_message("log", "331"))

def process_temp_file_manager(system_manager: SystemManager, message):
    """임시 파일 관리"""
    system_manager.get_manager("temp_file").handle_message(message)
    logging.info(system_manager.get_message("log", "315"))

def process_ai_prediction(system_manager: SystemManager, message):
    """AI 예측 수행"""
    system_manager.get_manager("ai_prediction").handle_message(message)
    logging.info(system_manager.get_message("log", "332"))

def process_ai_event(system_manager: SystemManager, message):
    """AI 이벤트 핸들링"""
    system_manager.get_manager("ai_event").handle_message(message)
    logging.info(system_manager.get_message("log", "333"))

def process_ai_ocr_running(system_manager: SystemManager, message):
    """AI OCR 실행"""
    system_manager.get_manager("ai_ocr_running").handle_ocr_result(message)
    logging.info(system_manager.get_message("log", "334"))

def create_manager(manager_config, settings_manager):
    """설정 파일에서 매니저 인스턴스를 생성합니다."""
    module_name = manager_config["module"]
    class_name = manager_config["class"]
    kwargs = manager_config.get("kwargs", {})
    module = __import__(module_name, fromlist=[class_name])
    manager_class = getattr(module, class_name)
    return manager_class(settings_manager, **kwargs)
class SystemManager:
    def __init__(self, settings_path="config/development.json", main_window=None, tesseract_cmd=None, tessdata_dir=None, settings_manager=None): # settings_manager 인자 추가
        self.config_manager = ConfigManager(settings_path)  # ConfigManager 인스턴스 생성
        self.settings = self.config_manager.get("settings")  # 설정 로드
        self.settings_manager = settings_manager  # settings_manager 할당
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
        self.managers["ai_model"] = self.create_ai_model_manager()  # AIModelManager 추가
        self._configure_tesseract()

    def create_manager_instance(self, manager_config):
        manager_class = self.get_class(manager_config["module"], manager_config["class"])
        kwargs = manager_config.get("kwargs", {})
        dependencies = [self.managers[dep] for dep in manager_config.get("dependencies", [])]
        return manager_class(*dependencies, **kwargs)

    def create_temp_file_manager(self):
        return TempFileManager(self.settings_manager)

    def create_rabbitmq_manager(self):
        return self  # SystemManager에서 RabbitMQManager 통합

    def create_database_manager(self):
        return DatabaseManager(self.settings_manager.get_setting("db_path"), self.settings_manager.get_setting("backup_path"))

    def create_ai_model_manager(self):
        from kocrd.managers.ai_managers.ai_model_manager import AIModelManager
        return AIModelManager(self.settings_manager)  # AIModelManager 생성

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
            logging.info(self.get_message("log", "320").format(tessdata_dir=self.tessdata_dir)) # self.get_message
        logging.info(self.get_message("log", "319").format(tesseract_cmd=self.tesseract_cmd)) # self.get_message
        logging.info(self.get_message("log", "333")) # self.get_message

    def _init_components(self, settings: Dict[str, Any]) -> None:
        """설정 파일을 기반으로 매니저 및 UI 초기화"""
        for component_type, component_dict in settings.items():
            for component_name, component_settings in component_dict.items():
                try:
                    class_ = self.get_class(component_settings["module"], component_settings["class"])
                    dependencies = [self.managers[dep] for dep in component_settings.get("dependencies", [])]
                    kwargs = component_settings.get("kwargs", {})
                    component_dict[component_name] = class_(*dependencies, **kwargs)
                    logging.info(self.get_message("log", "328").format(component_type=component_type.capitalize(), component_name=component_name)) # self.get_message
                except Exception as e:
                    logging.error(self.get_message("error", "333").format(component_type=component_type.capitalize(), component_name=component_name, e=e)) # self.get_message
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
                ai_manager = self.get_manager("ai_prediction")
                if ai_manager:
                    return ai_manager.generate_text(data.get("command", ""))
                else:
                    logging.error(self.get_message("error", "514")) # self.get_message 추가
            else:
                logging.warning(self.get_message("warning", "404").format(process_type=process_type)) # self.get_message 추가
                QMessageBox.warning(self.main_window, "오류", self.get_message("warning", "404").format(process_type=process_type)) # self.get_message 추가

    def get_message(self, message_type: str, message_code: str) -> str:
        """메시지 설정에서 메시지를 가져옵니다."""
        try:
            messages = self.config_manager.get("messages", {}) # default 값으로 빈 딕셔너리 지정
            return messages[message_type][message_code]
        except KeyError:
            logging.error(f"Message not found: {message_type} - {message_code}")
            return f"Message not found: {message_type} - {message_code}"  # 메시지 없을 경우 기본 메시지 반환

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
    system_manager = SystemManager(settings_manager)  # SystemManager 인스턴스 생성

    connection, channel = settings_manager.connect_to_rabbitmq()

    if connection is None:
        logging.error(system_manager.get_message("error", "511")) # system_manager.get_message 사용
        return

    try:
        channel.basic_qos(prefetch_count=1)

        config = settings_manager.load_development_settings()
        queues = config["queues"].values()
        for queue in queues:
            channel.queue_declare(queue=queue, durable=True)

        document_manager = settings_manager.get_manager("document")
        database_manager = settings_manager.get_manager("database")
        ai_manager = settings_manager.get_manager("ai_training")

        channel.basic_consume(
            queue=config["queues"]["document_processing"],
            on_message_callback=process_message(lambda ch, method, props, body: handle_process(ch, method, props, body, system_manager, process_document)),
            auto_ack=False
        )
        channel.basic_consume(queue=config["queues"]["database_packaging"], on_message_callback=process_message(lambda ch, method, props, body: handle_process(ch, method, props, body, database_manager, process_database_packaging)), auto_ack=False)
        channel.basic_consume(queue=config["queues"]["ai_training_queue"], on_message_callback=process_message(lambda ch, method, props, body: handle_process(ch, method, props, body, ai_manager, process_ai_training)), auto_ack=False)

        logging.info(system_manager.get_message("log", "333"))  # system_manager.get_message 호출
        channel.start_consuming()

    except KeyboardInterrupt:
        logging.info(system_manager.get_message("log", "333"))  # system_manager.get_message 호출
        if connection and connection.is_open:
            connection.close()

if __name__ == "__main__":
    main()
