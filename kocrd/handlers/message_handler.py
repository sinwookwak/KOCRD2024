# kocrd/handlers/message_handler.py
import json
import logging
from typing import Callable, Dict, Optional, Any

from kocrd.config.config import config  # config import
from kocrd.handlers.training_event_handler import TrainingEventHandler

class MessageHandler:
    def __init__(self, training_event_handler: TrainingEventHandler, error_handler: Callable[[Optional[Any], str, str, Exception, str], None]):
        self.training_event_handler = training_event_handler
        self.error_handler = error_handler
        self.message_handlers: Dict[str, Callable[[Dict[str, Any]], None]] = {
            config.get("messages.message_types.101"): self.handle_ocr_message,  # config.get() 사용
            config.get("messages.message_types.102"): self.handle_ocr_message,  # config.get() 사용
            # ... (다른 메시지 타입 처리 함수 추가)
        }

    def handle_message(self, ch, method, properties, body):
        try:
            message = json.loads(body)
            self.process_message(message)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except json.JSONDecodeError as e:
            self.error_handler(None, "json_parse_error", "512", e, f"JSON 파싱 오류: {body}")  # 메시지 본문 포함
            ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
        except Exception as e:
            self.error_handler(None, "message_process_error", "513", e, f"메시지 처리 중 오류: {e}")  # 예외 정보 포함
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    def process_message(self, message):
        message_type = message.get("type")
        handler = self.message_handlers.get(message_type)
        if handler:
            handler(message.get("data", {}))  # data가 없을 경우 빈 딕셔너리 전달
        else:
            logging.warning(f"알 수 없는 메시지 타입: {message_type}, 메시지: {message}")  # 메시지 정보 로깅

    def handle_ocr_message(self, data):
        """OCR 메시지 처리."""
        try:
            file_path = data.get("file_path")
            if not file_path:
                raise ValueError("file_path가 메시지 데이터에 없습니다. 데이터: {}".format(data))  # 데이터 내용 포함
            self.training_event_handler.handle_ocr_request(file_path)
            logging.info(f"OCR 요청: {file_path}")
        except ValueError as e:
            self.error_handler(None, "ocr_file_path_error", "514", e, str(e))
        except Exception as e:
            self.error_handler(None, "ocr_processing_error", "515", e, f"OCR 처리 중 오류: {e}, 데이터: {data}")  # 데이터 내용 포함

