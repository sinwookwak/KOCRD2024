# temp_file_manager.py
import tempfile
import os
import shutil
import logging
import json
import time
import uuid  # uuid 모듈 추가
from pdf2image import convert_from_path
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import threading
import pika
import sys
# config/development.py 임포트
try:
    from config import development  # Update the import path
except ImportError as e:
    logging.error(f"config.development 임포트 오류: {e}")
    sys.exit(1)

class TempFileManager:
    """임시 파일 및 디렉토리를 관리하는 클래스."""

    def __init__(self, settings_manager):
        self.settings_manager = settings_manager
        self.temp_dir = self.settings_manager.get_setting_path("temp_dir")

        if not self.temp_dir:
            self.temp_dir = tempfile.mkdtemp()
            self.settings_manager.set_setting("temp_dir", self.temp_dir)
            logging.warning("temp_dir 설정이 없어 임시 디렉토리를 새로 생성했습니다.")

        os.makedirs(self.temp_dir, exist_ok=True)
        logging.info(f"TempFileManager initialized with temp_dir: {self.temp_dir}")

        self.backup_interval = settings_manager.get_setting("TEMP_FILE_SAVE_INTERVAL", 600)
        self.backup_dir = os.path.join(self.temp_dir, "backup")
        os.makedirs(self.backup_dir, exist_ok=True)
        self.start_backup_timer()

    def start_backup_timer(self):
        """임시파일 백업 타이머 시작."""
        self.backup_timer = threading.Timer(self.backup_interval, self.backup_temp_files)
        self.backup_timer.start()

    def backup_temp_files(self):
        """임시파일을 백업합니다."""
        try:
            for filename in os.listdir(self.temp_dir):
                file_path = os.path.join(self.temp_dir, filename)
                if os.path.isfile(file_path):
                    shutil.copy(file_path, self.backup_dir)
            logging.info("Temporary files backed up.")
        except Exception as e:
            logging.error(f"Error backing up temporary files: {e}")
        finally:
            self.start_backup_timer()

    def restore_temp_files(self):
        """백업된 임시파일을 복원합니다."""
        try:
            for filename in os.listdir(self.backup_dir):
                file_path = os.path.join(self.backup_dir, filename)
                if os.path.isfile(file_path):
                    shutil.copy(file_path, self.temp_dir)
            logging.info("Temporary files restored.")
        except Exception as e:
            logging.error(f"Error restoring temporary files: {e}")

    def manage_temp_files(self):
        """임시파일을 관리합니다."""
        # 임시파일 관리 로직 추가
        pass

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

    def database_packaging(self):
        self.settings_manager.get_manager("system").database_packaging()
