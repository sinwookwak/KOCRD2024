# kocrd\utils\error_utils.py
import logging

def handle_error(logger, error_type, error_code, exception, message):
    logger.error(f"[{error_type} {error_code}] {message}: {exception}")
    # 필요한 추가 처리 (예: 데이터베이스에 에러 정보 저장, 사용자에게 메시지 전송 등)