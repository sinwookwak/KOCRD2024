# kocrd/handlers/message_handler.py
import json
import logging
from typing import Callable, Dict, Optional  # 타입 힌트 import

from kocrd.config.config import ConfigManager  # ConfigManager import
from kocrd.handlers.training_event_handler import TrainingEventHandler
from typing import Dict, Any

class MessageHandler:
    def __init__(self, config_manager: ConfigManager, training_event_handler: TrainingEventHandler, error_handler: Callable[[Optional[Any], str, str, Exception, str], None]):  # 타입 힌트 추가
        self.config_manager = config_manager
        self.training_event_handler = training_event_handler
        self.error_handler = error_handler
        self.message_handlers: Dict[str, Callable[[Dict[str, Any]], None]] = {  # 메시지 타입별 처리 함수 매핑
            self.config_manager.get("messages.message_types.101"): self.handle_ocr_message,
            self.config_manager.get("messages.message_types.102"): self.handle_ocr_message,
            # ... (다른 메시지 타입 처리 함수 추가)
        }
    def handle_message(self, ch, method, properties, body):
        try:
            message = json.loads(body)
            self.process_message(message)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except json.JSONDecodeError as e:
            self.error_handler(None, "json_parse_error", "512", e, "JSON 파싱 오류")  # ConfigManager 사용
            ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
        except Exception as e:
            self.error_handler(None, "message_process_error", "513", e, "메시지 처리 중 오류")  # ConfigManager 사용
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    def process_message(self, message):
        message_type = message.get("type")
        handler = self.message_handlers.get(message_type)
        if handler:
            handler(message["data"])
        else:
            logging.warning(f"알 수 없는 메시지 타입: {message_type}")

    def handle_ocr_message(self, data):
        """OCR 메시지 처리."""
        try:
            file_path = data.get("file_path")
            if not file_path:
                raise ValueError("file_path가 메시지 데이터에 없습니다.")  # 더 구체적인 에러 메시지
            self.training_event_handler.handle_ocr_request(file_path)
            logging.info(f"OCR 요청: {file_path}")
        except ValueError as e:
            self.error_handler(None, "ocr_file_path_error", "514", e, str(e))  # 더 구체적인 에러 코드
        except Exception as e:
            self.error_handler(None, "ocr_processing_error", "515", e, "OCR 처리 중 오류")  # 더 구체적인 에러 코드

