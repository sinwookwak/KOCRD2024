# file_name: document_ui_system.py
import logging
import json
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QSplitter, QTextEdit, QProgressBar, QTableWidget, QHeaderView, QMessageBox, QInputDialog, QTableWidgetItem
from PyQt5.QtCore import Qt
import sys
import os

# 프로젝트 루트 디렉토리를 sys.path에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from kocrd.window.monitoring_ui_system import MonitoringUISystem
from kocrd.config.config import load_config, get_message

class DocumentUISystem:
    def __init__(self, main_window):
        self.main_window = main_window
        self.table_widget = None
        self.monitoring_ui = MonitoringUISystem(main_window)
        self.progress_bar = QProgressBar(main_window)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        self.messages_config = load_config("config/messages.json")
        self.messages = self.messages_config["messages"]

    def _execute_action(self, action, confirmation_key=None, success_key=None, error_key=None, **kwargs):
        if confirmation_key:
            reply = QMessageBox.question(
                self.main_window, "확인",
                get_message(self.messages, confirmation_key).format(**kwargs),
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        try:
            result = action() if callable(action) else None  # Execute the action and store the result
            if success_key:
                QMessageBox.information(self.main_window, "완료", get_message(self.messages, success_key).format(**kwargs))
            return result # Return the result of the action
        except Exception as e:
            logging.error(f"Error: {e}")
            if error_key:
                QMessageBox.warning(self.main_window, "오류", get_message(self.messages, error_key))

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

            for widget_config in self.config["monitoring_ui"]["widgets"]:
                widget = getattr(self.main_window, widget_config["name"])
                monitoring_layout.addWidget(widget)

        else:
            logging.error("Monitoring UI is not a QWidget. Cannot add progress bar.")

        splitter.setSizes([1000, 200])
        logging.info("DocumentUISystem UI initialized.")

    def create_table_widget(self):
        """문서 테이블 생성."""
        self.table_widget = QTableWidget()

        self.table_widget.setColumnCount(len(self.messages["table_columns"]))
        self.table_widget.setHorizontalHeaderLabels(self.messages["table_columns"])

        # 헤더 조정
        header = self.table_widget.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)  # 컬럼 자동 크기 조정
        header.setStretchLastSection(True)

        return self.table_widget

    def clear_table(self):
        """파일 테이블을 초기화합니다."""
        self._execute_action(self._clear_table_action, "201", "203")

    def _clear_table_action(self):
        self.table_widget.setRowCount(0)  # 모든 행 삭제
        logging.info(get_message(self.messages, "203"))

    def filter_documents(self, criteria):
        """UIManager를 통해 문서 필터링."""
        self._execute_with_logging(
            lambda: self.main_window.system_manager.ui_control_manager.document_ui.filter_table(criteria),
            "311",
            "201"
        )

    def update_document_info(self, database_manager):
        """선택된 문서의 정보를 업데이트합니다."""
        selected_items = self.table_widget.selectedItems()
        if not selected_items:
            self._show_message_box("208")
            return

        selected_row = selected_items[0].row()
        current_file_name = self.table_widget.item(selected_row, 0).text()
        new_type, ok = QInputDialog.getText(self.main_window, "문서 유형 수정", f"{current_file_name}의 새로운 문서 유형을 입력하세요:")
        if ok and new_type:
            self._execute_action(
                lambda: self._update_document_type(database_manager, current_file_name, new_type, selected_row),
                success_key="204",
                error_key="205"
            )

    def _update_document_type(self, database_manager, current_file_name, new_type, selected_row):
        database_manager.update_document_type(current_file_name, new_type)
        self.table_widget.setItem(selected_row, 1, QTableWidgetItem(new_type))
        logging.info(f"Updated document type for {current_file_name} to {new_type}")

    def search_documents(self, keyword, column_index=None, match_exact=False):
        """문서 검색 기능을 구현합니다."""
        if not keyword.strip():
            for row in range(self.table_widget.rowCount()):
                self.table_widget.showRow(row)
            logging.info(get_message(self.messages, "209"))
            return

        for row in range(self.table_widget.rowCount()):
            match_found = False
            for col in range(self.table_widget.columnCount()):
                if column_index is not None and col != column_index:
                    continue

                item = self.table_widget.item(row, col)
                if item:
                    cell_text = item.text().lower()
                    keyword_lower = keyword.lower()
                    if (match_exact and cell_text == keyword_lower) or (not match_exact and keyword_lower in cell_text):
                        match_found = True
                        break

            if match_found:
                self.table_widget.showRow(row)
            else:
                self.table_widget.hideRow(row)

        logging.info(f"Document search completed for keyword: {keyword}")

    def delete_document(self, file_name, database_manager):
        """문서를 삭제합니다."""
        selected_items = self.table_widget.selectedItems()
        if not selected_items:
            self._show_message_box("208")
            return

        selected_row = selected_items[0].row()
        file_name = self.table_widget.item(selected_row, 0).text()
        self._execute_action(
            lambda: self._delete_document_action(database_manager, file_name, selected_row),
            confirmation_key="205",
            success_key="206",
            file_name=file_name
        )

    def _delete_document_action(self, database_manager, file_name, selected_row):
        self.table_widget.removeRow(selected_row)
        database_manager.delete_document(file_name)
        logging.info(get_message(self.messages, "206").format(file_name=file_name))

    def _show_message_box(self, confirmation_key, success_key=None, action=None, **kwargs):
        reply = QMessageBox.question(
            self.main_window, "확인",
            get_message(self.messages, confirmation_key).format(**kwargs),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes and action:
            action()
            if success_key:
                QMessageBox.information(self.main_window, "완료", get_message(self.messages, success_key).format(**kwargs))

    def _execute_with_logging(self, action, success_key, error_key):
        try:
            action()
            logging.info(get_message(self.messages, success_key))
        except Exception as e:
            logging.error(f"Error: {e}")
            QMessageBox.warning(self.main_window, "오류", get_message(self.messages, error_key))
