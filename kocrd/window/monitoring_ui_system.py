# filename: monitoring_ui_system.py
import json
import logging
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QSplitter, QTextEdit, QProgressBar, QLineEdit, QPushButton, QHBoxLayout, QListWidget
from transformers import GPT2Tokenizer, GPT2LMHeadModel
import os
from kocrd.config.messages import messages

class MonitoringUISystem(QWidget):
    """모니터링 UI 시스템 클래스."""
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.config = messages

        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("메시지를 입력하세요...")
        self.chat_output = QTextEdit()
        self.chat_output.setReadOnly(True)
        self.file_list_widget = QListWidget()
        self.tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
        self.gpt_model = GPT2LMHeadModel.from_pretrained("gpt2")
        if self.tokenizer.eos_token_id is None:
            self.tokenizer.eos_token_id = self.tokenizer.pad_token_id or 50256

        self.setup_ui()

    def setup_ui(self):
        """UI 구성."""
        layout = QVBoxLayout(self)
        layout.addWidget(self.log_display)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.chat_output)
        layout.addWidget(self.chat_input)

        send_button = QPushButton("전송")
        layout.addWidget(send_button)
        self.send_button = send_button

        button_section = self.create_button_section()
        layout.addLayout(button_section)

        self.setLayout(layout)

    def set_send_callback(self, callback):
        """전송 버튼 콜백 설정."""
        self.send_button.clicked.connect(lambda: callback(self.chat_input.text().strip()))

    def create_button_section(self):
        """버튼 섹션 생성."""
        button_section = QHBoxLayout()

        for button_config in self.config["buttons"]:
            button = QPushButton(button_config["label"])
            button.clicked.connect(getattr(self.main_window.system_manager, f"callback_{button_config['callback']}"))
            button_section.addWidget(button)

        return button_section

    def update_progress(self, value, total):
        """진행 상태를 업데이트."""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(value)

    def display_log(self, message):
        """로그 영역에 메시지 출력."""
        self.log_display.append(message)

    def display_chat_message(self, message, response):
        """채팅 메시지 표시."""
        self.chat_output.append(f"사용자: {message}")
        self.chat_output.append(f"AI: {response}")

    def generate_ai_response(self, message):
        """AI 응답 생성."""
        try:
            input_ids = self.tokenizer.encode(message, return_tensors="pt")
            pad_token_id = self.tokenizer.pad_token_id or self.tokenizer.eos_token_id
            attention_mask = (input_ids != pad_token_id).long()
            output = self.gpt_model.generate(
                input_ids=input_ids, attention_mask=attention_mask,
                max_new_tokens=50, pad_token_id=pad_token_id
            )
            return self.tokenizer.decode(output[0], skip_special_tokens=True)
        except Exception as e:
            logging.error(f"Error generating AI response: {e}")
            return "AI 응답 생성 중 오류가 발생했습니다."

    def update_file_list(self, documents):
        """가져온 파일 목록을 업데이트."""
        self.file_list_widget.clear()
        for doc in documents:
            self.file_list_widget.addItem(f"{doc['name']} ({doc['date']})")

    def init_ui(self):
        central_widget = QWidget(self.main_window)
        self.main_window.setCentralWidget(central_widget)
        central_widget.setLayout(QVBoxLayout())

        splitter = QSplitter(central_widget)
        central_widget.layout().addWidget(splitter)

        monitoring_ui_widget = self
        if isinstance(monitoring_ui_widget, QWidget):
            if monitoring_ui_widget.layout() is None:
                monitoring_layout = QVBoxLayout()
                monitoring_ui_widget.setLayout(monitoring_layout)
            else:
                monitoring_layout = monitoring_ui_widget.layout()
            monitoring_layout.addWidget(self.progress_bar)
            
            log_display = QTextEdit()
            log_display.setReadOnly(True)
            monitoring_layout.addWidget(log_display)

            for widget_config in self.config["monitoring_ui"]["widgets"]:
                widget = getattr(self.main_window, widget_config["name"])
                monitoring_layout.addWidget(widget)

        else:
            logging.error("Monitoring UI is not a QWidget. Cannot add progress bar.")

        splitter.setSizes([1000, 200])
        logging.info("MonitoringUISystem UI initialized.")

    def load_config(self):
        config_path = os.path.join(os.path.dirname(__file__), 'window_config.json')
        with open(config_path, 'r') as f:
            return json.load(f)

def setup_monitoring_ui():
    # ...existing code...
    print(messages["351"])  # Documents filtered successfully.
    # ...existing code...
    print(messages["352"])  # Document search completed for keyword: {keyword}
    # ...existing code...
