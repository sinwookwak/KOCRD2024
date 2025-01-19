# file_name: User
import shutil
import logging
import os
from PyQt5.QtWidgets import QMessageBox, QInputDialog

class User:
    """사용자 정보와 권한 관리를 담당하는 클래스."""

    def __init__(self, user_id, role):  # user_id 추가
        self.user_id = user_id
        self.role = role

    allowed_roles = {
        "action_name": ["admin", "editor"],
    }

    def check_permission(self, action):
        """사용자의 권한을 확인."""
        if self.role not in self.allowed_roles.get(action, []):
            QMessageBox.warning(None, "권한 부족", "이 작업을 수행할 권한이 없습니다.")
            return False
        return True

    def save_version(self, file_path):
        """문서의 새로운 버전을 저장합니다."""
        versioned_file_name = f"{file_path}_u{self.user_id}_v{self.get_next_version(file_path)}" # user_id 추가
        shutil.copy(file_path, versioned_file_name)
        logging.info(f"Version saved: {versioned_file_name}")

    def get_next_version(self, file_name):
        """다음 버전 번호를 가져옵니다."""
        version = 1
        while os.path.exists(f"{file_name}_u{self.user_id}_v{version}"): # user_id 추가
            version += 1
        return version

    def request_user_feedback(self, file_path, database_manager):
        """사용자에게 문서 유형에 대한 피드백을 요청하고 학습에 반영합니다."""
        valid_doc_types = database_manager.get_valid_doc_types()
        doc_type, ok = QInputDialog.getItem(
            None, '문서 유형 확인', f'문서 "{file_path}"의 유형을 선택해주세요:', valid_doc_types, 0, False
        )
        if ok and doc_type:
            database_manager.save_document_type_feedback(file_path, doc_type)
            return doc_type
        raise ValueError("유효한 문서 유형이 선택되지 않았습니다.") # 예외 발생