# file_name: MenubarManager.py

import os
import json
import logging
from PyQt5.QtWidgets import QMenuBar, QAction, QMessageBox, QApplication, QDialog
from ui.SettingsDialogUI import SettingsDialogUI
from ui.menubar_ui import MenubarUI  # MenubarUI를 참조

class MenubarManager:
    """메뉴바 이벤트 및 UI 관리 클래스."""
    def __init__(self, system_manager):
        self.system_manager = system_manager
        self.menu_bar = QMenuBar(system_manager.parent)

        # MenubarUI를 통한 메뉴 생성 (menu_bar 전달)
        self.ui = MenubarUI(self.menu_bar)
        self.setup_menus()

    def setup_menus(self):
        """메뉴 항목 설정."""
        self.ui.init_file_menu(self.menu_bar, self.system_manager.parent, self.system_manager)
        self.ui.init_settings_menu(self.menu_bar, self.system_manager.parent, self.system_manager.settings_manager)
        logging.info("MenubarManager initialized.")

    def get_ui(self):
        """MenuBar UI 반환."""
        return self.menu_bar

    def setup_file_menu(self):
        """파일 메뉴를 설정."""
        file_menu = self.menu_bar.addMenu("파일")

        # 문서 가져오기
        import_action = QAction("문서 가져오기", self.menu_bar)
        import_action.triggered.connect(self.system_manager.document_manager.batch_import_documents)
        file_menu.addAction(import_action)

        # 문서 내보내기
        export_action = QAction("문서 내보내기 (Excel)", self.menu_bar)
        export_action.triggered.connect(self.system_manager.document_manager.save_to_excel)
        file_menu.addAction(export_action)

        # 종료
        exit_action = QAction("종료", self.menu_bar)
        exit_action.triggered.connect(QApplication.quit)
        file_menu.addAction(exit_action)

    def setup_settings_menu(self):
        """설정 메뉴를 설정."""
        settings_menu = self.menu_bar.addMenu("설정")

        # 환경설정
        settings_action = QAction("환경설정", self.menu_bar)
        settings_action.triggered.connect(self.open_settings_dialog)
        settings_menu.addAction(settings_action)

        # 딥러닝 학습 시작
        deep_learning_action = QAction("딥러닝 학습 시작", self.menu_bar)
        deep_learning_action.triggered.connect(self.start_deep_learning)
        settings_menu.addAction(deep_learning_action)

    def open_settings_dialog(self, settings_manager, parent):
            """환경 설정 대화창을 엽니다."""
            dialog = settings_manager.get_settings_ui(parent) # parent 전달
            if dialog.exec_() == QDialog.Accepted:
                logging.info("Settings dialog closed with changes.")
            else:
                logging.info("Settings dialog closed without changes.")

    def start_deep_learning(self):
        """딥러닝 학습 시작."""
        QMessageBox.information(None, "딥러닝 학습 시작", "딥러닝 학습이 시작되었습니다.")

    def load_config(self):
        """설정 파일을 로드하거나 기본 설정을 생성합니다."""
        config_path = "config.json"
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