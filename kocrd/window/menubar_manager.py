# file_name: MenubarManager.py
import os
import json
import logging
from PyQt5.QtWidgets import QMenuBar, QAction, QMessageBox, QFileDialog, QApplication, QDialog

from kocrd.config.config import text_manager, AppConfig

class MenubarManager:
    """메뉴바 이벤트 및 UI 관리 클래스."""
    def __init__(self, system_manager):
        self.system_manager = system_manager
        self.menu_bar = QMenuBar(system_manager.parent)
        self.main_window = system_manager.parent
        
        self.text_manager = text_manager
        self.ui_settings = AppConfig.UI_SETTINGS # AppConfig.UI_SETTINGS에 ui.json 내용이 로드됨
        
        logging.info("MenubarManager initialized with main_window.")
        self.setup_menus()

    def setup_menus(self):
        """메뉴 항목 설정."""
        ui_structure_menus = self.ui_settings.get("structure", {}).get("menus", [])
        ui_elements_texts = self.ui_settings.get("elements", {})

        for menu_config in ui_structure_menus:
            menu_display_key = menu_config.get("display_key")
            if not menu_display_key:
                logging.error(f"Menu config missing 'display_key': {menu_config}")
                continue
            
            menu_text = ui_elements_texts.get(menu_display_key, menu_display_key)
            menu = self.menu_bar.addMenu(menu_text)
            
            for action_config in menu_config.get("actions", []):
                action_display_key = action_config.get("display_key")
                if not action_display_key:
                    logging.error(f"Action config missing 'display_key': {action_config}")
                    continue

                action_text = ui_elements_texts.get(action_display_key, action_display_key)
                action = QAction(action_text, self.main_window)
                
                callback_id = action_config.get("callback_id")
                if not callback_id:
                    logging.error(f"Action config missing 'callback_id': {action_config}")
                    continue

                try:
                    method_to_call = getattr(self, f"callback_{callback_id}")
                    action.triggered.connect(method_to_call)
                except AttributeError:
                    logging.error(f"Callback method 'callback_{callback_id}' not found in MenubarManager for action '{action_display_key}'.")
                    continue 

                menu.addAction(action)
        logging.info("MenubarManager menus setup successfully.")

    def create_menubar(self):
        """MainWindow에서 호출하여 메뉴바 UI를 반환합니다."""
        return self.menu_bar

    # 각 콜백 메서드에서 text_manager.get_text에 숫자 ID 사용
    def callback_701(self):
        """열기 콜백."""
        logging.info(self.text_manager.get_text("log", "401")) # "File open action executed."
        self.system_manager.open_file_dialog()

    def callback_702(self):
        """저장 콜백."""
        logging.info(self.text_manager.get_text("log", "402")) # "File save action executed."
        self.system_manager.save_file()

    def callback_703(self):
        """종료 콜백."""
        logging.info(self.text_manager.get_text("log", "403")) # "Application exit action executed."
        self.main_window.close()

    def callback_704(self):
        """설정 열기 콜백."""
        logging.info(self.text_manager.get_text("log", "404")) # "Settings open action executed."
        if hasattr(self.system_manager, 'settings_manager'):
            # 실제 설정 다이얼로그 호출 로직 (주석 처리)
            # from kocrd.Settings.settings_manager import SettingsDialogUI
            # dialog = SettingsDialogUI(self.system_manager.settings_manager, self.main_window)
            # dialog.exec_()
            QMessageBox.information(self.main_window,
                                    self.text_manager.get_text("general", "504"), # "KOCRD2024"
                                    self.text_manager.get_text("log", "404")) # "Settings open action executed."
        else:
            logging.error(self.text_manager.get_text("general", "501")) # "Settings Manager not configured."
            QMessageBox.critical(self.main_window,
                                 self.text_manager.get_text("general", "503"), # "Error"
                                 self.text_manager.get_text("general", "501")) # "Settings Manager not configured."

    def callback_705(self):
        """정보 콜백."""
        logging.info(self.text_manager.get_text("log", "405")) # "About dialog action executed."
        self.show_about_dialog()

    def open_deep_learning_dialog(self):
        """딥러닝 학습 경로를 선택하도록 대화창을 엽니다."""
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog

        ui_elements_texts = self.ui_settings.get("elements", {})

        dialog_title = ui_elements_texts.get("dialog_select_model_file_title", "Select Model File")
        info_message_success = ui_elements_texts.get("message_model_file_selected", "Selected file: {file_path}")
        info_message_warning = ui_elements_texts.get("message_no_file_selected", "No file selected.")
        
        model_file_filter = self.text_manager.get_text("general", "508") # "Model Parameters (*.traineddata);;All Files (*)"

        file_path, _ = QFileDialog.getOpenFileName(
            self.main_window,
            dialog_title,
            "",
            model_file_filter,
            options=options
        )
        if file_path:
            logging.info(self.text_manager.get_text("log", "406").format(file_path=file_path)) # "AI model file selected: {file_path}"
            QMessageBox.information(
                self.main_window,
                dialog_title,
                info_message_success.format(file_path=file_path)
            )
            if hasattr(self.system_manager, 'ai_model_manager') and hasattr(self.system_manager.ai_model_manager, 'train_with_parameters'):
                 self.system_manager.ai_model_manager.train_with_parameters(file_path)
            else:
                 logging.error(self.text_manager.get_text("general", "502")) # "AI Manager not properly configured."
                 QMessageBox.critical(self.main_window, self.text_manager.get_text("general", "503"), # "Error"
                                      self.text_manager.get_text("general", "502")) # "AI Manager not properly configured."
        else:
            logging.info(self.text_manager.get_text("log", "407")) # "No AI model file selected."
            QMessageBox.warning(
                self.main_window,
                dialog_title,
                info_message_warning
            )

    def show_about_dialog(self):
        """정보 대화창을 표시합니다."""
        app_name = self.text_manager.get_text("general", "504") # "KOCRD"
        app_version = self.text_manager.get_text("general", "505") # "1.0"
        app_author = self.text_manager.get_text("general", "506") # "Unknown"
        about_text = f"{app_name}\n{app_version}\n{app_author}"

        QMessageBox.about(
            self.main_window,
            self.text_manager.get_text("general", "507"), # "About"
            about_text
        )

    def get_ui(self):
        """MenuBar UI 반환."""
        return self.menu_bar
