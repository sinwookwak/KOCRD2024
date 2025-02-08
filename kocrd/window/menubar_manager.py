# file_name: MenubarManager.py
import os
import json
import logging
from PyQt5.QtWidgets import QMenuBar, QAction, QMessageBox, QFileDialog, QApplication, QDialog

from kocrd.config.config import load_config, get_message
from kocrd.Settings.settings_manager import SettingsManager

class MenubarManager:
    """메뉴바 이벤트 및 UI 관리 클래스."""
    def __init__(self, system_manager):
        self.system_manager = system_manager
        self.menu_bar = QMenuBar(system_manager.parent)
        self.main_window = system_manager.parent
        self.config_path = "config/ui.json"  # ui.json 파일 경로 변경
        logging.info("MenubarManager initialized with main_window.")

        self.config = load_config(self.config_path)  # 설정 로드
        self.messages_config = load_config("config/messages.json")  # messages.json 로드
        self.id_mapping = self.messages_config["id_mapping"]  # ID 매핑 로드
        self.setup_menus()

    def setup_menus(self):
        """메뉴 항목 설정."""
        for menu_config in self.config["components"]["menus"]:  # components.menus에서 메뉴 정보 가져옴
            menu = self.menu_bar.addMenu(menu_config["name"])
            for action_config in menu_config["actions"]:
                action = QAction(action_config["name"], self.main_window)
                action.triggered.connect(getattr(self, f"callback_{self.id_mapping[action_config['callback']]}"))
                menu.addAction(action)
        logging.info("MenubarManager initialized.")

    def callback_701(self):
        """열기 콜백."""
        print(get_message(self.messages_config, "701"))  # 열기
        self.system_manager.open_file_dialog()

    def callback_702(self):
        """저장 콜백."""
        print(get_message(self.messages_config, "702"))  # 저장
        self.system_manager.save_file()

    def callback_703(self):
        """종료 콜백."""
        print(get_message(self.messages_config, "703"))  # 종료
        self.main_window.close()

    def callback_704(self):
        """설정 열기 콜백."""
        self.open_settings_dialog()

    def callback_705(self):
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
        try:
            with open(config_path, "r", encoding="utf-8") as file:
                return json.load(file)
        except FileNotFoundError:
            logging.error(f"Config file not found: {config_path}")
            return {}  # 빈 설정 반환
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding config file: {e}")
            return {}  # 빈 설정 반환

    def load_id_mapping(self):
        """ID 매핑 파일을 로드합니다."""
        id_mapping_path = "config/messages.json"
        try:
            with open(id_mapping_path, "r", encoding="utf-8") as file:
                return json.load(file)["id_mapping"]
        except FileNotFoundError:
            logging.error(f"ID mapping file not found: {id_mapping_path}")
            return {}  # 빈 매핑 반환
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding ID mapping file: {e}")
            return {}  # 빈 매핑 반환

    def get_message(self, key):
        """메시지 키를 통해 메시지를 가져옵니다."""
        return get_message(self.messages_config, key)

    def get_ui(self):
        """MenuBar UI 반환."""
        return self.menu_bar