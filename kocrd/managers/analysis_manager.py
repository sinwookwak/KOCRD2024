# file_name: AnalysisManager
import concurrent.futures
import logging
from pdf2image import convert_from_path
import pytesseract

class SystemManager:
    def __init__(self):
        self.analysis_manager = AnalysisManager()

class AnalysisManager:
    def __init__(self):
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)
        logging.info("AnalysisManager initialized with ThreadPoolExecutor.")

    def analyze_document(self, file_path):
        try:
            pages = convert_from_path(file_path, 500)
            extracted_text = ""
            for page in pages:
                text = pytesseract.image_to_string(page, lang='kor+eng')
                extracted_text += text + "\n"
            return extracted_text
        except Exception as e:
            logging.error(f"Error during document analysis: {e}")
            return ""

    def analyze_document_async(self, file_path, callback):
        future = self.executor.submit(self.analyze_document, file_path)
        future.add_done_callback(lambda f: callback(f.result()))

