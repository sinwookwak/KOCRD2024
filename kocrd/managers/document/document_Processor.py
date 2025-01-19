# file_name: Document_Processor.py

import os
import logging
import datetime
from fpdf import FPDF
from pdf2image import convert_from_path  # pdf2image 임포트 추가
DEFAULT_REPORT_FILENAME = os.environ.get("DEFAULT_REPORT_FILENAME", "report.txt")
DEFAULT_EXCEL_FILENAME = os.environ.get("DEFAULT_EXCEL_FILENAME", "documents.xlsx")
VALID_FILE_EXTENSIONS = os.environ.get("VALID_FILE_EXTENSIONS", [".txt", ".pdf", ".png", ".jpg", ".xlsx", ".docx"])
MAX_FILE_SIZE = int(os.environ.get("MAX_FILE_SIZE", 10 * 1024 * 1024)) # 10MB default # 잘못된 환경 변수 값일 경우 예외 발생
from PyQt5.QtWidgets import QMessageBox, QFileDialog
import mimetypes

class DocumentProcessor:
    """
    문서 처리 로직을 담당하는 클래스.
    OCR 수행, 데이터베이스 저장 등의 기능을 제공합니다.
    """
    def __init__(self, database_manager, ocr_manager, parent, system_manager): # system_manager 추가
        self.system_manager = system_manager # system_manager 저장
        self.database_manager = database_manager
        self.ocr_manager = ocr_manager
        self.parent = parent # QMessageBox 사용을 위해 parent 추가
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
            logging.error(f"Error performing OCR on {file_path}: {e}")
            raise
    def process_single_document(self, file_path):
        """단일 문서를 처리합니다 (유효성 검사, OCR, 정보 생성 및 저장)."""
        max_file_size = self.system_manager.get_setting("MAX_FILE_SIZE") # 설정 값 가져오기
        valid_file_extensions = self.system_manager.get_setting("VALID_FILE_EXTENSIONS")

        if not os.path.isfile(file_path):
            QMessageBox.warning(self.parent, "파일 오류", f"파일이 존재하지 않습니다: {file_path}") # 파일 경로 추가
            return None

        file_extension = os.path.splitext(file_path)[1].lower()
        if file_extension not in VALID_FILE_EXTENSIONS:
            QMessageBox.warning(self.parent, "지원되지 않는 파일", f"허용되지 않는 파일 형식입니다. 허용된 형식: {', '.join(VALID_FILE_EXTENSIONS)}")
            return None
        file_size = os.path.getsize(file_path) # file_size 변수 정의
        max_file_size_mb = MAX_FILE_SIZE / (1024 * 1024)
        if file_size > MAX_FILE_SIZE:
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
            document_info = self.process_single_document(file_path) # 변경된 메서드 이름 사용
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
                return False  # 문서가 없을 경우 False 반환

            for key, value in new_data.items():
                if key in document:
                    document[key] = value

            self.database_manager.update_document(file_name, document)
            logging.info(f"Document updated successfully: {file_name}")
            return True # 성공적으로 수정 시 True 반환
        except Exception as e:
            logging.error(f"Error editing document {file_name}: {e}")
            return False # 오류 발생 시 False 반환
    def determine_document_type(self, text):
        """
        자동 문서 분석.
        Args: text (str): OCR로 추출된 텍스트.
        Returns: str: 문서 유형 (예: "Invoice", "Report" 등).
        """
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

    def save_ocr_images(self, pdf_file_path):
        """
        PDF 파일에서 OCR 이미지를 추출하고 저장합니다.

        Args:
            pdf_file_path (str): 처리할 PDF 파일 경로.
        """
        logging.info(f"Saving OCR images for: {pdf_file_path}")
        try:
            poppler_path = self.ocr_manager.find_poppler_path() #ocr_manager에서 poppler 경로를 가져옴
            if not poppler_path:
                raise FileNotFoundError("Poppler 경로를 찾을 수 없습니다.")
            images = convert_from_path(pdf_file_path, poppler_path=poppler_path) #pdf를 이미지로 변환
            for i, image in enumerate(images):
                image_path = f"{pdf_file_path}_page_{i + 1}.png"
                image.save(image_path)
                logging.info(f"OCR image saved: {image_path}")
        except FileNotFoundError as e:
            logging.error(str(e))
        except Exception as e:
            logging.error(f"Error saving OCR images: {e}")

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
                return [] # 빈 리스트 반환

            results = self.process_multiple_documents(file_paths) # process_multiple_documents 활용
            return results # 처리된 문서 정보 리스트 반환

        except Exception as e:
            logging.error(f"Error importing documents: {e}")
            return [] # 오류 발생 시 빈 리스트 반환
