# kocrd/handlers/message_handler.py
import json
import logging

from kocrd.config.config import config
from kocrd.handlers.training_event_handler import TrainingEventHandler # TrainingEventHandler import

class MessageHandler:
    def __init__(self, training_event_handler: TrainingEventHandler, error_handler):  # TrainingEventHandler 타입 힌트 추가
        self.training_event_handler = training_event_handler
        self.error_handler = error_handler

    def handle_message(self, ch, method, properties, body):
        try:
            message = json.loads(body)
            self.process_message(message)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except json.JSONDecodeError as e:
            self.error_handler.handle_error(None, "json_parse_error", "512", e, "JSON 파싱 오류")
            ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
        except Exception as e:
            self.error_handler.handle_error(None, "message_process_error", "513", e, "메시지 처리 중 오류")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    def process_message(self, message):
        message_type = message.get("type")
        if message_type == config.messages["message_types"]["101"]:  # config.messages 사용
            self.handle_ocr_message(message["data"])
        elif message_type == config.messages["message_types"]["102"]:  # config.messages 사용
            self.handle_ocr_message(message["data"])
        # ... (다른 메시지 타입 처리)
        else:
            logging.warning(f"알 수 없는 메시지 타입: {message_type}")

    def handle_ocr_message(self, data):
        """OCR 메시지 처리."""
        try:
            file_path = data.get("file_path")  # 파일 경로 추출
            if file_path:
                self.training_event_handler.handle_ocr_request(file_path)  # TrainingEventHandler에 OCR 요청
                logging.info(f"OCR 요청: {file_path}")
            else:
                raise ValueError("file_path가 메시지 데이터에 없습니다.")
        except ValueError as e:
            self.error_handler.handle_error(None, "ocr_error", "514", e, str(e))
        except Exception as e:
            self.error_handler.handle_error(None, "ocr_error", "514", e, "OCR 처리 중 오류")

