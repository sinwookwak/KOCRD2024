# ai_event_manager.py
import logging
import json
import pika
from datetime import datetime
from typing import Dict, Any, Callable
from managers.ai_managers.AI_model_manager import AIModelManager

class AIEventManager:
    """이벤트 처리, 데이터 저장, 메시지 전송 담당."""

    def __init__(self, system_manager, ai_data_manager, ai_prediction_manager):
        self.system_manager = system_manager
        self.settings_manager = self.system_manager.get_manager("settings_manager")
        self.rabbitmq_manager = self.system_manager.rabbitmq_manager
        self.model_manager = AIModelManager.get_instance()  # 싱글톤 인스턴스 사용
        self.model_manager.set_ai_event_manager(self)  # AIModelManager에 AIEventManager 설정
        self.ai_data_manager = ai_data_manager  # AIDataManager 인스턴스 주입
        self.ai_prediction_manager = ai_prediction_manager
        self.message_handlers = {
            "OCR_COMPLETED": self.handle_ocr_event,
            "PREDICT_DOCUMENT_TYPE_RESULT": self.handle_prediction_result,
            "TRAINING_COMPLETED": self.handle_training_event,
            "SAVE_FEEDBACK": self.handle_save_feedback,
            "REQUEST_USER_FEEDBACK": self.handle_request_user_feedback
        }

    def handle_ocr_event(self, file_path, extracted_text):
        """OCR 작업 후 이벤트 처리. 예측 요청 전송."""
        logging.info("Handling OCR completion event.")
        prediction_request = {
            "type": "PREDICT_DOCUMENT_TYPE",
            "data": {"text": extracted_text, "file_path": file_path}, # data 필드 추가
            "reply_to": self.settings_manager.get_queue_name("events")
        }
        self.system_manager.send_message(self.settings_manager.get_queue_name("prediction_requests"), prediction_request) # SystemManager를 통해 메시지 전송

    def handle_prediction_result(self, file_path, document_type):
        """예측 결과 처리 및 이벤트 데이터 저장."""
        self.save_event_data("PREDICTION_COMPLETED", {"file_path": file_path, "document_type": document_type})

    def handle_training_event(self, model_path=None, training_metrics=None):
        """AI 학습 후 이벤트 처리."""
        logging.info("Handling AI training completion event.")
        if training_metrics:
            self.save_event_data("TRAINING_COMPLETED", training_metrics)
        if model_path:
            try:
                self.model_manager.apply_trained_model(model_path) # AIModelManager의 apply_trained_model 사용
            except Exception as e:
                logging.exception(f"모델 적용 중 오류: {e}")

        # 문서 분석 재개
        self.system_manager.start_document_analysis()

        logging.info("AI training event successfully handled.")

    def handle_save_feedback(self, file_path, doc_type):
        """사용자 피드백 저장."""
        self.ai_data_manager.save_feedback({"file_path": file_path, "doc_type": doc_type, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})

    def handle_request_user_feedback(self, file_path):
        """사용자 피드백 요청 이벤트 처리."""
        logging.info("Handling user feedback request event.")
        doc_type = self.ai_data_manager.request_user_feedback(file_path)
        if doc_type:
            self.save_event_data("USER_FEEDBACK_RECEIVED", {"file_path": file_path, "doc_type": doc_type})
        else:
            logging.warning(f"User feedback for file {file_path} was not received.")

    def save_event_data(self, event_type, additional_data=None):
        """이벤트 데이터를 데이터베이스에 저장."""
        logging.info(f"Saving event data for {event_type}.")
        event_data = {
            "event_type": event_type,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "additional_data": additional_data or {}
        }
        self.ai_data_manager.save_feedback(event_data)
        logging.info(f"Event data saved: {event_data}")

    def handle_message(self, ch, method, properties, body):
        """메시지 큐에서 이벤트 메시지를 처리."""
        try:
            message = json.loads(body)
            message_type = message.get("type")

            if message_type not in self.message_handlers: # 메시지 타입 유효성 검사
                logging.warning(f"알 수 없는 메시지 타입: {message_type}, 메시지: {message}")
                self.request_feedback(message, "알 수 없는 메시지 타입") # 피드백 요청
                return

            handler = self.message_handlers[message_type]

            if message_type == "PREDICT_DOCUMENT_TYPE":
                file_path = message.get("file_path")
                extracted_text = message.get("text") # extracted_text 키 수정
                if not file_path or not extracted_text:
                    logging.warning(f"{message_type} 메시지에 필요한 필드(file_path, text)가 없습니다: {message}")
                    self.request_feedback(message, f"{message_type} 메시지 필드 오류")
                    return

                handler(file_path, extracted_text)

            elif message_type in ("SAVE_FEEDBACK", "PREDICT_DOCUMENT_TYPE_RESULT"):
                file_path = message.get("file_path")
                doc_type = message.get("document_type")
                if not file_path or not doc_type:
                    logging.warning(f"{message_type} 메시지에 필요한 필드(file_path, document_type)가 없습니다: {message}")
                    self.request_feedback(message, f"{message_type} 메시지 필드 오류")
                    return
                handler(file_path, doc_type)

            elif message_type == "TRAINING_COMPLETED":
                model_path = message.get("model_path")
                training_metrics = message.get("training_metrics")
                handler(model_path, training_metrics)

            elif message_type == "REQUEST_USER_FEEDBACK":
                file_path = message.get("file_path")
                if not file_path:
                    logging.warning(f"{message_type} 메시지에 필요한 필드(file_path)가 없습니다: {message}")
                    self.request_feedback(message, f"{message_type} 메시지 필드 오류")
                    return
                handler(file_path)

            else:
                logging.warning(f"처리되지 않은 메시지 타입: {message_type}, 메시지: {message}")
                self.request_feedback(message, "처리되지 않은 메시지 타입")
                return

        except json.JSONDecodeError as e:
            logging.exception(f"메시지 JSON 디코딩 오류: {e}, body: {body}")
            self.request_feedback(body, "JSON 디코딩 오류") # 원본 body 전달
        except Exception as e:
            logging.exception(f"메시지 처리 중 오류: {e}")
            self.request_feedback(message, "메시지 처리 오류")

    def request_feedback(self, original_message: Any, error_reason: str):
        """사용자에게 피드백을 요청하는 메시지를 생성하고 전송."""
        feedback_message = {
            "type": "REQUEST_FEEDBACK",  # 새로운 메시지 타입
            "original_message": original_message,
            "error_reason": error_reason,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        # settings_manager를 사용하여 메시지 전송
        self.settings_manager.send_message(
            "feedback_queue", json.dumps(feedback_message)
        )
        logging.info(f"피드백 요청 메시지 전송: {feedback_message}")

    def main(self):
        """메시지 큐에서 이벤트 메시지를 소비하여 처리."""
        try:
            events_queue = self.settings_manager.get_queue_name("events") # 큐 이름 설정에서 가져오기
            def callback(ch, method, properties, body):
                self.handle_message(ch, method, properties, body)
            self.system_manager.start_consuming_specific_queue(events_queue, callback) # SystemManager를 통해 메시지 소비

            print('Waiting for events. To exit press CTRL+C')
            self.rabbitmq_manager.channel.start_consuming() # 메시지 소비 시작

        except pika.exceptions.AMQPConnectionError as e:
            logging.error(f"RabbitMQ 연결 오류: {e}")
            # 필요한 경우 재연결 로직 추가
        except Exception as e:
            logging.exception(f"main 함수 실행 중 오류: {e}")
            # 필요한 경우 추가적인 오류 처리
