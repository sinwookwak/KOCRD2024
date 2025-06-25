import os
import json
import tempfile
import logging
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from PyQt5.QtWidgets import QDialog, QMessageBox, QFileDialog
from typing import Union, List, Tuple, Callable, Dict, Optional
from kocrd.config.config import ConfigLoader, text_manager # TextManager 및 ConfigLoader 사용

class SettingsManager:
    """설정 관리 클래스."""
    def __init__(self, config_file="config/development.json"):
        self.config_file = os.path.abspath(config_file)
        # self.config = load_config(self.config_file) # ConfigLoader 사용
        self.config = ConfigLoader.load_json_file(self.config_file)
        self.settings: Dict[str, Union[str, int, list, dict]] = {}
        self.load_config()
        self.load_from_env()
        self.text_manager = text_manager

    def load_config(self):
        """JSON 설정 파일을 로드합니다."""
        try:
            config = ConfigLoader.load_json_file(self.config_file)
            self.settings.update(config.get("rabbitmq", {})) # RabbitMQ 설정은 제거 예정
            self.settings.update(config.get("general", {})) # 일반 설정 로드
            self.settings.update(config.get("file_paths", {})) # 파일 경로 설정 로드
            self.settings.update(config.get("ocr_settings", {})) # OCR 설정 로드
            self.settings.update(config.get("file_handling_settings", {})) # 파일 처리 설정 로드
            # 기타 필요한 설정 섹션을 여기에 추가

            return config
        except Exception as e: # FileNotFoundError, json.JSONDecodeError 포함
            logging.error(self.text_manager.get_error_text("502", file=self.config_file, e=e)) # text_manager 사용
            sys.exit(1)

    def load_from_env(self):
        """환경 변수에서 설정을 로드합니다."""
        # 환경 변수 로딩 로직은 그대로 유지하되, RabbitMQ 관련 변수는 제거하거나 필요에 따라 수정
        env_vars: dict[str, Tuple[Callable, Union[str, int, list, dict]]] = {
            "MAX_FILE_SIZE": (int, 10 * 1024 * 1024),
            "DEFAULT_REPORT_FILENAME": (str, "report.txt"),
            "DEFAULT_EXCEL_FILENAME": (str, "documents.xlsx"),
            "VALID_FILE_EXTENSIONS": (json.loads, [".txt", ".pdf", ".png", ".jpg", ".xlsx", ".docx"]),
            "MODEL_PATH": (str, r"F:\AI-M1\model\Korean_CNN_model(97.8).h5"),
            "document_embedding_path": (str, r"F:\AI-M1\model\document_embedding.json"),
            "document_types_path": (str, r"F:\AI-M1\model\document_types.json"),
            "temp_dir": (str, tempfile.gettempdir()),
            "ai_version": (str, "1.0.0"),
        }
        for var_name, (cast_func, default_value) in env_vars.items():
            env_value = os.environ.get(var_name)
            try:
                self.settings[var_name] = cast_func(env_value) if env_value is not None else default_value
                logging.info(self.text_manager.get_log_text("354", message=f"Loaded {var_name} from {'environment' if env_value is not None else 'default'}: {self.settings[var_name]}")) # text_manager 사용
            except (ValueError, json.JSONDecodeError, TypeError) as e:
                logging.warning(self.text_manager.get_warning_text("401", var_name=var_name, e=e)) # text_manager 사용
                self.settings[var_name] = default_value

    def set_defaults(self):
        """기본 설정값을 설정합니다."""
        # RabbitMQ 관련 기본값 제거 또는 주석 처리
        self.settings = {
            "MAX_FILE_SIZE": 10 * 1024 * 1024,
            "DEFAULT_REPORT_FILENAME": "report.txt",
            "DEFAULT_EXCEL_FILENAME": "documents.xlsx",
            "VALID_FILE_EXTENSIONS": [".txt", ".pdf", ".png", ".jpg", ".xlsx", ".docx"],
            "MODEL_PATH": r"F:\AI-M1\model\Korean_CNN_model(97.8).h5",
            "document_embedding_path": r"F:\AI-M1\model\document_embedding.json",
            "document_types_path": r"F:\AI-M1\model\document_types.json",
            "temp_dir": tempfile.gettempdir(),
            "ai_version": "1.0.0",
        }

    def get_setting(self, setting_name: str, default: Union[str, int, list, dict, None] = None) -> Union[str, int, list, dict, None]:
        """설정 값을 반환합니다."""
        return self.settings.get(setting_name, default)

    def set_setting(self, setting_name: str, value: Union[str, int, list, dict]) -> None:
        """설정 값을 설정하고 저장합니다."""
        self.settings[setting_name] = value
        self.save_settings()

    def save_settings(self):
        """설정을 파일에 저장합니다."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=4)
            logging.info(self.text_manager.get_log_text("326")) # text_manager 사용
        except Exception as e:
            logging.error(self.text_manager.get_error_text("503", file=self.config_file, e=e)) # text_manager 사용

    def get_setting_path(self, setting_name: str) -> Union[str, None]:
        """경로 관련 설정을 반환합니다."""
        return self.get_setting(setting_name)

    def get_temp_dir(self) -> str:
        """임시 디렉토리 경로를 반환합니다."""
        return self.get_setting("temp_dir")

    def set_temp_dir(self, temp_dir: str) -> None:
        """임시 디렉토리 경로를 설정합니다."""
        self.set_setting("temp_dir", temp_dir)
        logging.info(self.text_manager.get_log_text("354", message=f"Temporary directory set to {temp_dir}")) # text_manager 사용

    def open_settings_dialog(self, parent=None):
        """설정 다이얼로그를 엽니다."""
        logging.info(self.text_manager.get_log_text("338")) # text_manager 사용
        # from Settings.SettingsDialogUI.SettingsDialogUI import SettingsDialogUI # 필요시 주석 해제
        # dialog = SettingsDialogUI(settings_manager=self, parent=parent) # 필요시 주석 해제
        # dialog.exec_() # 필요시 주석 해제
        QMessageBox.information(parent,
                                self.text_manager.get_ui_text("settings_dialog", "title"), # text_manager 사용
                                self.text_manager.get_log_text("338")) # text_manager 사용

    def set_file_path(self, parent, setting_name: str, file_filter: str = "All Files (*)",
                      engine_attr_name: str = None, init_func: Callable = None, open_file: bool = False):
        """파일 경로를 설정하고, 필요시 데이터베이스 엔진을 초기화합니다."""
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog

        file_dialog = QFileDialog.getOpenFileName if open_file else QFileDialog.getSaveFileName
        dialog_title = self.text_manager.get_ui_text("file_dialog", "select_file" if open_file else "select_path") # text_manager 사용
        file_path, _ = file_dialog(parent, dialog_title, "", file_filter, options=options)

        if file_path:
            old_path = self.get_setting(setting_name)
            self.set_setting(setting_name, file_path)
            logging.info(self.text_manager.get_log_text("354", message=f"{setting_name} path updated to: {file_path}")) # text_manager 사용

            if engine_attr_name and init_func:
                try:
                    # 데이터베이스 엔진 초기화 로직 (필요시 유지 또는 수정)
                    # init_func(getattr(self, engine_attr_name), file_path) # 예시
                    QMessageBox.information(parent, self.text_manager.get_general_text("success"), # text_manager 사용
                                            self.text_manager.get_general_text("path_set_success", path=file_path)) # text_manager 사용
                except Exception as e:
                    logging.error(self.text_manager.get_error_text("504", setting=setting_name, e=e)) # text_manager 사용
                    QMessageBox.critical(parent, self.text_manager.get_general_text("error"), # text_manager 사용
                                         self.text_manager.get_error_text("504", setting=setting_name, e=e)) # text_manager 사용
                    self.set_setting(setting_name, old_path)
                    logging.info(self.text_manager.get_log_text("354", message=f"{setting_name} path reverted to: {old_path}")) # text_manager 사용
        else:
            logging.info(self.text_manager.get_log_text("354", message=f"{setting_name} path selection cancelled.")) # text_manager 사용

    def get_user_settings(self, user_id):
        """사용자 설정을 반환합니다."""
        user_settings_file = os.path.join(os.path.dirname(self.config_file), f"user_{user_id}_settings.json") # config_file의 디렉토리 사용
        try:
            return ConfigLoader.load_json_file(user_settings_file)
        except Exception as e: # FileNotFoundError, json.JSONDecodeError 포함
            logging.error(self.text_manager.get_error_text("505", user_id=user_id, e=e)) # text_manager 사용
            return {}

    def cleanup_all_temp_files(self):
        """임시 디렉토리의 모든 파일 정리 (보관 기간 적용)."""
        self.temp_manager.cleanup_all_temp_files()

    def cleanup_specific_files(self, files: Optional[List[str]]):
        """특정 파일들을 정리합니다."""
        self.temp_manager.cleanup_specific_files(files)

    def get_temp_file_path(self, file_name: str) -> str:
        return self.temp_manager.get_temp_file_path(file_name)

    def list_temp_files(self) -> List[str]:
        return self.temp_manager.list_temp_files()

    def save_feedback(self, feedback_data):
        """피드백 데이터를 저장합니다."""
        # 임시 디렉토리 경로는 SettingsManager에서 가져옴
        temp_dir = self.get_temp_dir()
        feedback_file = os.path.join(temp_dir, "feedback.json")
        try:
            with open(feedback_file, "w", encoding='utf-8') as f: 
                json.dump(feedback_data, f, ensure_ascii=False, indent=4)
            logging.info(self.text_manager.get_log_text("334", data=feedback_data)) # text_manager 사용
        except Exception as e:
            logging.error(self.text_manager.get_error_text("506", e=e)) # text_manager 사용

    def get_message_exchange_settings(self) -> dict:
        """메시지 교환을 위한 설정값을 반환합니다."""
        return {
            "exchange_name": self.get_setting("exchange_name", "default_exchange"),
            "exchange_type": self.get_setting("exchange_type", "direct"),
            "routing_key": self.get_setting("routing_key", "default_key")
        }
