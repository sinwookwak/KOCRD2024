# ai_data_manager.py
import logging
import json
import os
import numpy as np
from datetime import datetime
from PyQt5.QtWidgets import QInputDialog
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from ai_model_manager import AIModelManager
from config.config import get_message, handle_error, send_message_to_queue
from utils.embedding_utils import generate_document_type_embeddings


class AIDataManager:
    def __init__(self, database_manager, model_manager, settings_manager, system_manager):
        """AIDataManager 초기화 메서드."""
        self.database_manager = database_manager
        self.model_manager = model_manager
        self.settings_manager = settings_manager
        self.system_manager = system_manager
        self.model_manager.set_ai_data_manager(self)  # AIModelManager에 AIDataManager 설정
        self.document_embedding_path = self.settings_manager.get("document_embedding_path")
        self.document_types_path = self.settings_manager.get("document_types_path")
        self.use_ml_model = False
        self.ko_e5_model = None
        self.document_type_embeddings = {}
        self.load_ko_e5_model()
        self.load_document_type_embeddings()

    def save_feedback(self, data):
        """피드백 데이터 저장."""
        try:
            self.database_manager.save_feedback(data)
            logging.info(f"피드백 저장 완료: {data}")
            send_message_to_queue(self.system_manager, "feedback_queue", data)
        except Exception as e:
            handle_error(self.system_manager, "error", "505", e, "피드백 저장 오류")

    def request_user_feedback(self, file_path):
        """사용자 피드백 요청."""
        valid_doc_types = self.database_manager.get_valid_doc_types()
        doc_type, ok = QInputDialog.getItem(
            None, '문서 유형 확인', f'문서 "{file_path}"의 유형을 선택해주세요:', valid_doc_types, 0, False
        )
        if ok and doc_type:
            try: # save_feedback에서 발생할 수 있는 예외를 여기서 처리
                self.save_feedback({
                    'file_path': file_path,
                    'doc_type': doc_type,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                return doc_type
            except Exception as e:
                logging.exception(f"피드백 저장 후 오류 발생: {e}")
                # 필요한 경우 QMessageBox를 여기서 다시 표시
                from PyQt5.QtWidgets import QMessageBox # QMessageBox import를 try 블록 안으로 옮김
                QMessageBox.critical(None, "오류", f"피드백 저장 후 오류가 발생했습니다: {e}")
                return None
        return None

    def load_ko_e5_model(self):
        """KoE5 모델 로드."""
        try:
            self.ko_e5_model = SentenceTransformer("nlpai-lab/KoE5")
            logging.info("KoE5 모델 로드 완료.")
        except Exception as e:
            handle_error(self.system_manager, "error", "505", e, "모델 로드 오류")
            self.ko_e5_model = None

    def set_use_ml_model(self, use_ml_model):
        """머신러닝 모델 사용 여부 설정."""
        self.use_ml_model = use_ml_model

    def predict_document_type(self, text):
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
            except Exception as e:
                handle_error(self.system_manager, "error", "505", e, "모델 예측 오류")
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
            handle_error(self.system_manager, "error", "505", e, "임베딩 생성 오류")
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
            except (json.JSONDecodeError, FileNotFoundError) as e:
                handle_error(self.system_manager, "error", "505", e, "임베딩 파일 오류")
                embeddings = generate_document_type_embeddings(self.document_types_path)
                if embeddings:
                    self.load_document_type_embeddings()
            except Exception as e:
                handle_error(self.system_manager, "error", "505", e, "임베딩 로드 오류")
        else:
            logging.info(f"문서 유형 임베딩 파일({embedding_file_path})을 찾을 수 없습니다. 재생성합니다.")
            embeddings = generate_document_type_embeddings(self.document_types_path)
            if embeddings:
                self.load_document_type_embeddings()