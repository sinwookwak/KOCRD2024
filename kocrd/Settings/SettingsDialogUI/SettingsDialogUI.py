# SettingsDialogUI.py
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog, QMessageBox, QTabWidget, QWidget, QHBoxLayout, QInputDialog, QFormLayout
)
import json
import os
import logging
import importlib  # 모듈 동적 로드를 위한 import
from .OCRUI import OCRUI  # OCRUI 모듈 불러오기

class SettingsDialogUI(QDialog):
    """
    환경설정 대화창 UI 생성 클래스.
    설정 값을 표시하고, 변경 사항을 저장합니다.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent  # 부모 클래스 참조 저장
        from Settings.settings_manager import SettingsManager  # settings_manager 모듈 불러오기
        self.settings_manager = SettingsManager()  # settings_manager 인스턴스 생성
        self.setWindowTitle("설정")
        self.resize(400, 300)
        self.tabs = QTabWidget(self)
        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)

        # 탭 추가
        self.load_tabs_from_config()

        # 저장 및 취소 버튼
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("저장", self)
        self.save_button.clicked.connect(self.save_settings)
        self.cancel_button = QPushButton("취소", self)
        self.cancel_button.clicked.connect(self.cancel_settings)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        self.cleanup_temp_files_button = QPushButton("임시 파일 정리", self)
        self.cleanup_temp_files_button.clicked.connect(self.cleanup_temp_files)
        button_layout.addWidget(self.cleanup_temp_files_button)
        layout.addLayout(button_layout)

        self.temp_settings = {}  # 임시 설정 저장소
        self.messages = self.settings_manager.config.get("messages", {})
        self.log_messages = self.settings_manager.config.get("log_messages", {})
        self.error_messages = self.settings_manager.config.get("error_messages", {})

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
        self.parent.system_manager.recreate_ocr_manager()  # SystemManager에 알림

    def load_tabs_from_config(self):
        """설정 파일에서 탭을 동적으로 로드합니다."""
        config = self.settings_manager.config.get("settings_tabs", [])
        for tab_config in config:
            module_name, class_name = tab_config["module"], tab_config["class"]
            module = importlib.import_module(module_name)
            tab_class = getattr(module, class_name)
            tab_instance = tab_class(self)
            self.tabs.addTab(tab_instance, tab_config["name"])

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

        # 사용자 설정 불러오기
        load_user_settings_button = QPushButton("사용자 설정 불러오기", self)
        load_user_settings_button.clicked.connect(self.load_user_settings)
        layout.addWidget(load_user_settings_button)

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

        # 임시파일 저장 작업 시간 설정
        temp_file_save_interval_label = QLabel("임시파일 저장 작업 시간 (초):")
        layout.addWidget(temp_file_save_interval_label)

        self.temp_file_save_interval_edit = QLineEdit(self)
        self.temp_file_save_interval_edit.setText(str(self.settings_manager.get_setting("TEMP_FILE_SAVE_INTERVAL", 600)))
        layout.addWidget(self.temp_file_save_interval_edit)

        # 저장 버튼
        save_button = QPushButton("저장하기")
        save_button.clicked.connect(self.save_model_path)  # 저장 메서드 연결
        layout.addWidget(save_button)

        self.tabs.addTab(tab, "고급 설정")

    def add_ai_management_tab(self):
        """AI 관리 탭 추가."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        ai_label = QLabel("딥러닝 모델 경로:")
        layout.addWidget(ai_label)

        self.ai_model_path_edit = QLineEdit(self)
        layout.addWidget(self.ai_model_path_edit)

        browse_button = QPushButton("경로 선택")
        browse_button.clicked.connect(self.select_model_path)
        layout.addWidget(browse_button)

        # AI 버전 관리 추가
        version_label = QLabel("AI 버전 관리:")
        layout.addWidget(version_label)

        self.version_edit = QLineEdit(self)
        layout.addWidget(self.version_edit)

        save_version_button = QPushButton("버전 저장")
        save_version_button.clicked.connect(self.save_ai_version)
        layout.addWidget(save_version_button)

        self.tabs.addTab(tab, "AI 관리")

    def add_ocr_settings_tab(self):
        """OCR 설정 탭을 추가합니다."""
        ocr_tab = self.ocr_ui.create_ocr_settings_tab(self)
        self.tabs.addTab(ocr_tab, "OCR Settings")

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
            self.temp_settings["ai_model_path"] = model_path

    def save_model_path(self):
        """모델 경로를 저장."""
        model_path = self.ai_model_path_edit.text()
        if not model_path:
            QMessageBox.warning(self, self.messages.get("12", "경로 없음"), self.messages.get("13", "모델 경로를 입력하거나 선택해 주세요."))
            return

        # 경로 유효성 검사
        if not os.path.isdir(os.path.dirname(model_path)):
            QMessageBox.critical(self, self.messages.get("invalid_path_title", "잘못된 경로"), self.messages.get("invalid_path_text", "유효한 경로를 입력하세요."))
            return

        # settings_manager를 통해 저장 (가정)
        if self.settings_manager:
            self.settings_manager.set_ai_model_path(model_path)  # settings_manager에 경로 저장
            self.parent.system_manager.update_ai_model_path(model_path)  # 부모 클래스에 알림
        QMessageBox.information(self, self.messages.get("14", "저장 완료"), self.messages.get("15", f"모델 경로가 저장되었습니다:\n{model_path}"))

    def save_ai_version(self):
        """AI 버전을 저장합니다."""
        version = self.version_edit.text()
        if version:
            self.settings_manager.set_setting("ai_version", version)
            QMessageBox.information(self, self.messages.get("14", "저장 완료"), self.messages.get("15", f"AI 버전이 저장되었습니다: {version}"))
        else:
            QMessageBox.warning(self, self.messages.get("16", "경고"), self.messages.get("17", "버전을 입력하세요."))

    def perform_ocr_task(self):
        """OCR 작업을 수행합니다."""
        self.parent.system_manager.perform_ocr_task()
        QMessageBox.information(self, self.messages.get("26", "작업 완료"), self.messages.get("27", "OCR 작업이 수행되었습니다."))

    def save_settings(self):
        """설정을 저장."""
        # 임시 설정을 실제 설정에 반영
        for key, value in self.temp_settings.items():
            self.settings_manager.set_setting(key, value)
        self.settings_manager.set_temp_dir(self.temp_dir_edit.text())
        QMessageBox.information(self, self.messages.get("14", "저장 완료"), self.messages.get("15", "설정이 저장되었습니다."))
        self.accept()

    def cancel_settings(self):
        """설정을 취소하고 임시 파일 삭제."""
        self.temp_settings.clear()
        QMessageBox.information(self, self.messages.get("28", "취소"), self.messages.get("29", "변경 사항이 취소되었습니다."))
        self.reject()

    def closeEvent(self, event):
        """환경설정 창을 닫을 때 임시 파일 삭제."""
        self.temp_settings.clear()
        event.accept()

    def load_user_settings(self):
        """사용자 설정을 불러옵니다."""
        user_id, ok = QInputDialog.getText(self, self.messages.get("18", "사용자 설정 불러오기"), self.messages.get("19", "사용자 ID를 입력하세요:"))
        if ok and user_id:
            self.parent.user.load_user_settings(self.settings_manager)
            QMessageBox.information(self, self.messages.get("20", "성공"), self.messages.get("21", "사용자 설정이 불러와졌습니다."))
        else:
            QMessageBox.warning(self, self.messages.get("22", "실패"), self.messages.get("23", "사용자 ID를 입력하세요."))

    def cleanup_temp_files(self):
        """임시 파일을 정리합니다."""
        self.settings_manager.cleanup_all_temp_files()
        QMessageBox.information(self, self.messages.get("24", "정리 완료"), self.messages.get("25", "임시 파일이 정리되었습니다."))