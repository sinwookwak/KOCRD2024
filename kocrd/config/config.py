# kocrd/config/config.py
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any
from kocrd.handlers.message_handler import MessageHandler
from kocrd.handlers.training_event_handler import TrainingEventHandler
from kocrd.utils.error_utils import handle_error
from kocrd.User import FeedbackEventHandler

MESSAGES_FILE_PATH = 'kocrd/config/messages.json'

class RabbitMQConfig:
    def __init__(self, config):
        self.host = config.get("host")
        self.port = config.get("port")
        self.user = config.get("user")
        self.password = config.get("password")
        self.virtual_host = config.get("virtual_host")

class FilePathConfig:
    def __init__(self, config):
        self.models = config.get("models")
        self.document_embedding = config.get("document_embedding")
        self.document_types = config.get("document_types")
        self.temp_files = config.get("temp_files")

class LanguageConfig:
    def __init__(self, config):
        self.language_packs = {}
        self.lang_dir = config.get("language_dir")
        self.messages = config.get("messages")
        self.language = config.get("ui.language")

    def load_language_pack(self, lang_code: str) -> dict:
        lang_path = os.path.join(self.lang_dir, f"{lang_code}.json")
        try:
            with open(lang_path, "r", encoding="utf-8") as f:
                lang_pack = json.load(f)
                if "language" not in lang_pack:
                    raise ValueError(f"Language pack '{lang_code}.json' must have 'language' attribute.")
                return lang_pack
        except FileNotFoundError:
            logging.error(f"Language pack '{lang_code}.json' not found.")
            return {}
        except json.JSONDecodeError:
            logging.error(f"Error decoding JSON in '{lang_code}.json'.")
            return {}
        except ValueError as e:
            logging.error(f"Error loading language pack: {e}")
            return {}
        except Exception as e:
            logging.exception(f"An unexpected error occurred: {e}")
            return {}

    def get_language_pack(self, lang_code: str) -> dict:
        if lang_code in self.language_packs:
            return self.language_packs[lang_code]
        else:
            lang_pack = self.load_language_pack(lang_code)
            self.language_packs[lang_code] = lang_pack
            return lang_pack

    def set_language_directory(self, lang_dir: str):
        self.lang_dir = lang_dir
        self.language_packs = {}

    def get_message(self, message_id, lang_pack=None):
        if lang_pack is None:
            lang_pack = self.get_language_pack(self.language)
        category, code = message_id.split("_")
        message_key = self.messages["messages"][category][code]
        try:
            return lang_pack[message_key]
        except KeyError:
            logging.error(f"Unknown message ID: {message_id} (in language pack: {self.language})")
            return f"Unknown message ID: {message_id}"

    def get_ui_text(self, ui_id, lang_pack=None):
        if lang_pack is None:
            lang_pack = self.get_language_pack(self.language)
        try:
            return lang_pack[self.messages["id_mapping"]["ui"][ui_id]]
        except KeyError:
            logging.error(f"Unknown UI ID: {ui_id} (in language pack: {self.language})")
            return f"Unknown UI ID: {ui_id}"

class UIConfig:
    def __init__(self, config):
        self.language = config.get("language", "ko")
        self.id_mapping = config.get("id_mapping")
        self.settings = config.get("settings")

class Config:
    def __init__(self, config_file):
        self.config_data = {}
        self._load_and_merge_configs([config_file, "config/queues.json", MESSAGES_FILE_PATH])
        self.rabbitmq = RabbitMQConfig(self.get("rabbitmq"))
        self.file_paths = FilePathConfig(self.get("file_paths"))
        self.ui = UIConfig(self.get("ui"))
        self.language = LanguageConfig(self.config_data)

    def _load_json(self, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError as e:
            handle_error(logging, "config_error", "512", e, f"설정 파일 '{file_path}'을 찾을 수 없습니다.")
            return {}
        except json.JSONDecodeError as e:
            handle_error(logging, "config_error", "511", e, f"설정 파일 '{file_path}'의 JSON 형식이 올바르지 않습니다.")
            return {}
        except Exception as e:
            handle_error(logging, "config_error", "513", e, f"설정 파일 '{file_path}' 로드 중 오류 발생")
            return {}

    def _merge_configs(self, config1: dict, config2: dict) -> dict:
        merged = config1.copy()
        merged.update(config2)
        return merged

    def _load_and_merge_configs(self, config_files: list):
        for file_path in config_files:
            config_data = self._load_json(file_path)
            self.config_data = self._merge_configs(self.config_data, config_data)

    def get(self, key_path: str, default=None):
        keys = key_path.split(".")
        data = self.config_data
        for key in keys:
            if isinstance(data, dict) and key in data:
                data = data[key]
            else:
                return default
        return data

    def validate(self, key_path: str, validator: callable, message: str):
        value = self.get(key_path)
        if not validator(value):
            raise ValueError(message)

    def get_rabbitmq_settings(self):
        return self.get("rabbitmq")

    def get_file_paths(self):
        return self.get("file_paths")

    def get_constants(self):
        return self.get("constants")

    def get_ui_settings(self):
        return self.get("ui.settings")

    def get_ui_id_mapping(self):
        return self.get("ui.id_mapping")

    def get_managers(self):
        return self.get("managers")

    def get_messages(self):
        return self.get("messages")

    def get_queues(self):
        return self.get("queues")

    def get_database_url(self):
        return self.get("database_url")

    def get_file_settings(self):
        return self.get("file_settings")

config = Config("config/development.json")

class SystemManager:
    def __init__(self, settings_manager):
        self.settings_manager = settings_manager
        self.managers = {}

    def initialize_managers(self):
        for manager_name, manager_config in config.managers.items():
            module_path = manager_config["module"]
            class_name = manager_config["class"]
            dependencies = manager_config.get("dependencies", [])
            kwargs = manager_config.get("kwargs", {})

            dependencies_instances = [
                self.managers[dep] for dep in dependencies
            ]

            try:
                module = __import__(module_path, fromlist=[class_name])
                manager_class = getattr(module, class_name)

                self.managers[manager_name] = manager_class(
                    *dependencies_instances, **kwargs
                )
            except ImportError as e:
                logging.error(f"Error importing module {module_path}: {e}")
            except AttributeError as e:
                logging.error(
                    f"Error getting class {class_name} from module {module_path}: {e}")
            except Exception as e:
                logging.error(
                    f"An unexpected error occurred during manager initialization: {e}")

    def get_manager(self, manager_name):
        return self.managers.get(manager_name)

class ConfigManager:
    def __init__(self, config_files: list):
        self.config_data = {}
        self._load_and_merge_configs(config_files)

    def _merge_configs(self, config1: dict, config2: dict) -> dict:
        config1.update(config2)
        return config1

    def _load_and_merge_configs(self, config_files: list):
        for file_path in config_files:
            config_data = self._load_json(file_path)
            self.config_data = self._merge_configs(self.config_data, config_data)

    def get(self, key_path: str, default=None):
        keys = key_path.split(".")
        data = self.config_data
        for key in keys:
            if isinstance(data, dict) and key in data:
                data = data[key]
            else:
                return default
        return data

    def validate(self, key_path: str, validator: callable, message: str):
        value = self.get(key_path)
        if not validator(value):
            raise ValueError(message)

    def get_rabbitmq_settings(self):
        return self.get("rabbitmq")

    def get_file_paths(self):
        return self.get("file_paths")

    def get_constants(self):
        return self.get("constants")

    def get_ui_settings(self):
        return self.get("ui.settings")

    def get_ui_id_mapping(self):
        return self.get("ui.id_mapping")

    def get_managers(self):
        return self.get("managers")

    def get_messages(self):
        return self.get("messages")

    def get_queues(self):
        return self.get("queues")

    def get_database_url(self):
        return self.get("database_url")

    def get_file_settings(self):
        return self.get("file_settings")

    def _load_json(self, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError as e:
            handle_error(logging, "config_error", "512", e, f"설정 파일 '{file_path}'을 찾을 수 없습니다.")
            return {}
        except json.JSONDecodeError as e:
            handle_error(logging, "config_error", "511", e, f"설정 파일 '{file_path}'의 JSON 형식이 올바르지 않습니다.")
            return {}
        except Exception as e:
            handle_error(logging, "config_error", "513", e, f"설정 파일 '{file_path}' 로드 중 오류 발생")
            return {}

class OCREngine:
    def perform_ocr(self, image: Any) -> str:
        raise NotImplementedError

class TesseractOCR(OCREngine):
    def perform_ocr(self, image: Any) -> str:
        import pytesseract

        return pytesseract.image_to_string(image)

class CloudVisionOCR(OCREngine):
    def perform_ocr(self, image: Any) -> str:
        pass

class AIModel:
    def predict(self, data: Any) -> Any:
        raise NotImplementedError

class ErrorHandler:
    def handle_error(system_manager, category, code, exception, error_type):
        error_message = config.language.get_message(category, code)
        system_manager.handle_error(error_message, error_type)
        logging.exception(error_message)

def send_message_to_queue(system_manager, queue_name, message):
    try:
        queue_config = config.queues[queue_name]
    except KeyError as e:
        handle_error(system_manager, "error", "511", e, "RabbitMQ 설정 오류")
        raise
    except Exception as e:
        handle_error(system_manager, "error", "511", e, "RabbitMQ 오류")
        raise

class OCRProcessor:
    def __init__(self, ai_event_manager, error_handler, settings_manager):
        self.ai_event_manager = ai_event_manager
        self.error_handler = error_handler
        self.settings_manager = settings_manager

    def process_ocr(self, data):
        file_path = data.get("file_path")
        ocr_engine_type = self.settings_manager.ui["settings"].get("ocr_engine", "tesseract")
        ocr_engine = OCREngineFactory.create_engine(ocr_engine_type)
        extracted_text = ocr_engine.perform_ocr(file_path)

class ClassificationModel(AIModel):
    def predict(self, data: Any) -> Any:
        pass

class ObjectDetectionModel(AIModel):
    def predict(self, data: Any) -> Any:
        pass

class OCREngineFactory:
    @staticmethod
    def create_engine(engine_type: str) -> OCREngine:
        if engine_type == "tesseract":
            return TesseractOCR()
        elif engine_type == "cloud_vision":
            return CloudVisionOCR()
        else:
            raise ValueError(f"Unknown OCR engine type: {engine_type}")

class AIModelFactory:
    @staticmethod
    def create_model(model_type: str) -> AIModel:
        if model_type == "classification":
            return ClassificationModel()
        elif model_type == "object_detection":
            return ObjectDetectionModel()
        else:
            raise ValueError(f"Unknown AI model type: {model_type}")

class OCREventHandler:
    def __init__(self, system_manager, error_handler, prediction_event_handler, queues):
        self.system_manager = system_manager
        self.error_handler = error_handler
        self.prediction_event_handler = prediction_event_handler
        self.queues = queues

    def handle_ocr_event(self, file_path, extracted_text):
        logging.info("Handling OCR completion event.")
        prediction_request = {
            "type": "PREDICT_DOCUMENT_TYPE",
            "data": {"text": extracted_text, "file_path": file_path},
            "reply_to": self.queues["events_queue"],
        }
        send_message_to_queue(
            self.system_manager, self.queues["prediction_requests"], prediction_request
        )
        self.prediction_event_handler.handle_prediction_requested(
            file_path
        )

class PredictionEventHandler:
    def __init__(self, ai_data_manager, error_handler):
        self.ai_data_manager = ai_data_manager
        self.error_handler = error_handler

    def handle_prediction_result(self, file_path, document_type):
        try:
            self._save_prediction_completed_event(file_path, document_type)
            self._trigger_next_step(file_path, document_type)
        except Exception as e:
            self.error_handler.handle_error(
                None,
                "prediction_error",
                "500",
                e,
                "예측 결과 처리 중 오류 발생",
            )

    def handle_prediction_requested(self, file_path):
        pass

    def _save_prediction_completed_event(self, file_path, document_type):
        event_data = {"file_path": file_path, "document_type": document_type}
        save_event_data(self.ai_data_manager, "PREDICTION_COMPLETED", event_data)

    def _trigger_next_step(self, file_path, document_type):
        pass

ocr_engine_type = config.ui["settings"].get("ocr_engine", "tesseract")
ai_model_type = config.ui["settings"].get("ai_model", "classification")

ocr_engine = OCREngineFactory.create_engine(ocr_engine_type)
ai_model = AIModelFactory.create_model(ai_model_type)

def save_event_data(ai_data_manager, event_type, additional_data=None):
    logging.info(f"Saving event data for {event_type}.")
    event_data = {
        "event_type": event_type,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "additional_data": additional_data or {},
    }
    if ai_data_manager is None:
        raise ValueError("ai_data_manager is not initialized.")
    ai_data_manager.save_feedback(event_data)
    logging.info(f"Event data saved: {event_data}")

class AIEventManager:
    def __init__(
        self,
        system_manager,
        settings_manager,
        model_manager,
        ai_data_manager,
        error_handler,
        queues,
    ):
        self.system_manager = system_manager
        self.settings_manager = settings_manager
        self.model_manager = model_manager
        self.ai_data_manager = ai_data_manager
        self.error_handler = error_handler
        self.queues = queues

        self.ocr_processor = OCRProcessor(self, error_handler, settings_manager)
        self.prediction_event_handler = PredictionEventHandler(ai_data_manager, error_handler)
        self.ocr_event_handler = OCREventHandler(
            system_manager, error_handler, self.prediction_event_handler, queues
        )
        self.feedback_event_handler = FeedbackEventHandler(ai_data_manager, error_handler)
        self.training_event_handler = TrainingEventHandler(
            system_manager, model_manager, ai_data_manager, error_handler, queues
        )
        self.message_handler = MessageHandler(
            self.training_event_handler, error_handler
        )

    def handle_message(self, ch, method, properties, body):
        self.message_handler.handle_message(ch, method, properties, body)

    def handle_ocr_event(self, file_path, extracted_text):
        self.ocr_event_handler.handle_ocr_event(file_path, extracted_text)

    def handle_prediction_result(self, file_path, document_type):
        self.prediction_event_handler.handle_prediction_result(
            file_path, document_type
        )

    def handle_training_event(self, model_path=None, training_metrics=None):
        self.training_event_handler.handle_training_event(
            model_path, training_metrics
        )

    def handle_save_feedback(self, file_path, doc_type):
        self.feedback_event_handler.handle_save_feedback(file_path, doc_type)

    def handle_request_user_feedback(self, file_path):
        self.feedback_event_handler.handle_request_user_feedback(file_path)

    def request_feedback(self, original_message: Any, error_reason: str):
        self.feedback_event_handler.request_feedback(original_message, error_reason)
