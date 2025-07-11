# file_name: Document_Processor.py

import os
import logging
import datetime
import json
from fpdf import FPDF
from pdf2image import convert_from_path
from PyQt5.QtWidgets import QMessageBox, QFileDialog 
from PyQt5.QtWidgets import QWidget
import mimetypes
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Optional, Any, Dict, Union

config_path = os.path.join(os.path.dirname(__file__), '..', 'managers_config.json')
try:
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
except FileNotFoundError:
    logging.error(f"Configuration file not found at {config_path}")
    # 기본값 또는 예외 처리 로직 추가
    config = {
        "DEFAULT_REPORT_FILENAME": "report.pdf",
        "DEFAULT_EXCEL_FILENAME": "data.xlsx",
        "VALID_FILE_EXTENSIONS": [".txt", ".pdf", ".png", ".jpg", ".jpeg"],
        "MAX_FILE_SIZE": 10 * 1024 * 1024, # 10MB
        "MESSAGE_QUEUE": {}, # 빈 딕셔너리로 초기화
        "message_types": {},
        "queues": {"document_queue": "document_tasks"},
        "messages": {
            "log": {},
            "warning": {"505": "Text is empty, cannot determine document type."},
            "error": {
                "519": "OCR extraction failed: {error}",
                "520": "An unexpected error occurred: {error}",
                "501": "Poppler path error or PDF conversion failed: {e}"
            }
        }
    }
from kocrd.config.config import AppConfig, text_manager
from kocrd.config.system_constants import SystemConstants

class DocumentProcessor:
    """
    문서 처리 로직을 담당하는 클래스.
    OCR 수행, 데이터베이스 저장 등의 기능을 제공합니다.
    """
    def __init__(self, database_manager: Any, ocr_manager: Any, parent: Optional[QWidget], system_manager: Any, message_queue_manager: Any):
        self.message_queue_manager = message_queue_manager # 현재 RabbitMQ 사용 중
        self.system_manager = system_manager # 설정 및 전역 오류 처리
        self.database_manager = database_manager # DatabaseManager 인스턴스
        self.ocr_manager = ocr_manager
        self.parent = parent
        logging.info("DocumentProcessor initialized.")

    def perform_ocr(self, file_path: str) -> Optional[str]:
        """OCR을 수행하여 텍스트를 추출합니다."""
        try:
            extracted_text = self.ocr_manager.extract_text(file_path)
            if not extracted_text:
                logging.warning(text_manager.get_warning_text("401", file_path=file_path)) # 새로운 경고 코드
                raise ValueError(text_manager.get_error_text("519_no_text", file_path=file_path)) # 새로운 에러 코드
            return extracted_text
        except Exception as e:
            logging.error(text_manager.get_error_text("519", error=e))
            self.system_manager.handle_error("519", error_detail=str(e))
            return None # 오류 발생 시 None 반환

    def process_single_document(self, file_path: str) -> Optional[Dict[str, Any]]:
        """단일 문서를 처리합니다 (유효성 검사, OCR, 정보 생성 및 저장)."""
        # 설정은 AppConfig 또는 SystemManager를 통해 가져옵니다.
        max_file_size = AppConfig.get_setting("MAX_FILE_SIZE") # AppConfig 직접 사용
        valid_file_extensions = AppConfig.get_setting("VALID_FILE_EXTENSIONS") # AppConfig 직접 사용

        if not os.path.isfile(file_path):
            QMessageBox.warning(self.parent, text_manager.get_text("file_error_title"), text_manager.get_error_text("501_file_not_exist", file_path=file_path)) # 새 텍스트 코드
            return None

        file_extension = os.path.splitext(file_path)[1].lower()
        if file_extension not in valid_file_extensions:
            QMessageBox.warning(self.parent, text_manager.get_text("unsupported_file_title"), text_manager.get_warning_text("402", file_extension=file_extension, valid_extensions=', '.join(valid_file_extensions)))
            return None
        
        file_size = os.path.getsize(file_path)
        max_file_size_mb = max_file_size / (1024 * 1024)
        if file_size > max_file_size:
            QMessageBox.warning(self.parent, text_manager.get_text("file_size_exceed_title"), text_manager.get_warning_text("403", current_size=(file_size / (1024 * 1024)), max_size=max_file_size_mb))
            return None
        
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type is None or not mime_type.startswith(('image/', 'application/pdf', 'text/')):
            QMessageBox.warning(self.parent, text_manager.get_text("unsupported_mime_type_title"), text_manager.get_warning_text("404", mime_type=mime_type))
            return None

        extracted_text = self.perform_ocr(file_path)
        if extracted_text is None:
            return None

        document_info = self.create_document_info(file_path, extracted_text)
        if document_info:
            # DocumentProcessor가 직접 save_document_info를 호출합니다.
            self.save_document_info(document_info) 
            logging.info(text_manager.get_log_text("301", file_path=file_path)) # "Document processed and saved: {file_path}"
            return document_info
        else:
            return None

    def process_multiple_documents(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        """여러 문서를 일괄적으로 처리합니다."""
        if isinstance(file_paths, str):
            file_paths = [file_paths]

        results = []
        for file_path in file_paths:
            document_info = self.process_single_document(file_path)
            if document_info:
                results.append(document_info)
        return results

    def create_document_info(self, file_path: str, extracted_text: str) -> Dict[str, Any]:
        """문서 정보를 생성합니다."""
        return {
            'file_name': os.path.basename(file_path),
            'type': self.determine_document_type(extracted_text),
            'date': datetime.datetime.now().strftime('%Y-%m-%d'),
            'content': extracted_text # 텍스트 내용도 저장
        }
        
    def save_document_info(self, document_info: Dict[str, Any]):
        """문서 정보를 데이터베이스에 저장합니다."""
        try:
            self.database_manager.save_document_info(document_info) # DatabaseManager에 저장 위임
            # 텍스트 내용도 별도의 파일로 저장 (DatabaseManager에서 처리)
            self.database_manager.save_text(document_info['file_name'], document_info['content'])
            logging.info(text_manager.get_log_text("302", file_name=document_info['file_name'])) # "Document info saved to DB: {file_name}"
            # 성공 이벤트 발행 (필요시)
            # publish_system_event(SystemConstants.EventTypes.DOCUMENT_SAVED, document_info=document_info)
        except SQLAlchemyError as e:
            logging.error(text_manager.get_error_text("521", file_name=document_info.get("file_name", "Unknown"), error=e))
            self.system_manager.handle_error("521", error_detail=str(e))
            raise # 예외 재발생

    def edit_document(self, file_name: str, new_data: Dict[str, Any]) -> bool:
        """문서 정보를 수정합니다."""
        try:
            # database_manager의 update_document_info를 활용 (DocumentProcessor에서 직접 호출)
            # DatabaseManager의 update_document_info가 new_data 딕셔너리를 받을 수 있도록 조정 필요
            self.database_manager.update_document_info({"file_name": file_name, **new_data})
            
            # 텍스트 내용이 변경되었을 경우 업데이트
            if 'content' in new_data:
                self.database_manager.save_text(file_name, new_data['content'])

            logging.info(text_manager.get_log_text("303", file_name=file_name)) # "Document updated successfully: {file_name}"
            return True
        except SQLAlchemyError as e:
            logging.error(text_manager.get_error_text("524", file_name=file_name, error=e))
            self.system_manager.handle_error("524", error_detail=str(e))
            return False

    def delete_document_from_db(self, file_name: str):
        """데이터베이스에서 문서를 삭제합니다. (DocumentManager에서 호출될 메서드)"""
        try:
            self.database_manager.delete_document(file_name)
            # 관련 텍스트 파일 등도 삭제하는 로직 추가
            text_file_path = os.path.join(self.database_manager.db_path, "text", f"{file_name}.txt")
            if os.path.exists(text_file_path):
                os.remove(text_file_path)
                logging.info(text_manager.get_log_text("304", file_path=text_file_path)) # "Related text file deleted: {file_path}"
            
            logging.info(text_manager.get_log_text("305", file_name=file_name)) # "Document deleted from DB: {file_name}"
            # 성공 이벤트 발행
            # publish_system_event(SystemConstants.EventTypes.DOCUMENT_DELETED, file_name=file_name)
        except SQLAlchemyError as e:
            logging.error(text_manager.get_error_text("523", file_name=file_name, error=e))
            self.system_manager.handle_error("523", error_detail=str(e))
            raise # 예외 재발생

    def load_documents_from_db(self) -> List[Dict[str, Any]]:
        """데이터베이스에서 저장된 모든 문서 정보를 로드합니다. (DocumentManager에서 호출될 메서드)"""
        try:
            documents = self.database_manager.load_documents()
            # 필요하다면 각 문서의 텍스트 내용도 여기서 로드하여 document_info에 추가할 수 있습니다.
            # for doc in documents:
            #    doc['content'] = self.database_manager.read_text(doc['file_name'])
            logging.info(text_manager.get_log_text("306", count=len(documents))) # "Loaded {count} documents from DB."
            return documents
        except SQLAlchemyError as e:
            logging.error(text_manager.get_error_text("525", error=e))
            self.system_manager.handle_error("525", error_detail=str(e))
            raise # 예외 재발생


    def determine_document_type(self, text: str) -> str:
        """자동 문서 분석."""
        if not text:
            logging.warning(text_manager.get_warning_text("505"))
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
            logging.error(text_manager.get_error_text("520", error=e))
            self.system_manager.handle_error("520", error_detail=str(e))
            return "Unknown"

    def save_ocr_images(self, pdf_file_path: str):
        """PDF 파일에서 OCR 이미지를 추출하고 저장합니다."""
        logging.info(text_manager.get_log_text("506", pdf_file_path=pdf_file_path))
        try:
            poppler_path = self.ocr_manager.find_poppler_path()
            if not poppler_path:
                raise FileNotFoundError(text_manager.get_error_text("501_poppler_not_found")) # 새 텍스트 코드
            images = convert_from_path(pdf_file_path, poppler_path=poppler_path)
            for i, image in enumerate(images):
                image_name = f"{os.path.basename(pdf_file_path).replace('.pdf', '')}_page_{i + 1}.png"
                # 이미지는 DatabaseManager를 통해 저장 (혹은 DocumentProcessor 내에서 파일 시스템에 직접 저장)
                self.database_manager.save_image(image_name, image) # DatabaseManager의 save_image 활용
                # logging.info(f"OCR image saved: {image_path}") # DatabaseManager에서 이미 로깅함
        except FileNotFoundError as e:
            logging.error(text_manager.get_error_text("501_file_error", e=e))
            self.system_manager.handle_error("501_file_error", error_detail=str(e))
        except Exception as e:
            logging.error(text_manager.get_error_text("520", error=e))
            self.system_manager.handle_error("520", error_detail=str(e))

    def batch_import_documents(self) -> List[Dict[str, Any]]:
        """문서를 일괄적으로 가져오고 처리합니다."""
        try:
            file_dialog = QFileDialog()
            file_dialog.setFileMode(QFileDialog.ExistingFiles)
            file_paths, _ = file_dialog.getOpenFileNames(
                self.parent, # QFileDialog의 부모 위젯으로 self.parent를 사용
                text_manager.get_text("import_documents_dialog_title"), # 새 텍스트 코드
                "",
                text_manager.get_text("import_documents_filter_text") # 새 텍스트 코드
            )

            if not file_paths:
                logging.warning(text_manager.get_warning_text("405")) # "No files selected for import."
                return []

            results = self.process_multiple_documents(file_paths)
            return results

        except Exception as e:
            logging.error(text_manager.get_error_text("520", error=e))
            self.system_manager.handle_error("520", error_detail=str(e))
            return []

    def get_valid_doc_types(self) -> List[str]:
        """유효한 문서 유형을 데이터베이스에서 로드."""
        try:
            # DatabaseManager에 execute_query 메서드가 있으므로 직접 호출
            query = 'SELECT DISTINCT doc_type FROM feedback'
            results = self.database_manager.execute_query(query, fetch=True)
            return [row['doc_type'] for row in results] if results else []
        except SQLAlchemyError as e:
            logging.error(text_manager.get_error_text("520", error=e))
            self.system_manager.handle_error("520", error_detail=str(e))
            return []

    def save_feedback(self, feedback_data: Dict[str, Any]):
        """피드백 데이터를 저장합니다."""
        try:
            self.database_manager.save_feedback(feedback_data) # DatabaseManager에 위임
            logging.info(text_manager.get_log_text("307")) # "Feedback saved successfully."
        except SQLAlchemyError as e:
            logging.error(text_manager.get_error_text("520", error=e))
            self.system_manager.handle_error("520", error_detail=str(e))
            raise

    def send_message(self, message: Dict[str, Any]):
        """지정된 큐에 메시지를 전송합니다. (현재 RabbitMQ 사용)"""
        try:
            # Queue 이름은 config에서 가져옴
            queue_name = config["queues"]["document_queue"]
            self.message_queue_manager.send_message(queue_name, message) # RabbitMQ 사용
            logging.info(text_manager.get_log_text("308", queue_name=queue_name, message=message)) # "Message sent to queue '{queue_name}': {message}"
        except Exception as e:
            logging.error(text_manager.get_error_text("520", error=e))
            self.system_manager.handle_error("520", error_detail=str(e))
            raise # 예외 재발생
