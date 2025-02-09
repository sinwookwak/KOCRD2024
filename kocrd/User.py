from kocrd.config.config import ConfigManager # ConfigManager import
from PyQt5.QtWidgets import QInputDialog, QMessageBox
import logging
import os
import shutil
from typing import Any

class User:
    """
    Manages user information and permissions.
    """

    def __init__(self, user_id, role, config_files=None):  # config_files 추가
        self.user_id = user_id
        self.role = role
        self.config_manager = ConfigManager(config_files or ["config/development.json"]) # ConfigManager 인스턴스 생성
        self.allowed_roles = self.config_manager.get("user.allowed_roles", {}) # config에서 allowed_roles 가져오기
        self.settings = {} # 인스턴스 속성으로 settings 선언

    def check_permission(self, action):
        """
        Checks the user's permission for a given action.
        """
        if self.role not in self.allowed_roles.get(action, []):
            QMessageBox.warning(None, "Permission Denied", "You do not have permission to perform this action.")
            return False
        return True

    def save_version(self, file_path):
        """
        Saves a new version of the document.
        """
        versioned_file_name = f"{file_path}_u{self.user_id}_v{self.get_next_version(file_path)}"
        shutil.copy(file_path, versioned_file_name)
        logging.info(f"Version saved: {versioned_file_name}")

    def get_next_version(self, file_name):
        """
        Gets the next version number for the document.
        """
        version = 1
        while os.path.exists(f"{file_name}_u{self.user_id}_v{version}"):
            version += 1
        return version

    def request_user_feedback(self, file_path, database_manager):
        """
        Requests feedback from the user on the document type.
        """
        try:
            valid_doc_types = database_manager.get_valid_doc_types()
            doc_type, ok = QInputDialog.getItem(
                None, 'Document Type Confirmation', f'Please select the type of document for "{file_path}":', valid_doc_types, 0, False
            )
            if ok and doc_type:
                try:
                    database_manager.save_document_type_feedback(file_path, doc_type)
                    return doc_type
                except (ValueError, TypeError) as e:  # 구체적인 예외 유형 처리
                    logging.error(f"Error saving document type feedback: {e}")
                    QMessageBox.critical(None, "Error", f"Failed to save feedback: {e}") # 사용자에게 에러 메시지 표시
                    return None
            else:  # 취소 버튼을 눌렀을 때
                return None
        except (ValueError, TypeError) as e:  # 구체적인 예외 유형 처리
            logging.error(f"Error requesting user feedback: {e}")
            QMessageBox.critical(None, "Error", f"Failed to request feedback: {e}") # 사용자에게 에러 메시지 표시
            return None

    def load_user_settings(self, settings_manager):
        """
        사용자 설정을 불러옵니다.
        """
        self.settings = settings_manager.get_user_settings(self.user_id)
        logging.info(f"User settings loaded for user_id {self.user_id}: {self.settings}")
class FeedbackEventHandler:
    def __init__(self, ai_data_manager, error_handler):
        self.ai_data_manager = ai_data_manager
        self.error_handler = error_handler

    def handle_save_feedback(self, file_path, doc_type):
        """피드백 저장 처리"""
        try:
            self._save_feedback(file_path, doc_type)
        except (ValueError, TypeError) as e:  # 구체적인 예외 유형 처리
            self.error_handler.handle_error(None, "feedback_error", "500", e, f"피드백 저장 중 오류 발생: {e}") # 더 자세한 에러 메시지

    def _request_user_feedback(self, file_path, database_manager):
        """실제 사용자 피드백 요청 로직"""
        valid_doc_types = database_manager.get_valid_doc_types()
        doc_type, ok = QInputDialog.getItem(
            None, 'Document Type Confirmation', f'Please select the type of document for "{file_path}":', valid_doc_types, 0, False
        )
        if ok and doc_type:
            return doc_type
        else:  # 취소 버튼을 눌렀을 때
            return None  # None 반환
        raise ValueError("No valid document type selected.") # 이 부분은 제거해도 괜찮습니다. None을 반환하므로.

    def _save_feedback(self, file_path, doc_type):
      """실제 피드백 저장 로직"""
      if self.ai_data_manager is None:
          raise ValueError("ai_data_manager must be initialized.") # 더 명확한 메시지
      self.ai_data_manager.save_feedback({"file_path": file_path, "doc_type": doc_type})
      logging.info(f"Feedback saved for {file_path}: {doc_type}")

    def request_feedback(self, original_message: Any, error_reason: str):
        """피드백 요청 (현재 사용되지 않는 것으로 보임)"""
        # 필요하다면 구현

