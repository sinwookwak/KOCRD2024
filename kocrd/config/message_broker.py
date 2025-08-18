# file_name: kocrd/managers/message_broker.py

import logging
from typing import Callable, Dict, Any, List, Optional, Union
import functools

# config 모듈에서 필요한 AppConfig, text_manager, SystemConstants 임포트 (경로에 따라 수정될 수 있음)
from kocrd.config.config import text_manager
from kocrd.config.system_constants import SystemConstants
from kocrd.window.event_window import (
    AlertDialog,
    WarningDialog,
    ErrorDialog,
    QuestionDialog,
    ConfirmDeleteDialog
)

# 이벤트 핸들러를 저장할 딕셔너리
_event_handlers: Dict[str, List[Callable[..., Any]]] = {}

def subscribe(event_type: str):
    """
    특정 이벤트 유형에 대한 핸들러를 등록하는 데코레이터.
    데코레이터는 함수를 등록하고, 함수가 호출될 때 해당 이벤트를 발행할 수 있도록 준비합니다.
    """
    def decorator(func: Callable[..., Any]):
        if event_type not in _event_handlers:
            _event_handlers[event_type] = []
        _event_handlers[event_type].append(func)
        logging.debug(f"Registered handler '{func.__name__}' for event type '{event_type}'")
        return func
    return decorator

def publish(event_type: str, **kwargs: Any):
    """
    특정 이벤트 유형에 대한 메시지를 발행합니다.
    등록된 모든 핸들러를 호출합니다.
    """
    if event_type not in _event_handlers:
        logging.warning(text_manager.get_warning_text("416", event_type=event_type)) # "No handlers registered for event type '{event_type}'."
        return

    for handler in _event_handlers[event_type]:
        try:
            logging.debug(f"Publishing event '{event_type}' to handler '{handler.__name__}' with args: {kwargs}")
            handler(**kwargs)
        except Exception as e:
            logging.error(text_manager.get_error_text("543", handler_name=handler.__name__, event_type=event_type, error=e))
            # 오류 발생 시 시스템 오류 메시지 표시 (재귀 호출 방지)
            _display_internal_error_message(f"Error in event handler '{handler.__name__}' for event '{event_type}': {e}")

# 내부적으로 EventWindow를 호출하는 함수 (SystemManager 의존성 제거)
def _display_internal_message_box(
    message_type: str, title_key: str, message_key: str,
    detail_info: Optional[str] = None,
    buttons_type: Optional[str] = None,
    delete_target: Optional[str] = None,
    show_do_not_show_again: bool = False,
    parent_window: Optional[Any] = None # QWidget을 받아야 함
) -> str:
    """
    이벤트 브로커 내부에서 직접 메시지 박스를 표시합니다.
    SystemManager의존성을 제거하고, UI 관련 처리를 MessageBroker가 담당하도록 합니다.
    """
    dialog_class = None
    if message_type == SystemConstants.EventTypes.ALERT:
        dialog_class = AlertDialog
    elif message_type == SystemConstants.EventTypes.WARNING:
        dialog_class = WarningDialog
    elif message_type == SystemConstants.EventTypes.ERROR:
        dialog_class = ErrorDialog
    elif message_type == SystemConstants.EventTypes.QUESTION:
        dialog_class = QuestionDialog
    elif message_type == SystemConstants.EventTypes.CONFIRM_DELETE:
        dialog_class = ConfirmDeleteDialog
    else:
        logging.warning(text_manager.get_warning_text("415", message_type=message_type))
        dialog_class = AlertDialog

    if dialog_class == ConfirmDeleteDialog:
        result = dialog_class.show_dialog(
            parent=parent_window,
            message_key=message_key,
            delete_target=delete_target if delete_target else text_manager.get_general_text("265") # 265: "selected item",
            detail_info=detail_info,
            show_do_not_show_again=show_do_not_show_again
        )
    elif dialog_class == QuestionDialog:
        result = dialog_class.show_dialog(
            parent=parent_window,
            title_key=title_key,
            message_key=message_key,
            detail_info=detail_info,
            buttons_type=buttons_type,
            show_do_not_show_again=show_do_not_show_again
        )
    else:
        result = dialog_class.show_dialog(
            parent=parent_window,
            title_key=title_key,
            message_key=message_key,
            detail_info=detail_info,
            show_do_not_show_again=show_do_not_show_again
        )
    return result

def _display_internal_error_message(message: str):
    """
    메시지 브로커 내부에서 발생하는 치명적인 오류를 표시하기 위한 비상용 메시지 박스.
    TextManager와 EventWindow가 정상 동작하지 않을 경우를 대비하여 직접 표시.
    """
    try:
        # text_manager와 event_window가 정상 작동할 경우
        _display_internal_message_box(
            SystemConstants.EventTypes.ERROR,
            "error_title", # text_manager 키
            "544",         # text_manager 키: "Internal system error occurred."
            detail_info=message
        )
    except Exception:
        # text_manager나 event_window마저 문제가 있을 경우, 최소한의 메시지 박스
        # (이 경우 Qt QApplication 인스턴스가 존재해야 함)
        from PyQt5.QtWidgets import QMessageBox
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle("Critical System Error")
        msg_box.setText("A critical internal error occurred that prevents normal operation. Please check logs.")
        msg_box.setInformativeText(message)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()


# --- 공개 API 정의 ---

# 함수를 통해 메시지 박스를 호출하도록 래핑
def display_alert(parent_window: Any, message_key: str, title_key: str = "alert_title", detail_info: Optional[str] = None, show_do_not_show_again: bool = False) -> str:
    """사용자에게 정보성 알림 메시지를 표시합니다."""
    return _display_internal_message_box(
        SystemConstants.EventTypes.ALERT, title_key, message_key, detail_info,
        parent_window=parent_window, show_do_not_show_again=show_do_not_show_again
    )

def display_warning(parent_window: Any, message_key: str, title_key: str = "warning_title", detail_info: Optional[str] = None, show_do_not_show_again: bool = False) -> str:
    """사용자에게 경고 메시지를 표시합니다."""
    return _display_internal_message_box(
        SystemConstants.EventTypes.WARNING, title_key, message_key, detail_info,
        parent_window=parent_window, show_do_not_show_again=show_do_not_show_again
    )

def display_error(parent_window: Any, message_key: str, title_key: str = "error_title", detail_info: Optional[str] = None, show_do_not_show_again: bool = False) -> str:
    """사용자에게 오류 메시지를 표시합니다."""
    return _display_internal_message_box(
        SystemConstants.EventTypes.ERROR, title_key, message_key, detail_info,
        parent_window=parent_window, show_do_not_show_again=show_do_not_show_again
    )

def ask_question(parent_window: Any, message_key: str, title_key: str = "question_title", detail_info: Optional[str] = None, buttons_type: str = "yes_no", show_do_not_show_again: bool = False) -> str:
    """사용자에게 질문을 하고 응답을 받습니다."""
    return _display_internal_message_box(
        SystemConstants.EventTypes.QUESTION, title_key, message_key, detail_info, buttons_type,
        parent_window=parent_window, show_do_not_show_again=show_do_not_show_again
    )

def confirm_delete(parent_window: Any, delete_target: str, message_key: str = "confirm_delete_message", detail_info: Optional[str] = None, show_do_not_show_again: bool = False) -> str:
    """삭제 여부를 사용자에게 확인합니다."""
    return _display_internal_message_box(
        SystemConstants.EventTypes.CONFIRM_DELETE, "confirm_delete_title", message_key, detail_info,
        delete_target=delete_target, parent_window=parent_window, show_do_not_show_again=show_do_not_show_again
    )

# --- 시스템 이벤트 발행 함수 (내부 로직을 위한) ---
# 이 함수들은 주로 시스템 내부에서 특정 이벤트를 다른 모듈에 알릴 때 사용됩니다.
# 예: process_completed, file_saved, data_updated 등

def publish_system_event(event_type: str, **kwargs: Any):
    """내부 시스템 이벤트를 발행합니다."""
    publish(event_type, **kwargs)

# --- 시스템 이벤트 구독 예시 (다른 모듈에서 호출될 함수에 데코레이터를 붙임) ---
# 예시: kocrd/managers/document/document_manager.py
# @subscribe("document_processed")
# def handle_document_processed(document_id: str, status: str):
#     logging.info(f"Document {document_id} processed with status: {status}")

# 예시: kocrd/managers/database_manager.py
# @subscribe("data_saved")
# def handle_data_saved(data_type: str, item_id: str):
#     logging.info(f"Data '{data_type}' with ID '{item_id}' successfully saved.")