# file_name: system_manager.py
import logging
import json
import sys
import os
import pika
import pytesseract
from typing import Dict, Any, Optional
from PyQt5.QtWidgets import QMessageBox, QApplication
from PIL import Image, UnidentifiedImageError  # PIL import 위치 변경

from kocrd.managers.ocr.ocr_manager import OCRManager
from kocrd.managers.temp_file_manager import TempFileManager
from kocrd.managers.database_manager import DatabaseManager
from kocrd.window.menubar_manager import MenubarManager
from kocrd.managers.document.document_manager import DocumentManager
from kocrd.managers.ai_managers.ai_model_manager import AIModelManager
from kocrd.config.config import ConfigManager
from kocrd.managers.manager_factory import ManagerFactory
from kocrd.handlers.message_handler import MessageHandler
from kocrd.managers.rabbitmq_manager import RabbitMQManager
from kocrd.Settings.settings_manager import SettingsManager # SettingsManager import 유지
from kocrd.utils.embedding_utils import EmbeddingUtils # EmbeddingUtils import 유지
from kocrd.handlers.training_event_handler import TrainingEventHandler

class SystemManager:
    def __init__(self, config_files: list, main_window=None):
        self.config_manager = ConfigManager(config_files)
        self.main_window = main_window
        self.manager_factory = ManagerFactory(self.config_manager)
        self.managers = {}
        self.message_handler = MessageHandler(self)
        self.rabbitmq_manager = RabbitMQManager(self.config_manager)
        self.ai_model_manager = AIModelManager.get_instance()
        self.training_event_handler = TrainingEventHandler(self, self.model_manager, self.ai_data_manager, self.ai_model_manager)
        self._initialize_managers()

    def _initialize_managers(self):
        managers_config = self.config_manager.get("managers")
        for manager_name, manager_config in managers_config.items():
            self.managers[manager_name] = self.manager_factory.create_manager(manager_name, manager_config)

    def trigger_process(self, process_type: str, data: Optional[Dict[str, Any]] = None):
        manager = self.managers.get(process_type)
        if manager:
            manager.handle_process(data)
        else:
            logging.warning(f"🔴 알 수 없는 프로세스 유형: {process_type}")
            QMessageBox.warning(self.main_window, "오류", "알 수 없는 작업 유형입니다.")

    def handle_message(self, ch, method, properties, body):
        self.message_handler.handle_message(ch, method, properties, body, self)

    def get_manager(self, manager_name):
        return self.managers.get(manager_name)

    @staticmethod
    def initialize_settings(settings_path="config/development.json"):
        config_manager = ConfigManager([settings_path])
        return config_manager

    def database_packaging(self):
        self.get_manager("database").package_database()

    def trigger_process(self, process_type: str, data: Optional[Dict[str, Any]] = None):
        """AI 모델 실행 프로세스 트리거"""
        manager = self.managers.get(process_type) # 매니저 이름으로 가져오기
        if manager:
            manager.handle_process(data)
        elif process_type == "database_packaging": # 별도로 처리하는 부분
            self.get_manager("temp_file").database_packaging() # get_manager 사용
        elif process_type == "ai_training":
            self.get_manager("ai_training").request_ai_training(data)
        elif process_type == "generate_text":
            ai_manager = self.get_manager("ai_prediction") # get_ai_manager() -> get_manager("ai_prediction")
            if ai_manager:
                return ai_manager.generate_text(data.get("command", ""))
            else:
                logging.error("AIManager가 초기화되지 않았습니다.")
        else:
            logging.warning(f"🔴 알 수 없는 프로세스 유형: {process_type}")
            QMessageBox.warning(self.main_window, "오류", "알 수 없는 작업 유형입니다.")


    def handle_message(self, ch, method, properties, body):
        """RabbitMQ 메시지를 처리합니다."""
        self.message_handler.handle_message(ch, method, properties, body, self) # MessageHandler로 위임

    def handle_error(self, message, error_message_key=None):  # error_message_key 추가
        if error_message_key:
            logging.error(f"{message} (Error Key: {error_message_key})")  # 키 정보 로깅
        else:
            logging.error(message)
        QMessageBox.critical(self.main_window, "Error", message)  # QMessageBox 그대로 사용

    def run_embedding_generation(self):
        EmbeddingUtils.run_embedding_generation(self.config_manager) # self.settings_manager -> self.config_manager

    def close_rabbitmq_connection(self):
        self.rabbitmq_manager.close() # rabbitmq_manager의 close() 호출

    def get_ai_manager(self): # 제거
        return self.managers.get("ai_prediction")

    def get_manager(self, manager_name: str) -> Optional[Any]:
        return self.managers.get(manager_name)

    def get_ui(self, ui_name: str) -> Optional[Any]:
        return self.uis.get(ui_name)

    def get_ai_model_manager(self):
        """AIModelManager 인스턴스 반환."""
        return self.managers.get("ai_model")

    def get_message(self, message_type: str, message_code: str) -> str:
        """메시지 설정에서 메시지를 가져옵니다."""
        try:
            messages = self.config_manager.get("messages")  # config에서 메시지 설정 로드
            return messages[message_type][message_code]
        except KeyError:
            logging.error(f"Message not found: {message_type} - {message_code}")
            return f"Message not found: {message_type} - {message_code}"  # 메시지 없을 경우 기본 메시지 반환

# main_window 모듈을 나중에 임포트
from kocrd.window.main_window import MainWindow