# file_name: Document_Manager

import os
import pika
import json
from fpdf import FPDF
import logging
import time
import threading
from PyQt5.QtWidgets import QWidget, QFileDialog, QMessageBox, QApplication
from sqlalchemy.exc import SQLAlchemyError
from pdf2image import convert_from_path
from typing import List, Optional

config_path = os.path.join(os.path.dirname(__file__), 'Document_config.json')
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

VALID_FILE_EXTENSIONS = config["VALID_FILE_EXTENSIONS"]
MAX_FILE_SIZE = config["MAX_FILE_SIZE"]
MESSAGE_QUEUE = config["MESSAGE_QUEUE"]
MESSAGE_TYPES = config["message_types"]
QUEUES = config["queues"]
LOGGING_INFO = config["logging"]["info"]
LOGGING_WARNING = config["logging"]["warning"]
LOGGING_ERROR = config["logging"]["error"]

from .Document_Controller import DocumentController
from .Document_Table_View import DocumentTableView # 상대 경로 import
from .Document_Processor import DocumentProcessor # 상대 경로 import
from .Document_temp import DocumentTempManager  # DocumentTempManager 임포트 추가

class DocumentManager(QWidget):
    def __init__(self, ocr_manager, database_manager, message_queue_manager, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.message_queue_manager = message_queue_manager
        self.database_manager = database_manager
        self.ocr_manager = ocr_manager
        self.temp_file_manager = DocumentTempManager()  # DocumentTempManager 인스턴스 생성
        self.document_processor = DocumentProcessor(database_manager, ocr_manager, parent, self, message_queue_manager)
        self.document_table_view = DocumentTableView(self)
        self.document_controller = DocumentController(self.document_processor, parent, self)
        logging.info("DocumentManager initialized.")
    
    def add_document_to_table(self, document_info):
        self.document_table_view.add_document(document_info)

    def save_document_info(self, document_info):
        """문서 정보를 데이터베이스에 저장."""
        self.database_manager.save_document_info(document_info)

    def update_document_info(self, document_info):
        """문서 정보를 업데이트."""
        self.database_manager.update_document_info(document_info)

    def delete_document(self, file_name):
        """문서를 데이터베이스에서 삭제."""
        self.database_manager.delete_document(file_name)

    def load_documents(self):
        """저장된 문서 정보를 로드."""
        return self.database_manager.load_documents()

    def send_message(self, message):
        """메시지를 큐에 전송."""
        try:
            queue_name = QUEUES["document_queue"]
            self.message_queue_manager.send_message(queue_name, message)
            logging.info(f"Message sent to queue '{queue_name}': {message}")
        except Exception as e:
            logging.error(config["messages"]["error"]["520"].format(error=e))

    def get_ui(self):
        return self.document_controller.get_ui()

    def search_documents(self, keyword, column_index=None, match_exact=False):
        self.document_controller.search_documents(keyword, column_index, match_exact)

    def save_ocr_images(self, pdf_file_path):
        self.document_processor.save_ocr_images(pdf_file_path)

    def save_feedback(self, feedback_data):
        self.document_processor.save_feedback(feedback_data)

    def get_valid_doc_types(self):
        return self.document_processor.get_valid_doc_types()

    def determine_document_type(self, text):
        return self.document_processor.determine_document_type(text)

    def export_to_pdf(self, data, filename="output.pdf"):
        self.document_controller.export_to_pdf(data, filename)

    def start_consuming(self):
        """메시지 큐에서 메시지 소비 시작."""
        self.message_queue_manager.start_consuming()

    def clear_table(self):
        self.document_table_view.clear_table()

    def filter_documents(self, criteria):
        self.document_table_view.filter_table(criteria)

    def get_selected_file_names(self):
        return self.document_table_view.get_selected_file_names()

    def load_document(self, file_path):
        document_info = self.document_processor.process_single_document(file_path)
        if document_info:
            self.document_table_view.add_document(document_info)

    def manage_temp_files(self):
        """임시 파일을 관리합니다."""
        self.temp_file_manager.cleanup()

    def create_temp_file(self, content, suffix=".tmp"):
        """임시 파일을 생성합니다."""
        return self.temp_file_manager.create_temp_file(content, suffix)

    def read_temp_file(self, file_path):
        """임시 파일을 읽습니다."""
        return self.temp_file_manager.read_temp_file(file_path)

    def delete_temp_file(self, file_path):
        """임시 파일을 삭제합니다."""
        self.temp_file_manager.delete_temp_file(file_path)

    def cleanup_temp_files(self):
        """모든 임시 파일을 정리합니다."""
        self.temp_file_manager.cleanup()

    def backup_temp_files(self):
        """임시 파일을 백업합니다."""
        self.temp_file_manager.backup_temp_files()

    def restore_temp_files(self):
        """백업된 임시 파일을 복원합니다."""
        self.temp_file_manager.restore_temp_files()

    def cleanup_all_temp_files(self, retention_time: int = 3600):
        """임시 디렉토리의 모든 파일 정리 (보관 기간 적용)."""
        self.temp_file_manager.cleanup_all_temp_files(retention_time)

    def cleanup_specific_files(self, files: Optional[List[str]]):
        """특정 파일들을 정리합니다."""
        self.temp_file_manager.cleanup_specific_files(files)

def process_document_task(ch, method, properties, body):
    message = json.loads(body)
    file_paths = message.get("file_paths")
    cleanup = message.get("cleanup")
    print(f"Received document processing task: {file_paths}")
    time.sleep(5)  # 문서 처리 작업 대신 5초 대기
    # 실제 문서 처리 로직 구현 (SystemManager의 handle_documents 로직을 여기에 옮김)
    # ...

def process_database_packaging_task(ch, method, properties, body):
    message = json.loads(body)
    print("Received database packaging task")
    time.sleep(5)  # 데이터베이스 패키징 작업 대신 5초 대기
    # 실제 데이터베이스 패키징 로직 구현 (SystemManager의 database_packaging 로직을 여기에 옮김)
    # ...
