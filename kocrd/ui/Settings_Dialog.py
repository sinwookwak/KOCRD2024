# Settings_Dialog

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
import os

class SettingsDialog(QDialog):
    """환경설정 창."""
    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager  # 설정 관리 객체
        self.setWindowTitle("환경설정")
        self.setGeometry(300, 300, 400, 200)
        self.init_ui()

    def init_ui(self):
        """UI 요소 초기화."""
        layout = QVBoxLayout(self)

        # 임시 디렉토리 경로 설정
        temp_dir_label = QLabel("임시 디렉토리 경로:")
        layout.addWidget(temp_dir_label)

        self.temp_dir_edit = QLineEdit(self)
        self.temp_dir_edit.setText(self.settings_manager.get_temp_dir())
        layout.addWidget(self.temp_dir_edit)

        # 저장 버튼
        save_button = QPushButton("저장", self)
        save_button.clicked.connect(self.save_settings)
        layout.addWidget(save_button)

    def save_settings(self):
        """사용자가 입력한 설정값을 저장."""
        new_temp_dir = self.temp_dir_edit.text().strip()
        if os.path.isdir(new_temp_dir):
            self.settings_manager.set_temp_dir(new_temp_dir)
            QMessageBox.information(self, "저장 완료", "설정이 저장되었습니다.")
        else:
            QMessageBox.warning(self, "오류", "유효한 디렉토리 경로를 입력하세요.")

