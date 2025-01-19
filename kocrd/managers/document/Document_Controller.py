# file_name: Document_Controller.py

import logging
import os
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QWidget, QVBoxLayout
import pandas as pd
from fpdf import FPDF
from managers.document.Document_Table_View import DocumentTableView

DEFAULT_REPORT_FILENAME = os.environ.get("DEFAULT_REPORT_FILENAME", "report.txt")
DEFAULT_EXCEL_FILENAME = os.environ.get("DEFAULT_EXCEL_FILENAME", "documents.xlsx")

class DocumentController(QWidget):
    def __init__(self, document_processor, parent, system_manager): # system_manager 추가
        self.document_processor = document_processor
        self.parent = parent
        self.system_manager = system_manager
        self.document_table_view = DocumentTableView(self)
        self.init_ui()
        logging.info("DocumentController initialized.")
    def init_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(self.document_table_view)
        self.setLayout(layout)
    def get_ui(self):
        return self.document_table_view
    def open_file_dialog(self):
        file_dialog = QFileDialog(self.parent, "문서 가져오기")
        file_dialog.setFileMode(QFileDialog.ExistingFiles)
        file_paths, _ = file_dialog.getOpenFileNames(
            self.parent, "문서 가져오기", "", f"모든 파일 (*.*);;텍스트 파일 (*.txt);;PDF 파일 (*.pdf);;이미지 파일 (*.png *.jpg);;엑셀 파일 (*.xlsx);;워드 파일 (*.docx)"
        )
        return file_paths
    def import_documents(self):
        file_paths = self.open_file_dialog()
        if not file_paths:
            return

        document_infos = self.document_processor.process_multiple_documents(file_paths)
        if document_infos:
            for document_info in document_infos:
                self.document_table_view.add_document(document_info)
    def generate_report(self, output_path=None):
        default_report_filename = self.system_manager.get_setting("DEFAULT_REPORT_FILENAME")
        # DocumentTableView의 데이터를 가져와 보고서 생성
        extracted_texts = []
        headers = self.document_table_view.headers # document_table_view의 headers 사용
        extracted_texts.append("\t".join(headers))
        for row in range(self.document_table_view.table_widget.rowCount()):
            row_data = []
            for col in range(self.document_table_view.table_widget.columnCount()):
                item = self.document_table_view.table_widget.item(row, col)
                row_data.append(item.text() if item else "")
            extracted_texts.append("\t".join(row_data))
        if not output_path:
            output_path, _ = QFileDialog.getSaveFileName(
                self.parent, "보고서 저장", DEFAULT_REPORT_FILENAME, "Text Files (*.txt);;All Files (*)"
            )
            if not output_path:
                QMessageBox.warning(self.parent, "저장 취소", "보고서 저장이 취소되었습니다.")
                return

        if not extracted_texts:
            QMessageBox.warning(self.parent, "보고서 생성 오류", "보고서에 포함할 데이터가 없습니다.")
            return

        try:
            with open(output_path, 'w', encoding='utf-8') as report_file:
                report_file.write("\n".join(extracted_texts))
            logging.info(f"Report saved to {output_path}")
            QMessageBox.information(self.parent, "저장 완료", f"보고서가 저장되었습니다: {output_path}")
        except Exception as e:
            logging.error(f"Error saving report: {e}")
            QMessageBox.critical(self.parent, "저장 오류", f"보고서를 저장하는 중 오류가 발생했습니다: {e}")
    def export_to_pdf(self, filename="output.pdf"):
        # DocumentTableView의 데이터를 가져와 PDF 생성
        data = []
        for row in range(self.document_table_view.table_widget.rowCount()):
            row_data = []
            for col in range(self.document_table_view.table_widget.columnCount()):
                item = self.document_table_view.table_widget.item(row, col)
                row_data.append(item.text() if item else "")
            data.append(row_data)

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        for row in data:
            for item in row:
                pdf.cell(40, 10, txt=str(item), border=1) # cell 크기 조정, border 추가
            pdf.ln() # 줄 바꿈
        pdf.output(filename)
        logging.info(f"PDF saved to {filename}.")
    def save_to_excel(self, file_path=None):
        default_excel_filename = self.system_manager.get_setting("DEFAULT_EXCEL_FILENAME")
        # DocumentTableView의 데이터를 가져와 Excel 저장
        rows = []
        for row in range(self.document_table_view.table_widget.rowCount()):
            row_data = []
            for col in range(self.document_table_view.table_widget.columnCount()):
                item = self.document_table_view.table_widget.item(row, col)
                row_data.append(item.text() if item else "")
            rows.append(row_data)

        df = pd.DataFrame(rows, columns=self.document_table_view.headers) # 헤더 정보는 DocumentTableView에서 가져옴
        try:
            if not file_path:
                file_path, _ = QFileDialog.getSaveFileName(
                    self.parent, "Excel 파일 저장", DEFAULT_EXCEL_FILENAME, "Excel Files (*.xlsx);;All Files (*)" # config 사용
                )
                if not file_path:
                    QMessageBox.warning(self.parent, "저장 취소", "Excel 파일 저장이 취소되었습니다.")
                    return
            if not os.path.splitext(file_path)[-1].lower() == '.xlsx':
                file_path += '.xlsx'

            df.to_excel(file_path, index=False, engine='openpyxl')
            logging.info(f"Data saved to Excel: {file_path}")
            QMessageBox.information(self.parent, "저장 완료", f"Excel 파일로 문서 정보가 저장되었습니다: {file_path}")
        except PermissionError as e:
            logging.error(f"Permission error when saving Excel file {file_path}: {e}")
            QMessageBox.critical(self.parent, "저장 오류", f"Excel 파일 {file_path}을(를) 저장하는 중 권한 오류가 발생했습니다: {e}")
        except IOError as e:
            logging.error(f"IO error when saving Excel file {file_path}: {e}")
            QMessageBox.critical(self.parent, "저장 오류", f"Excel 파일 {file_path}을(를) 저장하는 중 오류가 발생했습니다: {e}")
        except Exception as e:
            logging.error(f"Unexpected error when saving Excel file {file_path}: {e}")
            QMessageBox.critical(self.parent, "저장 오류", f"예기치 않은 오류가 발생했습니다: {e}")
    def clear_table(self):
        self.document_table_view.clear_table()
    def filter_documents(self, criteria):
        self.document_table_view.filter_table(criteria)
    def get_selected_file_name(self):
        return self.document_table_view.get_selected_file_name()
    def load_document(self, file_path):
        document_info = self.document_processor.process_single_document(file_path)
        if document_info:
            self.document_table_view.add_document(document_info)