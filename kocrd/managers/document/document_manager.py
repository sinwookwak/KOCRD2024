# file_name: kocrd/managers/document/document_manager.py

import os
import json
import logging
import time
import threading
import asyncio
from PyQt5.QtWidgets import QWidget, QFileDialog, QMessageBox, QApplication
from sqlalchemy.exc import SQLAlchemyError
from pdf2image import convert_from_path # pdf2image 필요시 사용
from typing import List, Optional, Any, Dict, Union

from kocrd.config.config import AppConfig, text_manager
from kocrd.config.system_constants import SystemConstants # 필요한 상수도 AppConfig 또는 별도 Constants 파일에서
from kocrd.config.message_broker import publish_system_event, subscribe, display_alert, display_warning, display_error, ask_question, confirm_delete

from kocrd.managers.document.document_controller import DocumentController
from kocrd.managers.document.document_table_view import DocumentTableView
from kocrd.managers.document.document_processor import DocumentProcessor
from kocrd.managers.unified_temp_manager import UnifiedTempManager, TempFileType

class DocumentManager(QWidget):
    def __init__(self, ocr_manager: Any, database_manager: Any, message_queue_manager: Any, system_manager: Any, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.parent = parent
        self.system_manager = system_manager
        self.ocr_manager = ocr_manager

        self.temp_file_manager = UnifiedTempManager(name="document_temp", settings_manager=getattr(system_manager, 'settings_manager', None))
        # Initialize the temp file manager asynchronously (will be done by parent system)
        
        # DocumentProcessor에 모든 매니저 인스턴스를 전달합니다.
        self.document_processor = DocumentProcessor(
            database_manager, # DatabaseManager 인스턴스 전달
            ocr_manager,
            parent,
            system_manager, # SystemManager 인스턴스 전달
            message_queue_manager # MessageQueueManager 인스턴스 전달 (현재 RabbitMQ 사용 중)
        )
        
        self.document_table_view = DocumentTableView(self)
        self.document_controller = DocumentController(self.document_processor, parent, self)

        logging.info(text_manager.get_log_text("345_document_manager_init")) 

        # MessageBroker 구독 등록 (이전과 동일)
        self._register_message_handlers()


    def _register_message_handlers(self):
        """DocumentManager가 처리할 이벤트를 MessageBroker에 등록합니다."""
        logging.info(text_manager.get_log_text("350_registering_handlers"))

    def add_document_to_table(self, document_info: Dict[str, Any]):
        """문서 정보를 테이블 뷰에 추가합니다."""
        self.document_table_view.add_document(document_info)

    def save_document_info(self, document_info: Dict[str, Any]):
        """문서 정보를 데이터베이스에 저장. DocumentProcessor에 위임."""
        try:
            self.document_processor.save_document_info(document_info) # DocumentProcessor의 메서드 호출
            publish_system_event(
                SystemConstants.EventTypes.DOCUMENT_SAVED,
                document_id=document_info.get("id"),
                file_name=document_info.get("file_name")
            )
        except SQLAlchemyError as e:
            error_msg = text_manager.get_error_text("521", file_name=document_info.get("file_name", "Unknown"), error=e)
            logging.error(error_msg)
            self.system_manager.handle_error("521", error_detail=str(e))
            publish_system_event(
                SystemConstants.EventTypes.DOCUMENT_SAVE_FAILED,
                file_name=document_info.get("file_name"),
                error=str(e)
            )

    def update_document_info(self, document_info: Dict[str, Any]):
        """문서 정보를 업데이트. DocumentProcessor에 위임."""
        try:
            # DocumentProcessor에는 update_document_info 대신 edit_document가 있습니다.
            # DocumentProcessor의 edit_document가 document_info 전체를 업데이트할 수 있다면 해당 메서드를 사용
            # 아니면 DocumentProcessor 내부에 update_document_info 로직을 추가하거나,
            # DocumentProcessor가 database_manager의 update_document_info를 직접 호출하도록 함.
            # 여기서는 편의상 document_info의 'file_name'을 기준으로 넘겨주는 것으로 가정합니다.
            self.document_processor.edit_document(document_info['file_name'], document_info) # DocumentProcessor의 메서드 호출
            publish_system_event(
                SystemConstants.EventTypes.DOCUMENT_UPDATED,
                document_id=document_info.get("id"),
                file_name=document_info.get("file_name")
            )
        except SQLAlchemyError as e:
            error_msg = text_manager.get_error_text("524", file_name=document_info.get("file_name", "Unknown"), error=e)
            logging.error(error_msg)
            self.system_manager.handle_error("524", error_detail=str(e))
            publish_system_event(
                SystemConstants.EventTypes.DOCUMENT_UPDATE_FAILED,
                file_name=document_info.get("file_name"),
                error=str(e)
            )

    def delete_document(self, file_name: str):
        """문서를 데이터베이스에서 삭제. DocumentProcessor에 위임."""
        try:
            # DocumentProcessor에는 delete_document가 직접 없습니다.
            # 이 경우 DocumentProcessor가 DatabaseManager를 통해 직접 삭제하도록 하거나,
            # DocumentProcessor에 delete_document 메서드를 추가하는 것이 좋습니다.
            # 여기서는 DocumentProcessor가 database_manager를 가지고 있으므로, DocumentProcessor에 위임합니다.
            # DocumentProcessor에 delete_document 메서드가 없으면 오류가 발생하므로, 추가가 필요합니다.
            self.document_processor.delete_document_from_db(file_name) # DocumentProcessor의 새로운 메서드 호출 가정
            self.document_table_view.remove_document(file_name)
            publish_system_event(
                SystemConstants.EventTypes.DOCUMENT_DELETED,
                file_name=file_name
            )
        except SQLAlchemyError as e:
            error_msg = text_manager.get_error_text("523", file_name=file_name, error=e)
            logging.error(error_msg)
            self.system_manager.handle_error("523", error_detail=str(e))
            publish_system_event(
                SystemConstants.EventTypes.DOCUMENT_DELETE_FAILED,
                file_name=file_name,
                error=str(e)
            )

    def load_documents(self) -> List[Dict[str, Any]]:
        """저장된 문서 정보를 로드. DocumentProcessor에 위임."""
        try:
            documents = self.document_processor.load_documents_from_db() # DocumentProcessor의 새로운 메서드 호출 가정
            self.document_table_view.clear_table()
            for doc in documents:
                self.document_table_view.add_document(doc)
            publish_system_event(SystemConstants.EventTypes.DOCUMENTS_LOADED, count=len(documents))
            return documents
        except SQLAlchemyError as e:
            error_msg = text_manager.get_error_text("525", error=e)
            logging.error(error_msg)
            self.system_manager.handle_error("525", error_detail=str(e))
            publish_system_event(SystemConstants.EventTypes.DOCUMENTS_LOAD_FAILED, error=str(e))
            return []
    def get_ui(self) -> QWidget:
        return self.document_controller.get_ui()

    def search_documents(self, keyword: str, column_index: Optional[int] = None, match_exact: bool = False):
        self.document_controller.search_documents(keyword, column_index, match_exact)
        publish_system_event(SystemConstants.EventTypes.DOCUMENT_SEARCHED, keyword=keyword)

    def save_ocr_images(self, pdf_file_path: str):
        self.document_processor.save_ocr_images(pdf_file_path)
        publish_system_event(SystemConstants.EventTypes.OCR_IMAGES_SAVED, file_path=pdf_file_path)

    def save_feedback(self, feedback_data: Dict[str, Any]):
        # DocumentProcessor에 save_feedback 메서드가 있으므로 직접 호출
        self.document_processor.save_feedback(feedback_data)
        publish_system_event(SystemConstants.EventTypes.FEEDBACK_SAVED)

    def get_valid_doc_types(self) -> List[str]:
        return self.document_processor.get_valid_doc_types()

    def determine_document_type(self, text: str) -> str:
        return self.document_processor.determine_document_type(text)

    def export_to_pdf(self, data: List[Dict[str, Any]], filename: str = "output.pdf"):
        self.document_controller.export_to_pdf(data, filename)
        publish_system_event(SystemConstants.EventTypes.DOCUMENTS_EXPORTED_PDF, filename=filename, count=len(data))

    def clear_table(self):
        self.document_table_view.clear_table()
        publish_system_event(SystemConstants.EventTypes.TABLE_CLEARED)

    def filter_documents(self, criteria: Dict[str, Any]):
        self.document_table_view.filter_table(criteria)
        publish_system_event(SystemConstants.EventTypes.DOCUMENTS_FILTERED, criteria=criteria)

    def get_selected_file_names(self) -> List[str]:
        return self.document_table_view.get_selected_file_names()

    def load_document(self, file_path: str):
        document_info = self.document_processor.process_single_document(file_path)
        if document_info:
            self.document_table_view.add_document(document_info)
            publish_system_event(SystemConstants.EventTypes.SINGLE_DOCUMENT_LOADED, file_path=file_path)
        else:
            logging.warning(text_manager.get_warning_text("417", file_path=file_path))
            publish_system_event(SystemConstants.EventTypes.SINGLE_DOCUMENT_LOAD_FAILED, file_path=file_path)

    async def manage_temp_files(self):
        """임시 파일을 관리합니다."""
        await self.temp_file_manager.cleanup_expired_files()
        publish_system_event(SystemConstants.EventTypes.TEMP_FILES_CLEANED)

    async def create_temp_file(self, content: Union[str, bytes], suffix: str = ".tmp") -> str:
        """임시 파일을 생성합니다."""
        file_id = await self.temp_file_manager.create_temp_file(content=content, suffix=suffix, file_type=TempFileType.DOCUMENT)
        file_path = self.temp_file_manager.get_temp_file_path(file_id)
        publish_system_event(SystemConstants.EventTypes.TEMP_FILE_CREATED, file_path=file_path)
        return file_id

    async def read_temp_file(self, file_id: str) -> Union[str, bytes]:
        """임시 파일을 읽습니다."""
        content = await self.temp_file_manager.read_temp_file(file_id)
        file_path = self.temp_file_manager.get_temp_file_path(file_id)
        publish_system_event(SystemConstants.EventTypes.TEMP_FILE_READ, file_path=file_path)
        return content

    async def delete_temp_file(self, file_id: str):
        """임시 파일을 삭제합니다."""
        file_path = self.temp_file_manager.get_temp_file_path(file_id)
        await self.temp_file_manager.delete_temp_file(file_id)
        publish_system_event(SystemConstants.EventTypes.TEMP_FILE_DELETED, file_path=file_path)

    async def cleanup_temp_files(self):
        """모든 임시 파일을 정리합니다 (default retention)."""
        await self.temp_file_manager.cleanup_expired_files() # 기본값 사용
        publish_system_event(SystemConstants.EventTypes.ALL_TEMP_FILES_CLEANED)

    async def backup_temp_files(self):
        """임시 파일을 백업합니다."""
        await self.temp_file_manager.backup_temp_files([TempFileType.DOCUMENT])
        publish_system_event(SystemConstants.EventTypes.TEMP_FILES_BACKED_UP)

    async def restore_temp_files(self):
        """백업된 임시 파일을 복원합니다."""
        # Note: restore_temp_files implementation needed in UnifiedTempManager
        # await self.temp_file_manager.restore_temp_files()
        logging.warning("Restore functionality needs to be implemented in UnifiedTempManager")
        publish_system_event(SystemConstants.EventTypes.TEMP_FILES_RESTORED)

    async def cleanup_all_temp_files(self, retention_time: int = 3600):
        """임시 디렉토리의 모든 파일 정리 (보관 기간 적용)."""
        hours = retention_time // 3600  # Convert seconds to hours
        await self.temp_file_manager.cleanup_by_type(TempFileType.DOCUMENT, older_than_hours=hours)
        publish_system_event(SystemConstants.EventTypes.ALL_TEMP_FILES_CLEANED_RETENTION, retention=retention_time)

    def cleanup_specific_files(self, files: Optional[List[str]]):
        """특정 파일들을 정리합니다."""
        if files: # files가 None이 아닐 때만 호출
            self.temp_file_manager.cleanup_specific_files(files)
            publish_system_event(SystemConstants.EventTypes.SPECIFIC_TEMP_FILES_CLEANED, count=len(files))
        else:
            logging.warning(text_manager.get_warning_text("418")) # "No specific files provided for cleanup."

@subscribe(SystemConstants.EventTypes.PROCESS_DOCUMENT_TASK)
def handle_process_document_task(file_paths: List[str], cleanup: bool, system_manager_instance: Any, **kwargs: Any):
    logging.info(text_manager.get_log_text("351", file_paths=file_paths))
    time.sleep(1)

    # SystemManager 인스턴스를 통해 DocumentManager에 접근
    if system_manager_instance:
        document_manager = system_manager_instance.get_manager("document") # 가정: SystemManager는 매니저를 가져오는 메서드를 가짐
        if document_manager:
            for file_path in file_paths:
                document_manager.load_document(file_path) # DocumentManager의 load_document 호출

    logging.info(text_manager.get_log_text("352", file_paths=file_paths))
    publish_system_event(SystemConstants.EventTypes.DOCUMENT_PROCESSING_COMPLETED, file_paths=file_paths)


@subscribe(SystemConstants.EventTypes.PROCESS_DATABASE_PACKAGING_TASK)
def handle_process_database_packaging_task(system_manager_instance: Any, **kwargs: Any):
    logging.info(text_manager.get_log_text("353"))
    time.sleep(1)

    # SystemManager 인스턴스를 통해 DatabaseManager에 접근
    if system_manager_instance:
        database_manager = system_manager_instance.get_manager("database") # 가정: SystemManager는 매니저를 가져오는 메서드를 가짐
        if database_manager:
            database_manager.package_database() # DatabaseManager의 package_database 호출

    logging.info(text_manager.get_log_text("354"))
    publish_system_event(SystemConstants.EventTypes.DATABASE_PACKAGING_COMPLETED)
