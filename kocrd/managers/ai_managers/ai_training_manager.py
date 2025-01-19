# ai_training_manager.py

import logging
import json
import os
from sklearn.model_selection import train_test_split
from PyQt5.QtWidgets import QMessageBox
class AITrainingManager:
    def __init__(self, model_manager, ai_data_manager, settings_manager, system_manager): # settings_manager 추가
        self.model_manager = model_manager
        self.ai_data_manager = ai_data_manager
        self.settings_manager = settings_manager # settings_manager 저장
        self.system_manager = system_manager
        self.document_embedding_path = self.settings_manager.get_setting("document_embedding_path") # 설정 가져오기

    def prepare_training_data(self, data, features, label):
        """훈련 데이터를 준비합니다."""
        try:
            X = data[features]
            y = data[label]
            return train_test_split(X, y, test_size=0.2)
        except KeyError as e:
            error_message = f"데이터에 필요한 열이 없습니다: {e}"
            self.system_manager.handle_error(error_message, "데이터 오류")
            logging.error(error_message) # 로그 추가
            return None, None, None, None
        except Exception as e: # 추가적인 예외 처리
            error_message = f"데이터 준비 중 오류 발생: {e}"
            self.system_manager.handle_error(error_message, "데이터 오류")
            logging.exception(error_message) # 로그 추가
            return None, None, None, None

    def train_model(self, data, features, label):
        """모델을 훈련합니다."""
        try:
            if self.model_manager.tensorflow_model is None:
                raise ValueError("학습할 TensorFlow 모델이 없습니다.")
            logging.info("AI 모델 학습 시작...")
            result = self.model_manager.train(data, features, label)
            logging.info("AI 모델 학습 완료.")
            return result
        except ValueError as e: # ValueError 처리 추가
            error_message = str(e)
            self.system_manager.handle_error(error_message, "모델 오류")
            logging.error(error_message)
            return None
        except Exception as e:
            error_message = f"모델 학습 중 오류: {e}"
            self.system_manager.handle_error(error_message, "학습 오류")
            logging.exception(error_message)
            return None

    def apply_parameters(self, parameters):
        """모델에 하이퍼파라미터 적용."""
        try:
            self.model_manager.apply_parameters(parameters)
            logging.info("Parameters applied successfully.")
        except Exception as e:
            error_message = f"파라미터 적용 중 오류: {e}"
            self.system_manager.handle_error(error_message, "파라미터 오류")
            logging.exception(error_message)
    def train_with_parameters(self, file_path, features, label):
        """사용자가 제공한 파라미터 파일로 모델을 학습."""
        try:
            with open(file_path, "r", encoding="utf-8") as param_file:
                parameters = json.load(param_file)
            self.apply_parameters(parameters)
            data = self.ai_data_manager.load_data()
            if data is not None:
                self.train_model(data, features, label)
            logging.info("Model training completed with provided parameters.")
            QMessageBox.information(None, "학습 완료", "모델 학습이 성공적으로 완료되었습니다.")
        except json.JSONDecodeError:
            error_message = f"선택한 파일이 JSON 형식이 아닙니다: {file_path}"
            self.system_manager.handle_error(error_message, "파일 오류")
            logging.error(error_message)
        except FileNotFoundError:
            error_message = f"파일을 찾을 수 없습니다: {file_path}"
            self.system_manager.handle_error(error_message, "파일 오류")
            logging.error(error_message)
        except Exception as e:
            error_message = f"모델 학습 중 오류: {e}"
            self.system_manager.handle_error(error_message, "학습 오류")
            logging.exception(error_message)
