# ai_ocr_running.py

import logging
import json
import pika
import time
from typing import Callable, Dict, Any
import pika.exceptions
from ai_model_manager import AIModelManager
from config.config import get_message, handle_error, send_message_to_queue, handle_message

class OCRResultHandler:
    """OCR 결과 메시지 처리 담당."""
    def __init__(self, system_manager, ai_data_manager):
        self.system_manager = system_manager
        self.settings_manager = self.system_manager.get_manager("settings_manager")
        self.ai_model_manager = AIModelManager.get_instance()  # AIModelManager 인스턴스 가져오기
        self.ai_data_manager = ai_data_manager  # AIDataManager 인스턴스 주입

    def create_ai_request(self, message_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """AI 요청 메시지 생성 (확장성 고려)."""
        return {
            "type": message_type,
            "data": data,
            "reply_to": self.settings_manager.get_queue_name("events")
        }

    def handle_message(self, ch, method, properties, body):
        """AIEventManager의 handle_message 메서드 호출."""
        handle_message(self, ch, method, properties, body)
        send_message_to_queue(self.system_manager, "events_queue", body)

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
            handle_error(self.system_manager, "error", "505", e, "메시지 소비 중 오류")
            self.rabbitmq_manager.close_connection()

class AIOCRRunning:
    def __init__(self, system_manager, ai_data_manager):
        self.system_manager = system_manager
        self.settings_manager = self.system_manager.get_manager("settings_manager")
        self.ai_model_manager = AIModelManager.get_instance()  # AIModelManager 인스턴스 가져오기
        self.rabbitmq_manager = self.ai_model_manager.rabbitmq_manager  # AIModelManager에서 가져오기
        self.ocr_result_handler = OCRResultHandler(self.system_manager, ai_data_manager)  # AIDataManager 인스턴스 주입
        self.message_consumer = MessageConsumer(self.rabbitmq_manager)

    def main(self):
        """메시지 큐에서 OCR 결과 메시지를 소비하여 처리."""
        queue_name = self.settings_manager.get_queue_name("ocr_results")
        self.message_consumer.consume_messages(queue_name, self.ocr_result_handler.handle_message)
