
# file_name: event_window.py
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QCheckBox, QMessageBox, QWidget
from PyQt5.QtCore import Qt
from typing import Optional, Dict, Any

# kocrd.config.config에서 text_manager 임포트
from kocrd.config.config import text_manager
# system_constants 모듈에서 필요한 상수 임포트
from kocrd.config.system_constants import SystemConstants

# --- 기본 메시지 창 클래스 ---
class BaseMessageWindow(QDialog):
    """모든 메시지 창의 기본 클래스."""
    def __init__(self, parent: QWidget = None,
                 title_key: str = "general_notification_title",
                 message_key: str = "general_notification_message",
                 detail_info: Optional[str] = None,
                 buttons_config: Dict[str, Any] = None):
        super().__init__(parent)
        self.setWindowTitle(text_manager.get_general_text(title_key))
        self.setModal(True) # 모달 창으로 설정
        # UISettings에서 기본 크기 가져오기
        self.setMinimumSize(SystemConstants.UISettings.DEFAULT_MESSAGE_WINDOW_WIDTH,
                            SystemConstants.UISettings.DEFAULT_MESSAGE_WINDOW_HEIGHT)
        self.return_value: Optional[str] = None

        self.main_layout = QVBoxLayout()
        self.message_label = QLabel(text_manager.get_general_text(message_key))
        self.main_layout.addWidget(self.message_label)

        if detail_info:
            self.detail_label = QLabel(f"<small>{detail_info}</small>")
            self.main_layout.addWidget(self.detail_label)

        self.checkbox_layout = QHBoxLayout()
        self.do_not_show_again_checkbox: Optional[QCheckBox] = None
        self.main_layout.addLayout(self.checkbox_layout)

        self.button_layout = QHBoxLayout()
        self.main_layout.addLayout(self.button_layout)

        self.setLayout(self.main_layout)

        self._setup_buttons(buttons_config)
        self._set_window_icon_and_style()

    def _setup_buttons(self, buttons_config: Optional[Dict[str, Any]]):
        """버튼을 설정합니다. buttons_config = {"OK": SystemConstants.EventResults.OK, ...}"""
        if buttons_config:
            for btn_text_key, result_value in buttons_config.items():
                # ButtonKeys에서 텍스트 가져오기
                button = QPushButton(text_manager.get_ui_text("buttons", SystemConstants.ButtonKeys.__dict__.get(btn_text_key, btn_text_key)))
                button.clicked.connect(lambda _, val=result_value: self._set_result_and_accept(val))
                self.button_layout.addWidget(button)
        else: # 기본 OK 버튼
            ok_button = QPushButton(text_manager.get_ui_text("buttons", SystemConstants.ButtonKeys.OK))
            ok_button.clicked.connect(lambda: self._set_result_and_accept(SystemConstants.EventResults.OK))
            self.button_layout.addWidget(ok_button)

    def _set_result_and_accept(self, result: str):
        self.return_value = result
        if self.do_not_show_again_checkbox and self.do_not_show_again_checkbox.isChecked():
            # 결과 값과 "다시 보지 않기" 상수를 쉼표로 연결
            self.return_value = f"{self.return_value},{SystemConstants.EventResults.NOT_SHOW_AGAIN}"
        self.accept()

    def _set_window_icon_and_style(self):
        pass

    @classmethod
    def show_dialog(cls, parent: QWidget, title_key: str, message_key: str, detail_info: Optional[str] = None,
                    buttons_config: Optional[Dict[str, Any]] = None,
                    show_do_not_show_again: bool = False, **kwargs) -> Optional[str]:
        """클래스 메서드로 다이얼로그를 표시하고 결과를 반환합니다."""
        dialog = cls(parent, title_key, message_key, detail_info, buttons_config, **kwargs)
        if show_do_not_show_again:
            dialog.do_not_show_again_checkbox = QCheckBox(text_manager.get_ui_text("buttons", SystemConstants.ButtonKeys.DO_NOT_SHOW_AGAIN))
            dialog.checkbox_layout.addWidget(dialog.do_not_show_again_checkbox)

        dialog.exec_()
        return dialog.get_result()

# --- 메시지 유형별 서브 클래스 (SystemConstants.EventResults 사용) ---

class AlertDialog(BaseMessageWindow):
    def __init__(self, parent: QWidget = None, title_key: str = "alert_title",
                 message_key: str = "alert_message", detail_info: Optional[str] = None):
        super().__init__(parent, title_key, message_key, detail_info,
                         buttons_config={SystemConstants.ButtonKeys.OK: SystemConstants.EventResults.OK})
        self.setWindowTitle(text_manager.get_ui_text("main_window", "title") + " - " + text_manager.get_general_text(title_key))
    def _set_window_icon_and_style(self):
        self.message_label.setStyleSheet("color: blue;")
        self.message_label.setText("ℹ️ " + self.message_label.text())

class WarningDialog(BaseMessageWindow):
    def __init__(self, parent: QWidget = None, title_key: str = "warning_title",
                 message_key: str = "warning_message", detail_info: Optional[str] = None):
        super().__init__(parent, title_key, message_key, detail_info,
                         buttons_config={SystemConstants.ButtonKeys.OK: SystemConstants.EventResults.OK})
        self.setWindowTitle(text_manager.get_ui_text("main_window", "title") + " - " + text_manager.get_general_text(title_key))
    def _set_window_icon_and_style(self):
        self.message_label.setStyleSheet("color: orange;")
        self.message_label.setText("⚠️ " + self.message_label.text())

class ErrorDialog(BaseMessageWindow):
    def __init__(self, parent: QWidget = None, title_key: str = "error_title",
                 message_key: str = "error_message", detail_info: Optional[str] = None):
        super().__init__(parent, title_key, message_key, detail_info,
                         buttons_config={SystemConstants.ButtonKeys.OK: SystemConstants.EventResults.OK})
        self.setWindowTitle(text_manager.get_ui_text("main_window", "title") + " - " + text_manager.get_general_text(title_key))
    def _set_window_icon_and_style(self):
        self.message_label.setStyleSheet("color: red; font-weight: bold;")
        self.message_label.setText("❌ " + self.message_label.text())

class QuestionDialog(BaseMessageWindow):
    def __init__(self, parent: QWidget = None, title_key: str = "question_title",
                 message_key: str = "question_message", detail_info: Optional[str] = None,
                 buttons_type: str = "yes_no"):
        buttons = {}
        if buttons_type == "yes_no":
            buttons = {SystemConstants.ButtonKeys.YES: SystemConstants.EventResults.YES,
                       SystemConstants.ButtonKeys.NO: SystemConstants.EventResults.NO}
        elif buttons_type == "ok_cancel":
            buttons = {SystemConstants.ButtonKeys.OK: SystemConstants.EventResults.OK,
                       SystemConstants.ButtonKeys.CANCEL: SystemConstants.EventResults.CANCEL}
        elif buttons_type == "delete_cancel":
            buttons = {SystemConstants.ButtonKeys.DELETE: SystemConstants.EventResults.DELETE,
                       SystemConstants.ButtonKeys.CANCEL: SystemConstants.EventResults.CANCEL}
        else:
            buttons = {SystemConstants.ButtonKeys.YES: SystemConstants.EventResults.YES,
                       SystemConstants.ButtonKeys.NO: SystemConstants.EventResults.NO}

        super().__init__(parent, title_key, message_key, detail_info, buttons_config=buttons)
        self.setWindowTitle(text_manager.get_ui_text("main_window", "title") + " - " + text_manager.get_general_text(title_key))
    def _set_window_icon_and_style(self):
        self.message_label.setText("❓ " + self.message_label.text())

class ConfirmDeleteDialog(QuestionDialog):
    def __init__(self, parent: QWidget = None, delete_target: str = "선택된 항목",
                 message_key: str = "confirm_delete_message", detail_info: Optional[str] = None):
        translated_message = text_manager.get_general_text(message_key).format(target=delete_target)
        super().__init__(parent, title_key="confirm_delete_title",
                         message_key="confirm_delete_message", # 이 키는 text_manager에서 템플릿 문자열을 가져오는 용도
                         detail_info=detail_info,
                         buttons_type="delete_cancel")
        self.message_label.setText("⚠️ " + translated_message) # 메시지 라벨 텍스트 업데이트
        self.setWindowTitle(text_manager.get_ui_text("main_window", "title") + " - " + text_manager.get_general_text("confirm_delete_title"))