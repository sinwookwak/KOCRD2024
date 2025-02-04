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
        self.config_path = "config/window_config.json"
        logging.info("MenubarManager initialized with main_window.")

        self.config = self.load_config()
        self.messages = self.config.get("messages", {})
        self.log_messages = self.config.get("log_messages", {})
        self.error_messages = self.config.get("error_messages", {})

        self.setup_menus()

    def setup_menus(self):
        """메뉴 항목 설정."""
        for menu_config in self.config["menus"]:
            menu = self.menu_bar.addMenu(menu_config["name"])
            for action_config in menu_config["actions"]:
                action = QAction(action_config["name"], self.main_window)
                action.triggered.connect(getattr(self, f"callback_{action_config['callback']}"))
                menu.addAction(action)
        logging.info("MenubarManager initialized.")

    def callback_04(self):
        """열기 콜백."""
        self.system_manager.open_file_dialog()

    def callback_05(self):
        """저장 콜백."""
        self.system_manager.save_file()

    def callback_06(self):
        """종료 콜백."""
        self.main_window.close()

    def callback_07(self):
        """설정 열기 콜백."""
        self.open_settings_dialog()

    def callback_08(self):
        """정보 콜백."""
        self.show_about_dialog()

    def open_deep_learning_dialog(self):
        """딥러닝 학습 경로를 선택하도록 대화창을 엽니다."""
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self.main_window,
            self.get_message("12"),
            "",
            "Model Parameters (*.traineddata);;All Files (*)",
            options=options
        )
        if file_path:
            QMessageBox.information(
                self.main_window,
                self.get_message("12"),
                self.get_message("14").format(file_path=file_path)
            )
            self.system_manager.ai_manager.train_with_parameters(file_path)  # 학습 시작
        else:
            QMessageBox.warning(
                self.main_window,
                self.get_message("12"),
                self.get_message("15")
            )

    def open_settings_dialog(self):
        """환경설정 대화창 열기."""
        dialog = SettingsDialogUI(self.system_manager.settings_manager, self.main_window)
        dialog.exec_()

    def load_config(self):
        """설정 파일을 로드하거나 기본 설정을 생성합니다."""
        config_path = self.config_path
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

    def get_message(self, key):
        """메시지 키를 통해 메시지를 가져옵니다."""
        return self.messages.get(key, "메시지를 찾을 수 없습니다.")

    def get_ui(self):
        """MenuBar UI 반환."""
        return self.menu_bar