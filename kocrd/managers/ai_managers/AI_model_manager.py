# file_name: ai_model_manager
import logging
import os
from typing import Optional, Tuple, Dict, Any

import tensorflow as tf
from transformers import GPT2Tokenizer, GPT2LMHeadModel

from kocrd.config.config import ConfigManager  # ConfigManager import
from kocrd.managers.database_manager import DatabaseManager
from kocrd.handlers.training_event_handler import TrainingEventHandler
from kocrd.managers.ai_managers.ai_training_manager import AITrainingManager  # import 추가
from kocrd.utils.error_utils import handle_error  # import 추가


def singleton(cls):
    instances = {}

    def getinstance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return singleton


@singleton  # 싱글톤 적용
class AIModelManager:
    def __init__(self, config_manager: ConfigManager, database_manager: DatabaseManager,
                 training_event_handler: TrainingEventHandler, ai_training_manager: AITrainingManager):  # 의존성 주입
        self.config_manager = config_manager
        self.model_path = self.config_manager.get("file_paths.ai_model_path")  # ConfigManager 사용
        self.gpt_model_path = self.config_manager.get("file_paths.gpt_model_path", "gpt2")  # ConfigManager 사용
        self.model: Optional[tf.keras.Model] = None
        self.tokenizer: Optional[GPT2Tokenizer] = None
        self.gpt_model: Optional[GPT2LMHeadModel] = None
        self.database_manager = database_manager
        self.training_event_handler = training_event_handler
        self.ai_training_manager = ai_training_manager  # AI Training Manager 추가
        self._load_tensorflow_model()  # 모델 로딩 분리
        self._load_gpt_model()  # 모델 로딩 분리
        self.ai_event_manager = None # ai_event_manager 초기화
    def _load_tensorflow_model(self):
        """TensorFlow 모델 로드."""
        try:
            if self.model_path:
                self.model = tf.keras.models.load_model(self.model_path)
                logging.info(f"TensorFlow 모델 로딩 완료: {self.model_path}")
        except Exception as e:
            logging.error(f"TensorFlow 모델 로드 오류: {e}")  # 더 구체적인 로깅

    def _load_gpt_model(self):
        """GPT 모델 로드."""
        try:
            logging.info("GPT 모델 로딩 중...")
            self.tokenizer = GPT2Tokenizer.from_pretrained(self.gpt_model_path)
            self.gpt_model = GPT2LMHeadModel.from_pretrained(self.gpt_model_path)
            logging.info(f"GPT 모델 로딩 완료: {self.gpt_model_path}")
        except Exception as e:
            logging.error(f"GPT 모델 로드 오류: {e}")  # 더 구체적인 로깅

    def request_ai_training(self, data: Optional[Dict[str, Any]] = None):
        """AI 학습 요청 처리 (구현 필요)."""
        try:
            # 실제 학습 로직 구현
            logging.info("AI 학습 시작")
            self.train_ai(data)  # train_ai 호출
            logging.info("AI 학습 완료")
        except Exception as e:
            logging.error(f"AI 학습 오류: {e}")  # 더 구체적인 로깅
            raise
    def train_ai(self, data: Optional[Dict[str, Any]] = None):  # train_ai 구현
        """AI 모델 학습."""
        try:
            # 학습 데이터 준비
            # ...

            # 모델 학습
            # ...

            # 학습 결과 저장
            # ...
            self.ai_training_manager.train_model(data, "features", "label")  # AI Training Manager 사용
            pass  # placeholder
        except Exception as e:
            logging.error(f"AI 모델 학습 오류: {e}")
            raise
    def set_ai_event_manager(self, ai_event_manager: TrainingEventHandler):  # 타입 힌트 추가
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
            output = self.gpt_model.generate(input_ids=input_ids, attention_mask=attention_mask, max_new_tokens=50,
                                            pad_token_id=pad_token_id)
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