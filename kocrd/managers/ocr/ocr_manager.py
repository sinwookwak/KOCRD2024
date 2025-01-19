# F:\AI-M2\managers\ocr\ocr_manager.py
import pytesseract
from pdf2image import convert_from_path
import shutil
import fitz
import json
import logging
import os
import pika
from PIL import Image
from typing import List, Optional, Tuple, Dict, Any, Callable
from .ocr_utils import OCRHelper
from managers.settings_manager import SettingsManager


class OCRManager:
    """OCR 작업을 처리하는 클래스."""
    def __init__(self, tesseract_cmd: Optional[str], tessdata_dir: Optional[str], settings_manager: SettingsManager, monitoring_window: Any = None):
        self.monitoring_window = monitoring_window
        self.tesseract_cmd = tesseract_cmd
        self.tessdata_dir = tessdata_dir
        self.settings_manager = settings_manager
        if self.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
        if self.tessdata_dir:
            os.environ["TESSDATA_PREFIX"] = self.tessdata_dir
            logging.info(f"Tessdata 설정 완료: {self.tessdata_dir}")
        logging.info(f"Tesseract 설정 완료: {self.tesseract_cmd}")
        self.progress_bar = monitoring_window.progress_bar if monitoring_window else None
        self.temp_dir = os.path.join(os.environ.get("TEMP", os.path.expanduser("~/.tmp")), "ocr_manager")
        os.makedirs(self.temp_dir, exist_ok=True)

    def log_scan_results(self, results: List[str]) -> None:
        """OCR 결과를 로그로 기록."""
        if not results:
            logging.warning("No results to log.")
            return

        for result in results:
            logging.info(f"OCR Result: {result}")

    def start_scan(self, file_paths: List[str]) -> Optional[List[str]]:
        """문서 스캔 시작."""
        if not file_paths:
            logging.warning("스캔할 파일 경로가 제공되지 않았습니다.")
            return None

        logging.info(f"{len(file_paths)}개의 파일 스캔 시작...")
        ocr_results = []
        try:
            for index, file_path in enumerate(file_paths):
                ocr_result = self.extract_text(file_path)
                ocr_results.append(ocr_result)
                logging.info(f"{file_path}의 OCR 결과: {ocr_result}")

                if self.progress_bar:
                    progress = int((index + 1) / len(file_paths) * 100)
                    self.progress_bar.setValue(progress)

        except Exception as e:
            logging.error(f"스캔 중 오류 발생: {e}")
            return None

        return ocr_results

    def perform_ocr(self, image: Image.Image, lang: str = "kor+eng") -> Optional[str]:
        """OCR 수행 로직 분리."""
        try:
            text = pytesseract.image_to_string(image, lang=lang)
            return text.strip()
        except Exception as e:
            logging.error(f"OCR 수행 중 오류: {e}")
            return None

    def extract_text(self, file_path: str, lang: str = "kor+eng") -> Optional[str]:
        """텍스트 추출. PDF 텍스트 레이어 우선 추출 후 이미지 OCR 수행."""
        try:
            if file_path.endswith(".pdf"):
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
                                logging.error(f"Page {page_num} 이미지 변환 실패")
                                return None
                    return "\n".join(extracted_texts).strip()

                except ImportError:
                    logging.warning("PyMuPDF가 설치되어 있지 않습니다. 이미지 변환 후 OCR을 수행합니다.")
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
                    logging.error(f"PDF 처리 중 오류 발생: {e}")
                    return None
            elif file_path.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
                image = Image.open(file_path)
                return self.perform_ocr(image, lang)
            else:
                logging.error(f"지원하지 않는 파일 형식: {file_path}")
                return None
        except Exception as e:
            logging.error(f"텍스트 추출 중 오류 발생: {e}")
            return None

    def find_poppler_path(self) -> Optional[str]:
        return self.settings_manager.get_setting_path("POPPLER_PATH")

    def request_temp_files(self, file_path: str, callback: Optional[Callable] = None) -> Any:
        if self.monitoring_window is None:
            logging.error("monitoring_window가 초기화되지 않았습니다.")
            return None
        return self.monitoring_window.system_manager.send_temp_file_message("create_temp_files", file_path=file_path, callback=callback)

    def save_page_as_image(self, page: Image.Image, page_num: int) -> Optional[str]:
        """PDF 페이지를 임시 이미지로 저장."""
        try:
            os.makedirs(self.temp_dir, exist_ok=True)
            temp_image_path = os.path.join(self.temp_dir, f"page_{page_num}.png")
            page.save(temp_image_path, "PNG")
            logging.info(f"Page {page_num} saved as image: {temp_image_path}")
            return temp_image_path
        except Exception as e:
            logging.error(f"Error saving page {page_num} as image: {e}")
            return None # RuntimeError 대신 None 반환

    def cleanup_temp_files(self) -> None:
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                logging.info("Temporary files cleaned up.")
        except Exception as e:
            logging.error(f"Error cleaning temporary files: {e}")

    def request_temp_files_cleanup(self, file_paths: List[str]) -> None:
        if self.monitoring_window is None:
            logging.error("monitoring_window가 초기화되지 않았습니다.")
            return

        self.monitoring_window.system_manager.send_temp_file_message("cleanup_temp_files", file_paths=file_paths)

    def _send_ocr_result(self, file_path: str, extracted_text: Optional[str]) -> None:
        """OCR 결과를 메시지로 전송."""
        if self.monitoring_window:
            self.monitoring_window.system_manager.send_message("OCR_RESULT", {"type": "OCR_RESULT", "file_path": file_path, "extracted_text": extracted_text, "reply_to": "events_queue"})
        else:
            logging.error("system_manager가 초기화되지 않았습니다.")

    def handle_message(self, ch: pika.BlockingConnection, method: pika.spec.Basic.Deliver, properties: pika.BasicProperties, body: bytes) -> None:
        try:
            message: Dict = json.loads(body.decode())
            message_type = message.get("type")

            if message_type == "PERFORM_OCR":
                file_path = message.get("file_path")
                if not file_path:
                    logging.warning("파일 경로가 제공되지 않았습니다.")
                    ch.basic_ack(delivery_tag=method.delivery_tag) # 파일 경로가 없는 메시지이므로 ACK 처리
                    return

                extracted_text = self.extract_text(file_path)

                if extracted_text:
                    is_valid = OCRHelper.validate_extracted_text(extracted_text)
                    if is_valid:
                        ocr_result = OCRHelper.extract_cell_and_kclb(extracted_text)
                        if ocr_result:
                            logging.info(f"OCR 결과: {ocr_result}")
                        else:
                            logging.warning("OCR 결과 추출 실패")
                    else:
                        logging.warning("추출된 텍스트가 유효하지 않습니다 (비어 있음).")
                else:
                    logging.warning("텍스트 추출 실패")

                self._send_ocr_result(file_path, extracted_text)
                ch.basic_ack(delivery_tag=method.delivery_tag) # 정상 처리 후 ACK

            else:
                logging.warning(f"알 수 없는 메시지 타입: {message_type}")
                ch.basic_ack(delivery_tag=method.delivery_tag) # 알 수 없는 메시지 타입이므로 ACK 처리
        except json.JSONDecodeError as e:
            logging.error(f"JSON 파싱 오류: {e}. 메시지 내용: {body.decode()}")
            ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False) # JSON 파싱 오류이므로 NACK, requeue=False
        except Exception as e:
            logging.error(f"OCR 메시지 처리 중 오류 발생: {e}. 메시지 내용: {body.decode()}")
            ch.basic_reject(delivery_tag=method.delivery_tag, requeue=True) # 그 외 오류는 NACK, requeue=True

    def main(self):
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
            channel = connection.channel()
            channel.queue_declare(queue='ocr_queue')
            channel.basic_consume(queue='ocr_queue', on_message_callback=self.handle_message, auto_ack=False) # auto_ack=False로 변경
            print('Waiting for messages. To exit press CTRL+C')
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError as e:
            logging.error(f"RabbitMQ 연결 오류: {e}")
        except KeyboardInterrupt:
            print('Interrupted')
            try:
                channel.stop_consuming()
                connection.close()
            except Exception as e2:
                logging.error(f"Error during shutdown: {e2}")
        finally:
            if channel is not None and channel.is_open:
                channel.close()
            if connection is not None and connection.is_open:
                connection.close()
