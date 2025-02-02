import pytesseract
from pdf2image import convert_from_path
import shutil
import fitz
import json
import logging
import os
import pika
from PIL import Image
from typing import List, Optional, Dict, Any, Callable
import sys
from PyQt5.QtWidgets import QMessageBox
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from managers.ocr.ocr_utils import OCRHelper
from Settings.settings_manager import SettingsManager

# ocr_config.json 파일 로드
with open(os.path.join(os.path.dirname(__file__), 'ocr_config.json'), 'r') as f:
    ocr_config = json.load(f)

class OCRManager:
    """OCR 작업을 처리하는 클래스."""
    def __init__(self, tesseract_cmd: Optional[str], tessdata_dir: Optional[str], settings_manager: SettingsManager, monitoring_window: Any = None):
        self.monitoring_window = monitoring_window
        self.tesseract_cmd = tesseract_cmd
        self.tessdata_dir = tessdata_dir
        self.settings_manager = settings_manager
        self.progress_bar = monitoring_window.progress_bar if monitoring_window else None
        self.temp_dir = os.path.join(os.environ.get("TEMP", os.path.expanduser("~/.tmp")), "ocr_manager")
        os.makedirs(self.temp_dir, exist_ok=True)

        if self.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
        if self.tessdata_dir:
            os.environ["TESSDATA_PREFIX"] = self.tessdata_dir
            self.log("info", "Tessdata 설정 완료: {self.tessdata_dir}")
        self.log("info", "Tesseract 설정 완료: {self.tesseract_cmd}")

        # 시스템 매니저와 프로그레스바 초기화 확인
        if self.monitoring_window:
            if not hasattr(self.monitoring_window, 'system_manager'):
                self.log("error", "monitoring_window에 system_manager가 없습니다.")
            if not hasattr(self.monitoring_window, 'progress_bar'):
                self.log("error", "monitoring_window에 progress_bar가 없습니다.")
        else:
            self.log("warning", "monitoring_window가 None입니다.")

    def log(self, level: str, code: str, **kwargs) -> None:
        """간략화된 로깅."""
        message = ocr_config["logging"][level].get(code, "").format(**kwargs)
        getattr(logging, level)(message)

    def show_message(self, level: str, code: str) -> None:
        """간략화된 메시지 박스."""
        message = ocr_config["messages"].get(code, "")
        if level == "warning":
            QMessageBox.warning(self.monitoring_window, "오류", message)

    def start_scan(self, file_paths: List[str]) -> Optional[List[str]]:
        """문서 스캔 시작."""
        if not file_paths:
            self.log("warning", "스캔할 파일 경로가 제공되지 않았습니다.")
            return None

        self.log("info", "06", file_paths=len(file_paths))
        ocr_results = []
        try:
            for index, file_path in enumerate(file_paths):
                self.log("info", "06", file_path=file_path)
                ocr_result = self.extract_text(file_path)
                ocr_results.append(ocr_result)
                self.log("info", "03", file_path=file_path, ocr_result=ocr_result)

                if self.progress_bar:
                    progress = int((index + 1) / len(file_paths) * 100)
                    self.progress_bar.setValue(progress)

        except Exception as e:
            self.log("error", "08", file_path=file_path, e=e)
            return None

        return ocr_results

    def extract_text(self, file_path: str, lang: str = "kor+eng") -> Optional[str]:
        """텍스트 추출. PDF 텍스트 레이어 우선 추출 후 이미지 OCR 수행."""
        try:
            self.log("info", "07", file_path=file_path)
            if file_path.endswith(".pdf"):
                return self._extract_text_from_pdf(file_path, lang)
            elif file_path.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
                image = Image.open(file_path)
                return self.perform_ocr(image, lang)
            else:
                self.log("error", "04", file_path=file_path)
                return None
        except Exception as e:
            self.log("error", "05", e=e)
            return None

    def _extract_text_from_pdf(self, file_path: str, lang: str) -> Optional[str]:
        """PDF 파일에서 텍스트를 추출."""
        try:
            doc = fitz.open(file_path)
            extracted_texts: List[str] = []
            for page_num in range(doc.page_count):
                page = doc[page_num]
                text = page.get_text("text")
                if text:
                    extracted_texts.append(text)
                else:
                    pix = page.get_pixmap()
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    temp_image_path = self.save_page_as_image(img, page_num)
                    if temp_image_path:
                        ocr_result = self.perform_ocr(img, lang)
                        if ocr_result:
                            extracted_texts.append(ocr_result)
                        os.remove(temp_image_path)
                    else:
                        self.log("error", "02", page_num=page_num)
                        return None
            return "\n".join(extracted_texts).strip()

        except ImportError:
            self.log("warning", "PyMuPDF가 설치되어 있지 않습니다. 이미지 변환 후 OCR을 수행합니다.")
            result = self.request_temp_files(file_path)
            if result is None:
                return None
            images = [Image.open(image_path) for image_path in result]
            extracted_texts = []
            for image in images:
                ocr_result = self.perform_ocr(image, lang)
                if ocr_result:
                    extracted_texts.append(ocr_result)
            self.request_temp_files_cleanup(result)
            return "\n".join(extracted_texts).strip()

        except Exception as e:
            self.log("error", "03", e=e)
            return None

    def perform_ocr(self, image: Image.Image, lang: str = "kor+eng") -> Optional[str]:
        """OCR 수행 로직 분리."""
        try:
            self.log("info", "08")
            text = pytesseract.image_to_string(image, lang=lang)
            return text.strip()
        except Exception as e:
            self.log("error", "01", e=e)
            return None

    def find_poppler_path(self) -> Optional[str]:
        """Poppler 경로를 찾습니다."""
        return self.settings_manager.get_setting_path("POPPLER_PATH")

    def request_temp_files(self, file_path: str, callback: Optional[Callable] = None) -> Any:
        """임시 파일을 요청합니다."""
        if self.monitoring_window is None:
            self.log("error", "monitoring_window가 초기화되지 않았습니다.")
            return None
        if not hasattr(self.monitoring_window, 'system_manager'):
            self.log("error", "monitoring_window에 system_manager가 없습니다.")
            return None
        return self.monitoring_window.system_manager.send_temp_file_message("create_temp_files", file_path=file_path, callback=callback)

    def save_page_as_image(self, page: Image.Image, page_num: int) -> Optional[str]:
        """PDF 페이지를 임시 이미지로 저장."""
        try:
            os.makedirs(self.temp_dir, exist_ok=True)
            temp_image_path = os.path.join(self.temp_dir, f"page_{page_num}.png")
            page.save(temp_image_path, "PNG")
            self.log("info", "04", page_num=page_num, temp_image_path=temp_image_path)
            return temp_image_path
        except Exception as e:
            self.log("error", "06", page_num=page_num, e=e)
            return None

    def cleanup_temp_files(self) -> None:
        """임시 파일을 정리합니다."""
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                self.log("info", "05")
        except Exception as e:
            self.log("error", "07", e=e)

    def request_temp_files_cleanup(self, file_paths: List[str]) -> None:
        """임시 파일 정리를 요청합니다."""
        if self.monitoring_window is None:
            self.log("error", "monitoring_window가 초기화되지 않았습니다.")
            return

        self.monitoring_window.system_manager.send_temp_file_message("cleanup_temp_files", file_paths=file_paths)

    def _send_ocr_result(self, file_path: str, extracted_text: Optional[str]) -> None:
        """OCR 결과를 메시지로 전송."""
        if self.monitoring_window:
            self.monitoring_window.system_manager.send_message(ocr_config["message_types"]["OCR_RESULT"], {"type": ocr_config["message_types"]["OCR_RESULT"], "file_path": file_path, "extracted_text": extracted_text, "reply_to": ocr_config["queues"]["events_queue"]})
        else:
            self.log("error", "system_manager가 초기화되지 않았습니다.")

    def handle_message(self, ch: pika.BlockingConnection, method: pika.spec.Basic.Deliver, properties: pika.BasicProperties, body: bytes) -> None:
        """메시지 큐에서 OCR 작업 요청을 처리."""
        try:
            message: Dict = json.loads(body.decode())
            message_type = message.get("type")

            if message_type == ocr_config["message_types"]["PERFORM_OCR"]:
                file_path = message.get("file_path")
                if not file_path:
                    self.log("warning", "파일 경로가 제공되지 않았습니다.")
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    return

                extracted_text = self.extract_text(file_path)

                if extracted_text:
                    is_valid = OCRHelper.validate_extracted_text(extracted_text)
                    if is_valid:
                        ocr_result = OCRHelper.extract_cell_and_kclb(extracted_text)
                        if ocr_result:
                            self.log("info", "OCR 결과: {ocr_result}", ocr_result=ocr_result)
                        else:
                            self.log("warning", "OCR 결과 추출 실패")
                    else:
                        self.log("warning", "추출된 텍스트가 유효하지 않습니다 (비어 있음).")
                else:
                    self.log("warning", "텍스트 추출 실패")

                self._send_ocr_result(file_path, extracted_text)
                ch.basic_ack(delivery_tag=method.delivery_tag)

            else:
                self.log("warning", f"알 수 없는 메시지 타입: {message_type}")
                ch.basic_ack(delivery_tag=method.delivery_tag)
        except json.JSONDecodeError as e:
            self.log("error", "JSON 파싱 오류: {e}. 메시지 내용: {body.decode()}", e=e, body=body.decode())
            ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
        except Exception as e:
            self.log("error", "OCR 메시지 처리 중 오류 발생: {e}. 메시지 내용: {body.decode()}", e=e, body=body.decode())
            ch.basic_reject(delivery_tag=method.delivery_tag, requeue=True)

    def main(self):
        """메시지 큐에서 메시지를 소비하여 OCR 작업을 수행."""
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
            channel = connection.channel()
            channel.queue_declare(queue=ocr_config["queues"]["ocr_queue"])
            channel.basic_consume(queue=ocr_config["queues"]["ocr_queue"], on_message_callback=self.handle_message, auto_ack=False)
            print('Waiting for messages. To exit press CTRL+C')
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError as e:
            self.log("error", "RabbitMQ 연결 오류: {e}", e=e)
        except KeyboardInterrupt:
            print('Interrupted')
            try:
                channel.stop_consuming()
                connection.close()
            except Exception as e2:
                self.log("error", "Error during shutdown: {e2}", e=e2)
        finally:
            if channel is not None and channel.is_open:
                channel.close()
            if connection is not None and connection.is_open:
                connection.close()

    def filter_documents(self, criteria):
        """문서 필터링."""
        try:
            self.lot[criteria] = self.main_window.filter_table(criteria)
            self.log("info", "01")
        except Exception as e:
            self.log("error", "01", e=e)
            self.show_message("warning", "01")
