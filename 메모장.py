
class SystemManager:
    """
    시스템 작업을 관리하는 클래스.
    """
    def handle_error(self, error_message, error_code=None, critical=True):
        """
        에러 처리를 위한 메서드.
        
        Args:
            error_message (str): 에러 메시지.
            error_code (str, optional): 에러 코드를 지정하여 오류 유형 구분. Default는 None.
            critical (bool): True이면 critical 알림을 표시, False이면 warning 알림을 표시.
        """
        # 에러 코드 포함 메시지 생성
        full_message = f"[Error Code: {error_code}] {error_message}" if error_code else error_message

        # 로그 기록 (스택 트레이스 포함)
        logging.error(full_message)
        logging.debug("Stack trace:\n" + traceback.format_exc())

        # 사용자 알림 표시
        if critical:
            QMessageBox.critical(self, "오류 발생", full_message)
        else:
            QMessageBox.warning(self, "경고", full_message)

    def export_documents_to_excel(self):
        """문서 정보를 Excel 파일로 내보냅니다."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Excel 파일로 저장", "", "Excel Files (*.xlsx);;All Files (*)"
        )

        if not file_path:
            QMessageBox.warning(self, "저장 취소", "Excel 파일 저장이 취소되었습니다.")
            return

        # 확장자 누락 시 자동 추가
        if not file_path.lower().endswith('.xlsx'):
            file_path += '.xlsx'

        # 기존 파일 덮어쓰기 확인
        if os.path.exists(file_path):
            reply = QMessageBox.question(
                self, "덮어쓰기 확인",
                f"파일 '{file_path}'이(가) 이미 존재합니다. 덮어쓰시겠습니까?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                QMessageBox.information(self, "저장 취소", "Excel 파일 저장이 취소되었습니다.")
                return

        # 데이터 저장 처리
        try:
            self.save_to_excel(file_path)
            QMessageBox.information(self, "내보내기 완료", f"문서 정보가 저장되었습니다: {file_path}")
        except PermissionError as e:
            logging.error(f"Permission error when saving Excel file {file_path}: {e}")
            QMessageBox.critical(self, "저장 오류", f"Excel 파일 저장 중 권한 오류가 발생했습니다: {e}")
        except Exception as e:
            logging.error(f"Unexpected error when saving Excel file {file_path}: {e}")
            QMessageBox.critical(self, "저장 오류", f"예기치 않은 오류가 발생했습니다: {e}")


    def closeEvent(self, event):
        """프로그램 종료 시 호출되어 데이터베이스 백업 및 확인 작업을 수행합니다."""
        reply = QMessageBox.question(
            self, "프로그램 종료", "프로그램을 종료하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                # 데이터베이스 패키징 호출
                self.database_packaging()
                
                self.temp_file_manager.cleanup_temp_dir()  # 임시 파일 정리
                logging.info("Temporary files cleaned up successfully.")
                event.accept()
            except Exception as e:
                logging.error(f"Error during application close: {e}")
                QMessageBox.critical(self, "종료 오류", f"프로그램 종료 중 오류가 발생했습니다: {e}")
                event.ignore()
        else:
            event.ignore()
    def cleanup_temp_files(self):
        """임시 파일 정리."""
        self.temp_file_manager.cleanup_temp_dir()

    def get_column_index(self, column_name):
        """테이블 헤더 이름에 따라 컬럼 인덱스를 반환합니다."""
        headers = [
            '파일명', '유형', '텍스트', '날짜', '담당자',
            '공급자', '물품명', '카탈로그 번호', '결합 내용', '파일 경로'
        ]
        return headers.index(column_name) if column_name in headers else -1
