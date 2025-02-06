import json
import logging
from datetime import datetime

# managers_config.json 파일 로드
with open('managers/managers_config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

def get_message(category, code):
    return config["messages"][category][code]

def handle_error(system_manager, category, code, exception, error_type):
    """에러 처리 및 로깅."""
    error_message = get_message("error", code).format(e=exception)
    system_manager.handle_error(error_message, error_type)
    logging.exception(error_message)

def send_message_to_queue(system_manager, queue_name, message):
    """메시지를 지정된 큐에 전송."""
    try:
        queue_config = config["queues"][queue_name]
        # 메시지를 큐에 전송하는 로직 추가
    except Exception as e:
        handle_error(system_manager, "error", "511", e, "RabbitMQ 오류")
        raise

def handle_message(ai_event_manager, ch, method, properties, body):
    """AIEventManager의 handle_message 메서드 호출."""
    try:
        message = json.loads(body)
        message_type = message.get("type")

        if message_type == config["message_types"]["101"]:
            perform_ocr(ai_event_manager, message["data"])
        elif message_type == config["message_types"]["102"]:
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
