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
# config import
DEFAULT_REPORT_FILENAME = os.environ.get("DEFAULT_REPORT_FILENAME", "report.txt")
DEFAULT_EXCEL_FILENAME = os.environ.get("DEFAULT_EXCEL_FILENAME", "documents.xlsx")
VALID_FILE_EXTENSIONS = os.environ.get("VALID_FILE_EXTENSIONS", [".txt", ".pdf", ".png", ".jpg", ".xlsx", ".docx"])
MAX_FILE_SIZE = int(os.environ.get("MAX_FILE_SIZE", 10 * 1024 * 1024))
import os
from .Document_Controller import DocumentController
from .Document_Table_View import DocumentTableView # 상대 경로 import
from .document_Processor import DocumentProcessor # 상대 경로 import

class DocumentManager(QWidget):
    def __init__(self, ocr_manager, database_manager, message_queue_manager, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.message_queue_manager = message_queue_manager
        self.database_manager = database_manager
        self.ocr_manager = ocr_manager
        self.document_processor = DocumentProcessor(database_manager, ocr_manager, parent) # 인스턴스 생성!
        self.document_table_view = DocumentTableView(self) #인스턴스 생성
        self.document_controller = DocumentController(self.document_processor, parent) # 인스턴스 생성!
        logging.info("DocumentManager initialized.")
    def add_document_to_table(self, document_info):
        self.document_table_view.add_document(document_info)

    def send_message(self, message_type, message_data):
        self.message_queue_manager.send_message(message_type, message_data)

    def get_ui(self):
        return self.document_controller.get_ui()

    def search_documents(self, keyword, column_index=None, match_exact=False):
        if not keyword.strip():
            for row in range(self.document_controller.get_ui().table_widget.rowCount()): # 수정
                self.document_controller.get_ui().table_widget.showRow(row) # 수정
            logging.info("Search keyword is empty. Showing all rows.")
            return

        found_any = False

        for row in range(self.document_controller.get_ui().table_widget.rowCount()): # 수정
            match_found = False
            for col in range(self.document_controller.get_ui().table_widget.columnCount()): # 수정
                if column_index is not None and col != column_index:
                    continue

                item = self.document_controller.get_ui().table_widget.item(row, col) # 수정
                if item:
                    cell_text = item.text().lower()
                    keyword_lower = keyword.lower()

                    if (match_exact and cell_text == keyword_lower) or (not match_exact and keyword_lower in cell_text):
                        match_found = True
                        found_any = True
                        break

            if match_found:
                self.document_controller.get_ui().table_widget.showRow(row) # 수정
            else:
                self.document_controller.get_ui().table_widget.hideRow(row) # 수정

        if not found_any:
            QMessageBox.information(self, "검색 결과", "검색 결과가 없습니다.")

        logging.info(f"Document search completed for keyword: {keyword}")
    def save_ocr_images(self, pdf_file_path):
        logging.info(f"Saving OCR images for: {pdf_file_path}")
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
            logging.error(str(e))
        except Exception as e:
            logging.error(f"Error saving OCR images: {e}")

    def save_feedback(self, feedback_data):
        """피드백 데이터를 저장."""
        query = '''
        INSERT INTO feedback (file_path, doc_type, timestamp)
        VALUES (:file_path, :doc_type, :timestamp)
        ON CONFLICT(file_path) DO UPDATE SET
        doc_type = excluded.doc_type,
        timestamp = excluded.timestamp
        '''
        self.execute_query(query, feedback_data)
        logging.info(f"Feedback saved: {feedback_data}")
    def get_valid_doc_types(self):
        """유효한 문서 유형을 데이터베이스에서 로드."""
        query = 'SELECT DISTINCT doc_type FROM feedback'
        try:
            results = self.execute_query(query, fetch=True)
            return [row['doc_type'] for row in results] if results else []
        except SQLAlchemyError as e:
            logging.error(f"Error fetching valid document types: {e}")
            return []
    def determine_document_type(self, text):
        if not text:
            logging.warning("No text provided for document type determination.")
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
            logging.error(f"Error determining document type: {e}")
            return "Unknown"

    def export_to_pdf(self, data, filename="output.pdf"):
        """데이터를 PDF로 내보냅니다."""
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        for item in data:
            pdf.cell(200, 10, txt=str(item), ln=True, align='C')
        pdf.output(filename)
        logging.info(f"PDF 파일이 저장되었습니다: {filename}")
    def start_consuming(self):
        """RabbitMQ 메시지 처리를 별도의 스레드에서 실행."""
        def consume_messages():
            try:
                connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
                channel = connection.channel()

                channel.queue_declare(queue='document_processing_queue')
                channel.queue_declare(queue='database_packaging_queue')

                channel.basic_consume(queue='document_processing_queue', on_message_callback=process_document_task, auto_ack=True)
                channel.basic_consume(queue='database_packaging_queue', on_message_callback=process_database_packaging_task, auto_ack=True)

                print('Waiting for messages. To exit press CTRL+C')
                channel.start_consuming() # 메시지 소비 시작. 블로킹 함수
            except pika.exceptions.AMQPConnectionError as e:
                logging.error(f"RabbitMQ 연결 오류 (스레드): {e}")
                # 스레드에서 UI 요소에 접근할 때는 invoke를 사용해야 함
                QApplication.instance().invoke(lambda: QMessageBox.critical(self.parent, "RabbitMQ 연결 오류", str(e)))

        thread = threading.Thread(target=consume_messages)
        thread.daemon = True # 메인 스레드가 종료될 때 함께 종료
        thread.start()

def process_document_task(ch, method, properties, body):
    message = json.loads(body)
    file_paths = message.get("file_paths")
    cleanup = message.get("cleanup")
    print(f"Received document processing task: {file_paths}")
    time.sleep(5) #문서 처리 작업 대신 5초 대기
    # 실제 문서 처리 로직 구현 (SystemManager의 handle_documents 로직을 여기에 옮김)
    # ...

def process_database_packaging_task(ch, method, properties, body):
    message = json.loads(body)
    print("Received database packaging task")
    time.sleep(5) #데이터베이스 패키징 작업 대신 5초 대기
    # 실제 데이터베이스 패키징 로직 구현 (SystemManager의 database_packaging 로직을 여기에 옮김)
    # ...
