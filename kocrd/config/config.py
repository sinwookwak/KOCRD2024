import json
import logging
from datetime import datetime
from typing import Dict, Any
import os

class ConfigLoader:
    @staticmethod
    def load_config(file_path: str) -> Dict[str, Any]:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

class RabbitMQConfig:
    def __init__(self, config: Dict[str, Any]):
        self.host = config["host"]
        self.port = config["port"]
        self.user = config["user"]
        self.password = config["password"]
        self.virtual_host = config["virtual_host"]

class FilePathConfig:
    def __init__(self, config: Dict[str, Any]):
        self.models = config["models"]
        self.document_embedding = config["document_embedding"]
        self.document_types = config["document_types"]
        self.temp_files = config["temp_files"]

class LanguageConfig:
    def __init__(self, lang_dir: str):
        self.lang_packs = {}
        for filename in os.listdir(lang_dir):
            if filename.endswith(".json"):
                lang_code = filename[:-5]
                lang_path = os.path.join(lang_dir, filename)
                try:
                    with open(lang_path, "r", encoding="utf-8") as f:
                        lang_pack = json.load(f)
                        if "language" not in lang_pack:
                            raise ValueError(f"Language pack '{filename}' must have 'language' attribute.")
                        self.lang_packs[lang_code] = lang_pack
                except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
                    print(f"Error loading language pack '{filename}': {e}")

    def load_language_pack(self, lang_code: str) -> Dict[str, Any]:
        lang_path = os.path.join(LANG_DIR, f"{lang_code}.json")
        try:
            with open(lang_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading default language pack '{lang_code}': {e}")
            return {}

class Config:
    def __init__(self):
        self.rabbitmq = RabbitMQConfig(ConfigLoader.load_config("config/rabbitmq.json"))
        self.file_paths = FilePathConfig(ConfigLoader.load_config("config/file_paths.json"))
        self.language = LanguageConfig("config/language")
        self.messages = ConfigLoader.load_config("config/messages.json")
        self.queues = ConfigLoader.load_config("config/queues.json")
        self.managers = ConfigLoader.load_config("config/managers.json")
        self.ui = ConfigLoader.load_config("config/ui.json")

config = Config()

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

# 메시지 출력 함수
def get_message(lang_pack: Dict[str, str], message_id: str, default_lang_pack: Dict[str, str] = None) -> str:
    message = lang_pack.get(message_id) or default_lang_pack.get(message_id, f"Unknown message ID: {message_id}")
    return message

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

# 설정 파일에서 전략 선택
ocr_engine_type = config.ui["settings"].get("ocr_engine", "tesseract")
ai_model_type = config.ui["settings"].get("ai_model", "classification")

# 팩토리를 사용하여 객체 생성
ocr_engine = OCREngineFactory.create_engine(ocr_engine_type)
ai_model = AIModelFactory.create_model(ai_model_type)

# 예제 사용
def process_image(image_path: str):
    from PIL import Image
    image = Image.open(image_path)
    ocr_result = ocr_engine.perform_ocr(image)
    logging.info(f"OCR Result: {ocr_result}")
    prediction = ai_model.predict(ocr_result)
    logging.info(f"AI Prediction: {prediction}")

# ID 맵핑 예제
def get_message_by_id(message_id: str) -> str:
    return id_mapping.get(message_id, "Unknown ID")

# 예제 실행
if __name__ == "__main__":
    process_image("path/to/image.png")
    print(get_message_by_id("601"))

def get_message(category, code):
    return config.managers["messages"][category][code]

def handle_error(system_manager, category, code, exception, error_type):
    """에러 처리 및 로깅."""
    error_message = get_message(category, code).format(e=exception)
    system_manager.handle_error(error_message, error_type)
    logging.exception(error_message)

def send_message_to_queue(system_manager, queue_name, message):
    """메시지를 지정된 큐에 전송."""
    try:
        queue_config = config.managers["queues"][queue_name]
        # 메시지를 큐에 전송하는 로직 추가
    except Exception as e:
        handle_error(system_manager, "error", "511", e, "RabbitMQ 오류")
        raise

def process_message(ai_event_manager, message):
    """메시지 처리 로직."""
    message_type = message.get("type")

    if message_type == config.managers["message_types"]["101"]:
        perform_ocr(ai_event_manager, message["data"])
    elif message_type == config.managers["message_types"]["102"]:
        process_ocr_result(ai_event_manager, message["data"])
    else:
        logging.warning(f"알 수 없는 메시지 타입: {message_type}")

def handle_message(ai_event_manager, ch, method, properties, body):
    """AIEventManager의 handle_message 메서드 호출."""
    try:
        message = json.loads(body)
        process_message(ai_event_manager, message)
    except json.JSONDecodeError as e:
        handle_error(ai_event_manager.system_manager, "error", "512", e, "JSON 파싱 오류")
    except Exception as e:
        handle_error(ai_event_manager.system_manager, "error", "513", e, "OCR 메시지 처리 중 오류")

def perform_ocr(ai_event_manager, data):
    """OCR 작업 수행."""
    file_path = data.get("file_path")
    # OCR 수행 로직 추가
    extracted_text = "dummy_text"  # 예시용 더미 텍스트
    handle_ocr_event(ai_event_manager, file_path, extracted_text)

def process_ocr_result(ai_event_manager, data):
    """OCR 결과 처리."""
    file_path = data.get("file_path")
    extracted_text = data.get("extracted_text")
    handle_ocr_event(ai_event_manager, file_path, extracted_text)

def handle_ocr_event(ai_event_manager, file_path, extracted_text):
    """OCR 작업 후 이벤트 처리. 예측 요청 전송."""
    logging.info("Handling OCR completion event.")
    prediction_request = {
        "type": "PREDICT_DOCUMENT_TYPE",
        "data": {"text": extracted_text, "file_path": file_path},
        "reply_to": ai_event_manager.settings_manager.get_queue_name("events")
    }
    send_message_to_queue(ai_event_manager.system_manager, ai_event_manager.settings_manager.get_queue_name("prediction_requests"), prediction_request)

def handle_prediction_result(ai_event_manager, file_path, document_type):
    """예측 결과 처리 및 이벤트 데이터 저장."""
    save_event_data(ai_event_manager, "PREDICTION_COMPLETED", {"file_path": file_path, "document_type": document_type})

def handle_training_event(ai_event_manager, model_path=None, training_metrics=None):
    """AI 학습 후 이벤트 처리."""
    logging.info("Handling AI training completion event.")
    if training_metrics:
        save_event_data(ai_event_manager, "TRAINING_COMPLETED", training_metrics)
    if model_path:
        try:
            ai_event_manager.model_manager.apply_trained_model(model_path)
        except Exception as e:
            handle_error(ai_event_manager.system_manager, "error", "505", e, "모델 적용 오류")

    ai_event_manager.system_manager.start_document_analysis()
    logging.info("AI training event successfully handled.")

def handle_save_feedback(ai_event_manager, file_path, doc_type):
    """사용자 피드백 저장."""
    ai_event_manager.ai_data_manager.save_feedback({
        "file_path": file_path,
        "doc_type": doc_type,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

def handle_request_user_feedback(ai_event_manager, file_path):
    """사용자 피드백 요청 이벤트 처리."""
    logging.info("Handling user feedback request event.")
    doc_type = ai_event_manager.ai_data_manager.request_user_feedback(file_path)
    if doc_type:
        save_event_data(ai_event_manager, "USER_FEEDBACK_RECEIVED", {"file_path": file_path, "doc_type": doc_type})
    else:
        logging.warning(f"User feedback for file {file_path} was not received.")

def save_event_data(ai_event_manager, event_type, additional_data=None):
    """이벤트 데이터를 데이터베이스에 저장."""
    logging.info(f"Saving event data for {event_type}.")
    event_data = {
        "event_type": event_type,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "additional_data": additional_data or {}
    }
    ai_event_manager.ai_data_manager.save_feedback(event_data)
    logging.info(f"Event data saved: {event_data}")

def request_feedback(ai_event_manager, original_message: Any, error_reason: str):
    """사용자에게 피드백을 요청하는 메시지를 생성하고 전송."""
    feedback_message = {
        "type": "REQUEST_FEEDBACK",
        "original_message": original_message,
        "error_reason": error_reason,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    send_message_to_queue(ai_event_manager.system_manager, "feedback_queue", feedback_message)
    logging.info(f"피드백 요청 메시지 전송: {feedback_message}")
