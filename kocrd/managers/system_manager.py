# file_name: system_manager.py
import logging
import json
import sys
import os
import pika
import pytesseract
from typing import Dict, Any, Optional
from PyQt5.QtWidgets import QMessageBox, QApplication

from kocrd.config.config import load_config, load_language_pack, get_message, handle_error, send_message_to_queue
from kocrd.managers.ocr.ocr_manager import OCRManager
from kocrd.managers.temp_file_manager import TempFileManager
from kocrd.managers.database_manager import DatabaseManager
from kocrd.window.menubar_manager import MenubarManager
from kocrd.managers.document.document_manager import DocumentManager
from kocrd.Settings.settings_manager import SettingsManager
from kocrd.utils.embedding_utils import generate_document_type_embeddings, run_embedding_generation, EmbeddingUtils
from kocrd.managers.ai_managers.ai_model_manager import AIModelManager
from kocrd.config.config import ConfigManager
from kocrd.managers.manager_factory import ManagerFactory
from kocrd.handlers.message_handler import MessageHandler
from kocrd.managers.rabbitmq_manager import RabbitMQManager

class SystemManager:
    def __init__(self, settings_manager: SettingsManager,config_files: list, main_window=None, tesseract_cmd=None, tessdata_dir=None):
        self.settings_manager = settings_manager
        self.main_window = main_window  # MainWindow 인스턴스 설정
        self.tesseract_cmd = tesseract_cmd
        self.tessdata_dir = tessdata_dir
        self.managers = {}
        self.uis = {}
        self._init_components(self.settings)
        self.rabbitmq_connection = None
        self.rabbitmq_channel = None
        self._configure_rabbitmq()
        self.config_manager = ConfigManager(config_files)
        self.message_handler = MessageHandler(self)
        self.rabbitmq_manager = RabbitMQManager(self.config_manager)
        self._initialize_managers()
        self.manager_factory = ManagerFactory(self.config_manager)
    def _initialize_managers(self):
        managers_config = self.config_manager.get("managers")
        for manager_name, manager_config in managers_config.items():
            self.managers[manager_name] = self.manager_factory.create_manager(manager_name, manager_config)

    def trigger_process(self, process_type: str, data: Optional[Dict[str, Any]] = None):
        manager = self.get_manager(process_type) # 매니저 이름 대신 process_type으로 매니저 객체를 가져온다.
        if manager:
            manager.handle_process(data) # 각 매니저가 handle_process 메서드를 구현해야 한다.
        else:
            logging.warning(f"🔴 알 수 없는 프로세스 유형: {process_type}")
            QMessageBox.warning(self.main_window, "오류", "알 수 없는 작업 유형입니다.")

    def handle_message(self, ch, method, properties, body):
        self.message_handler.handle_message(ch, method, properties, body, self)

    def get_manager(self, manager_name):
        return self.managers.get(manager_name)

    @staticmethod
    def initialize_settings(settings_path="config/development.json"):
        config_path = os.path.join(os.path.dirname(__file__), settings_path)
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            if "constants" not in config:
                raise KeyError("Missing 'constants' in configuration file.")
        except FileNotFoundError:
            logging.critical(f"Configuration file not found: {config_path}")
            raise
        except json.JSONDecodeError as e:
            logging.critical(f"Error decoding JSON from configuration file: {e}")
            raise
        except KeyError as e:
            logging.critical(f"Configuration error: {e}")
            raise
        except Exception as e:
            logging.critical(f"Unexpected error loading configuration file: {e}")
            raise

        settings_manager = SettingsManager(config_path)
        settings_manager.load_from_env()
        return settings_manager, config

    def initialize_managers(self):
        config = self.settings
        for manager_name, manager_config in config["managers"].items():
            manager_class = self.get_class(manager_config["module"], manager_config["class"])
            kwargs = manager_config.get("kwargs", {})
            dependencies = [self.managers[dep] for dep in manager_config.get("dependencies", [])]
            manager_instance = manager_class(*dependencies, **kwargs)
            self.managers[manager_name] = manager_instance

        self.managers["temp_file"] = self.create_temp_file_manager()
        self.managers["database"] = self.create_database_manager()
        self.managers["analysis"] = self.create_analysis_manager()
        self.managers["menubar"] = self.create_menubar_manager()
        self.managers["document"] = self.create_document_manager()
        self.managers["ocr"] = self.create_ocr_manager()
        self._configure_tesseract()

    def get_temp_file_manager(self):
        return self.managers.get("temp_file")

    def get_database_manager(self):
        return self.managers.get("database")

    def create_menubar_manager(self):
        return MenubarManager(self.main_window)

    def create_document_manager(self):
        return DocumentManager(self.settings_manager)

    def create_ocr_manager(self):
        return OCRManager(self.settings_manager)

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
        else:
            manager = self.get_manager("document")
            if process_type == "document_processing":
                manager.request_document_processing(data)
            elif process_type == "database_packaging":
                self.get_database_manager().request_database_packaging()
            elif process_type == "ai_training":
                self.get_manager("ai_training").request_ai_training(data)
            elif process_type == "generate_text":
                ai_manager = self.get_ai_manager()
                if (ai_manager):
                    return ai_manager.generate_text(data.get("command", ""))
                else:
                    logging.error("AIManager가 초기화되지 않았습니다.")
            else:
                logging.warning(f"🔴 알 수 없는 프로세스 유형: {process_type}")
                QMessageBox.warning(self.main_window, "오류", "알 수 없는 작업 유형입니다.")

    def handle_message(self, ch, method, properties, body):
        """RabbitMQ 메시지를 처리합니다."""
        # 메시지 처리 로직을 여기에 추가합니다.
        logging.info(f"Received message: {body}")

    def handle_error(self, message, error_code=None):
        if error_code:
            logging.error(f"{message} (Error Code: {error_code})")
        else:
            logging.error(message)
        QMessageBox.critical(self.main_window, "Error", message)

    def run_embedding_generation(self):
        EmbeddingUtils.run_embedding_generation(self.settings_manager)

    def close_rabbitmq_connection(self):
        if self.rabbitmq_connection:
            self.rabbitmq_connection.close()
            logging.info("🟢 RabbitMQ 연결 종료.")

    def get_ai_manager(self):
        return self.managers.get("ai_prediction")

    def get_manager(self, manager_name: str) -> Optional[Any]:
        return self.managers.get(manager_name)

    def get_ui(self, ui_name: str) -> Optional[Any]:
        return self.uis.get(ui_name)

    def get_ai_model_manager(self):
        """AIModelManager 인스턴스 반환."""
        return self.managers.get("ai_model")


# main_window 모듈을 나중에 임포트
from kocrd.window.main_window import MainWindow