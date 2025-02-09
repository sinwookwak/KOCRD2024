# kocrd/handlers/training_event_handler.py
import json
import logging

from kocrd.managers.ai_managers.ai_training_manager import AITrainingManager
from kocrd.managers.ai_managers.ai_model_manager import AIModelManager
from kocrd.utils.file_utils import copy_file
from kocrd.config.config import config


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
    def handle_ocr_request(self, file_path):
        """OCR 요청 처리."""
        try:
            # OCR 처리 로직 (예: OCR 엔진 초기화, 이미지 로드, OCR 수행 등)
            # ...
            extracted_text = self.perform_ocr(file_path) # perform_ocr() 메서드 추가

            # OCR 완료 이벤트 발생
            self.system_manager.trigger_event("ocr_completed", {"file_path": file_path, "extracted_text": extracted_text})

        except Exception as e:
            self.error_handler.handle_error(None, "ocr_error", "515", e, "OCR 처리 중 오류 발생")
            self.system_manager.trigger_event("ocr_failed", {"file_path": file_path, "error_message": str(e)})

    def perform_ocr(self, file_path):
        """실제 OCR 작업을 수행."""
        # OCR 엔진 선택 및 초기화
        ocr_engine_type = config.ui["settings"].get("ocr_engine", "tesseract")
        ocr_engine = OCREngineFactory.create_engine(ocr_engine_type)

        # 이미지 로드 및 OCR 수행
        try:
            # 필요한 이미지 처리 라이브러리 import (예: PIL)
            from PIL import Image

            image = Image.open(file_path)
            extracted_text = ocr_engine.perform_ocr(image)
            return extracted_text
        except Exception as e:
            self.error_handler.handle_error(None, "ocr_engine_error", "516", e, "OCR 엔진 실행 중 오류")
            raise  # 에러를 다시 발생시켜 handle_ocr_request()에서 처리하도록 함

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
    def handle_hyperparameter_change(self, hyperparameters):
        try:
            self.ai_training_manager.apply_parameters(hyperparameters)
            logging.info(f"Hyperparameters changed: {hyperparameters}")
            self.system_manager.trigger_event("hyperparameters_changed", hyperparameters)

        except KeyError as e:  # 더 구체적인 예외 처리
            self.error_handler.handle_error(None, "hyperparameter_error", "500", e, f"하이퍼파라미터 변경 중 KeyError 발생: {e}")
            self.system_manager.trigger_event("hyperparameters_change_failed", {"error_message": str(e)})
        except ValueError as e: # 추가적인 예외 처리
            self.error_handler.handle_error(None, "hyperparameter_error", "500", e, f"하이퍼파라미터 변경 중 ValueError 발생: {e}")
            self.system_manager.trigger_event("hyperparameters_change_failed", {"error_message": str(e)})
        except Exception as e:
            self.error_handler.handle_error(None, "hyperparameter_error", "500", e, "하이퍼파라미터 변경 중 오류 발생")
            self.system_manager.trigger_event("hyperparameters_change_failed", {"error_message": str(e)})

    def handle_training_data_change(self, data_path):
        try:
            data = self.ai_data_manager.load_data(data_path)
            if data is None:
                raise ValueError("No training data available.")
            # ... (필요한 데이터 전처리 및 모델 재훈련 로직)
            logging.info(f"Training data changed: {data_path}")
            self.system_manager.trigger_event("training_data_changed", data_path)

        except FileNotFoundError as e:  # 더 구체적인 예외 처리
            self.error_handler.handle_error(None, "training_data_error", "500", e, f"훈련 데이터 변경 중 FileNotFoundError 발생: {e}")
            self.system_manager.trigger_event("training_data_change_failed", {"error_message": str(e)})
        except Exception as e:
            self.error_handler.handle_error(None, "training_data_error", "500", e, "훈련 데이터 변경 중 오류 발생")
            self.system_manager.trigger_event("training_data_change_failed", {"error_message": str(e)})

    def handle_model_save_request(self, source_path, destination_path):
        try:
            copy_file(source_path, destination_path)
            logging.info(f"Model saved to {destination_path}")
        except Exception as e:
            self.error_handler.handle_error(None, "model_save_error", "500", e, "모델 저장 중 오류 발생")

    def send_message_to_queue(self, queue_name, message):  # self 추가
        try:
            queue_config = config.queues[queue_name]
            # RabbitMQ에 메시지 전송 로직 (queue_config 활용)
            # ...
        except KeyError:
            handle_error(self.system_manager, "error", "511", None, "RabbitMQ 설정 오류")
            raise
        except Exception as e:
            handle_error(self.system_manager, "error", "511", e, "RabbitMQ 오류")
            raise
