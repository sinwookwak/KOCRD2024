# kocrd/handlers/training_event_handler.py
import json
import logging
from PIL import Image, UnidentifiedImageError  # PIL import 위치 변경

from kocrd.managers.ai_managers.ai_training_manager import AITrainingManager
from kocrd.utils.file_utils import copy_file
from kocrd.config.config import config, OCREngineFactory  # config 및 OCREngineFactory import
from kocrd.utils.error_utils import handle_error  # error_utils import

class TrainingEventHandler:
    def __init__(self, system_manager, model_manager, ai_data_manager, ai_model_manager):
        self.system_manager = system_manager
        self.model_manager = model_manager
        self.ai_data_manager = ai_data_manager
        self.ai_training_manager = AITrainingManager(model_manager, system_manager, ai_data_manager)
        self.ai_model_manager = ai_model_manager
        self.ai_model_manager.set_ai_event_manager(self)

    def handle_ocr_request(self, file_path):
        try:
            extracted_text = self.perform_ocr(file_path)
            self.system_manager.trigger_event("ocr_completed", {"file_path": file_path, "extracted_text": extracted_text})
        except Exception as e:
            handle_error(self.system_manager, "ocr_error", "515", e, f"OCR 처리 중 오류 발생: {e}, 파일 경로: {file_path}")
            self.system_manager.trigger_event("ocr_failed", {"file_path": file_path, "error_message": str(e)})

    def perform_ocr(self, file_path):
        ocr_engine_type = config.get("ui.settings.ocr_engine", "tesseract")
        try:
            ocr_engine = OCREngineFactory.create_engine(ocr_engine_type)
            image = Image.open(file_path)
            extracted_text = ocr_engine.perform_ocr(image)
            return extracted_text
        except ValueError as e:
            handle_error(self.system_manager, "ocr_engine_error", "516", e, "OCR 엔진 선택 오류")
            raise
        except ImportError as e:
            handle_error(self.system_manager, "ocr_engine_error", "516", e, "PIL import 오류")
            raise
        except FileNotFoundError as e:
            handle_error(self.system_manager, "ocr_engine_error", "516", e, "파일을 찾을 수 없음")
            raise
        except UnidentifiedImageError as e:
            handle_error(self.system_manager, "ocr_engine_error", "516", e, "이미지 식별 오류")
            raise
        except Exception as e:
            handle_error(self.system_manager, "ocr_engine_error", "516", e, "OCR 엔진 실행 중 오류")
            raise

    def handle_training_start(self, features, label):
        """훈련 시작 이벤트 처리."""
        try:
            data = self.ai_data_manager.load_data()
            if data is None:
                raise ValueError("No training data available. Please check the data source.")

            X_train, X_test, y_train, y_test = self.ai_training_manager.prepare_training_data(data, features, label)
            if X_train is None:
                raise ValueError("Failed to prepare training data. Please verify the feature and label configuration.")

            result = self.ai_training_manager.train_model((X_train, X_test, y_train, y_test), features, label)
            if result is None:
                raise ValueError("Model training failed. Please check the training process and parameters.")

            model_save_path = self.ai_model_manager.save_model(result)
            if model_save_path:
                logging.info(f"Model saved to: {model_save_path}")

            self.system_manager.trigger_event("training_completed", {"model_path": model_save_path})

        except Exception as e:
            handle_error(self.system_manager, "training_error", "500", e, "모델 훈련 중 오류 발생")
            self.system_manager.trigger_event("training_failed", {"error_message": str(e)})

    def handle_hyperparameter_change(self, hyperparameters):
        try:
            self.ai_training_manager.apply_parameters(hyperparameters)
            logging.info(f"Hyperparameters changed: {hyperparameters}")
            self.system_manager.trigger_event("hyperparameters_changed", hyperparameters)

        except (KeyError, ValueError) as e:
            handle_error(self.system_manager, "hyperparameter_error", "500", e, f"하이퍼파라미터 변경 중 오류 발생: {e}")
            self.system_manager.trigger_event("hyperparameters_change_failed", {"error_message": str(e)})
        except Exception as e:
            handle_error(self.system_manager, "hyperparameter_error", "500", e, "하이퍼파라미터 변경 중 오류 발생")
            self.system_manager.trigger_event("hyperparameters_change_failed", {"error_message": str(e)})

    def handle_training_data_change(self, data_path):
        try:
            data = self.ai_data_manager.load_data(data_path)
            if data is None:
                raise ValueError("No training data available. Please check the data source.")
            logging.info(f"Training data changed: {data_path}")
            self.system_manager.trigger_event("training_data_changed", data_path)

        except (FileNotFoundError, ValueError) as e:
            handle_error(self.system_manager, "training_data_error", "500", e, f"훈련 데이터 변경 중 오류 발생: {e}")
            self.system_manager.trigger_event("training_data_change_failed", {"error_message": str(e)})
        except Exception as e:
            handle_error(self.system_manager, "training_data_error", "500", e, "훈련 데이터 변경 중 오류 발생")
            self.system_manager.trigger_event("training_data_change_failed", {"error_message": str(e)})

    def handle_model_save_request(self, source_path, destination_path):
        try:
            copy_file(source_path, destination_path)
            logging.info(f"Model saved to {destination_path}")
        except Exception as e:
            handle_error(self.system_manager, "model_save_error", "500", e, f"모델 저장 중 오류 발생: {e}")
            self.system_manager.trigger_event("model_save_failed", {"error_message": str(e)})

    def send_message_to_queue(self, queue_name, message):
        try:
            queue_config = config.get(f"queues.{queue_name}")
            # RabbitMQ에 메시지 전송 로직 (queue_config 활용)
            # ...
        except KeyError as e:
            handle_error(self.system_manager, "queue_error", "601", e, f"RabbitMQ 설정 오류: {queue_name} not found in configuration.")
            raise
        except Exception as e:
            handle_error(self.system_manager, "queue_error", "600", e, "RabbitMQ 오류")
            raise
