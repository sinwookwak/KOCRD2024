import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from PIL import Image
import shutil
from datetime import datetime
from sqlalchemy.orm import declarative_base # 이 부분은 ORM 사용 시 필요하며, 현재 쿼리 방식에서는 직접 사용되지 않음
import pika # RabbitMQ 사용
import json
from typing import Optional, List, Dict, Any, Union

# AppConfig 및 TextManager 임포트 (config/config.py에서 가져옴)
from kocrd.config.config import AppConfig, text_manager # load_config 대신 AppConfig 사용
from kocrd.config.system_constants import SystemConstants # 이벤트 타입 등 상수
from kocrd.config.message_broker import publish_system_event


class DatabaseManager:
    # message_queue_manager는 __init__에서 직접 주입받지 않고, 필요시 publish_system_event를 사용하거나,
    # DatabaseManager 외부에서 메시지 발송을 처리하도록 유도.
    # 하지만 현재 원본 코드에서는 send_message를 가지고 있으므로, 해당 메서드는 유지합니다.
    # 이 클래스 자체에서 pika를 사용하는 것은 역할 분리에 위배되므로, 최종적으로는 MessageBroker가 담당해야 합니다.
    def __init__(self, db_path: str, message_queue_manager: Any, backup_path: Optional[str] = None):
        self.db_path = db_path
        self.backup_path = backup_path
        self.message_queue_manager = message_queue_manager # RabbitMQ 메시지 큐 매니저
        
        if self.backup_path:
            logging.info(text_manager.get_log_text("309", backup_path=self.backup_path)) # "Backup path set to: {self.backup_path}"
        
        self.db_file = os.path.join(db_path, "documents.db")
        self.engine = create_engine(f'sqlite:///{self.db_file}', pool_size=10, max_overflow=20)

        os.makedirs(os.path.join(db_path, "image"), exist_ok=True)
        os.makedirs(os.path.join(db_path, "text"), exist_ok=True)

        self.initialize_database()
        logging.info(text_manager.get_log_text("310", db_path=db_path)) # "DatabaseManager initialized with database path: {db_path}"

    def set_package_path(self, new_path: str):
        """데이터베이스 경로를 업데이트하고 엔진을 재초기화."""
        self.db_path = new_path
        self.db_file = os.path.join(new_path, "documents.db")
        self.engine = create_engine(f'sqlite:///{self.db_file}', pool_size=10, max_overflow=20)
        self.initialize_database()
        logging.info(text_manager.get_log_text("311", new_path=new_path)) # "Database path updated to: {new_path}"

    def initialize_database(self):
        """SQLAlchemy를 사용하여 데이터베이스 테이블 생성."""
        try:
            # config 로드 방식 변경 (AppConfig에서 직접 가져오기)
            # config = load_config('config/development.json') # 기존
            init_queries = AppConfig.get_setting("database.init_queries") # AppConfig에서 가져오기

            queries = [text(query) for query in init_queries]
            with self.engine.connect() as conn:
                for query in queries:
                    conn.execute(query)
                logging.info(text_manager.get_log_text("312")) # "Database initialized and required tables created."
        except (SQLAlchemyError, IOError, KeyError) as e:
            logging.error(text_manager.get_error_text("526", error=e)) # "Error initializing database: {e}"
            raise RuntimeError(text_manager.get_error_text("527")) from e # "Database initialization failed."

    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None, fetch: bool = False) -> Optional[List[Dict[str, Any]]]:
        """데이터베이스 쿼리를 실행하는 공통 메서드."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query), params or {})
                if fetch:
                    return [dict(row) for row in result]
                # INSERT, UPDATE, DELETE 쿼리의 경우 영향을 받은 행 수를 반환할 수 있음
                return None
        except SQLAlchemyError as e:
            logging.error(text_manager.get_error_text("528", error=e)) # "Database query error: {e}"
            raise

    def update_document_info(self, document_info: Dict[str, Any]):
        """문서 정보를 업데이트합니다."""
        query = '''
        UPDATE documents
        SET type = :type, date = :date, supplier = :supplier
        WHERE file_name = :file_name
        '''
        self._execute_and_log(query, document_info, text_manager.get_log_text("313")) # "Document info updated"

    def update_document_type(self, file_name: str, new_type: str):
        """문서의 유형을 업데이트합니다."""
        query = '''
        UPDATE documents
        SET type = :new_type
        WHERE file_name = :file_name
        '''
        self._execute_and_log(query, {"new_type": new_type, "file_name": file_name}, text_manager.get_log_text("314", file_name=file_name, new_type=new_type)) # f"Document {file_name} updated to type: {new_type}"

    def package_database(self):
        """데이터베이스를 패키징하여 백업."""
        if not self.backup_path:
            logging.warning(text_manager.get_warning_text("406")) # "Backup path not set, cannot package database."
            return # 백업 경로 없으면 리턴

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        package_name_base = f"database_package_{timestamp}"
        package_name = os.path.join(self.backup_path, package_name_base)
        try:
            backup_dir = os.path.join(self.backup_path, f"backup_{timestamp}")
            os.makedirs(backup_dir, exist_ok=True)
            shutil.copy(self.db_file, backup_dir)
            shutil.make_archive(package_name, 'zip', backup_dir)
            shutil.rmtree(backup_dir)
            logging.info(text_manager.get_log_text("315", package_name=f"{package_name}.zip")) # f"Database packaged as '{package_name}.zip'."
            publish_system_event(SystemConstants.EventTypes.DATABASE_PACKAGING_COMPLETED, package_path=f"{package_name}.zip") # 이벤트 발행
        except Exception as e:
            logging.error(text_manager.get_error_text("529", error=e)) # f"Error during packaging database: {e}"
            publish_system_event(SystemConstants.EventTypes.DATABASE_PACKAGING_FAILED, error=str(e)) # 실패 이벤트 발행
            raise

    def save_document_info(self, document_info: Dict[str, Any]):
        """문서 정보를 데이터베이스에 저장하거나 업데이트."""
        query = '''
        INSERT INTO documents (file_name, type, date, supplier)
        VALUES (:file_name, :type, :date, :supplier)
        ON CONFLICT(file_name) DO UPDATE SET
        type = excluded.type,
        date = excluded.date,
        supplier = excluded.supplier;
        '''
        self._execute_and_log(query, document_info, text_manager.get_log_text("316")) # "Document info saved or updated"

    def load_documents(self) -> List[Dict[str, Any]]:
        """저장된 문서 정보를 로드."""
        query = 'SELECT file_name, type, date, supplier FROM documents'
        return self._execute_and_fetch(query, text_manager.get_error_text("530")) # "Error loading documents"

    def delete_document(self, file_name: str):
        """데이터베이스에서 문서를 삭제."""
        query = 'DELETE FROM documents WHERE file_name = :file_name'
        self._execute_and_log(query, {'file_name': file_name}, text_manager.get_log_text("317", file_name=file_name)) # f"Document deleted: {file_name}"

    def save_feedback(self, feedback_data: Dict[str, Any]):
        """피드백 데이터를 저장."""
        query = '''
        INSERT INTO feedback (file_path, doc_type, timestamp)
        VALUES (:file_path, :doc_type, :timestamp)
        ON CONFLICT(file_path) DO UPDATE SET
        doc_type = excluded.doc_type,
        timestamp = excluded.timestamp
        '''
        self._execute_and_log(query, feedback_data, text_manager.get_log_text("318")) # "Feedback saved"

    def save_text(self, file_name: str, text_content: str):
        """텍스트를 파일로 저장."""
        text_file_path = os.path.join(self.db_path, "text", f"{file_name}.txt")
        try:
            with open(text_file_path, 'w', encoding='utf-8') as f:
                f.write(text_content)
            logging.info(text_manager.get_log_text("319", text_file_path=text_file_path)) # f"Text saved: {text_file_path}"
        except IOError as e:
            logging.error(text_manager.get_error_text("531", file_path=text_file_path, error=e)) # f"Error saving text file {text_file_path}: {e}"
            raise

    def read_text(self, file_name: str) -> Optional[str]:
        """텍스트 파일을 읽어 반환합니다."""
        text_file_path = os.path.join(self.db_path, "text", f"{file_name}.txt")
        try:
            if os.path.exists(text_file_path):
                with open(text_file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                logging.warning(text_manager.get_warning_text("407", file_path=text_file_path)) # "Text file not found: {file_path}"
                return None
        except IOError as e:
            logging.error(text_manager.get_error_text("532", file_path=text_file_path, error=e)) # "Error reading text file {file_path}: {e}"
            return None

    def save_image(self, image_name: str, image: Image.Image):
        """이미지를 파일로 저장."""
        image_file_path = os.path.join(self.db_path, "image", image_name)
        try:
            if not isinstance(image, Image.Image):
                raise ValueError(text_manager.get_error_text("533")) # "Provided image is not a PIL.Image object."
            image.save(image_file_path)
            logging.info(text_manager.get_log_text("320", image_file_path=image_file_path)) # f"Image saved: {image_file_path}"
        except (IOError, ValueError) as e:
            logging.error(text_manager.get_error_text("534", file_path=image_file_path, error=e)) # f"Error saving image {image_file_path}: {e}"
            raise

    def get_document(self, file_name: str) -> Optional[Dict[str, Any]]:
        """파일명을 기준으로 문서 정보를 조회."""
        query = 'SELECT * FROM documents WHERE file_name = :file_name'
        result = self._execute_and_fetch(query, text_manager.get_error_text("535"), {'file_name': file_name}) # "Error fetching document"
        if result:
            return result[0]
        logging.warning(text_manager.get_warning_text("408", file_name=file_name)) # f"Document not found: {file_name}"
        return None

    # DatabaseManager 자체의 send_message는 유지 (현재 RabbitMQ 사용)
    # 하지만 궁극적으로는 MessageBroker로 통합되어야 할 기능입니다.
    def send_message(self, queue_name: str, message: Dict[str, Any]):
        """지정된 큐에 메시지를 전송합니다."""
        try:
            # send_message_to_queue 함수는 kocrd.config.config에 있다고 가정
            # 이 부분을 self.message_queue_manager.send_message(queue_name, message) 로 변경해야 함.
            # 지금은 임시로 publish_system_event를 사용하거나, 원래 구조를 따르겠습니다.
            # 원본 코드에 따라 message_queue_manager를 주입받아 사용하도록 합니다.
            self.message_queue_manager.send_message(queue_name, message) # RabbitMQ
            logging.info(text_manager.get_log_text("321", queue_name=queue_name, message=message)) # f"Message sent to queue '{queue_name}': {message}"
        except pika.exceptions.AMQPConnectionError as e:
            logging.error(text_manager.get_error_text("536", error=e)) # f"RabbitMQ 연결 오류: {e}"
            raise
        except Exception as e:
            logging.error(text_manager.get_error_text("520", error=e))
            raise

    def _execute_and_log(self, query: str, params: Optional[Dict[str, Any]], success_message: str):
        """쿼리를 실행하고 성공 메시지를 로깅합니다."""
        try:
            self.execute_query(query, params)
            logging.info(success_message)
        except SQLAlchemyError as e:
            logging.error(text_manager.get_error_text("537", error=e)) # "Error executing query: {e}"
            raise

    def _execute_and_fetch(self, query: str, error_message: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """쿼리를 실행하고 결과를 반환합니다."""
        try:
            results = self.execute_query(query, params, fetch=True)
            return results if results is not None else [] # execute_query가 None을 반환할 수 있으므로 빈 리스트 반환
        except SQLAlchemyError as e:
            logging.error(text_manager.get_error_text("538", error_message=error_message, error=e)) # f"{error_message}: {e}"
            return []

# SQLAlchemy ORM의 declarative_base는 현재 쿼리 방식에서는 직접 사용되지 않지만,
# ORM으로 전환할 계획이 있다면 유지하는 것이 좋습니다.
Base = declarative_base()