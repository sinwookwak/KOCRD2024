# temp_file_manager.py
import tempfile
import os
import shutil
import logging
import json
import time
import uuid
from pdf2image import convert_from_path
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import threading
import pika
import sys

from kocrd.config.config import ConfigManager # ConfigManager import
class TempFileManager:
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.temp_dir = self.config_manager.get("file_paths.temp_dir")  # 설정 파일에서 가져옴

        if not self.temp_dir:
            self.temp_dir = tempfile.mkdtemp()
            self.config_manager.set("file_paths.temp_dir", self.temp_dir)  # 설정 파일에 저장
            logging.warning("temp_dir 설정이 없어 임시 디렉토리를 새로 생성했습니다.")
            
        os.makedirs(self.temp_dir, exist_ok=True)
        logging.info(f"TempFileManager initialized with temp_dir: {self.temp_dir}")

        self.backup_interval = self.config_manager.get("TEMP_FILE_SAVE_INTERVAL", 600) # ConfigManager 사용
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
    def cleanup_all_temp_files(self):
        """임시 디렉토리의 모든 파일 정리 (보관 기간 적용)."""
        retention_time = self.config_manager.get("TEMP_FILE_RETENTION_TIME", 3600)  # ConfigManager 사용
        cutoff_time = datetime.now() - timedelta(seconds=retention_time)

        try:
            for filename in os.listdir(self.temp_dir):
                file_path = os.path.join(self.temp_dir, filename)
                if os.path.isfile(file_path):
                    file_creation_time = datetime.fromtimestamp(os.path.getctime(file_path))
                    if file_creation_time < cutoff_time:
                        os.remove(file_path)
                        logging.info(f"Expired temporary file removed: {file_path}")
        except FileNotFoundError:
            logging.warning(self.config_manager.get("error.502", f"Temporary directory not found: {self.temp_dir}")) # ConfigManager 사용
        except Exception as e:
            logging.error(self.config_manager.get("error.503", f"Error cleaning temporary directory: {e}")) # ConfigManager 사용

        logging.info(self.config_manager.get("messages.224", "Temporary directory cleaned.")) # ConfigManager 사용

    def cleanup_specific_files(self, files: Optional[List[str]]): # 통합된 cleanup_files
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
            self.cleanup_all_temp_files() # 필요에 따라 all or specific 선택

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
