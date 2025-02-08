import os
import tempfile
import logging
from typing import List, Optional
from datetime import datetime, timedelta

class SettingsTempManager:
    """SettingsManager에서 발생하는 임시 파일을 관리하는 클래스."""

    def __init__(self, settings_manager):
        self.settings_manager = settings_manager
        self.temp_dir = self.settings_manager.get_setting("temp_dir", tempfile.gettempdir())
        os.makedirs(self.temp_dir, exist_ok=True)
        logging.info(f"SettingsTempManager initialized with temp_dir: {self.temp_dir}")

    def cleanup_all_temp_files(self):
        """임시 디렉토리의 모든 파일 정리 (보관 기간 적용)."""
        retention_time = self.settings_manager.get_setting("TEMP_FILE_RETENTION_TIME", 3600)  # 기본값 1시간 (초 단위)
        cutoff_time = datetime.now() - timedelta(seconds=retention_time)

        try:
            for filename in os.listdir(self.temp_dir):
                file_path = os.path.join(self.temp_dir, filename)
                if os.path.isfile(file_path):
                    file_creation_time = datetime.fromtimestamp(os.path.getctime(file_path))
                    if file_creation_time < cutoff_time:
                        os.remove(file_path)
                        logging.info(f"Expired temporary file removed: {file_path}")
            logging.info(self.settings_manager.config["messages"].get("224", "Temporary directory cleaned."))
        except FileNotFoundError:
            logging.warning(self.settings_manager.config["error"].get("502", f"Temporary directory not found: {self.temp_dir}"))
        except Exception as e:
            logging.error(self.settings_manager.config["error"].get("503", f"Error cleaning temporary directory: {e}"))

    def cleanup_specific_files(self, files: Optional[List[str]]):
        """특정 파일들을 정리합니다."""
        if files:
            for file_path in files:
                try:
                    os.remove(file_path)
                    logging.info(f"File removed: {file_path}")
                except FileNotFoundError:
                    logging.warning(f"File not found: {file_path}")
                except Exception as e:
                    logging.error(f"Error removing file {file_path}: {e}")
        else:
            self.cleanup_all_temp_files()

    def get_temp_file_path(self, file_name: str) -> str:
        return os.path.join(self.temp_dir, file_name)

    def list_temp_files(self) -> List[str]:
        try:
            files = os.listdir(self.temp_dir)
            logging.info(f"Temporary files listed: {files}")
            return files
        except FileNotFoundError:
            logging.warning(f"Temporary directory not found: {self.temp_dir}")
            return []
        except Exception as e:
            logging.error(f"Error listing files in temporary directory: {e}")
            return []

    def list_feedback_files(self) -> List[str]:
        """피드백 파일 목록을 반환합니다."""
        feedback_files = []
        try:
            for filename in os.listdir(self.temp_dir):
                if filename.startswith("feedback_") and filename.endswith(".json"):
                    feedback_files.append(os.path.join(self.temp_dir, filename))
            logging.info(f"Feedback files listed: {feedback_files}")
        except FileNotFoundError:
            logging.warning(f"Temporary directory not found: {self.temp_dir}")
        except Exception as e:
            logging.error(f"Error listing feedback files in temporary directory: {e}")
        return feedback_files
