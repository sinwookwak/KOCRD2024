# DocumentUI.py

import os
import logging
from PyQt5.QtWidgets import QTableWidget, QHeaderView, QMessageBox
from PyQt5.QtWidgets import QTableWidgetItem, QFileDialog, QInputDialog

class DocumentUI:
    """문서 목록 테이블 UI 생성 클래스."""
    def __init__(self):
        # 테이블 위젯 저장
        self.table_widget = None

    def create_table_widget(self):
        """문서 테이블 생성."""
        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(10)
        self.table_widget.setHorizontalHeaderLabels([
            '파일명', '유형', '텍스트', '날짜', '담당자',
            '공급자', '물품명', '카탈로그 번호', '결합 내용', '파일 경로'
        ])
        
        # 헤더 조정
        header = self.table_widget.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)  # 컬럼 자동 크기 조정
        header.setStretchLastSection(True)
        
        return self.table_widget

    def setup_widget(self):
        """테이블 위젯 초기화 및 반환."""
        if not self.table_widget:
            self.table_widget = QTableWidget()
            self.table_widget.setColumnCount(4)  # 필요한 열 수 설정
            self.table_widget.setHorizontalHeaderLabels(['파일명', '유형', '날짜', '공급자'])
        return self.table_widget

    def clear_table(self):
        """파일 테이블을 초기화합니다."""
        reply = QMessageBox.question(
            self, "테이블 초기화",
            "파일 테이블의 모든 데이터를 삭제하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.file_table.setRowCount(0)  # 모든 행 삭제
            logging.info("파일 테이블이 초기화되었습니다.")
            QMessageBox.information(self, "초기화 완료", "파일 테이블이 초기화되었습니다.")

    def filter_documents(self, criteria):#처리됨
        """UIManager를 통해 문서 필터링."""
        try:
            self.ui_control_manager.document_ui.filter_table(criteria)
            logging.info("Documents filtered successfully.")
        except Exception as e:
            logging.error(f"Error filtering documents: {e}")
            QMessageBox.warning(self.ui_control_manager.document_ui.table_widget, "필터 오류", "문서를 필터링하는 중 오류가 발생했습니다.")
    def update_document_info(self, database_manager):
        """선택된 문서의 정보를 업데이트합니다."""
        selected_items = self.file_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "선택 오류", "수정할 문서를 선택하세요.")
            return

        # 선택된 행과 현재 파일 이름 가져오기
        selected_row = selected_items[0].row()
        current_file_name = self.file_table.item(selected_row, 0).text()

        # 새로운 문서 유형 입력받기
        new_type, ok = QInputDialog.getText(self, "문서 유형 수정",
                                            f"{current_file_name}의 새로운 문서 유형을 입력하세요:")
        if ok and new_type:
            try:
                # 데이터베이스 업데이트
                self.database_manager.update_document_type(current_file_name, new_type)

                # UI 테이블 업데이트
                self.file_table.setItem(selected_row, 1, QTableWidgetItem(new_type))
                logging.info(f"Updated document type for {current_file_name} to {new_type}")
            except Exception as e:
                logging.error(f"Error updating document type for {current_file_name}: {e}")
                QMessageBox.critical(self, "업데이트 오류", f"문서 유형을 업데이트하는 중 오류가 발생했습니다: {e}")

    def search_documents(self, keyword, column_index=None, match_exact=False):
        # 키워드 검색 및 테이블 행 필터링
        """
        문서 검색 기능을 구현합니다.
        
        Args:
            keyword (str): 검색 키워드.
            column_index (int, optional): 특정 열에서 검색하려는 경우 해당 열의 인덱스. None이면 모든 열 검색. Default는 None.
            match_exact (bool, optional): True일 경우 완전 일치 검색, False일 경우 부분 검색. Default는 False.
        """
        if not keyword.strip():
            # 키워드가 비어있으면 모든 행 표시
            for row in range(self.file_table.rowCount()):
                self.file_table.showRow(row)
            logging.info("Search keyword is empty. Showing all rows.")
            return

        # 검색 조건에 따라 테이블 행 처리
        for row in range(self.file_table.rowCount()):
            match_found = False
            for col in range(self.file_table.columnCount()):
                # 특정 열에서 검색하는 경우 필터링
                if column_index is not None and col != column_index:
                    continue

                item = self.file_table.item(row, col)
                if item:
                    cell_text = item.text().lower()
                    keyword_lower = keyword.lower()

                    # 완전 일치 또는 부분 검색 조건
                    if (match_exact and cell_text == keyword_lower) or (not match_exact and keyword_lower in cell_text):
                        match_found = True
                        break

            # 행 표시 또는 숨기기
            if match_found:
                self.file_table.showRow(row)
            else:
                self.file_table.hideRow(row)

        logging.info(f"Document search completed for keyword: {keyword}")

    def delete_document(self, file_name, database_manager):
        """
        문서를 삭제합니다.

        Args:
            file_name (str): 삭제할 문서의 파일 이름. None이면 UI에서 선택된 문서를 삭제.
        """
        try:
            if not file_name:
                # UI에서 선택된 문서를 삭제
                selected_items = self.ui_control_manager.document_ui.table_widget.selectedItems()
                if not selected_items:
                    QMessageBox.warning(self, "선택 오류", "삭제할 문서를 선택하세요.")
                    return

                # 선택된 행에서 파일 이름 가져오기
                selected_row = selected_items[0].row()
                file_name = self.file_table.item(selected_row, 0).text()

                # 사용자 확인
                reply = QMessageBox.question(
                    self, "문서 삭제",
                    f"문서 '{file_name}'을(를) 삭제하시겠습니까?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return

                # UI에서 행 삭제
                self.file_table.removeRow(selected_row)
            else:
                # 파일 이름이 직접 전달된 경우
                if not self.ui_control_manager.document_ui.remove_document_from_table(file_name):
                    logging.warning(f"File {file_name} not found in table.")


            # 데이터베이스에서 문서 삭제
            self.database_manager.delete_document(file_name)
            logging.info(f"Document deleted: {file_name}")
            QMessageBox.information(self, "삭제 완료", f"문서 '{file_name}'이(가) 삭제되었습니다.")
        except Exception as e:
            logging.error(f"Error deleting document: {e}")
            QMessageBox.critical(self, "삭제 오류", f"문서를 삭제하는 중 오류가 발생했습니다: {e}")

