import json
import logging
from datetime import datetime
from typing import Dict, Any
import os

# RabbitMQ 설정
RABBITMQ_HOST = "localhost"  # RabbitMQ 서버 주소
RABBITMQ_PORT = 5672       # RabbitMQ 서버 포트
RABBITMQ_USER = "guest"     # RabbitMQ 사용자 이름
RABBITMQ_PASSWORD = "guest" # RabbitMQ 비밀번호
RABBITMQ_VIRTUAL_HOST = "/" # RabbitMQ Virtual Host (기본값 "/")

# RabbitMQ 큐 이름
OCR_REQUESTS_QUEUE = "dev_ocr_requests"        # OCR 요청 큐
OCR_RESULTS_QUEUE = "dev_ocr_results"          # OCR 결과 큐
PREDICTION_REQUESTS_QUEUE = "dev_prediction_requests" # 예측 요청 큐
PREDICTION_RESULTS_QUEUE = "dev_prediction_results" # 예측 결과 큐
EVENTS_QUEUE = "dev_events"                  # 이벤트 큐
UI_FEEDBACK_REQUESTS_QUEUE = "dev_ui_feedback_requests" # UI 피드백 요청 큐

# 파일 경로
MODELS_PATH = "F:/AI-M2/models/dev_models"              # 모델 저장 경로
DOCUMENT_EMBEDDING_PATH = "F:/AI-M2/model/dev_document_embedding.json" # 문서 임베딩 파일 경로
DOCUMENT_TYPES_PATH = "F:/AI-M2/model/dev_document_types.json"     # 문서 타입 정의 파일 경로
TEMP_FILES_DIR = "F:/AI-M2/temp/dev_temp_files"          # 임시 파일 저장 경로

# 데이터베이스 연결
DATABASE_URL = "dev_database_url"  # 개발용 데이터베이스 URL

# 파일 처리 설정
DEFAULT_REPORT_FILENAME = "report.txt"      # 기본 보고서 파일 이름
DEFAULT_EXCEL_FILENAME = "documents.xlsx"  # 기본 엑셀 파일 이름
VALID_FILE_EXTENSIONS = {'.pdf', '.docx', '.xlsx', '.txt', '.csv', '.png', '.jpg', '.jpeg'} # 허용된 파일 확장자
MAX_FILE_SIZE = 10 * 1024 * 1024          # 최대 파일 크기 (10MB)

# 언어팩 디렉토리 경로
lang_dir = "config/language"

# 언어팩 정보 저장 딕셔너리
lang_packs = {}

# 언어팩 디렉토리 순회
for filename in os.listdir(lang_dir):
    if filename.endswith(".json"):
        lang_code = filename[:-5]  # 확장자 제거
        lang_path = os.path.join(lang_dir, filename)

        try:
            with open(lang_path, "r", encoding="utf-8") as f:  # 파일 인코딩 지정
                lang_pack = json.load(f)

                # 언어팩 내부 language 속성 확인
                if "language" not in lang_pack:
                    raise ValueError(f"Language pack '{filename}' must have 'language' attribute.")

                lang_packs[lang_code] = lang_pack
        except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
            print(f"Error loading language pack '{filename}': {e}")

# 기본 언어팩 (한국어) 로드
def load_language_pack(lang_code):
    lang_path = os.path.join(lang_dir, f"{lang_code}.json")
    try:
        with open(lang_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading default language pack '{lang_code}': {e}")
        return {}

default_lang_pack = load_language_pack("ko")

# 설정 파일 로드
with open("config/development.json", "r", encoding="utf-8") as f:
    config = json.load(f)

# 언어 설정
language = config.get("language", "ko")  # 기본값 한국어

# 언어팩 선택
if language in lang_packs:
    selected_lang_pack = lang_packs[language]
else:
    print(f"Warning: Language pack '{language}' not found. Using default language 'ko'.")
    selected_lang_pack = default_lang_pack

# 메시지 출력 함수 (예외 처리 및 한국어 출력 기능 추가)
def get_message(lang_pack, message_id, default_lang_pack=None):
    """메시지 텍스트 반환 (누락 시 한국어 출력)"""
    message = lang_pack.get(message_id)
    if message:
        return message
    elif default_lang_pack and message_id in default_lang_pack:
        return default_lang_pack[message_id]
    else:
        return f"Unknown message ID: {message_id}"

# 메시지 사용 예시
message = get_message(selected_lang_pack, "MSG_001", default_lang_pack)  # 한국어 메시지
print(message)

message = get_message(selected_lang_pack, "MSG_999", default_lang_pack)  # 존재하지 않는 메시지 ID
print(message)  # 한국어 메시지 또는 "Unknown message ID" 출력

# ID 맵핑
id_mapping = config["id_mapping"]

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
ocr_engine_type = config["settings"].get("ocr_engine", "tesseract")
ai_model_type = config["settings"].get("ai_model", "classification")

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

# managers_config.json 파일 로드
with open('managers/managers_config.json', 'r', encoding='utf-8') as f:
    managers_config = json.load(f)

def get_message(category, code):
    return managers_config["messages"][category][code]

def handle_error(system_manager, category, code, exception, error_type):
    """에러 처리 및 로깅."""
    error_message = get_message("error", code).format(e=exception)
    system_manager.handle_error(error_message, error_type)
    logging.exception(error_message)

def send_message_to_queue(system_manager, queue_name, message):
    """메시지를 지정된 큐에 전송."""
    try:
        queue_config = managers_config["queues"][queue_name]
        # 메시지를 큐에 전송하는 로직 추가
    except Exception as e:
        handle_error(system_manager, "error", "511", e, "RabbitMQ 오류")
        raise

def handle_message(ai_event_manager, ch, method, properties, body):
    """AIEventManager의 handle_message 메서드 호출."""
    try:
        message = json.loads(body)
        message_type = message.get("type")

        if message_type == managers_config["message_types"]["101"]:
            perform_ocr(ai_event_manager, message["data"])
        elif message_type == managers_config["message_types"]["102"]:
            process_ocr_result(ai_event_manager, message["data"])
        else:
            logging.warning(f"알 수 없는 메시지 타입: {message_type}")
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
    ai_event_manager.ai_data_manager.save_feedback({"file_path": file_path, "doc_type": doc_type, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})

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

# config/development.py
# 개발 환경 설정 파일
{
  "constants": {
    "MODEL_PATH_KEY": "model_path",
    "TESSERACT_CMD_KEY": "tesseract_cmd",
    "TESSDATA_DIR_KEY": "tessdata_dir",
    "MANAGERS_KEY": "managers",
    "AI_MODEL_KEY": "ai_model",
    "KWARGS_KEY": "kwargs"
  },
  "managers": {
    "database": {
      "class": "DatabaseManager",
      "module": "kocrd.managers.database_manager",
      "kwargs": {
        "db_path": "DATABASE_PATH",
        "backup_path": "DATABASE_BACKUP_PATH"
      }
    },
    "temp_file": {
      "class": "TempFileManager",
      "module": "kocrd.managers.temp_file_manager",
      "dependencies": [],
      "inject_settings": true
    },
    "ocr": {
      "class": "OCRManager",
      "module": "kocrd.managers.ocr.ocr_manager",
      "dependencies": [],
      "kwargs": {
        "tesseract_cmd": "TESSERACT_CMD",
        "tessdata_dir": "TESSDATA_DIR"
      },
      "inject_settings": true,
      "inject_main_window": true
    },
    "menubar": {
      "class": "MenubarManager",
      "module": "kocrd.managers.menubar_manager",
      "dependencies": [],
      "inject_system_manager": true
    },
    "ai_model": {
      "class": "AIModelManager",
      "module": "kocrd.managers.ai_managers.ai_model_manager",
      "kwargs": {
        "model_path": "MODELS_PATH",
        "model_type": "gpt2",
        "inject_settings": true
      }
    },
    "ai_data": {
      "class": "AIDataManager",
      "module": "kocrd.managers.ai_managers.ai_data_manager",
      "dependencies": ["database"]
    },
    "ai_prediction": {
      "class": "AIPredictionManager",
      "module": "kocrd.managers.ai_managers.ai_prediction_manager",
      "dependencies": ["ai_model", "ai_data", "database"],
      "inject_settings": true
    },
    "monitoring": {
      "class": "MonitoringManager",
      "module": "kocrd.managers.monitoring_manager",
      "dependencies": ["document", "ocr", "ai_prediction"]
    },
    "message_queue": {
      "class": "RabbitMQManager",
      "module": "kocrd.managers.rabbitmq_manager",
      "dependencies": []
    },
    "document": {
      "class": "DocumentManager",
      "module": "kocrd.managers.document.document_manager",
      "dependencies": ["ocr", "database", "message_queue"],
      "inject_main_window": true,
      "inject_system_manager": true
    },
    "ai_trainer": {
      "class": "AITrainer",
      "module": "kocrd.managers.ai_managers.ai_training_manager",
      "dependencies": ["ai_model", "ai_data", "message_queue", "database", "settings_manager"],
      "kwargs": {},
      "inject_settings": true
    },
    "settings_manager": {
      "class": "SettingsManager",
      "module": "kocrd.managers.settings_manager",
      "kwargs": {
        "config_file": "config/development.json"
      }
    },
    "document_processor": {
      "class": "DocumentProcessor",
      "module": "kocrd.managers.document.document_processor"
    },
    "analysis_manager": {
      "class": "AnalysisManager",
      "module": "kocrd.managers.analysis_manager"
    }
  },
  "uis": {
    "menubar": {
      "class": "MenubarUI",
      "module": "kocrd.ui.menubar_ui",
      "dependencies": [],
      "inject_system_manager": true
    },
    "document": {
      "class": "DocumentUI",
      "module": "kocrd.ui.document_ui",
      "dependencies": [],
      "inject_system_manager": true
    },
    "monitoring": {
      "class": "MonitoringUI",
      "module": "kocrd.ui.monitoring_ui",
      "dependencies": [],
      "inject_system_manager": true
    }
  },
  "settings": {
    "document_types_path": "path/to/document_types.json",
    "ai_model_path": "path/to/your/ai_model"
  },
  "queues": {
    "prediction_requests": "prediction_requests",
    "prediction_results": "prediction_results",
    "ui_feedback_requests": "ui_feedback_requests",
    "events": "events",
    "document_processing": "document_processing",
    "database_packaging": "database_packaging",
    "result": "result",
    "ai_training_queue": "ai_training_queue",
    "temp_file_queue": "temp_file_queue",
    "prediction_requests_queue": "prediction_requests_queue",
    "events_queue": "events_queue",
    "ocr_results": "ocr_results",
    "ocr_requests": "ocr_requests",
    "ai_result_handling": "ai_result_handling",
    "feedback_queue": "feedback_queue"
  }
}

settings = {
    "DEFAULT_REPORT_FILENAME": "report.txt",
    "DEFAULT_EXCEL_FILENAME": "report.xlsx",
    "VALID_FILE_EXTENSIONS": [".txt", ".pdf", ".png", ".jpg"],
    "MAX_FILE_SIZE": 10485760
}