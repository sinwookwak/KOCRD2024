# Document_temp.py: 문서 임시 파일 관리를 위한 클래스입니다.
import os
import tempfile
import logging
import shutil
import uuid
from datetime import datetime, timedelta
from typing import List, Optional
from kocrd.config.development import settings
import json

config_path = os.path.join(os.path.dirname(__file__), '..', 'managers_config.json')
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

class DocumentTempManager:
    def __init__(self):
        self.temp_files = []
        self.temp_dir = tempfile.mkdtemp()
        self.backup_dir = os.path.join(self.temp_dir, "backup")
        os.makedirs(self.backup_dir, exist_ok=True)
        logging.info(f"DocumentTempManager initialized with temp_dir: {self.temp_dir}")

    def create_temp_file(self, content, suffix=".tmp"):
        """임시 파일을 생성하고 내용을 작성합니다."""
        try:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            temp_file.write(content.encode('utf-8'))
            temp_file.close()
            self.temp_files.append(temp_file.name)
            logging.info(f"Temporary file created: {temp_file.name}")
            return temp_file.name
        except Exception as e:
            logging.error(config["messages"]["error"]["507"].format(e=e))
            return None

    def read_temp_file(self, file_path):
        """임시 파일의 내용을 읽어 반환합니다."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            logging.info(f"Temporary file read: {file_path}")
            return content
        except Exception as e:
            logging.error(config["messages"]["error"]["507"].format(e=e))
            return None

    def delete_temp_file(self, file_path):
        """임시 파일을 삭제합니다."""
        try:
            os.remove(file_path)
            self.temp_files.remove(file_path)
            logging.info(f"Temporary file deleted: {file_path}")
        except Exception as e:
            logging.error(config["messages"]["error"]["507"].format(e=e))

    def cleanup(self):
        """모든 임시 파일을 삭제합니다."""
        for file_path in self.temp_files:
            self.delete_temp_file(file_path)
        self.temp_files = []
        logging.info("All temporary files cleaned up.")

    def backup_temp_files(self):
        """임시파일을 백업합니다."""
        try:
            for filename in os.listdir(self.temp_dir):
                file_path = os.path.join(self.temp_dir, filename)
                if os.path.isfile(file_path):
                    shutil.copy(file_path, self.backup_dir)
            logging.info("Temporary files backed up.")
        except Exception as e:
            logging.error(config["messages"]["error"]["507"].format(e=e))

    def restore_temp_files(self):
        """백업된 임시파일을 복원합니다."""
        try:
            for filename in os.listdir(self.backup_dir):
                file_path = os.path.join(self.backup_dir, filename)
                if os.path.isfile(file_path):
                    shutil.copy(file_path, self.temp_dir)
            logging.info("Temporary files restored.")
        except Exception as e:
            logging.error(config["messages"]["error"]["507"].format(e=e))

    def cleanup_all_temp_files(self, retention_time: int = 3600):
        """임시 디렉토리의 모든 파일 정리 (보관 기간 적용)."""
        cutoff_time = datetime.now() - timedelta(seconds=retention_time)

        try:
            for filename in os.listdir(self.temp_dir):
                file_path = os.path.join(self.temp_dir, filename)
                if os.path.isfile(file_path):
                    file_creation_time = datetime.fromtimestamp(os.path.getctime(file_path))
                    if file_creation_time < cutoff_time:
                        os.remove(file_path)
                        logging.info(f"Expired temporary file removed: {file_path}")
            logging.info(f"Temporary directory cleaned.")
        except FileNotFoundError:
            logging.warning(config["messages"]["warning"]["401"].format(temp_dir=self.temp_dir))
        except Exception as e:
            logging.error(config["messages"]["error"]["507"].format(e=e))

    def cleanup_specific_files(self, files: Optional[List[str]]):
        """특정 파일들을 정리합니다."""
        if files:
            for file_path in files:
                try:
                    os.remove(file_path)
                    logging.info(f"File removed: {file_path}")
                except FileNotFoundError:
                    logging.warning(config["messages"]["warning"]["401"].format(file_path=file_path))
                except Exception as e:
                    logging.error(config["messages"]["error"]["507"].format(e=e))
        else:
            self.cleanup_all_temp_files()
