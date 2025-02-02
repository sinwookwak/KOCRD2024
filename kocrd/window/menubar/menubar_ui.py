# MenubarUI.py
from PyQt5.QtWidgets import QAction, QMessageBox, QFileDialog
import logging
import os
import sys
import json

class MenubarUI:
    """메뉴바 UI 생성 클래스."""
    def __init__(self, menu_bar):
        self.menu_bar = menu_bar
        self.config = self.load_config()
        self.messages = self.config.get("messages", {})
        self.error_messages = self.config.get("error_messages", {})

    def init_file_menu(self, menu_bar, parent, system_manager):
        """파일 메뉴를 초기화."""
        file_menu = menu_bar.addMenu("파일")

        # 문서 가져오기
        if system_manager.document_manager is not None:
            import_action = QAction("문서 가져오기", parent)
            import_action.triggered.connect(system_manager.document_manager.batch_import_documents)
            file_menu.addAction(import_action)
        else:
            logging.error("DocumentManager is not initialized. '문서 가져오기' 기능 비활성화.")

        # 문서 내보내기
        if system_manager.document_manager is not None:
            export_action = QAction("문서 내보내기 (Excel)", parent)
            export_action.triggered.connect(system_manager.document_manager.save_to_excel)
            file_menu.addAction(export_action)
        else:
            logging.error("DocumentManager is not initialized. '문서 내보내기' 기능 비활성화.")

        # 종료
        exit_action = QAction("종료", parent)
        exit_action.triggered.connect(parent.close)
        file_menu.addAction(exit_action)

        logging.info("File menu initialized.")

    def init_settings_menu(self, menu_bar, parent, settings_manager):
        """설정 메뉴"""
        settings_menu = menu_bar.addMenu("설정")

        # 환경설정
        settings_action = QAction("환경설정", parent)
        settings_action.triggered.connect(lambda: self.open_settings_dialog(settings_manager, parent))
        settings_menu.addAction(settings_action)

        # 딥러닝 학습 시작
        deep_learning_action = QAction("딥러닝 학습 시작", parent)
        deep_learning_action.triggered.connect(lambda: self.open_deep_learning_dialog(parent))
        settings_menu.addAction(deep_learning_action)

    def open_deep_learning_dialog(self, parent):
        """딥러닝 학습 경로를 선택하도록 대화창을 엽니다."""
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_path, _ = QFileDialog.getOpenFileName(
            parent,
            self.messages["start_deep_learning_title"]["ko"],
            "",
            "Model Parameters (*.traineddata);;All Files (*)",
            options=options
        )
        if file_path:
            QMessageBox.information(
                parent,
                self.messages["start_deep_learning_title"]["ko"],
                self.messages["training_started"]["ko"].format(file_path=file_path)
            )
            parent.system_manager.ai_manager.train_with_parameters(file_path)  # 학습 시작
        else:
            QMessageBox.warning(
                parent,
                self.messages["start_deep_learning_title"]["ko"],
                self.messages["training_cancelled"]["ko"]
            )

    def open_settings_dialog(self, settings_manager, parent):
        """환경설정 대화창 열기."""
        from kocrd.Settings.SettingsDialogUI.SettingsDialogUI import SettingsDialogUI
        dialog = SettingsDialogUI(settings_manager, parent)  # 수정된 초기화 방식 반영
        dialog.exec_()

    def load_config(self):
        """설정 파일을 로드하거나 기본 설정을 생성합니다."""
        config_path = "window_config.json"
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as file:
                return json.load(file)
        else:
            default_config = {
                "about_text": "Date Extractor AI\n© 2024"
            }
            with open(config_path, "w", encoding="utf-8") as file:
                json.dump(default_config, file, indent=4)
            return default_config

    def get_menubar_ui(self):
        """MenubarManager의 UI 반환."""
        return self.menu_bar  # 수정된 반환값