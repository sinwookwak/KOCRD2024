# AI-M2\kocrd\managers\ai_managers\ai_prediction_manager.py
import logging
import json
import os
import uuid
import pika
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from utils.embedding_utils import generate_document_type_embeddings
import pika.exceptions
from managers.ai_managers.AI_model_manager import AIModelManager

class AIPredictionManager:
    def __init__(self, model_manager, settings_manager, database_manager, system_manager, rabbitmq_manager):
        self.database_manager = database_manager
        self.model_manager = model_manager
        self.settings_manager = settings_manager
        self.system_manager = system_manager
        self.rabbitmq_manager = rabbitmq_manager
        self.use_ml_model = False
        self.ko_e5_model = None
        self.document_type_embeddings = {}
        self.document_embedding_path = self.settings_manager.get("document_embedding_path")
        self.document_types_path = self.settings_manager.get("document_types_path")
        self.queues = self.settings_manager.get("queues")
        self.ai_data_manager = self.model_manager.ai_data_manager  # AIDataManager 인스턴스 가져오기
        self.load_ko_e5_model()
        self.load_document_type_embeddings()

    def send_prediction_request(self, data):
        """예측 요청 메시지를 큐에 전송."""
        message = {"type": "prediction_request", "data": data}
        self.send_message_to_queue(self.queues["prediction_requests"], message) # queues 사용

    def send_message_to_queue(self, queue_name, message):
        """메시지를 지정된 큐에 전송."""
        try:
            self.rabbitmq_manager.send_message(queue_name, json.dumps(message))
        except pika.exceptions.AMQPError as e:
            logging.error(f"RabbitMQ 전송 오류: {e}")
            self.system_manager.handle_error(f"RabbitMQ 전송 오류: {e}", "RabbitMQ 오류")
            raise


    def load_ko_e5_model(self):
        """KoE5 모델 로드."""
        try:
            self.ko_e5_model = SentenceTransformer("nlpai-lab/KoE5")
            logging.info("KoE5 모델 로드 완료.")
        except Exception as e:
            logging.exception(f"KoE5 모델 로드 오류: {e}")
            self.system_manager.handle_error(f"KoE5 모델 로드 오류: {e}", "모델 로드 오류")
            self.ko_e5_model = None

    def set_use_ml_model(self, use_ml_model):
        """머신러닝 모델 사용 여부 설정."""
        self.use_ml_model = use_ml_model

    def predict_document_type(self, text, file_path):
        """문서 유형 예측."""
        document_type = "Unknown"
        is_rule_based = True
        if self.use_ml_model and self.ko_e5_model is not None:
            try:
                processed_text = self.preprocess_text(text)
                model_input = self.text_to_input(processed_text)
                if model_input is not None and not np.all(model_input == 0):
                    document_type = self.postprocess_prediction(model_input)
                    is_rule_based = False

                    # 피드백 반영
                    feedback = self.ai_data_manager.get_feedback(file_path)
                    if feedback:
                        document_type = feedback.get("document_type", document_type)
            except Exception as e:
                logging.exception(f"머신러닝 모델 예측 오류: {e}")
                self.system_manager.handle_error(f"머신러닝 모델 예측 오류: {e}", "모델 예측 오류")
        else:
            if "invoice" in text.lower():
                document_type = "Invoice"
            elif "report" in text.lower():
                document_type = "Report"
        return document_type, is_rule_based

    def preprocess_text(self, text):
        """텍스트 전처리."""
        return text

    def text_to_input(self, text):
        """텍스트를 모델 입력 형식으로 변환."""
        if self.ko_e5_model is None:
            logging.error("KoE5 모델이 로드되지 않았습니다.")
            return None
        try:
            embeddings = self.ko_e5_model.encode([text])
            return embeddings
        except Exception as e:
            logging.exception(f"KoE5 임베딩 생성 오류: {e}")
            return None

    def postprocess_prediction(self, prediction):
        """모델 예측 결과 후처리 (유사도 비교)."""
        if prediction is None:
            return "Unknown"

        best_similarity = -1
        predicted_type = "Unknown"

        for doc_type, embedding in self.document_type_embeddings.items():
            similarity = cosine_similarity(prediction, np.array(embedding).reshape(1, -1))[0][0]
            if similarity > best_similarity:
                best_similarity = similarity
                predicted_type = doc_type

        return predicted_type


    def load_document_type_embeddings(self):
        """문서 유형 임베딩 로드."""
        embedding_file_path = self.document_embedding_path
        if os.path.exists(embedding_file_path):
            try:
                with open(embedding_file_path, "r", encoding="utf-8") as f:
                    embeddings = json.load(f)
                    for doc_type, embedding in embeddings.items():
                        self.document_type_embeddings[doc_type] = np.array(embedding)
                    logging.info("문서 유형 임베딩 로드 완료.")
            except (json.JSONDecodeError, FileNotFoundError) as e: # 두 예외를 한번에 처리
                logging.error(f"임베딩 파일 오류: {e}")
                self.system_manager.handle_error(f"임베딩 파일 오류: {e}", "파일 오류")
                embeddings = generate_document_type_embeddings(self.document_types_path)
                if embeddings:
                    self.load_document_type_embeddings()
            except Exception as e:
                logging.exception(f"문서 유형 임베딩 로드 오류: {e}")
                self.system_manager.handle_error(f"문서 유형 임베딩 로드 오류: {e}", "임베딩 로드 오류")
        else:
            logging.info(f"문서 유형 임베딩 파일({embedding_file_path})을 찾을 수 없습니다. 재생성합니다.")
            embeddings = generate_document_type_embeddings(self.document_types_path)
            if embeddings:
                self.load_document_type_embeddings()

    def handle_message(self, ch, method, properties, body):
        """메시지 큐에서 예측 요청 메시지를 처리."""
        try:
            message = json.loads(body)
            message_type = message.get("type")
            if message_type == "PREDICT_DOCUMENT_TYPE":
                text = message.get("text")
                file_path = message.get("file_path")
                if not text or not file_path:
                    logging.warning(f"PREDICT_DOCUMENT_TYPE 메시지에 필요한 인자가 없습니다: {message}")
                    return

                document_type, is_rule_based = self.predict_document_type(text, file_path)
                result_message = {
                    "type": "PREDICT_DOCUMENT_TYPE_RESULT",
                    "file_path": file_path,
                    "document_type": document_type,
                    "is_rule_based": is_rule_based,
                    "reply_to": self.queues["events_queue"] # queues 사용
                }
                self.send_message_to_queue(self.queues["prediction_results"], result_message) # queues 사용

                feedback_request_message = {
                    "type": "UI_FEEDBACK_REQUEST",
                    "file_path": file_path,
                    "predicted_type": document_type
                }
                self.send_message_to_queue(self.queues["ui_feedback_requests"], feedback_request_message) # queues 사용
            else:
                logging.warning(f"알 수 없는 메시지 타입: {message_type}")
        except json.JSONDecodeError as e:
            logging.exception(f"메시지 JSON 디코딩 오류: {e}, body: {body}")
            self.system_manager.handle_error(f"메시지 JSON 디코딩 오류: {e}", "메시지 오류")
        except Exception as e:
            logging.exception(f"메시지 처리 중 오류: {e}")
            self.system_manager.handle_error(f"메시지 처리 중 오류: {e}", "메시지 오류")
