# kocrd\utils\error_utils.py
import logging
from kocrd.config.config import config

def handle_error(system_manager, category, code, exception, message=None):  # message default value 추가
    error_message_key = f"{category}_{code}"
    error_message = config.language.get_message(error_message_key)  # config.language 사용

    if message:  # message 추가
        error_message += f" - {message}"

    if exception:
        logging.exception(error_message)  # exception 정보 로깅
    else:
        logging.error(error_message)

    if system_manager:
        system_manager.handle_error(error_message, error_message_key)  # system_manager 에러 처리 함수 호출
