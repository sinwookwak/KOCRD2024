# file_name: system_manager.py
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
from managers.database_manager import DatabaseManager
from kocrd.window.menubar.menubar_manager import MenubarManager
from managers.document.document_manager import DocumentManager
from managers.rabbitmq_manager import RabbitMQManager
from Settings.settings_manager import SettingsManager
from managers.analysis_manager import AnalysisManager

from kocrd.config import development

class SystemManager:
    def __init__(self, settings_manager: SettingsManager, main_window=None, tesseract_cmd=None, tessdata_dir=None):
        self.settings_manager = settings_manager
        self.main_window = main_window  # MainWindow 인스턴스 설정
        self.tesseract_cmd = tesseract_cmd
        self.tessdata_dir = tessdata_dir
        self.rabbitmq_manager = RabbitMQManager()
        self.managers = {}
        self.uis = {}
        self.settings = self.load_development_settings()
        self._init_components(self.settings)
        self.initialize_managers()

    def load_development_settings(self):
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'development.json')
        with open(config_path, 'r') as f:
            return json.load(f)

    def initialize_managers(self):
        config = self.settings
        for manager_name, manager_config in config["managers"].items():
            manager_class = self.get_class(manager_config["module"], manager_config["class"])
            kwargs = manager_config.get("kwargs", {})
            dependencies = [self.managers[dep] for dep in manager_config.get("dependencies", [])]
            manager_instance = manager_class(*dependencies, **kwargs)
            self.managers[manager_name] = manager_instance

        self._configure_tesseract()

    def _configure_tesseract(self):
        pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
        if self.tessdata_dir:
            pytesseract.pytesseract.tessdata_dir = self.tessdata_dir
            logging.info(f"🟢 Tessdata 설정 완료: {self.tessdata_dir}")
        logging.info(f"🟢 Tesseract 설정 완료: {self.tesseract_cmd}")
        logging.info("🟢 SystemManager 초기화 완료.")

    def _init_components(self, settings: Dict[str, Any]) -> None:
        """설정 파일을 기반으로 매니저 및 UI 초기화"""
        with open('development.json', 'r') as f:
            config = json.load(f)

        for component_type, component_dict in config.items():
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
        manager = self.get_manager("document")
        if process_type == "document_processing":
            manager.request_document_processing(data)
        elif process_type == "database_packaging":
            self.get_manager("database").request_database_packaging()
        elif process_type == "ai_training":
            self.get_manager("ai_training").request_ai_training(data)
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

    def get_ai_model_manager(self):
        """AIModelManager 인스턴스 반환."""
        return self.managers.get("ai_model")

# main_window 모듈을 나중에 임포트
from kocrd.window.main_window import MainWindow