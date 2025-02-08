# file_name: ai_model_manager
import logging
import os
import shutil
from typing import Optional, Tuple

from regex import F
import tensorflow as tf
from transformers import GPT2Tokenizer, GPT2LMHeadModel
from system import DatabaseManager, SettingsManager
from typing import Dict, Any, Optional
from config.config import get_message, handle_error, send_message_to_queue

class AIModelManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(AIModelManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, settings_manager: SettingsManager, ai_data_manager, ai_event_manager, model_path: Optional[str] = None, gpt_model_path: str = "gpt2"):
        if not hasattr(self, 'initialized'):  # Prevent reinitialization
            self.settings_manager = settings_manager
            self.model_path = model_path or self.settings_manager.get_setting("ai_model_path")
            self.gpt_model_path = gpt_model_path
            self.model: Optional[tf.keras.Model] = None
            self.tokenizer: Optional[GPT2Tokenizer] = None
            self.gpt_model: Optional[GPT2LMHeadModel] = None
            self.ai_data_manager = ai_data_manager
            self.ai_event_manager = ai_event_manager
            self.database_manager: Optional[DatabaseManager] = None
            self._load_models()
            self.initialized = True

    def set_ai_data_manager(self, ai_data_manager):
        """AIDataManager 인스턴스 설정."""
        self.ai_data_manager = ai_data_manager

    def set_ai_event_manager(self, ai_event_manager):
        """AIEventManager 인스턴스 설정."""
        self.ai_event_manager = ai_event_manager

    def set_database_manager(self, database_manager: DatabaseManager):
        """DatabaseManager 인스턴스 설정."""
        self.database_manager = database_manager

    def get_ai_data_manager(self):
        """AIDataManager 인스턴스 반환."""
        return self.ai_data_manager

    def get_ai_event_manager(self):
        """AIEventManager 인스턴스 반환."""
        return self.ai_event_manager

    def get_database_manager(self):
        """DatabaseManager 인스턴스 반환."""
        return self.database_manager

    @classmethod
    def get_instance(cls):
        """AIModelManager 싱글톤 인스턴스 반환."""
        if cls._instance is None:
            raise ValueError("AIModelManager 인스턴스가 초기화되지 않았습니다.")
        return cls._instance

    def _load_models(self):
        """모델 로드."""
        try:
            self.tokenizer, self.gpt_model = self._load_gpt_model(self.gpt_model_path)
            if self.model_path:
                self.model = tf.keras.models.load_model(self.model_path)
                logging.info(f"TensorFlow 모델 로딩 완료: {self.model_path}")
        except Exception as e:
            handle_error(self.system_manager, "error", "505", e, "모델 로드 오류")
            raise

    def _load_gpt_model(self, model_path: str) -> Tuple[Optional[GPT2Tokenizer], Optional[GPT2LMHeadModel]]:
        """GPT 모델 로드."""
        try:
            logging.info("GPT 모델 로딩 중...")
            self.tokenizer = GPT2Tokenizer.from_pretrained(model_path if os.path.exists(model_path) else "gpt2")
            self.gpt_model = GPT2LMHeadModel.from_pretrained(model_path if os.path.exists(model_path) else "gpt2")
            logging.info(f"GPT 모델 로딩 완료: {model_path if os.path.exists(model_path) else 'gpt2'}")
            return self.tokenizer, self.gpt_model
        except Exception as e:
            handle_error(self.system_manager, "error", "505", e, "모델 로드 오류")
            return None, None

    def request_ai_training(self, data: Optional[Dict[str, Any]] = None):
        """AI 학습 요청 처리"""
        self.train_ai()
        logging.info("AI 학습 완료")

    def generate_text(self, command: str) -> Optional[str]:
        """GPT 모델을 사용하여 텍스트 생성"""
        if not self.tokenizer or not self.gpt_model:
            logging.error("GPT 모델 또는 토크나이저가 초기화되지 않았습니다.")
            return "GPT 모델 초기화 오류"
        try:
            input_ids = self.tokenizer.encode(command, return_tensors="pt")
            pad_token_id = self.tokenizer.pad_token_id or self.tokenizer.eos_token_id
            attention_mask = (input_ids != pad_token_id).long()
            output = self.gpt_model.generate(input_ids=input_ids, attention_mask=attention_mask, max_new_tokens=50, pad_token_id=pad_token_id)
            return self.tokenizer.decode(output[0], skip_special_tokens=True)
        except Exception as e:
            handle_error(self.system_manager, "error", "505", e, "GPT 텍스트 생성 오류")
            return "GPT 텍스트 생성 오류"

    def save_generated_text_to_db(self, file_name: str, text: str):
        """생성된 텍스트를 데이터베이스에 저장."""
        if not self.database_manager:
            logging.error("DatabaseManager가 설정되지 않았습니다.")
            return
        try:
            self.database_manager.save_text(file_name, text)
            logging.info(f"Generated text saved to database: {file_name}")
        except Exception as e:
            handle_error(self.system_manager, "error", "505", e, "텍스트 저장 오류")
            raise

    def send_message_to_queue(self, queue_name: str, message: str):
        """RabbitMQ 큐에 메시지 전송."""
        send_message_to_queue(self.system_manager, queue_name, message)

    def save_model(self, save_path: str) -> None:
        """모델 저장."""
        if not self.model:
            raise ValueError("저장할 모델이 없습니다.")
        try:
            self.model.save(save_path)
            logging.info(f"모델 저장 완료: {save_path}")
        except Exception as e:
            handle_error(self.system_manager, "error", "505", e, "모델 저장 오류")
            raise

    def apply_trained_model(self, model_path: str) -> None:
        """학습된 모델 적용."""
        try:
            logging.info(f"학습된 모델 로딩 중: {model_path}")
            self.model = tf.keras.models.load_model(model_path)
            logging.info("모델 로딩 완료")
        except FileNotFoundError as e:
            handle_error(self.system_manager, "error", "505", e, "모델 파일 오류")
            raise
        except Exception as e:
            handle_error(self.system_manager, "error", "505", e, "모델 적용 오류")
            raise