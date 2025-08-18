import pytesseract
from pdf2image import convert_from_path
from PIL import Image
from typing import List, Optional, Dict, Any, Callable
from PyQt5.QtWidgets import QMessageBox
import sys
import os
import shutil
import fitz
import json
import logging
import asyncio
import uuid
from datetime import datetime
try:
    import pika
except ImportError:
    pika = None
    logging.warning("pika module not available - RabbitMQ functionality will be disabled")

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from kocrd.managers.ocr.ocr_utils import OCRHelper # kocrd 패키지 내부 경로 사용
from kocrd.setting.settings_manager import SettingsManager # kocrd 패키지 내부 경로 사용
from kocrd.config.config import text_manager # text_manager 임포트
from kocrd.config.message_broker import display_error, display_warning, display_alert, publish_system_event
from kocrd.managers.unified_temp_manager import UnifiedTempManager, TempFileType
from kocrd.patterns.messaging_system import global_message_bus, Message, MessageType, MessagePriority


class OCRManager:
    """OCR 작업을 처리하는 클래스."""
    def __init__(self, tesseract_cmd: Optional[str], tessdata_dir: Optional[str], settings_manager: SettingsManager, monitoring_window: Any = None):
        self.monitoring_window = monitoring_window
        # Tesseract 경로는 SettingsManager 또는 생성자 인자로 받아 사용
        self.tesseract_cmd = tesseract_cmd
        self.tessdata_dir = tessdata_dir
        self.settings_manager = settings_manager
        self.progress_bar = monitoring_window.progress_bar if monitoring_window else None
        
        # Initialize unified temp manager for OCR files
        self.temp_manager = UnifiedTempManager(
            name="ocr_temp",
            settings_manager=settings_manager
        )
        
        # Legacy temp directory for backward compatibility
        self.temp_dir = os.path.join(self.settings_manager.get_temp_dir(), "ocr_manager")
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # Register modern message handlers
        self._register_message_handlers()

        # pytesseract 설정은 SystemManager 또는 OCRManager 초기화 시 SettingsManager 값을 사용
        if self.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
            self.log("info", "319", tesseract_cmd=self.tesseract_cmd) # 수정된 키워드 인자 사용
        else:
             self.log("warning", "410") # Tesseract 경로 설정 안됨 경고

        if self.tessdata_dir:
            os.environ["TESSDATA_PREFIX"] = self.tessdata_dir
            self.log("info", "320", tessdata_dir=self.tessdata_dir) # 수정된 키워드 인자 사용
        # else: # tessdata_dir이 필수는 아닐 수 있으므로 경고는 필요에 따라 추가
        #      self.log("warning", "...") # Tessdata 경로 설정 안됨 경고 (새 ID 필요)


        # 시스템 매니저와 프로그레스바 초기화 확인
        # 이 로직은 SystemManager에서 OCRManager를 생성하고 주입할 때 확인하는 것이 더 적절할 수 있습니다.
        # OCRManager 자체는 monitoring_window가 None일 수도 있습니다.
        if self.monitoring_window:
            if not hasattr(self.monitoring_window, 'system_manager'):
                self.log("error", "509") # text_manager 사용
            if not hasattr(self.monitoring_window, 'progress_bar'):
                self.log("error", "510") # text_manager 사용
        else:
            self.log("warning", "408") # text_manager 사용

    def log(self, level: str, code: str, **kwargs) -> None:
        """TextManager를 사용하여 로그 메시지를 기록합니다."""
        message = text_manager.get_text(level, code, **kwargs)
        if level == "info":
            logging.info(message)
        elif level == "warning":
            logging.warning(message)
        elif level == "error":
            logging.error(message)
        elif level == "critical":
            logging.critical(message)
        else:
            logging.debug(message) # 알 수 없는 레벨은 debug로 처리
    
    def _register_message_handlers(self):
        """현대적인 메시지 핸들러를 등록합니다."""
        try:
            # OCR 요청 메시지 핸들러 등록
            global_message_bus.register_handler(
                "ocr.extract_text",
                self._handle_extract_text_request
            )
            
            global_message_bus.register_handler(
                "ocr.batch_process",
                self._handle_batch_process_request
            )
            
            global_message_bus.register_handler(
                "ocr.get_status", 
                self._handle_status_request
            )
            
            self.log("info", "350")  # OCR handlers registered
        except Exception as e:
            self.log("error", "529", manager_name="OCRManager", e=str(e))



    def show_message(self, level: str, code: str, **kwargs) -> None:
        """통합된 메시지 박스 표시."""
        if not self.monitoring_window:
            self.log("warning", "408")
            return
        
        try:
            message = text_manager.get_text(level, code, **kwargs)
            title = text_manager.get_general_text("264")  # "Application Error"
            
            if level == "error":
                display_error(self.monitoring_window, code, "264", **kwargs)
            elif level == "warning": 
                display_warning(self.monitoring_window, code, "264", **kwargs)
            else:
                display_alert(self.monitoring_window, code, "264", **kwargs)
                
        except Exception as e:
            self.log("error", "521", error=str(e))

    def start_scan(self, file_paths: List[str]) -> Optional[List[str]]:
        """문서 스캔 시작."""
        if not file_paths:
            self.log("warning", "402")
            return None

        self.log("info", "316", file_paths=len(file_paths))
        ocr_results = []
        try:
            for index, file_path in enumerate(file_paths):
                self.log("info", "316", file_path=file_path)
                ocr_result = self.extract_text(file_path)
                ocr_results.append(ocr_result)
                self.log("info", "313", file_path=file_path, ocr_result=ocr_result)

                if self.progress_bar:
                    progress = int((index + 1) / len(file_paths) * 100)
                    self.progress_bar.setValue(progress)

        except Exception as e:
            self.log("error", "508", file_path=file_path, e=e)
            return None

        return ocr_results

    def extract_text(self, file_path: str, lang: str = "kor+eng") -> Optional[str]:
        """텍스트 추출. PDF 텍스트 레이어 우선 추출 후 이미지 OCR 수행."""
        try:
            self.log("info", "317", file_path=file_path)
            if file_path.endswith(".pdf"):
                return self._extract_text_from_pdf(file_path, lang)
            elif file_path.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
                image = Image.open(file_path)
                return self.perform_ocr(image, lang)
            else:
                self.log("error", "504", file_path=file_path)
                return None
        except Exception as e:
            self.log("error", "505", e=e)
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
                        self.log("error", "502", page_num=page_num)
                        return None
            return "\n".join(extracted_texts).strip()

        except ImportError:
            self.log("warning", "401")
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
            self.log("error", "503", e=e)
            return None

    def perform_ocr(self, image: Image.Image, lang: str = "kor+eng") -> Optional[str]:
        """OCR 수행 로직 분리."""
        try:
            self.log("info", "318")
            text = pytesseract.image_to_string(image, lang=lang)
            return text.strip()
        except Exception as e:
            self.log("error", "501", e=e)
            return None

    def find_poppler_path(self) -> Optional[str]:
        """Poppler 경로를 찾습니다."""
        return self.settings_manager.get_setting_path("POPPLER_PATH")

    def request_temp_files(self, file_path: str, callback: Optional[Callable] = None) -> Any:
        """임시 파일을 요청합니다."""
        if self.monitoring_window is None:
            self.log("error", "515")
            return None
        if not hasattr(self.monitoring_window, 'system_manager'):
            self.log("error", "509")
            return None
        return self.monitoring_window.system_manager.send_temp_file_message("create_temp_files", file_path=file_path, callback=callback)

    def save_page_as_image(self, page: Image.Image, page_num: int) -> Optional[str]:
        """PDF 페이지를 임시 이미지로 저장."""
        try:
            os.makedirs(self.temp_dir, exist_ok=True)
            temp_image_path = os.path.join(self.temp_dir, f"page_{page_num}.png")
            page.save(temp_image_path, "PNG")
            self.log("info", "314", page_num=page_num, temp_image_path=temp_image_path)
            return temp_image_path
        except Exception as e:
            self.log("error", "506", page_num=page_num, e=e)
            return None

    def cleanup_temp_files(self) -> None:
        """임시 파일을 정리합니다."""
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                self.log("info", "315")
        except Exception as e:
            self.log("error", "507", e=e)

    def request_temp_files_cleanup(self, file_paths: List[str]) -> None:
        """임시 파일 정리를 요청합니다."""
        if self.monitoring_window is None:
            self.log("error", "515")
            return

        self.monitoring_window.system_manager.send_temp_file_message("cleanup_temp_files", file_paths=file_paths)

    def _send_ocr_result(self, file_path: str, extracted_text: Optional[str]) -> None:
        """현대적인 이벤트 시스템을 사용하여 OCR 결과를 전송."""
        try:
            # Create result message
            result_data = {
                "file_path": file_path,
                "extracted_text": extracted_text,
                "success": extracted_text is not None,
                "timestamp": datetime.now().isoformat(),
                "ocr_manager_id": id(self)
            }
            
            # Send event via modern messaging system
            message = Message(
                id=str(uuid.uuid4()),
                type=MessageType.EVENT,
                topic="ocr.result",
                data=result_data,
                priority=MessagePriority.NORMAL
            )
            
            global_message_bus.publish(message)
            
            # Also publish system event for backward compatibility
            publish_system_event(
                "ocr_result_processed",
                file_path=file_path,
                success=result_data["success"]
            )
            
            self.log("info", "324", file_path=file_path)  # Document processing completed
            
        except Exception as e:
            self.log("error", "513", e=str(e), body=str(result_data) if 'result_data' in locals() else "unknown")

    async def _handle_extract_text_request(self, message: Message) -> Message:
        """텍스트 추출 요청을 처리합니다."""
        try:
            file_path = message.data.get("file_path")
            lang = message.data.get("language", "kor+eng")
            
            if not file_path:
                raise ValueError("file_path is required")
            
            self.log("info", "322", file_path=file_path)  # Starting document processing
            extracted_text = self.extract_text(file_path, lang)
            
            # Validate and process result
            success = extracted_text is not None
            if success:
                is_valid = OCRHelper.validate_extracted_text(extracted_text)
                if is_valid:
                    ocr_result = OCRHelper.extract_cell_and_kclb(extracted_text)
                    if ocr_result:
                        self.log("info", "313", file_path=file_path, ocr_result=len(ocr_result))
                    else:
                        self.log("warning", "407")
                else:
                    self.log("warning", "405")
            else:
                self.log("warning", "417")  # Text extraction failed
            
            # Send result
            self._send_ocr_result(file_path, extracted_text)
            
            # Return response
            return Message(
                id=str(uuid.uuid4()),
                type=MessageType.RESPONSE,
                topic=f"{message.topic}.response",
                data={
                    "file_path": file_path,
                    "extracted_text": extracted_text,
                    "success": success,
                    "request_id": message.id
                },
                priority=MessagePriority.NORMAL
            )
            
        except Exception as e:
            self.log("error", "513", e=str(e), body=str(message.data))
            return Message(
                id=str(uuid.uuid4()),
                type=MessageType.ERROR,
                topic=f"{message.topic}.error",
                data={
                    "error": str(e),
                    "request_id": message.id
                },
                priority=MessagePriority.HIGH
            )
    
    async def _handle_batch_process_request(self, message: Message) -> Message:
        """배치 처리 요청을 처리합니다."""
        try:
            file_paths = message.data.get("file_paths", [])
            lang = message.data.get("language", "kor+eng")
            
            if not file_paths:
                raise ValueError("file_paths list is required")
            
            results = []
            for file_path in file_paths:
                extracted_text = self.extract_text(file_path, lang)
                results.append({
                    "file_path": file_path,
                    "extracted_text": extracted_text,
                    "success": extracted_text is not None
                })
                self._send_ocr_result(file_path, extracted_text)
            
            return Message(
                id=str(uuid.uuid4()),
                type=MessageType.RESPONSE,
                topic=f"{message.topic}.response",
                data={
                    "results": results,
                    "total_processed": len(file_paths),
                    "request_id": message.id
                },
                priority=MessagePriority.NORMAL
            )
            
        except Exception as e:
            self.log("error", "513", e=str(e), body=str(message.data))
            return Message(
                id=str(uuid.uuid4()),
                type=MessageType.ERROR,
                topic=f"{message.topic}.error",
                data={
                    "error": str(e),
                    "request_id": message.id
                },
                priority=MessagePriority.HIGH
            )
    
    async def _handle_status_request(self, message: Message) -> Message:
        """상태 요청을 처리합니다."""
        try:
            status_data = {
                "manager_type": "OCRManager",
                "temp_manager_ready": self.temp_manager.is_ready if hasattr(self.temp_manager, 'is_ready') else True,
                "tesseract_configured": self.tesseract_cmd is not None,
                "tessdata_configured": self.tessdata_dir is not None,
                "monitoring_window_available": self.monitoring_window is not None,
                "timestamp": datetime.now().isoformat()
            }
            
            return Message(
                id=str(uuid.uuid4()),
                type=MessageType.RESPONSE,
                topic=f"{message.topic}.response",
                data=status_data,
                priority=MessagePriority.NORMAL
            )
            
        except Exception as e:
            self.log("error", "519", error=str(e))
            return Message(
                id=str(uuid.uuid4()),
                type=MessageType.ERROR,
                topic=f"{message.topic}.error",
                data={"error": str(e)},
                priority=MessagePriority.HIGH
            )

    async def start_modern_messaging(self):
        """현대적인 메시징 시스템을 시작합니다."""
        try:
            self.log("info", "351")  # Message consumption started
            print('OCR Manager started with modern messaging system')
            # The message handlers are already registered in _register_message_handlers
            # The global_message_bus will route messages to our handlers automatically
        except Exception as e:
            self.log("error", "532", e=str(e))
    
    async def stop_modern_messaging(self):
        """현대적인 메시징 시스템을 정지합니다."""
        try:
            # Unregister handlers
            global_message_bus.unregister_handler("ocr.extract_text")
            global_message_bus.unregister_handler("ocr.batch_process") 
            global_message_bus.unregister_handler("ocr.get_status")
            
            self.log("info", "352")  # Message consumption stopped
            print('OCR Manager stopped')
        except Exception as e:
            self.log("error", "532", e=str(e))

    def filter_documents(self, criteria):
        """문서 필터링."""
        try:
            if hasattr(self, 'main_window') and self.main_window:
                if hasattr(self.main_window, 'filter_table'):
                    result = self.main_window.filter_table(criteria)
                    self.log("info", "311")  # Document filtering successful
                    return result
                else:
                    self.log("warning", "416")  # Main window not properly configured
            else:
                self.log("warning", "408")  # monitoring_window is None
        except Exception as e:
            self.log("error", "501", e=str(e))
            self.show_message("error", "516")  # Document filtering error
