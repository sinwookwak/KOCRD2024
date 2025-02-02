# file_name: document_ui_system.py
import logging
import json
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QSplitter, QTextEdit, QProgressBar, QTableWidget, QHeaderView, QMessageBox, QInputDialog, QTableWidgetItem
from PyQt5.QtCore import Qt
import sys
import os

# 프로젝트 루트 디렉토리를 sys.path에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from window.monitoring_ui_system import MonitoringUISystem

class DocumentUISystem:
    def __init__(self, main_window):
        self.main_window = main_window
        self.table_widget = None
        self.monitoring_ui = MonitoringUISystem(main_window)
        self.progress_bar = QProgressBar(main_window)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

    def init_ui(self):
        central_widget = QWidget(self.main_window)
        self.main_window.setCentralWidget(central_widget)
        central_widget.setLayout(QVBoxLayout())

        splitter = QSplitter(central_widget)
        central_widget.layout().addWidget(splitter)

        document_ui_widget = self.create_table_widget()
        splitter.addWidget(document_ui_widget)

        monitoring_ui_widget = self.monitoring_ui
        if isinstance(monitoring_ui_widget, QWidget):
            if monitoring_ui_widget.layout() is None:
                monitoring_layout = QVBoxLayout()
                monitoring_ui_widget.setLayout(monitoring_layout)
            else:
                monitoring_layout = monitoring_ui_widget.layout()
            monitoring_layout.addWidget(self.progress_bar)
            
            log_display = QTextEdit()
            log_display.setReadOnly(True)
            monitoring_layout.addWidget(log_display)

            with open('../window/window_config.json', 'r') as f:
                config = json.load(f)

            for widget_config in config["monitoring_ui"]["widgets"]:
                widget = getattr(self.main_window, widget_config["name"])
                monitoring_layout.addWidget(widget)

        else:
            logging.error("Monitoring UI is not a QWidget. Cannot add progress bar.")

        splitter.setSizes([1000, 200])
        logging.info("DocumentUISystem UI initialized.")

    def create_table_widget(self):
        """문서 테이블 생성."""
        self.table_widget = QTableWidget()

        with open('../window/window_config.json', 'r') as f:
            config = json.load(f)

        self.table_widget.setColumnCount(len(config["table_columns"]))
        self.table_widget.setHorizontalHeaderLabels(config["table_columns"])

        # 헤더 조정
        header = self.table_widget.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)  # 컬럼 자동 크기 조정
        header.setStretchLastSection(True)

        return self.table_widget

    def clear_table(self):
        """파일 테이블을 초기화합니다."""
        with open('../window/window_config.json', 'r') as f:
            config = json.load(f)

        reply = QMessageBox.question(
            self.main_window, "테이블 초기화",
            config["messages"]["clear_table_confirmation"],
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.table_widget.setRowCount(0)  # 모든 행 삭제
            logging.info(config["messages"]["clear_table_success"])
            QMessageBox.information(self.main_window, "초기화 완료", config["messages"]["clear_table_success"])

    def filter_documents(self, criteria):
        """UIManager를 통해 문서 필터링."""
        with open('../window/window_config.json', 'r') as f:
            config = json.load(f)

        try:
            self.main_window.system_manager.ui_control_manager.document_ui.filter_table(criteria)
            logging.info("Documents filtered successfully.")
        except Exception as e:
            logging.error(f"Error filtering documents: {e}")
            QMessageBox.warning(self.main_window, "필터 오류", config["messages"]["filter_error"])

    def update_document_info(self, database_manager):
        """선택된 문서의 정보를 업데이트합니다."""
        with open('../window/window_config.json', 'r') as f:
            config = json.load(f)

        selected_items = self.table_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self.main_window, "선택 오류", config["messages"]["select_document_error"])
            return

        # 선택된 행과 현재 파일 이름 가져오기
        selected_row = selected_items[0].row()
        current_file_name = self.table_widget.item(selected_row, 0).text()

        # 새로운 문서 유형 입력받기
        new_type, ok = QInputDialog.getText(self.main_window, "문서 유형 수정",
                                            f"{current_file_name}의 새로운 문서 유형을 입력하세요:")
        if ok and new_type:
            try:
                # 데이터베이스 업데이트
                database_manager.update_document_type(current_file_name, new_type)

                # UI 테이블 업데이트
                self.table_widget.setItem(selected_row, 1, QTableWidgetItem(new_type))
                logging.info(f"Updated document type for {current_file_name} to {new_type}")
            except Exception as e:
                logging.error(f"Error updating document type for {current_file_name}: {e}")
                QMessageBox.critical(self.main_window, "업데이트 오류", f"{config['messages']['update_error']} {e}")

    def search_documents(self, keyword, column_index=None, match_exact=False):
        """문서 검색 기능을 구현합니다."""
        with open('../window/window_config.json', 'r') as f:
            config = json.load(f)

        if not keyword.strip():
            # 키워드가 비어있으면 모든 행 표시
            for row in range(self.table_widget.rowCount()):
                self.table_widget.showRow(row)
            logging.info(config["messages"]["search_empty"])
            return

        # 검색 조건에 따라 테이블 행 처리
        for row in range(self.table_widget.rowCount()):
            match_found = False
            for col in range(self.table_widget.columnCount()):
                # 특정 열에서 검색하는 경우 필터링
                if column_index is not None and col != column_index:
                    continue

                item = self.table_widget.item(row, col)
                if item:
                    cell_text = item.text().lower()
                    keyword_lower = keyword.lower()

                    # 완전 일치 또는 부분 검색 조건
                    if (match_exact and cell_text == keyword_lower) or (not match_exact and keyword_lower in cell_text):
                        match_found = True
                        break

            # 행 표시 또는 숨기기
            if match_found:
                self.table_widget.showRow(row)
            else:
                self.table_widget.hideRow(row)

        logging.info(f"Document search completed for keyword: {keyword}")

    def delete_document(self, file_name, database_manager):
        """문서를 삭제합니다."""
        with open('../window/window_config.json', 'r') as f:
            config = json.load(f)

        try:
            if not file_name:
                # UI에서 선택된 문서를 삭제
                selected_items = self.table_widget.selectedItems()
                if not selected_items:
                    QMessageBox.warning(self.main_window, "선택 오류", config["messages"]["select_document_error"])
                    return

                # 선택된 행에서 파일 이름 가져오기
                selected_row = selected_items[0].row()
                file_name = self.table_widget.item(selected_row, 0).text()

                # 사용자 확인
                reply = QMessageBox.question(
                    self.main_window, "문서 삭제",
                    config["messages"]["delete_confirmation"].format(file_name=file_name),
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return

                # UI에서 행 삭제
                self.table_widget.removeRow(selected_row)
            else:
                # 파일 이름이 직접 전달된 경우
                if not self.main_window.system_manager.ui_control_manager.document_ui.remove_document_from_table(file_name):
                    logging.warning(f"File {file_name} not found in table.")

            # 데이터베이스에서 문서 삭제
            database_manager.delete_document(file_name)
            logging.info(config["messages"]["delete_success"].format(file_name=file_name))
            QMessageBox.information(self.main_window, "삭제 완료", config["messages"]["delete_success"].format(file_name=file_name))
        except Exception as e:
            logging.error(f"Error deleting document: {e}")
            QMessageBox.critical(self.main_window, "삭제 오류", f"{config['messages']['delete_error']} {e}")
