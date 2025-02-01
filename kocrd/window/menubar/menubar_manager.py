# file_name: MenubarManager.py
import os
import json
import logging
from PyQt5.QtWidgets import QMenuBar, QAction, QMessageBox, QApplication, QDialog
from kocrd.Settings.SettingsDialogUI.SettingsDialogUI import SettingsDialogUI
from kocrd.window.menubar.menubar_ui import MenubarUI

class MenubarManager:
    """메뉴바 이벤트 및 UI 관리 클래스."""
    def __init__(self, system_manager):
        self.system_manager = system_manager
        self.menu_bar = QMenuBar(system_manager.parent)
        self.main_window = system_manager.parent
        logging.info("MenubarManager initialized with main_window.")

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

    def open_settings_dialog(self):
        """환경 설정 대화창을 엽니다."""
        dialog = self.system_manager.settings_manager.get_settings_ui(self.system_manager.parent)
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