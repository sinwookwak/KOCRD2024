# MonitoringManager.py
from PyQt5.QtWidgets import QWidget, QMessageBox
from PyQt5.QtCore import pyqtSignal
import logging
from ui.monitoring_ui import MonitoringUI
from managers.ai_managers.AI_model_manager import AIModelManager # import 추가

class MonitoringManager(QWidget):
    """AI와 소통하는 대화창 및 문서 작업 창."""
    command_processed = pyqtSignal(str, str)  # (Command Text, AI Response) 신호

    def __init__(self, model_manager: AIModelManager, ocr_manager, event_manager): # 의존성 명시적 주입
        super().__init__()
        self.monitoring_ui = MonitoringUI()
        self.model_manager = model_manager # Model Manager 저장
        self.ocr_manager = ocr_manager
        self.event_manager = event_manager

    def get_ui(self):
        """Monitoring UI 반환."""
        return self.monitoring_ui

    def display_document_content(self, text, source="AI"):
        """문서 내용 표시."""
        try:
            self.monitoring_ui.display_log(f"[{source}]:\n{text}\n")
            logging.info(f"Displayed content from {source}.")
        except Exception as e:
            logging.error(f"Error displaying content: {e}")

    def handle_command(self, command_text):
        """GPT 명령 처리."""
        if not command_text.strip():
            logging.warning("Command input field is empty.")
            return

        try:
            response = self.model_manager.generate_text(command_text) # Model Manager의 generate_text 사용
            self.monitoring_ui.display_chat_response(response)
            self.command_processed.emit(command_text, response)
        except Exception as e:
            logging.error(f"Error handling command '{command_text}': {e}")
            QMessageBox.critical(self, "Command Error", f"Error handling command: {str(e)}")

    def process_ocr_event(self, file_path): # ocr_manager를 생성자에서 받으므로 인자에서 제거
        """OCR 이벤트 처리."""
        try:
            text = self.ocr_manager.extract_text(file_path) # ocr_manager의 메서드 직접 호출
            log_message = f"Extracted Text: {text}"
            self.monitoring_ui.display_log(log_message)
        except Exception as e:
            logging.error(f"Error processing OCR event: {e}")
            QMessageBox.critical(self, "OCR Error", f"OCR 처리 중 오류가 발생했습니다: {e}")

    def handle_monitoring_event(self, event_type):
        """AI_Monitoring_event와 연동."""
        try:
            self.event_manager.handle_monitoring_event(event_type) # event_manager의 메서드 호출
            logging.info(f"Monitoring event '{event_type}' handled successfully.")
        except Exception as e:
            logging.error(f"Error handling monitoring event: {e}")
            QMessageBox.critical(self, "Monitoring Event Error", f"Monitoring event 처리 중 오류가 발생했습니다: {e}")

    def handle_chat(self, message):
        """사용자 메시지 처리."""
        try:
            if not message.strip():
                logging.warning("Empty message received.")
                return

            response = self.model_manager.generate_text(message)
            self.display_chat_message(message, response) # UI 업데이트 함수 호출

        except Exception as e:
            logging.error(f"Error in chat handling: {e}")
            self.display_chat_message(message, "AI 응답 처리 중 오류가 발생했습니다.") # UI 업데이트 함수 호출

    def display_chat_message(self, message, response):
        """채팅 메시지 UI 표시."""
        self.monitoring_ui.display_chat_message(message, response) # UI 클래스의 display_chat_message 호출


# class MonitoringManager(QWidget):
#     """AI와 소통하는 대화창 및 문서 작업 창."""
#     command_processed = pyqtSignal(str, str)  # (Command Text, AI Response) 신호
#     def load_gpt_model(self):
#         """GPT 모델 로드."""
#         try:
#             self.tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
#             self.gpt_model = GPT2LMHeadModel.from_pretrained("gpt2")
#             if self.tokenizer.eos_token_id is None:
#                 self.tokenizer.eos_token_id = self.tokenizer.pad_token_id or 50256
#             logging.info("GPT model and tokenizer loaded successfully.")
#         except Exception as e:
#             logging.error(f"Error loading GPT model or tokenizer: {e}")
#             QMessageBox.critical(self, "모델 로드 오류", f"GPT 모델 로드 중 오류가 발생했습니다: {e}") # QMessageBox 추가
#             return None # 모델 로드 실패 시 None 반환

#     def display_document_content(self, text, source="AI"):
#         """문서 내용 표시."""
#         try:
#             self.monitoring_ui.display_log(f"[{source}]:\n{text}\n") # UI 업데이트는 UI 클래스에서
#             logging.info(f"Displayed content from {source}.")
#         except Exception as e:
#             logging.error(f"Error displaying content: {e}")
#     def generate_ai_response(self, message): # public 메서드 추가
#         return self._generate_ai_response(message)

#     def _generate_ai_response(self, message): # 채팅 처리 로직 분리
#         """AI 응답 생성."""
#         try:
#             input_ids = self.tokenizer.encode(message, return_tensors="pt")
#             pad_token_id = self.tokenizer.pad_token_id or self.tokenizer.eos_token_id
#             attention_mask = (input_ids != pad_token_id).long()
#             output = self.gpt_model.generate(
#                 input_ids=input_ids, attention_mask=attention_mask,
#                 max_new_tokens=50, pad_token_id=pad_token_id
#             )
#             return self.tokenizer.decode(output[0], skip_special_tokens=True)
#         except Exception as e:
#             logging.error(f"Error generating AI response: {e}")
#             return "AI 응답 생성 중 오류가 발생했습니다."

#     def handle_command(self, command_text):
#         """GPT 명령 처리."""
#         if not command_text.strip():
#             logging.warning("Command input field is empty.")
#             return

#         try:
#             response = self.ai_manager.generate_text(command_text)
#             self.monitoring_ui.display_chat_response(response)
#             self.command_processed.emit(command_text, response)
#         except Exception as e:
#             logging.error(f"Error handling command '{command_text}': {e}")
#             QMessageBox.critical(self, "Command Error", f"Error handling command: {str(e)}")

#     def process_ocr_event(self, file_path, ocr_manager): # ocr_manager 인자로 받음
#         """OCR 이벤트 처리."""
#         try:
#             text = ocr_manager.extract_text(file_path) # ocr_manager의 메서드 직접 호출
#             log_message = f"Extracted Text: {text}"
#             self.monitoring_ui.display_log(log_message)
#         except Exception as e:
#             logging.error(f"Error processing OCR event: {e}")

#     def handle_monitoring_event(self, event_type):
#         """AI_Monitoring_event와 연동."""
#         try:
#             self.ai_manager.handle_monitoring_event(event_type)
#             logging.info(f"Monitoring event '{event_type}' handled successfully.")
#         except Exception as e:
#             logging.error(f"Error handling monitoring event: {e}")
