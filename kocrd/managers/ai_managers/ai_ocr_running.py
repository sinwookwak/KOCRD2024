# ai_ocr_running.py

import logging
import json
import pika
import time
import sys
from typing import Callable, Dict, Any
import pika.exceptions
class OCRResultHandler:
    """OCR 결과 메시지 처리 담당."""
    def __init__(self, system_manager, ai_model_manager):
        self.system_manager = system_manager
        self.settings_manager = self.system_manager.get_manager("settings_manager")
        self.ai_model_manager = ai_model_manager  # AI 모델 관리자 추가
        self.rabbitmq_manager = self.system_manager.rabbitmq_manager

    def create_ai_request(self, message_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """AI 요청 메시지 생성 (확장성 고려)."""
        return {
            "type": message_type,
            "data": data,
            "reply_to": self.settings_manager.get_queue_name("events")
        }

    def handle_message(self, ch, method, properties, body):
        """OCR 결과 메시지 처리 및 AI 요청 전송."""
        try:
            message = json.loads(body)
            message_type = message.get("type")
            if message_type == "OCR_COMPLETED":
                extracted_text = message.get("data", {}).get("extracted_text") # data 필드 추가
                file_path = message.get("data", {}).get("file_path")
                if extracted_text:
                    ai_request = self.create_ai_request("PREDICT_DOCUMENT_TYPE", {"text": extracted_text, "file_path": file_path})
                    queue_name = self.settings_manager.get_queue_name("prediction_requests")
                    self.system_manager.send_message(queue_name, ai_request)
                else:
                    logging.warning(f"No text extracted from file: {file_path}")
            # 다른 AI 작업 처리 (예시)
            elif message_type == "IMAGE_CLASSIFICATION_COMPLETED":
                image_path = message.get("data", {}).get("image_path")
                # 이미지 분류 결과 처리 및 추가 작업 수행
                try:
                    classification_result = self.ai_model_manager.predict(image_path)
                    ai_request = self.create_ai_request("HANDLE_IMAGE_CLASSIFICATION_RESULT", {"result": classification_result, "image_path": image_path})
                    queue_name = self.settings_manager.get_queue_name("ai_result_handling")
                    self.system_manager.send_message(queue_name, ai_request)
                except Exception as e:
                     logging.exception(f"이미지 분류 후처리 오류: {e}")
            else:
                logging.warning(f"Unknown message type: {message_type}")

        except json.JSONDecodeError as e:
            logging.exception(f"OCR 결과 JSON 디코딩 오류: {e}, body: {body}")
        except Exception as e:
            logging.exception(f"OCR 결과 처리 중 오류: {e}")

class MessageConsumer:
    """메시지 큐 소비 담당."""
    def __init__(self, rabbitmq_manager):
        self.rabbitmq_manager = rabbitmq_manager

    def consume_messages(self, queue_name: str, callback: Callable):
        """메시지 소비."""
        try:
            self.rabbitmq_manager.start_consuming_specific_queue(queue_name, callback)
            self.rabbitmq_manager.channel.start_consuming()
        except pika.exceptions.AMQPConnectionError as e:
            logging.error(f"RabbitMQ 연결 오류: {e}")
            print(f"RabbitMQ 연결에 실패했습니다. 5초 후 재시도합니다: {e}")
            time.sleep(5)
            self.consume_messages(queue_name, callback) # 재귀 호출을 통한 재시도
        except KeyboardInterrupt:
            print('프로그램을 종료합니다.')
            self.rabbitmq_manager.close_connection()
        except Exception as e:
            logging.exception(f"메시지 소비 중 오류: {e}")
            self.rabbitmq_manager.close_connection()

class AIOCRRunning:
    def __init__(self, system_manager):
        self.system_manager = system_manager
        self.settings_manager = self.system_manager.get_manager("settings_manager")
        self.ai_model_manager = self.system_manager.get_manager("ai_model") # AI 모델 매니저 가져오기
        self.rabbitmq_manager = self.system_manager.rabbitmq_manager
        self.ocr_result_handler = OCRResultHandler(self.system_manager, self.ai_model_manager)
        self.message_consumer = MessageConsumer(self.rabbitmq_manager)

    def main(self):
        queue_name = self.settings_manager.get_queue_name("ocr_results")
        self.message_consumer.consume_messages(queue_name, self.ocr_result_handler.handle_message)
