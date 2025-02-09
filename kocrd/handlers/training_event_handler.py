# kocrd/handlers/training_event_handler.py
import json
import logging

from kocrd.managers.ai_managers.ai_training_manager import AITrainingManager
from kocrd.managers.ai_managers.ai_model_manager import AIModelManager # AIModelManager import
from kocrd.utils.file_utils import copy_file # file_utils import (필요한 경우)

class TrainingEventHandler:
    def __init__(self, system_manager, model_manager, ai_data_manager, error_handler, queues):
        self.system_manager = system_manager
        self.model_manager = model_manager
        self.ai_data_manager = ai_data_manager
        self.error_handler = error_handler
        self.queues = queues
        self.ai_training_manager = AITrainingManager(model_manager, system_manager, ai_data_manager)
        self.ai_model_manager = AIModelManager.get_instance() # AIModelManager 싱글톤 인스턴스 가져오기
        self.ai_model_manager.set_ai_event_manager(self) # AIEventManager를 AIModelManager에 설정

    def handle_training_start(self, features, label):
        """훈련 시작 이벤트 처리."""
        try:
            data = self.ai_data_manager.load_data()
            if data is None:
                raise ValueError("No training data available.")

            X_train, X_test, y_train, y_test = self.ai_training_manager.prepare_training_data(data, features, label)
            if X_train is None:
                raise ValueError("Failed to prepare training data.")

            # 모델 훈련 시작
            result = self.ai_training_manager.train_model((X_train, X_test, y_train, y_test), features, label)
            if result is None:
                raise ValueError("Model training failed.")

            # 모델 저장 (예시)
            model_save_path = self.ai_model_manager.save_model(result) # AIModelManager의 save_model() 사용
            if model_save_path:
                logging.info(f"Model saved to: {model_save_path}")

            # 훈련 완료 이벤트 발생 (다른 컴포넌트에게 알림)
            self.system_manager.trigger_event("training_completed", {"model_path": model_save_path}) # system_manager에 event trigger 추가

        except Exception as e:
            self.error_handler.handle_error(None, "training_error", "500", e, "모델 훈련 중 오류 발생")
            # 훈련 실패 이벤트 발생 (다른 컴포넌트에게 알림)
            self.system_manager.trigger_event("training_failed", {"error_message": str(e)}) # system_manager에 event trigger 추가

    # ... (다른 이벤트 처리 메서드: handle_hyperparameter_change, handle_training_data_change 등)

    def handle_model_save_request(self, source_path, destination_path): # 새로운 메서드 추가
        """모델 저장 요청 처리"""
        try:
            copy_file(source_path, destination_path) # file_utils의 copy_file() 사용
            logging.info(f"Model saved to {destination_path}")
        except Exception as e:
            self.error_handler.handle_error(None, "model_save_error", "500", e, "모델 저장 중 오류 발생")

# ... (send_message_to_queue 함수는 필요에 따라 여기에 정의하거나, 별도의 모듈로 분리)