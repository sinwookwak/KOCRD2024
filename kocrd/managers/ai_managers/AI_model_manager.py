# file_name: AI_model_manager
import logging
import os
import shutil
from typing import Optional, Tuple

import tensorflow as tf
from transformers import GPT2Tokenizer, GPT2LMHeadModel

from managers.settings_manager import SettingsManager


class AIModelManager:
    def __init__(self, settings_manager: SettingsManager, model_path: Optional[str] = None, gpt_model_path: str = "gpt2"):
        self.settings_manager = settings_manager
        self.model_path = model_path or self.settings_manager.get_setting("ai_model_path")  # 설정에서 모델 경로 가져오기
        self.gpt_model_path = gpt_model_path
        self.model: Optional[tf.keras.Model] = None
        self.tokenizer: Optional[GPT2Tokenizer] = None
        self.gpt_model: Optional[GPT2LMHeadModel] = None
        self._load_models()

    def _load_models(self):
        try:
            self.tokenizer, self.gpt_model = self._load_gpt_model(self.gpt_model_path)
            if self.model_path:  # TensorFlow 모델 경로가 설정된 경우에만 로드
                self.model = tf.keras.models.load_model(self.model_path)
                logging.info(f"TensorFlow 모델 로딩 완료: {self.model_path}")
        except Exception as e:
            logging.exception(f"모델 로딩 중 오류 발생: {e}")
            raise  # 오류를 상위로 전파

    def _load_gpt_model(self, model_path: str) -> Tuple[Optional[GPT2Tokenizer], Optional[GPT2LMHeadModel]]:
        try:
            logging.info("GPT 모델 로딩 중...")
            if os.path.exists(model_path):
                self.tokenizer = GPT2Tokenizer.from_pretrained(model_path)
                self.gpt_model = GPT2LMHeadModel.from_pretrained(model_path)
                logging.info(f"GPT 모델 로딩 완료: {model_path}")
            else:
                logging.warning(f"GPT 모델 경로({model_path})를 찾을 수 없어 기본 모델(gpt2)을 사용합니다.")
                self.tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
                self.gpt_model = GPT2LMHeadModel.from_pretrained("gpt2")
                logging.info("기본 GPT 모델(gpt2) 로딩 완료")
            return self.tokenizer, self.gpt_model
        except Exception as e:
            logging.exception(f"GPT 모델 로딩 중 오류 발생: {e}")
            return None, None

    def generate_text(self, command: str) -> Optional[str]:
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
            logging.exception(f"GPT 텍스트 생성 중 오류 발생: {e}")
            return "GPT 텍스트 생성 오류"

    def save_model(self, save_path: str) -> None: # tensorflow 모델 저장 기능만 남김
        if not self.model:
            raise ValueError("저장할 모델이 없습니다.")
        try:
            self.model.save(save_path)
            logging.info(f"모델 저장 완료: {save_path}")
        except Exception as e:
            logging.exception(f"모델 저장 중 오류 발생: {e}")
            raise # 오류를 상위로 전파

    def apply_trained_model(self, model_path: str) -> None:
        try:
            logging.info(f"학습된 모델 로딩 중: {model_path}")
            self.model = tf.keras.models.load_model(model_path)
            logging.info("모델 로딩 완료")
        except FileNotFoundError:
            logging.error(f"모델 파일을 찾을 수 없습니다: {model_path}")
            raise # 오류를 상위로 전파
        except Exception as e:
            logging.exception(f"학습된 모델 적용 오류: {e}")
            raise # 오류를 상위로 전파