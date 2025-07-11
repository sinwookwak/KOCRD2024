#OCR_UI.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QProgressBar, QPushButton, QHBoxLayout, QListWidget, QLabel, QLineEdit, QSplitter, QFileDialog, QFormLayout, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
import logging
import importlib  # 모듈 동적 로드를 위한 import

class OCRUI:
    """OCR 관련 UI 요소 생성 클래스."""
    def __init__(self, settings_manager):
        self.settings_manager = settings_manager
        self.messages = self.settings_manager.config.get("messages", {})
        self.log_messages = self.settings_manager.config.get("log_messages", {})
        self.error_messages = self.settings_manager.config.get("error_messages", {})

    def create_button_layout(self, parent, system_manager):
        """OCR 관련 버튼 생성."""
        button_layout = QHBoxLayout()
        config = self.settings_manager.config.get("ocr_buttons", [])
        for button_config in config:
            button = QPushButton(button_config["label"], parent)
            method = getattr(system_manager, button_config["method"])
            button.clicked.connect(lambda: method(parent.get_selected_files()))
            button_layout.addWidget(button)
        return button_layout

    def create_feedback_layout(self, parent, system_manager):
        """피드백 받은 OCR 결과를 표시하고 수정하는 레이아웃 생성."""
        feedback_layout = QSplitter(Qt.Horizontal)
        config = self.settings_manager.config.get("ocr_feedback", {})

        # 피드백 받은 이미지 파일 목록
        self.feedback_list = QListWidget(parent)
        self.feedback_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.feedback_list.itemClicked.connect(self.display_feedback_details)
        feedback_layout.addWidget(self.feedback_list)

        # 피드백 상세 정보 표시
        self.feedback_details = QWidget(parent)
        details_layout = QVBoxLayout(self.feedback_details)

        self.image_label = QLabel()
        details_layout.addWidget(self.image_label)

        self.ocr_result_label = QLabel(config["ocr_result_label"])
        details_layout.addWidget(self.ocr_result_label)

        self.ocr_result_edit = QLineEdit()
        details_layout.addWidget(self.ocr_result_edit)

        self.feedback_input_label = QLabel(config["feedback_input_label"])
        details_layout.addWidget(self.feedback_input_label)

        self.feedback_input_edit = QLineEdit()
        details_layout.addWidget(self.feedback_input_edit)

        self.save_button = QPushButton(config["save_button_label"], parent)
        self.save_button.clicked.connect(lambda: self.save_feedback(system_manager))
        details_layout.addWidget(self.save_button)

        feedback_layout.addWidget(self.feedback_details)
        return feedback_layout

    def display_feedback_details(self, item):
        """선택된 피드백 항목의 상세 정보를 표시."""
        feedback_data = item.data(Qt.UserRole)
        self.image_label.setPixmap(QPixmap(feedback_data['image_path']))
        self.ocr_result_edit.setText(feedback_data['ocr_text'])
        self.feedback_input_edit.setText(feedback_data.get('feedback_text', ''))

    def save_feedback(self, system_manager):
        """수정된 피드백을 저장."""
        selected_item = self.feedback_list.currentItem()
        if selected_item:
            feedback_data = selected_item.data(Qt.UserRole)
            feedback_data['ocr_text'] = self.ocr_result_edit.text()
            feedback_data['feedback_text'] = self.feedback_input_edit.text()
            system_manager.save_feedback(feedback_data)
            QMessageBox.information(self, self.messages.get("214", "저장 완료"), self.messages.get("215", "피드백이 저장되었습니다."))

    def setup_widget(self, system_manager):
        """모니터링 창 생성."""
        monitoring_window = QWidget()
        layout = QVBoxLayout(monitoring_window)

        # 로그 출력
        log_display = QTextEdit()
        log_display.setReadOnly(True)
        layout.addWidget(log_display)

        # 진행 상태 Progress Bar
        progress_bar = QProgressBar()
        progress_bar.setMaximum(100)
        layout.addWidget(progress_bar)

        # 피드백 레이아웃 추가
        feedback_layout = self.create_feedback_layout(monitoring_window, system_manager)
        layout.addWidget(feedback_layout)

        # 버튼 레이아웃 추가
        button_layout = self.create_button_layout(monitoring_window, system_manager)
        layout.addLayout(button_layout)

        return monitoring_window

    def create_ocr_settings_tab(self, parent):
        """OCR 설정 탭을 생성합니다."""
        ocr_tab = QWidget()
        form_layout = QFormLayout()

        self.tesseract_cmd_input = QLineEdit(parent)
        self.tesseract_cmd_input.setText(self.settings_manager.get_setting("tesseract_cmd", ""))
        form_layout.addRow("Tesseract Command:", self.tesseract_cmd_input)

        self.tessdata_dir_input = QLineEdit(parent)
        self.tessdata_dir_input.setText(self.settings_manager.get_setting("tessdata_dir", ""))
        form_layout.addRow("Tessdata Directory:", self.tessdata_dir_input)

        save_button = QPushButton("Save", parent)
        save_button.clicked.connect(self.save_ocr_settings)
        form_layout.addWidget(save_button)

        ocr_tab.setLayout(form_layout)
        return ocr_tab

    def save_ocr_settings(self):
        """OCR 설정을 저장합니다."""
        tesseract_cmd = self.tesseract_cmd_input.text()
        tessdata_dir = self.tessdata_dir_input.text()

        self.settings_manager.set_setting("tesseract_cmd", tesseract_cmd)
        self.settings_manager.set_setting("tessdata_dir", tessdata_dir)

        logging.info(self.log_messages.get("311", "OCR settings saved."))

        # DatabaseManager를 통해 설정 저장
        database_manager = self.settings_manager.get_manager("database")
        if database_manager:
            database_manager.save_document_info({
                "file_name": "ocr_settings",
                "type": "settings",
                "date": "",
                "supplier": ""
            })
            logging.info(self.log_messages.get("ocr_settings_saved_to_db", "OCR settings saved to database."))
        else:
            logging.error(self.error_messages.get("501", "DatabaseManager not found."))