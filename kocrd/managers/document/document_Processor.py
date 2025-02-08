# file_name: Document_Processor.py

import os
import logging
import datetime
import json
from fpdf import FPDF
from pdf2image import convert_from_path
from PyQt5.QtWidgets import QMessageBox, QFileDialog
import mimetypes
from sqlalchemy.exc import SQLAlchemyError
from kocrd.config import development

# 설정 파일을 호출하도록 수정
config_path = os.path.join(os.path.dirname(__file__), '..', 'managers_config.json')
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

DEFAULT_REPORT_FILENAME = config["DEFAULT_REPORT_FILENAME"]
DEFAULT_EXCEL_FILENAME = config["DEFAULT_EXCEL_FILENAME"]
VALID_FILE_EXTENSIONS = config["VALID_FILE_EXTENSIONS"]
MAX_FILE_SIZE = config["MAX_FILE_SIZE"]
MESSAGE_QUEUE = config["MESSAGE_QUEUE"]
MESSAGE_TYPES = config["message_types"]
QUEUES = config["queues"]
LOGGING_INFO = config["messages"]["log"]
LOGGING_WARNING = config["messages"]["warning"]
LOGGING_ERROR = config["messages"]["error"]

class DocumentProcessor:
    """
    문서 처리 로직을 담당하는 클래스.
    OCR 수행, 데이터베이스 저장 등의 기능을 제공합니다.
    """
    def __init__(self, database_manager, ocr_manager, parent, system_manager, message_queue_manager):
        self.message_queue_manager = message_queue_manager
        self.system_manager = system_manager
        self.database_manager = database_manager
        self.ocr_manager = ocr_manager
        self.parent = parent
        logging.info("DocumentProcessor initialized.")
    def perform_ocr(self, file_path):
        """OCR을 수행하여 텍스트를 추출합니다."""
        try:
            extracted_text = self.ocr_manager.extract_text(file_path)
            if not extracted_text:
                logging.warning(f"No text extracted from file: {file_path}")
                raise ValueError(f"No text extracted for: {file_path}")
            return extracted_text
        except Exception as e:
            logging.error(config["messages"]["error"]["519"].format(error=e))
            raise
    def process_single_document(self, file_path):
        """단일 문서를 처리합니다 (유효성 검사, OCR, 정보 생성 및 저장)."""
        max_file_size = self.system_manager.get_setting("MAX_FILE_SIZE")
        valid_file_extensions = self.system_manager.get_setting("VALID_FILE_EXTENSIONS")

        if not os.path.isfile(file_path):
            QMessageBox.warning(self.parent, "파일 오류", f"파일이 존재하지 않습니다: {file_path}")
            return None

        file_extension = os.path.splitext(file_path)[1].lower()
        if file_extension not in valid_file_extensions:
            QMessageBox.warning(self.parent, "지원되지 않는 파일", f"허용되지 않는 파일 형식입니다. 허용된 형식: {', '.join(valid_file_extensions)}")
            return None
        file_size = os.path.getsize(file_path)
        max_file_size_mb = max_file_size / (1024 * 1024)
        if file_size > max_file_size:
            QMessageBox.warning(self.parent, "파일 크기 초과", f"파일 크기가 {(file_size / (1024 * 1024)):.2f}MB입니다. 최대 허용 크기: {max_file_size_mb:.2f}MB")
            return None
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type is None or not mime_type.startswith(('image/', 'application/pdf', 'text/')):
            QMessageBox.warning(self.parent, "지원되지 않는 파일 형식", f"지원되지 않는 파일 형식입니다. ({mime_type})")
            return None

        extracted_text = self.perform_ocr(file_path)
        if extracted_text is None:
            return None

        document_info = self.create_document_info(file_path, extracted_text)
        if document_info:
            self.save_document_info(document_info)
            logging.info(f"Document processed and saved: {file_path}")
            return document_info
        else:
            return None
    def process_multiple_documents(self, file_paths):
        """여러 문서를 일괄적으로 처리합니다."""
        if isinstance(file_paths, str):
            file_paths = [file_paths]

        results = []
        for file_path in file_paths:
            document_info = self.process_single_document(file_path)
            if document_info:
                results.append(document_info)
        return results
    def create_document_info(self, file_path, extracted_text):
        """문서 정보를 생성합니다."""
        return {
            'file_name': os.path.basename(file_path),
            'type': self.determine_document_type(extracted_text),
            'date': datetime.datetime.now().strftime('%Y-%m-%d'),
            'content': extracted_text
        }
    def save_document_info(self, document_info):
        """문서 정보를 데이터베이스에 저장합니다."""
        self.database_manager.save_document_info(document_info)

    def edit_document(self, file_name, new_data):
        try:
            document = self.database_manager.get_document(file_name)
            if not document:
                logging.error(f"Document not found: {file_name}")
                return False

            for key, value in new_data.items():
                if key in document:
                    document[key] = value

            self.database_manager.update_document(file_name, document)
            logging.info(f"Document updated successfully: {file_name}")
            return True
        except Exception as e:
            logging.error(config["messages"]["error"]["520"].format(error=e))
            return False
    def determine_document_type(self, text):
        """자동 문서 분석."""
        if not text:
            logging.warning(config["messages"]["warning"]["505"])
            return "Unknown"

        try:
            text_lower = text.lower()
            if "invoice" in text_lower:
                return "Invoice"
            elif "report" in text_lower:
                return "Report"
            else:
                return "Unknown"
        except Exception as e:
            logging.error(config["messages"]["error"]["520"].format(error=e))
            return "Unknown"

    def save_ocr_images(self, pdf_file_path):
        """PDF 파일에서 OCR 이미지를 추출하고 저장합니다."""
        logging.info(config["messages"]["log"]["506"].format(pdf_file_path=pdf_file_path))
        try:
            poppler_path = self.ocr_manager.find_poppler_path()
            if not poppler_path:
                raise FileNotFoundError("Poppler 경로를 찾을 수 없습니다.")
            images = convert_from_path(pdf_file_path, poppler_path=poppler_path)
            for i, image in enumerate(images):
                image_path = f"{pdf_file_path}_page_{i + 1}.png"
                image.save(image_path)
                logging.info(f"OCR image saved: {image_path}")
        except FileNotFoundError as e:
            logging.error(config["messages"]["error"]["501"].format(e=e))
        except Exception as e:
            logging.error(config["messages"]["error"]["520"].format(error=e))

    def batch_import_documents(self):
        """문서를 일괄적으로 가져오고 처리합니다."""
        try:
            file_dialog = QFileDialog()
            file_dialog.setFileMode(QFileDialog.ExistingFiles)
            file_paths, _ = file_dialog.getOpenFileNames(
                None, "문서 가져오기", "", "모든 파일 (*.*);;텍스트 파일 (*.txt);;PDF 파일 (*.pdf);;이미지 파일 (*.png *.jpg)"
            )

            if not file_paths:
                logging.warning("No files selected for import.")
                return []

            results = self.process_multiple_documents(file_paths)
            return results

        except Exception as e:
            logging.error(config["messages"]["error"]["520"].format(error=e))
            return []

    def get_valid_doc_types(self):
        """유효한 문서 유형을 데이터베이스에서 로드."""
        try:
            query = 'SELECT DISTINCT doc_type FROM feedback'
            results = self.database_manager.execute_query(query, fetch=True)
            return [row['doc_type'] for row in results] if results else []
        except SQLAlchemyError as e:
            logging.error(config["messages"]["error"]["520"].format(error=e))
            return []

    def send_message(self, message):
        """지정된 큐에 메시지를 전송합니다."""
        try:
            queue_name = QUEUES["document_queue"]
            self.message_queue_manager.send_message(queue_name, message)
            logging.info(f"Message sent to queue '{queue_name}': {message}")
        except Exception as e:
            logging.error(config["messages"]["error"]["520"].format(error=e))
