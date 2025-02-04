# file_name: MenubarManager.py
import os
import json
import logging
from PyQt5.QtWidgets import QMenuBar, QAction, QMessageBox, QFileDialog, QApplication, QDialog
from kocrd.Settings.SettingsDialogUI.SettingsDialogUI import SettingsDialogUI

class MenubarManager:
    """메뉴바 이벤트 및 UI 관리 클래스."""
    def __init__(self, system_manager):
        self.system_manager = system_manager
        self.menu_bar = QMenuBar(system_manager.parent)
        self.main_window = system_manager.parent
        self.config_path = "config.json"
        logging.info("MenubarManager initialized with main_window.")

        self.config = self.load_config()
        self.messages = self.config.get("messages", {})
        self.log_messages = self.config.get("log_messages", {})
        self.error_messages = self.config.get("error_messages", {})

        self.setup_menus()

    def setup_menus(self):
        """메뉴 항목 설정."""
        self.init_file_menu()
        self.init_settings_menu()
        logging.info("MenubarManager initialized.")

    def init_file_menu(self):
        """파일 메뉴를 초기화."""
        file_menu = self.menu_bar.addMenu("파일")

        # 문서 가져오기
        if self.system_manager.document_manager is not None:
            import_action = QAction("문서 가져오기", self.main_window)
            import_action.triggered.connect(self.system_manager.document_manager.batch_import_documents)
            file_menu.addAction(import_action)
        else:
            logging.error("DocumentManager is not initialized. '문서 가져오기' 기능 비활성화.")

        # 문서 내보내기
        if self.system_manager.document_manager is not None:
            export_action = QAction("문서 내보내기 (Excel)", self.main_window)
            export_action.triggered.connect(self.system_manager.document_manager.save_to_excel)
            file_menu.addAction(export_action)
        else:
            logging.error("DocumentManager is not initialized. '문서 내보내기' 기능 비활성화.")

        # 종료
        exit_action = QAction("종료", self.main_window)
        exit_action.triggered.connect(self.main_window.close)
        file_menu.addAction(exit_action)

        logging.info("File menu initialized.")

    def init_settings_menu(self):
        """설정 메뉴"""
        settings_menu = self.menu_bar.addMenu("설정")

        # 환경설정
        settings_action = QAction("환경설정", self.main_window)
        settings_action.triggered.connect(self.open_settings_dialog)
        settings_menu.addAction(settings_action)

        # 딥러닝 학습 시작
        deep_learning_action = QAction("딥러닝 학습 시작", self.main_window)
        deep_learning_action.triggered.connect(self.open_deep_learning_dialog)
        settings_menu.addAction(deep_learning_action)

    def open_deep_learning_dialog(self):
        """딥러닝 학습 경로를 선택하도록 대화창을 엽니다."""
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self.main_window,
            self.messages["start_deep_learning_title"]["ko"],
            "",
            "Model Parameters (*.traineddata);;All Files (*)",
            options=options
        )
        if file_path:
            QMessageBox.information(
                self.main_window,
                self.messages["start_deep_learning_title"]["ko"],
                self.messages["training_started"]["ko"].format(file_path=file_path)
            )
            self.system_manager.ai_manager.train_with_parameters(file_path)  # 학습 시작
        else:
            QMessageBox.warning(
                self.main_window,
                self.messages["start_deep_learning_title"]["ko"],
                self.messages["training_cancelled"]["ko"]
            )

    def open_settings_dialog(self):
        """환경설정 대화창 열기."""
        dialog = SettingsDialogUI(self.system_manager.settings_manager, self.main_window)
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

    def get_ui(self):
        """MenuBar UI 반환."""
        return self.menu_bar