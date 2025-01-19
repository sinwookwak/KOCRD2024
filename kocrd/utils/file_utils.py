# file_utils.py
import shutil
import logging
import chardet
from typing import Dict, Optional, Any

def log_error(message: str, title: str = "오류") -> None:
    """오류 메시지를 로깅합니다."""
    logging.error(message)

def _show_message_box(message: str, title: str = "오류", icon: Any = None) -> None:
    """PyQt5 메시지 박스를 표시합니다. PyQt5가 설치된 경우에만 호출해야 합니다."""
    from PyQt5.QtWidgets import QMessageBox # PyQt5 임포트를 함수 내부로 이동
    if icon is None:
        icon = QMessageBox.Critical
    QMessageBox.critical(None, title, message)

def show_message_box_safe(message: str, title: str = "오류", icon: Any = None) -> None:
    """안전하게 메시지 박스를 표시합니다. PyQt5가 설치되어 있지 않으면 로깅합니다."""
    try:
        _show_message_box(message, title, icon)
    except ImportError:
        logging.warning("PyQt5가 설치되어 있지 않아 메시지 박스를 표시할 수 없습니다.")
        logging.error(message)

def detect_encoding(file_path: str) -> str:
    """파일의 인코딩을 감지합니다.

    Raises:
        FileNotFoundError: 파일을 찾을 수 없는 경우 발생합니다.
        OSError: 파일 읽기 중 오류가 발생한 경우 발생합니다.
    
    Returns:
        str: 감지된 인코딩 (감지 실패 시 'utf-8' 반환)
    """
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read()
        result = chardet.detect(raw_data)
        encoding = result.get('encoding')
        confidence = result.get('confidence', 0)
        if encoding is None:
            logging.warning(f"인코딩 감지 실패. 기본값 utf-8 사용. 파일 경로: {file_path}")
            return "utf-8"
        logging.info(f"Detected encoding: {encoding} (Confidence: {confidence})")
        return encoding
    except FileNotFoundError as e:
        log_error(f"파일을 찾을 수 없습니다: {file_path}", "파일 오류")
        raise
    except OSError as e:
        log_error(f"파일 읽기 오류: {e}", "파일 오류")
        raise

def copy_file(source_path: str, destination_path: str) -> str:
    """파일을 복사합니다.

    Raises:
        FileNotFoundError: 원본 파일을 찾을 수 없는 경우 발생합니다.
        OSError: 파일 복사 중 오류가 발생한 경우 발생합니다.
    
    Returns:
        str: 복사된 파일 경로
    """
    try:
        shutil.copy2(source_path, destination_path)
        logging.info(f"파일 복사 완료: {destination_path}")
        return destination_path
    except FileNotFoundError as e:
        log_error(f"원본 파일을 찾을 수 없습니다: {source_path}", "파일 오류")
        raise
    except OSError as e:
        log_error(f"파일 복사 오류: {e}", "파일 오류")
        raise