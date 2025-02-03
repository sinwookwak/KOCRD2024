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
