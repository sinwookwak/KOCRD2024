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

class TempFileManager:
    """임시 파일 및 디렉토리를 관리하는 클래스."""

    def __init__(self, settings_manager, ocr_manager):
        self.settings_manager = settings_manager
        self.ocr_manager = ocr_manager
        self.temp_dir = self.settings_manager.get_setting_path("temp_dir")

        if not self.temp_dir:
            self.temp_dir = tempfile.mkdtemp()
            self.settings_manager.set_setting("temp_dir", self.temp_dir)
            logging.warning("temp_dir 설정이 없어 임시 디렉토리를 새로 생성했습니다.")

        os.makedirs(self.temp_dir, exist_ok=True)
        logging.info(f"TempFileManager initialized with temp_dir: {self.temp_dir}")

    def _handle_create_temp_files(self, ch, method, properties, message: Dict[str, Any]) -> None:
        """create_temp_files 메시지 처리."""
        file_path = message.get("file_path")
        try:
            result = self.create_temp_files(file_path)
            response_message = {"result": result, "status": "success"}  # 성공 상태 추가
        except Exception as e:
            logging.error(f"임시 파일 생성 중 오류: {e}")
            response_message = {"error": str(e), "status": "error"}  # 오류 정보 추가
        ch.basic_publish(exchange='', routing_key=properties.reply_to, body=json.dumps(response_message))

    def _handle_cleanup_temp_files(self, ch, method, properties, message: Dict[str, Any]) -> None:
        """cleanup_temp_files 메시지 처리."""
        file_paths = message.get("file_paths")
        self.cleanup_specific_files(file_paths) # 명확한 이름의 메서드 호출
    def handle_message(self, ch, method, properties, body):
        """RabbitMQ 메시지를 처리합니다."""
        try:
            message: Dict[str, Any] = json.loads(body.decode())
            message_type = message.get("type")
            handlers = {
                "create_temp_files": self._handle_create_temp_files,
                "cleanup_temp_files": self._handle_cleanup_temp_files,
            }
            handler = handlers.get(message_type)
            if handler:
                handler(ch, method, properties, message)
                ch.basic_ack(delivery_tag=method.delivery_tag)
                logging.info(f"Message handled: {message_type}")
            else:
                logging.warning(f"알 수 없는 메시지 타입: {message_type}")
                ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
        except json.JSONDecodeError as e:
            logging.error(f"메시지 파싱 오류: {e}. 메시지: {body.decode()}")
            ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
        except Exception as e:
            logging.error(f"메시지 처리 중 오류: {e}")
            ch.basic_reject(delivery_tag=method.delivery_tag, requeue=True)

    def create_temp_files(self, file_path: str) -> Optional[List[str]]:
        """PDF 페이지를 임시 이미지로 저장."""
        try:
            poppler_path = self.ocr_manager.find_poppler_path()
            if not poppler_path:
                raise FileNotFoundError("Poppler 경로를 찾을 수 없습니다.")

            pages = convert_from_path(file_path, poppler_path=poppler_path)
            temp_image_paths: List[str] = []
            for page in pages:
                # UUID를 사용하여 더욱 안전한 임시 파일 이름 생성
                temp_image_path = os.path.join(self.temp_dir, f"page_{uuid.uuid4()}.png")
                page.save(temp_image_path, "PNG")
                logging.info(f"Page saved as image: {temp_image_path}")
                temp_image_paths.append(temp_image_path)
            return temp_image_paths
        except Exception as e:
            logging.error(f"Error saving page as image: {e}")
            return None # 오류 발생 시 None 반환
    def cleanup_all_temp_files(self): # 이름 변경
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
            logging.info(f"Temporary directory cleaned.")

        except FileNotFoundError:
            logging.warning(f"Temporary directory not found: {self.temp_dir}")
        except Exception as e:
            logging.error(f"Error cleaning temporary directory: {e}")

    def cleanup_specific_files(self, files: Optional[List[str]]): # 이름 변경 및 타입 힌트 추가
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
            self.cleanup_all_temp_files() # 명확하게 이름이 변경된 메서드 호출

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
