# kocrd/config/config.py
import json
import logging
from datetime import datetime
from typing import Dict, Any
import os
from kocrd.handlers.message_handler import MessageHandler
from kocrd.handlers.training_event_handler import TrainingEventHandler


class RabbitMQConfig:
    def __init__(self, config):
        self.host = config["host"]
        self.port = config["port"]
        self.user = config["user"]
        self.password = config["password"]
        self.virtual_host = config["virtual_host"]
class FilePathConfig:
    def __init__(self, config):
        self.models = config["models"]
        self.document_embedding = config["document_embedding"]
        self.document_types = config["document_types"]
        self.temp_files = config["temp_files"]
class LanguageConfig:
    def __init__(self, config):
        self.language_packs = {}
        self.lang_dir = config["language_dir"]
        self.messages = config["messages"]

    def load_language_pack(self, lang_code: str) -> dict:
        """특정 언어 코드에 대한 언어팩을 로드합니다."""
        lang_path = os.path.join(self.lang_dir, f"{lang_code}.json")
        try:
            with open(lang_path, "r", encoding="utf-8") as f:
                lang_pack = json.load(f)

                # "language" 속성 체크 (필요에 따라)
                if "language" not in lang_pack:
                    raise ValueError(f"Language pack '{lang_code}.json' must have 'language' attribute.")

                return lang_pack
        except FileNotFoundError:
            logging.error(f"Language pack '{lang_code}.json' not found.")
            return {}  # 빈 딕셔너리 반환 또는 예외 발생 등 적절한 처리
        except json.JSONDecodeError:
            logging.error(f"Error decoding JSON in '{lang_code}.json'.")
            return {}
        except ValueError as e:
            logging.error(str(e))
            return {}
        except Exception as e: # 예상치 못한 에러에 대한 처리
            logging.exception(f"An unexpected error occurred: {e}")
            return {}
    def get_language_pack(self, lang_code: str) -> dict:
        """언어팩을 반환하거나, 언어팩이 없을 경우 로드 후 반환합니다."""

        if lang_code in self.language_packs:
            return self.language_packs[lang_code]
        else:
            lang_pack = self.load_language_pack(lang_code)
            self.language_packs[lang_code] = lang_pack  # 로드한 언어팩 저장
            return lang_pack
    def set_language_directory(self, lang_dir: str):
        """언어팩 디렉토리 경로를 변경합니다. 기존 언어팩은 초기화됩니다."""
        self.lang_dir = lang_dir
        self.language_packs = {}  # 기존 언어팩 초기화
    def get_message(self, message_id, lang_pack=None):
        if lang_pack is None:
            lang_pack = self.get_language_pack(self.language)

        category, code = message_id.split("_")  # 예: "MES_201" -> "MES", "201"
        message_key = self.messages["messages"][category][code]  # 메시지 키 가져오기

        try:
            return lang_pack[message_key]  # 언어팩에서 메시지 가져오기
        except KeyError:
            return f"Unknown message ID: {message_id}"
    def get_ui_text(self, ui_id, lang_pack=None):  # UI 텍스트 가져오는 메서드 추가
        if lang_pack is None:
            lang_pack = self.get_language_pack(self.language)

        try:
            return lang_pack[self.messages["id_mapping"]["ui"][ui_id]]  # 언어팩에서 UI 텍스트 가져오기
        except KeyError:
            return f"Unknown UI ID: {ui_id}"

class UIConfig:
    def __init__(self, config):
        self.language = config.get("language", "ko")
        self.id_mapping = config["id_mapping"]
        self.settings = config["settings"]
class Config:
    def __init__(self, config_file):
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        self.rabbitmq = RabbitMQConfig(config["rabbitmq"])
        self.file_paths = FilePathConfig(config["file_paths"])
        self.ui = UIConfig(config["ui"])

        self.managers = {}  # 매니저 정보를 담을 딕셔너리
        for manager_name, manager_config in config["managers"].items():
            self.managers[manager_name] = manager_config  # managers.json의 각 매니저 설정 저장
        self.messages = config["messages"]  # messages.json 내용 저장
        self.language = LanguageConfig(config)  # LanguageConfig 객체 생성 시 config 전달
        self.queues = self._load_json("config/queues.json") # queues.json 파일 경로 직접 지정
    def _load_json(self, file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

config = Config("config/development.json")
# SystemManager에서 매니저 객체 생성 및 관리
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

            # 의존성 있는 매니저 인스턴스 가져오기
            dependencies_instances = [self.managers[dep] for dep in dependencies]  # 의존성 매니저가 아직 생성되지 않았을 수 있으므로 try-except 필요

            try:
                # 매니저 클래스 동적 로딩
                module = __import__(module_path, fromlist=[class_name])
                manager_class = getattr(module, class_name)

                # 매니저 인스턴스 생성 및 저장
                self.managers[manager_name] = manager_class(*dependencies_instances, **kwargs) # 의존성 주입
            except ImportError as e:
                logging.error(f"Error importing module {module_path}: {e}")
            except AttributeError as e:
                logging.error(f"Error getting class {class_name} from module {module_path}: {e}")
            except Exception as e:
                logging.error(f"An unexpected error occurred during manager initialization: {e}")

    def get_manager(self, manager_name):
        return self.managers.get(manager_name) # 매니저가 없을 경우 None 반환
class ConfigManager:
    def __init__(self, config_file_path: str):
        self.config_file_path = config_file_path
        self.config_data = self._load_config_file()

    def _load_config_file(self) -> dict:
        """설정 파일을 로드하고 JSON 데이터를 파싱합니다."""
        try:
            with open(self.config_file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"설정 파일 '{self.config_file_path}'을 찾을 수 없습니다.")
        except json.JSONDecodeError:
            raise json.JSONDecodeError(f"설정 파일 '{self.config_file_path}'의 JSON 형식이 올바르지 않습니다.")

    def get(self, key: str, default=None):
        """설정 값을 반환합니다. key가 없으면 default 값을 반환합니다."""
        return self.config_data.get(key, default)

    def validate(self, key: str, validator: callable, message: str):
        """설정 값의 유효성을 검증합니다. validator는 검증 함수이고, message는 에러 메시지입니다."""
        value = self.get(key)
        if not validator(value):
            raise ValueError(message)
# RabbitMQ 큐 이름
QUEUE_NAMES = {
    "ocr_requests": "dev_ocr_requests",
    "ocr_results": "dev_ocr_results",
    "prediction_requests": "dev_prediction_requests",
    "prediction_results": "dev_prediction_results",
    "events": "dev_events",
    "ui_feedback_requests": "dev_ui_feedback_requests"
}

# 데이터베이스 연결
DATABASE_URL = "dev_database_url"

# 파일 처리 설정
FILE_SETTINGS = {
    "default_report_filename": "report.txt",
    "default_excel_filename": "documents.xlsx",
    "valid_file_extensions": {'.pdf', '.docx', '.xlsx', '.txt', '.csv', '.png', '.jpg', '.jpeg'},
    "max_file_size": 10 * 1024 * 1024  # 10MB
}

# 언어팩 디렉토리 경로
LANG_DIR = "config/language"
lang_packs = config.language.lang_packs

default_lang_pack = config.language.load_language_pack("ko")

# 언어 설정
language = config.ui.get("language", "ko")
selected_lang_pack = lang_packs.get(language, default_lang_pack)

# ID 맵핑
id_mapping = config.ui["id_mapping"]

# 전략 패턴을 위한 인터페이스 정의
class OCREngine:
    def perform_ocr(self, image: Any) -> str:
        raise NotImplementedError

class TesseractOCR(OCREngine):
    def perform_ocr(self, image: Any) -> str:
        import pytesseract
        return pytesseract.image_to_string(image)

class CloudVisionOCR(OCREngine):
    def perform_ocr(self, image: Any) -> str:
        # Cloud Vision API 호출 로직
        pass

class AIModel:
    def predict(self, data: Any) -> Any:
        raise NotImplementedError

class ErrorHandler:
    def handle_error(system_manager, category, code, exception, error_type):
        error_message = config.language.get_message(category, code)  # config.language.get_message() 호출
        system_manager.handle_error(error_message, error_type)  # system_manager의 에러 처리 함수 호출 (추가 필요)
        logging.exception(error_message)

def send_message_to_queue(system_manager, queue_name, message):
    try:
        queue_config = config.queues[queue_name]  # config.queues에서 큐 설정 정보 가져오기
        # 메시지를 큐에 전송하는 로직 추가 (queue_config 사용)
    except KeyError:
        handle_error(system_manager, "error", "511", None, "RabbitMQ 설정 오류")
        raise
    except Exception as e:
        handle_error(system_manager, "error", "511", e, "RabbitMQ 오류")
        raise

class OCRProcessor:
    def __init__(self, ai_event_manager, error_handler, settings_manager):
        self.ai_event_manager = ai_event_manager
        self.error_handler = error_handler
        self.settings_manager = settings_manager

    def process_ocr(self, data):  # 통합된 메서드
        file_path = data.get("file_path")
        ocr_engine_type = self.settings_manager.ui["settings"].get("ocr_engine", "tesseract")
        ocr_engine = OCREngineFactory.create_engine(ocr_engine_type)
        extracted_text = ocr_engine.perform_ocr(file_path)

class ClassificationModel(AIModel):
    def predict(self, data: Any) -> Any:
        # 분류 모델 예측 로직
        pass

class ObjectDetectionModel(AIModel):
    def predict(self, data: Any) -> Any:
        # 객체 탐지 모델 예측 로직
        pass

# 팩토리 패턴을 위한 팩토리 클래스 정의
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
        self.queues = queues  # queues 저장

    def handle_ocr_event(self, file_path, extracted_text):
        logging.info("Handling OCR completion event.")
        prediction_request = {
            "type": "PREDICT_DOCUMENT_TYPE",
            "data": {"text": extracted_text, "file_path": file_path},
            "reply_to": self.queues["events_queue"]  # queues 사용, "events" -> "events_queue"로 변경
        }
        send_message_to_queue(self.system_manager, self.queues["prediction_requests"], prediction_request)  # queues 사용
        self.prediction_event_handler.handle_prediction_requested(file_path) # 예측 요청 이벤트 발생

class PredictionEventHandler:
    def __init__(self, ai_data_manager, error_handler):
        self.ai_data_manager = ai_data_manager
        self.error_handler = error_handler

    def handle_prediction_result(self, file_path, document_type):
        """예측 결과를 처리하고 관련 이벤트를 저장합니다."""
        try:
            self._save_prediction_completed_event(file_path, document_type)
            # 추가적인 예측 결과 처리 로직 (예: 다음 단계 작업 실행, 사용자에게 알림 등)
            self._trigger_next_step(file_path, document_type)  # 예시: 다음 단계 작업 트리거
        except Exception as e:
            self.error_handler.handle_error(  # ErrorHandler를 통해 에러 처리
                None, "prediction_error", "500", e, "예측 결과 처리 중 오류 발생"  # 적절한 에러 카테고리, 코드, 메시지 사용
            )

    def handle_prediction_requested(self, file_path):
        """예측 요청에 대한 처리를 담당합니다."""
        # 필요한 경우 예측 요청 관련 로직 추가 (예: 큐에 메시지 전송, 상태 업데이트 등)
        pass

    def _save_prediction_completed_event(self, file_path, document_type):
        """예측 완료 이벤트를 저장합니다."""
        event_data = {"file_path": file_path, "document_type": document_type}
        save_event_data(self.ai_data_manager, "PREDICTION_COMPLETED", event_data)  # save_event_data 함수 사용

    def _trigger_next_step(self, file_path, document_type):
        """다음 단계 작업을 트리거합니다 (예시)."""
        # 다음 단계 작업에 필요한 정보 (예: document_type)를 기반으로
        # 적절한 작업을 실행하거나, 큐에 메시지를 보내는 등의 로직 구현
        # 예시:
        # if document_type == "type_A":
        #     # type_A에 대한 다음 작업 실행
        # elif document_type == "type_B":
        #     # type_B에 대한 다음 작업 실행
        pass  # 다음 단계 작업 로직 구현

# 설정 파일에서 전략 선택
ocr_engine_type = config.ui["settings"].get("ocr_engine", "tesseract")
ai_model_type = config.ui["settings"].get("ai_model", "classification")

# 팩토리를 사용하여 객체 생성
ocr_engine = OCREngineFactory.create_engine(ocr_engine_type)
ai_model = AIModelFactory.create_model(ai_model_type)
def save_event_data(ai_data_manager, event_type, additional_data=None):
    logging.info(f"Saving event data for {event_type}.")
    event_data = {
        "event_type": event_type,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "additional_data": additional_data or {}
    }
    if ai_data_manager is None:  # ai_data_manager가 None인 경우 예외 발생
        raise ValueError("ai_data_manager is not initialized.")
    ai_data_manager.save_feedback(event_data)
    logging.info(f"Event data saved: {event_data}")

class AIEventManager:
    def __init__(self, system_manager, settings_manager, model_manager, ai_data_manager, error_handler, queues):
        self.system_manager = system_manager
        self.settings_manager = settings_manager
        self.model_manager = model_manager
        self.ai_data_manager = ai_data_manager
        self.error_handler = error_handler
        self.queues = queues

        self.ocr_processor = OCRProcessor(self, error_handler, settings_manager)
        self.prediction_event_handler = PredictionEventHandler(ai_data_manager, error_handler)
        self.ocr_event_handler = OCREventHandler(system_manager, error_handler, self.prediction_event_handler, queues)
        self.feedback_event_handler = FeedbackEventHandler(ai_data_manager, error_handler)
        self.training_event_handler = TrainingEventHandler(system_manager, model_manager, ai_data_manager, error_handler, queues)
        self.message_handler = MessageHandler(self.training_event_handler, error_handler)  # TrainingEventHandler 전달

    def handle_message(self, ch, method, properties, body):
        self.message_handler.handle_message(ch, method, properties, body)
    def handle_ocr_event(self, file_path, extracted_text):
        self.ocr_event_handler.handle_ocr_event(file_path, extracted_text)
    def handle_prediction_result(self, file_path, document_type):
        self.prediction_event_handler.handle_prediction_result(file_path, document_type)
    def handle_training_event(self, model_path=None, training_metrics=None):
        self.training_event_handler.handle_training_event(model_path, training_metrics)
    def handle_save_feedback(self, file_path, doc_type):
        self.feedback_event_handler.handle_save_feedback(file_path, doc_type)
    def handle_request_user_feedback(self, file_path):
        self.feedback_event_handler.handle_request_user_feedback(file_path)
    def request_feedback(self, original_message: Any, error_reason: str):
        self.feedback_event_handler.request_feedback(original_message, error_reason)