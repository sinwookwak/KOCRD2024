# file_name: DatabaseManager
import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from PIL import Image
import shutil
from datetime import datetime
from sqlalchemy.orm import declarative_base
import pika
import json

class DatabaseManager:
    def __init__(self, db_path, backup_path=None):
        self.db_path = db_path
        self.backup_path = backup_path
        # 기타 초기화 코드
        if self.backup_path:
            logging.info(f"Backup path set to: {self.backup_path}")
        self.db_file = os.path.join(db_path, "documents.db")
        self.engine = create_engine(f'sqlite:///{self.db_file}', pool_size=10, max_overflow=20)

        # 이미지 및 텍스트 디렉토리 생성
        os.makedirs(os.path.join(db_path, "image"), exist_ok=True)
        os.makedirs(os.path.join(db_path, "text"), exist_ok=True)

        # 데이터베이스 초기화
        self.initialize_database()
        logging.info(f"DatabaseManager initialized with database path: {db_path}")
    def set_package_path(self, new_path):
        """데이터베이스 경로를 업데이트하고 엔진을 재초기화."""
        self.db_path = new_path
        self.db_file = os.path.join(new_path, "documents.db")
        self.engine = create_engine(f'sqlite:///{self.db_file}', pool_size=10, max_overflow=20)
        self.initialize_database()
        logging.info(f"Database path updated to: {new_path}")
    def initialize_database(self):
        """SQLAlchemy를 사용하여 데이터베이스 테이블 생성."""
        try:
            config_path = os.path.join(os.path.dirname(__file__), '../config/development.json')
            with open(config_path, 'r') as f:
                config = json.load(f)
            queries = [text(query) for query in config["database"]["init_queries"]]
            with self.engine.connect() as conn:
                for query in queries:
                    conn.execute(query)
                logging.info("Database initialized and required tables created.")
        except (SQLAlchemyError, IOError, KeyError) as e:
            logging.error(f"Error initializing database: {e}")
            raise RuntimeError("Database initialization failed.") from e
    def execute_query(self, query, params=None, fetch=False):
        """데이터베이스 쿼리를 실행하는 공통 메서드."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query), params or {})
                if fetch:
                    return [dict(row) for row in result]
                return None
        except SQLAlchemyError as e:
            logging.error(f"Database query error: {e}")
            raise
    def update_document_info(self, document_info):
        """
        문서 정보를 업데이트합니다.
        """
        query = '''
        UPDATE documents
        SET type = :type, date = :date, supplier = :supplier
        WHERE file_name = :file_name
        '''
        try:
            self.execute_query(query, document_info)
            logging.info(f"Document info updated: {document_info}")
        except SQLAlchemyError as e:
            logging.error(f"Error updating document info: {e}")
            raise
    def update_document_type(self, file_name, new_type):
        """문서의 유형을 업데이트합니다."""
        try:
            with self.engine.connect() as conn:
                conn.execute(
                    text("UPDATE documents SET type = :new_type WHERE file_name = :file_name"),
                    {"new_type": new_type, "file_name": file_name}
                )
                logging.info(f"Document {file_name} updated to type: {new_type}")
        except Exception as e:
            logging.error(f"Error updating document type for {file_name}: {e}")
            raise
    def package_database(self):
        """데이터베이스를 패키징하여 백업."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        package_name = os.path.join(self.backup_path, f"database_package_{timestamp}")
        try:
            backup_dir = os.path.join(self.backup_path, f"backup_{timestamp}")
            os.makedirs(backup_dir, exist_ok=True)
            shutil.copy(self.db_file, backup_dir)  # 데이터베이스 파일 복사
            shutil.make_archive(package_name, 'zip', backup_dir)
            shutil.rmtree(backup_dir)  # 임시 백업 디렉토리 삭제
            logging.info(f"Database packaged as '{package_name}.zip'.")
        except Exception as e:
            logging.error(f"Error during packaging database: {e}")
            raise
    def save_document_info(self, document_info):
        """문서 정보를 데이터베이스에 저장하거나 업데이트."""
        query = '''
        INSERT INTO documents (file_name, type, date, supplier)
        VALUES (:file_name, :type, :date, :supplier)
        ON CONFLICT(file_name) DO UPDATE SET
        type = excluded.type,
        date = excluded.date,
        supplier = excluded.supplier;
        '''
        try:
            self.execute_query(query, document_info)
            logging.info(f"Document info saved or updated: {document_info}")
        except SQLAlchemyError as e:
            logging.error(f"Error saving document info: {e}")
            raise
    def load_documents(self):
        """저장된 문서 정보를 로드."""
        query = 'SELECT file_name, type, date, supplier FROM documents'
        try:
            return self.execute_query(query, fetch=True)
        except SQLAlchemyError as e:
            logging.error(f"Error loading documents: {e}")
            return []
    def delete_document(self, file_name):
        """데이터베이스에서 문서를 삭제."""
        query = 'DELETE FROM documents WHERE file_name = :file_name'
        try:
            self.execute_query(query, {'file_name': file_name})
            logging.info(f"Document deleted: {file_name}")
        except SQLAlchemyError as e:
            logging.error(f"Error deleting document: {e}")
            raise
    def save_feedback(self, feedback_data):
        """피드백 데이터를 저장."""
        query = '''
        INSERT INTO feedback (file_path, doc_type, timestamp)
        VALUES (:file_path, :doc_type, :timestamp)
        ON CONFLICT(file_path) DO UPDATE SET
        doc_type = excluded.doc_type,
        timestamp = excluded.timestamp
        '''
        try:
            self.execute_query(query, feedback_data)
            logging.info(f"Feedback saved: {feedback_data}")
        except SQLAlchemyError as e:
            logging.error(f"Error saving feedback: {e}")
            raise
    def save_text(self, file_name, text):
        """텍스트를 파일로 저장."""
        text_file_path = os.path.join(self.db_path, "text", f"{file_name}.txt")
        try:
            with open(text_file_path, 'w', encoding='utf-8') as f:
                f.write(text)
            logging.info(f"Text saved: {text_file_path}")
        except IOError as e:
            logging.error(f"Error saving text file {text_file_path}: {e}")
            raise
    def save_image(self, file_name, image):
        """이미지를 파일로 저장."""
        image_file_path = os.path.join(self.db_path, "image", file_name)
        try:
            if not isinstance(image, Image.Image):
                raise ValueError("Provided image is not a PIL.Image object.")
            image.save(image_file_path)
            logging.info(f"Image saved: {image_file_path}")
        except (IOError, ValueError) as e:
            logging.error(f"Error saving image {image_file_path}: {e}")
            raise
    def get_document(self, file_name):
        """파일명을 기준으로 문서 정보를 조회."""
        query = text('SELECT * FROM documents WHERE file_name = :file_name')
        try:
            result = self.execute_query(query, {'file_name': file_name}, fetch=True)
            if result:
                return result[0]
            logging.warning(f"Document not found: {file_name}")
            return None
        except SQLAlchemyError as e:
            logging.error(f"Error fetching document: {e}")
            raise
    def send_message(self, queue_name, message):
        """지정된 큐에 메시지를 전송합니다."""
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
            channel = connection.channel()
            channel.queue_declare(queue=queue_name)
            channel.basic_publish(exchange='', routing_key=queue_name, body=json.dumps(message))
            connection.close()
            logging.info(f"Message sent to queue '{queue_name}': {message}")
        except pika.exceptions.AMQPConnectionError as e:
            logging.error(f"RabbitMQ 연결 오류: {e}")
            raise

Base = declarative_base()
