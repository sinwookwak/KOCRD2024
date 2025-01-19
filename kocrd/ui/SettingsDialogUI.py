# SettingsDialogUI.py
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog, QMessageBox, QTabWidget, QWidget
)
import json
import os

class SettingsDialogUI(QDialog):
    """
    환경설정 대화창 UI 생성 클래스.
    설정 값을 표시하고, 변경 사항을 저장합니다.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("설정")
        self.resize(400, 300)
        self.tabs = QTabWidget(self)
        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)

        # 고급 설정 탭 추가
        self.add_advanced_settings_tab()

    def init_ui(self):
        """UI 초기화."""
        self.setWindowTitle("환경설정")
        self.setGeometry(300, 300, 400, 200)

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # 탭 추가
        self.add_general_settings_tab()
        self.add_advanced_settings_tab()

        # 저장 버튼
        save_button = QPushButton("저장", self)
        save_button.clicked.connect(self.save_settings)
        layout.addWidget(save_button)
    def apply_settings(self):
        # ... (다른 설정 적용)
        tesseract_path = self.ui.tesseractPathLineEdit.text()
        self.settings_manager.set_tesseract_path(tesseract_path)
        self.parent.system_manager.recreate_ocr_manager() # SystemManager에 알림

    def add_general_settings_tab(self):
        """일반 설정 탭 추가."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 임시 디렉토리 설정
        temp_dir_label = QLabel("임시 디렉토리 경로:")
        layout.addWidget(temp_dir_label)

        self.temp_dir_edit = QLineEdit(self)
        self.temp_dir_edit.setText(self.settings_manager.get_temp_dir())
        layout.addWidget(self.temp_dir_edit)

        self.tabs.addTab(tab, "일반 설정")
    def add_advanced_settings_tab(self):
        """고급 설정 탭 추가."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 딥러닝 모델 경로 설정
        ai_label = QLabel("딥러닝 모델 경로:")
        layout.addWidget(ai_label)

        self.ai_model_path_edit = QLineEdit(self)
        layout.addWidget(self.ai_model_path_edit)

        # 모델 경로 선택 버튼
        browse_button = QPushButton("경로 선택")
        browse_button.clicked.connect(self.select_model_path)  # 경로 선택 메서드 연결
        layout.addWidget(browse_button)

        # 저장 버튼
        save_button = QPushButton("저장하기")
        save_button.clicked.connect(self.save_model_path)  # 저장 메서드 연결
        layout.addWidget(save_button)

        self.tabs.addTab(tab, "고급 설정")
    def select_model_path(self):
        """모델 경로 선택."""
        model_path, _ = QFileDialog.getSaveFileName(
            self,
            "모델 저장 경로 선택",
            os.getenv("HOME", ""),  # 기본 디렉토리 (사용자 홈 디렉토리)
            "모델 파일 (*.traineddata);;모든 파일 (*)"
        )
        if model_path:
            self.ai_model_path_edit.setText(model_path)

    def save_model_path(self):
        """모델 경로를 저장."""
        model_path = self.ai_model_path_edit.text()
        if not model_path:
            QMessageBox.warning(self, "경로 없음", "모델 경로를 입력하거나 선택해 주세요.")
            return

        # 경로 유효성 검사
        if not os.path.isdir(os.path.dirname(model_path)):
            QMessageBox.critical(self, "잘못된 경로", "유효한 경로를 입력하세요.")
            return

        # settings_manager를 통해 저장 (가정)
        if self.settings_manager:
            self.settings_manager.set_ai_model_path(model_path)  # settings_manager에 경로 저장
        QMessageBox.information(self, "저장 완료", f"모델 경로가 저장되었습니다:\n{model_path}")

    def save_settings(self):
        """설정을 저장."""
        temp_dir = self.temp_dir_edit.text().strip()
        if temp_dir:
            self.settings_manager.set_temp_dir(temp_dir)
        QMessageBox.information(self, "저장 완료", "설정이 저장되었습니다.")
        self.accept()