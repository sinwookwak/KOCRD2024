import shutil
import logging
import os
from PyQt5.QtWidgets import QMessageBox, QInputDialog
from kocrd.config import development  # Update the import path

class User:
    """
    Manages user information and permissions.
    """

    def __init__(self, user_id, role):  # user_id added
        self.user_id = user_id
        self.role = role

    allowed_roles = {
        "action_name": ["admin", "editor"],
    }

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
        versioned_file_name = f"{file_path}_u{self.user_id}_v{self.get_next_version(file_path)}" # user_id added
        shutil.copy(file_path, versioned_file_name)
        logging.info(f"Version saved: {versioned_file_name}")

    def get_next_version(self, file_name):
        """
        Gets the next version number for the document.
        """
        version = 1
        while os.path.exists(f"{file_name}_u{self.user_id}_v{version}"): # user_id added
            version += 1
        return version

    def request_user_feedback(self, file_path, database_manager):
        """
        Requests feedback from the user on the document type and incorporates it into the learning process.
        """
        valid_doc_types = database_manager.get_valid_doc_types()
        doc_type, ok = QInputDialog.getItem(
            None, 'Document Type Confirmation', f'Please select the type of document for "{file_path}":', valid_doc_types, 0, False
        )
        if ok and doc_type:
            database_manager.save_document_type_feedback(file_path, doc_type)
            return doc_type
        raise ValueError("No valid document type selected.") # Exception handling

    def load_user_settings(self, settings_manager):
        """
        사용자 설정을 불러옵니다.
        """
        self.settings = settings_manager.get_user_settings(self.user_id)
        logging.info(f"User settings loaded for user_id {self.user_id}: {self.settings}")