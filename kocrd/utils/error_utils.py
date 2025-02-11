# kocrd\utils\error_utils.py
import logging
from kocrd import config

def handle_error(system_manager, category, code, exception, error_type, message=None):
    error_message = config.language.get_message(f"{category}_{code}") # config.get() 대신 config.language.get_message() 사용
    if message:
        error_message += f" - {message}" # 추가 메시지 포함
    if exception:
        logging.exception(error_message) # exception 정보 로깅
    else:
        logging.error(error_message) # 일반 에러 메시지 로깅
    if system_manager:
        system_manager.handle_error(error_message, error_type)  # system_manager 에러 처리 함수 호출
