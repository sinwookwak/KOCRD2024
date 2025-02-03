import json 
import logging

def get_message(category, code):
    with open("ai_config.json", "r", encoding="utf-8") as file:
        config = json.load(file)
    return config["messages"][category][code]

def handle_error(system_manager, category, code, exception, error_type):
    """에러 처리 및 로깅."""
    error_message = get_message(category, code).format(e=exception)
    system_manager.handle_error(error_message, error_type)
    logging.exception(error_message)

def send_message_to_queue(system_manager, queue_name, message):
    """메시지를 지정된 큐에 전송."""
    try:
        queue_config = get_message("queues", queue_name)
        # 메시지를 큐에 전송하는 로직 추가
    except Exception as e:
        handle_error(system_manager, "error", "11", e, "RabbitMQ 오류")
        raise
