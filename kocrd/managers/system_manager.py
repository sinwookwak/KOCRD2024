# file_name: system_manager.py
import logging
import json
import sys
import os
from typing import Dict, Any, Optional
from PyQt5.QtWidgets import QMessageBox, QApplication
from PyQt5.QtCore import Qt # QMessageBox.StandardButtons 등을 위해 필요할 수 있습니다.
from kocrd.config.config import AppConfig, text_manager # AppConfig와 text_manager 임포트
from kocrd.config.message_broker import display_alert, display_warning, display_error,ask_question, confirm_delete,publish_system_event, subscribe 

from kocrd.config.system_constants import SystemConstants #상수

from kocrd.managers.ocr.ocr_manager import OCRManager
from kocrd.managers.temp_file_manager import TempFileManager
from kocrd.managers.database_manager import DatabaseManager
from kocrd.managers.document.document_manager import DocumentManager
from kocrd.Settings.settings_manager import SettingsManager
from kocrd.utils.embedding_utils import EmbeddingUtils 

try:
    import pytesseract
except ImportError:
    logging.warning("pytesseract is not installed. OCR functionalities might be limited.")
    pytesseract = None

class SystemManager:
    def __init__(self, settings_manager: SettingsManager, main_window=None):
        self.settings_manager = settings_manager
        self.main_window = main_window  # MainWindow 인스턴스 설정
        # Tesseract 경로는 AppConfig 또는 settings_manager에서 가져옴
        self.tesseract_cmd = AppConfig.OCR_SETTINGS.get("tesseract_cmd")
        self.tessdata_dir = AppConfig.OCR_SETTINGS.get("tessdata_dir")

        self.managers: Dict[str, Any] = {} # 매니저 인스턴스를 저장할 딕셔너리
        self.uis: Dict[str, Any] = {} # UI 컴포넌트 인스턴스를 저장할 딕셔너리 (_init_components가 UI를 처리할 경우)

        # 설정 파일 로드 (settings_manager를 통해 로드)
        # settings_manager가 development.json과 같은 메인 설정 파일을 로드한다고 가정
        self.config = self.settings_manager.load_config() # 메인 설정 파일 로드

        self.initialize_managers()
        self._configure_tesseract()
        logging.info(text_manager.get_log_text("345")) # "SystemManager initialization completed."

    def load_development_settings(self):
        # 이 메서드는 AppConfig와 별개로 설정을 로드합니다. 코드 구조 검토가 필요합니다.
        # 현재는 _init_components에서 사용하므로 유지합니다.
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'development.json')
        try:
            with open(config_path, 'r', encoding='utf-8') as f: # 인코딩 추가
                return json.load(f)
        except FileNotFoundError:
            logging.critical(f"Development settings file not found: {config_path}")
            raise
        except json.JSONDecodeError as e:
            logging.critical(f"Error decoding JSON from development settings file: {e}")
            raise
        except Exception as e:
            logging.critical(f"Unexpected error loading development settings file: {e}")
            raise

    def initialize_managers(self):
        """로드된 설정을 기반으로 매니저를 초기화합니다."""
        # self.config 또는 AppConfig.MANAGERS 사용 (settings_manager가 메인 config를 로드하므로 self.config 사용)
        manager_configs = self.config.get("managers", {})

        # 의존성 주입을 고려하여 매니저 인스턴스 생성
        manager_instances: Dict[str, Any] = {}
        for manager_name, manager_config in manager_configs.items():
             try:
                 manager_class = self.get_class(manager_config["module"], manager_config["class"])
                 kwargs = manager_config.get("kwargs", {})

                 # settings_manager 주입
                 if manager_config.get("inject_settings"):
                     # 생성자 인자로 settings_manager를 받는다고 가정
                     # kwargs에 추가하거나, 생성자 시그니처에 따라 직접 전달
                     # 여기서는 생성자 첫 인자로 settings_manager를 받는다고 가정하고 처리
                     # 실제 매니저 클래스의 __init__ 시그니처에 맞게 수정 필요
                     # 예: class MyManager: def __init__(self, settings_manager, ..., **kwargs): ...
                     manager_instances[manager_name] = manager_class(self.settings_manager, **kwargs)
                 else:
                     manager_instances[manager_name] = manager_class(**kwargs)

                 logging.debug(text_manager.get_log_text("358", manager_name=manager_name)) # "Created instance for manager '{manager_name}'."
             except (KeyError, ImportError, AttributeError) as e:
                  logging.error(text_manager.get_error_text("529", manager_name=manager_name, e=e)) # 매니저 초기화 실패 오류 메시지 추가 (예: 529)
                  # 심각도에 따라 sys.exit(1) 호출 고려
             except Exception as e:
                  logging.error(text_manager.get_error_text("530", manager_name=manager_name, e=e)) # 예상치 못한 오류 메시지 추가 (예: 530)
                  # sys.exit(1)

        # 생성된 인스턴스에 의존성 및 기타 객체 주입 (main_window, system_manager 등)
        for manager_name, manager_instance in manager_instances.items():
             manager_config = manager_configs.get(manager_name, {})
             # 의존성 주입
             for dep_name in manager_config.get("dependencies", []):
                 if dep_name in manager_instances:
                     # 의존성 주입 방식에 따라 수정 (속성 설정, 메서드 호출 등)
                     # 여기서는 속성 설정으로 가정
                     setattr(manager_instance, dep_name, manager_instances[dep_name])
                     logging.debug(text_manager.get_log_text("355", dep_name=dep_name, manager_name=manager_name)) # "Injected dependency '{dep_name}' into '{manager_name}'."
                 else:
                     logging.warning(text_manager.get_warning_text("409", dep_name=dep_name, manager_name=manager_name)) # 의존성 누락 경고 메시지 추가 (예: 409)

             # main_window 주입
             if manager_config.get("inject_main_window") and self.main_window:
                 setattr(manager_instance, "main_window", self.main_window)
                 logging.debug(text_manager.get_log_text("356", manager_name=manager_name)) # "Injected main_window into '{manager_name}'."

             # system_manager (self) 주입
             if manager_config.get("inject_system_manager"):
                 setattr(manager_instance, "system_manager", self)
                 logging.debug(text_manager.get_log_text("357", manager_name=manager_name)) # "Injected system_manager into '{manager_name}'."

             self.managers[manager_name] = manager_instance
             logging.info(text_manager.get_log_text("328", component_type="Manager", component_name=manager_name)) # 초기화 완료 로그 (text_manager 사용)

    def get_temp_file_manager(self):
        return self.managers.get("temp_file")

    def get_database_manager(self):
        return self.managers.get("database")

    def _configure_tesseract(self):
        """Tesseract 경로를 설정합니다."""
        # Tesseract 경로는 AppConfig 또는 settings_manager에서 가져옴
        tesseract_cmd = AppConfig.OCR_SETTINGS.get("tesseract_cmd", self.tesseract_cmd)
        tessdata_dir = AppConfig.OCR_SETTINGS.get("tessdata_dir", self.tessdata_dir)

        if tesseract_cmd:
             pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
             logging.info(text_manager.get_log_text("342", tesseract_cmd=tesseract_cmd)) # "Tesseract configuration completed: {tesseract_cmd}"
        else:
             logging.warning(text_manager.get_warning_text("410")) # tesseract_cmd 누락 경고 메시지 추가 (예: 410)

        if tessdata_dir:
            pytesseract.pytesseract.tessdata_dir = tessdata_dir
            logging.info(text_manager.get_log_text("343", tessdata_dir=tessdata_dir)) # "Tessdata configuration completed: {tessdata_dir}"

    def _process_document(self, message: Dict[str, Any]):
        """문서 처리 메시지를 처리합니다."""
        file_paths = message.get("file_paths", [])
        if not file_paths:
            logging.warning(text_manager.get_warning_text("403")) # text_manager 사용
            return
        document_manager = self.get_manager("document")
        if document_manager:
            for file_path in file_paths:
                document_manager.load_document(file_path) # DocumentManager에 load_document 메서드가 있다고 가정
            logging.info(text_manager.get_log_text("344", file_paths=file_paths)) # "Document processing completed for {file_paths}"
        else:
            logging.error(text_manager.get_error_text("528")) # DocumentManager 누락 오류 메시지 추가 (예: 528)

    def _process_database_packaging(self, message: Dict[str, Any]):
        """데이터베이스 패키징 메시지를 처리합니다."""
        database_manager = self.get_manager("database")
        if database_manager:
            database_manager.package_database() # DatabaseManager에 package_database 메서드가 있다고 가정
            logging.info(text_manager.get_log_text("330")) # text_manager 사용
        else:
            logging.error(text_manager.get_error_text("522")) # text_manager 사용

    def _process_ai_training(self, message: Dict[str, Any]):
        """AI 학습 메시지를 처리합니다."""
        ai_trainer = self.get_manager("ai_trainer") # config에서 매니저 이름이 'ai_trainer'라고 가정
        if ai_trainer:
            ai_trainer.train_ai(message) # AITrainer에 train_ai 메서드가 있다고 가정
            logging.info(text_manager.get_log_text("347")) # "AI training completed."
        else:
            logging.error(text_manager.get_error_text("529")) # AITrainer 누락 오류 메시지 추가 (예: 529)

    def _process_temp_file_manager(self, message: Dict[str, Any]):
        """임시 파일 관리 메시지를 처리합니다."""
        temp_file_manager = self.get_manager("temp_file")
        if temp_file_manager:
            temp_file_manager.handle_message(message) # TempFileManager에 handle_message 메서드가 있다고 가정
            logging.info(text_manager.get_log_text("315")) # text_manager 사용 (기존 ID 유지)
        else:
            logging.error(text_manager.get_error_text("534")) # TempFileManager 누락 오류 메시지 추가 (예: 534)

    def _process_ai_prediction(self, message: Dict[str, Any]):
        """AI 예측 메시지를 처리합니다."""
        ai_prediction_manager = self.get_manager("ai_prediction")
        if ai_prediction_manager:
            ai_prediction_manager.handle_message(message) # AIPredictionManager에 handle_message 메서드가 있다고 가정
            logging.info(text_manager.get_log_text("348")) # "AI prediction processed."
        else:
            logging.error(text_manager.get_error_text("535")) # AIPredictionManager 누락 오류 메시지 추가 (예: 535)

    def _process_ai_event(self, message: Dict[str, Any]):
        """AI 이벤트 메시지를 처리합니다."""
        # AI 이벤트 매니저가 있거나 AI 예측/모델 매니저가 처리한다고 가정
        # 여기서는 AI 예측 매니저가 이벤트를 처리한다고 가정
        ai_prediction_manager = self.get_manager("ai_prediction")
        if ai_prediction_manager:
            ai_prediction_manager.handle_ai_event(message) # handle_ai_event 메서드가 있다고 가정
            logging.info(text_manager.get_log_text("354", message="AI event processed")) # "System process completed: AI event processed" (일반적인 로그)
        else:
            logging.error(text_manager.get_error_text("536")) # AI 이벤트 핸들러 누락 오류 메시지 추가 (예: 536)

    def _process_ai_ocr_running(self, message: Dict[str, Any]):
        """AI OCR 실행 메시지 (OCR 결과 처리)를 처리합니다."""
        ocr_manager = self.get_manager("ocr")
        if ocr_manager:
            ocr_manager.handle_ocr_result(message) # OCRManager가 결과를 처리한다고 가정
            logging.info(text_manager.get_log_text("350")) # "AI OCR result handled."
        else:
            logging.error(text_manager.get_error_text("537")) # OCR Manager 누락 오류 메시지 추가 (예: 537)

    def display_message_box(self, message_type: str, title_key: str, message_key: str,
                            detail_info: Optional[str] = None,
                            buttons_type: Optional[str] = None,
                            delete_target: Optional[str] = None,
                            show_do_not_show_again: bool = False) -> str:

        if not self.main_window:
            logging.error(text_manager.get_error_text("542", message="Main window instance not available to display message box."))
            title = text_manager.get_general_text(title_key)
            message = text_manager.get_general_text(message_key)
            logging.error(f"UI Error (No MainWindow): {title} - {message} {f'Details: {detail_info}' if detail_info else ''}")
            return SystemConstants.EventResults.CANCEL # UI 없이 진행될 경우 기본 반환값

        # MessageBroker의 공개 함수를 직접 호출
        if message_type == SystemConstants.EventTypes.ALERT:
            return display_alert(self.main_window, message_key, title_key, detail_info, show_do_not_show_again)
        elif message_type == SystemConstants.EventTypes.WARNING:
            return display_warning(self.main_window, message_key, title_key, detail_info, show_do_not_show_again)
        elif message_type == SystemConstants.EventTypes.ERROR:
            return display_error(self.main_window, message_key, title_key, detail_info, show_do_not_show_again)
        elif message_type == SystemConstants.EventTypes.QUESTION:
            return ask_question(self.main_window, message_key, title_key, detail_info, buttons_type, show_do_not_show_again)
        elif message_type == SystemConstants.EventTypes.CONFIRM_DELETE:
            return confirm_delete(self.main_window, delete_target if delete_target else text_manager.get_general_text("selected_item_default"), message_key, detail_info, show_do_not_show_again)
        else:
            logging.warning(text_manager.get_warning_text("415", message_type=message_type))
            return display_alert(self.main_window, message_key, title_key, detail_info, show_do_not_show_again) # 알 수 없는 유형은 기본 알림으로

    # --- 공개 메서드 ---

    def start_message_consumption(self):
        """RabbitMQ 메시지 소비 루프를 시작합니다."""
        if not self.rabbitmq_channel:
            logging.error(text_manager.get_error_text("538")) # 채널 설정 오류 메시지 추가 (예: 538)
            return

        try:
            self.rabbitmq_channel.basic_qos(prefetch_count=1)

            # 큐 이름과 해당 내부 처리 메서드 이름 매핑
            # AppConfig.QUEUES의 큐 이름과 SystemManager의 _process_* 메서드 이름을 연결
            queue_handlers = {
                AppConfig.QUEUES.get("document_processing", {}).get("name"): "_process_document",
                AppConfig.QUEUES.get("database_packaging", {}).get("name"): "_process_database_packaging",
                AppConfig.QUEUES.get("ai_training_queue", {}).get("name"): "_process_ai_training",
                AppConfig.QUEUES.get("temp_file_queue", {}).get("name"): "_process_temp_file_manager",
                AppConfig.QUEUES.get("prediction_requests", {}).get("name"): "_process_ai_prediction", # 예측 요청 처리
                AppConfig.QUEUES.get("ai_result_handling", {}).get("name"): "_process_ai_ocr_running", # OCR/AI 결과 처리
                # 다른 큐와 해당 핸들러 메서드 이름 추가
                # AppConfig.QUEUES.get("events_queue", {}).get("name"): "_process_ai_event", # 이벤트 큐 처리
                # AppConfig.QUEUES.get("ui_feedback_requests", {}).get("name"): "_process_ui_feedback", # UI 피드백 처리 메서드 필요
                # AppConfig.QUEUES.get("result", {}).get("name"): "_process_result", # 결과 큐 처리 메서드 필요
                # AppConfig.QUEUES.get("feedback_queue", {}).get("name"): "_process_feedback", # 피드백 큐 처리 메서드 필요
            }

            for queue_name, handler_method_name in queue_handlers.items():
                 if queue_name and handler_method_name:
                     # _handle_process를 호출하는 콜백 생성
                     callback = self._process_message_callback(
                         # 람다를 사용하여 _handle_process에 handler_method_name 전달
                         lambda ch, method, props, body, h=handler_method_name: self._handle_process(ch, method, props, body, h)
                     )
                     self.rabbitmq_channel.basic_consume(
                         queue=queue_name,
                         on_message_callback=callback,
                         auto_ack=False
                     )
                     logging.info(f"🟢 Started consuming from queue: {queue_name}")
                 elif not queue_name:
                     logging.warning(text_manager.get_warning_text("411")) # 설정에 큐 이름 누락 경고 메시지 추가 (예: 411)
                 else:
                     logging.warning(text_manager.get_warning_text("412", queue_name=queue_name)) # 핸들러 메서드 이름 누락 경고 메시지 추가 (예: 412)

            logging.info(text_manager.get_log_text("351")) # "Message consumption started."
            self.rabbitmq_channel.start_consuming()

        except KeyboardInterrupt:
            logging.info(text_manager.get_log_text("352")) # "Message consumption stopped."
        except Exception as e:
            logging.error(text_manager.get_error_text("539", e=e)) # 메시지 소비 중 오류 메시지 추가 (예: 539)
        finally:
            self.close_rabbitmq_connection()


    def database_packaging(self):
        """데이터베이스 매니저를 통해 데이터베이스 패키징을 트리거합니다."""
        db_manager = self.get_manager("database")
        if db_manager:
            db_manager.package_database() # DatabaseManager에 package_database 메서드가 있다고 가정
        else:
            logging.error(text_manager.get_error_text("522")) # text_manager 사용

    def trigger_process(self, process_type: str, data: Optional[Dict[str, Any]] = None):
        """프로세스 유형에 따라 적절한 매니저로 요청을 라우팅합니다."""
        if process_type == "database_packaging":
            db_manager = self.get_manager("database")
            if db_manager:
                db_manager.request_database_packaging(data)
                publish_system_event("database_packaged", status="success", timestamp=datetime.now().isoformat())
            else:
                logging.error(text_manager.get_error_text("522"))
                self.display_message_box(SystemConstants.EventTypes.ERROR,"501","522",)

        elif process_type == "document_processing":
            doc_manager = self.get_manager("document")
            if doc_manager:
                doc_manager.request_document_processing(data)
                publish_system_event("document_processed", doc_id=data.get("id"), status="completed")
            else:
                logging.error(text_manager.get_error_text("528"))
                self.display_message_box(SystemConstants.EventTypes.ERROR,"501","528",)

        elif process_type == "ai_training":
            ai_trainer = self.get_manager("ai_trainer")
            if ai_trainer:
                ai_trainer.request_ai_training(data)
                publish_system_event("ai_training_completed", model_type=data.get("model_type"))
            else:
                logging.error(text_manager.get_error_text("529"))
                self.display_message_box(
                    SystemConstants.EventTypes.ERROR,"501","529",)

        elif process_type == "generate_text":
            ai_prediction_manager = self.get_manager("ai_prediction")
            if ai_prediction_manager:
                result = ai_prediction_manager.generate_text(data.get("command", ""))
                publish_system_event("text_generated", result_len=len(result))
                return result
            else:
                logging.error(text_manager.get_error_text("526"))
                self.display_message_box(SystemConstants.EventTypes.ERROR,"501","526",)
                return text_manager.get_error_text("526")

        else:
            logging.warning(text_manager.get_warning_text("404", message_type=process_type))
            self.display_message_box(SystemConstants.EventTypes.WARNING,"501","404",detail_info=f"Type: {process_type}")

    def handle_error(self, message_key: str, error_detail: str = None, title_key: str = "501"): # 오류를 로깅하고 SystemManager를 통해 메시지 박스를 표시합니다.
        log_message = text_manager.get_error_text(message_key, error=error_detail)
        logging.error(log_message)
        display_error(self.main_window,message_key,title_key,detail_info=error_detail)

    def run_embedding_generation(self):
        """임베딩 생성을 트리거합니다."""
        # EmbeddingUtils가 유틸리티 클래스라고 가정
        EmbeddingUtils.run_embedding_generation(self.settings_manager)
        logging.info(text_manager.get_log_text("354", message="Embedding generation triggered")) # "System process completed: Embedding generation triggered" (일반적인 로그)

    def close_rabbitmq_connection(self):
        """RabbitMQ 연결을 종료합니다."""
        if self.rabbitmq_connection and self.rabbitmq_connection.is_open:
            self.rabbitmq_connection.close()
            logging.info(text_manager.get_log_text("353")) # "RabbitMQ connection closed."

    def get_ai_manager(self):
        """AI 예측 매니저 인스턴스를 가져옵니다."""
        return self.managers.get("ai_prediction")

    def get_manager(self, manager_name: str) -> Optional[Any]:
        """이름으로 매니저 인스턴스를 가져옵니다."""
        manager = self.managers.get(manager_name)
        if manager is None:
             logging.warning(text_manager.get_warning_text("413", manager_name=manager_name)) # 요청된 매니저 누락 경고 메시지 추가 (예: 413)
        return manager

    def get_ui(self, ui_name: str) -> Optional[Any]:
        """이름으로 UI 컴포넌트 인스턴스를 가져옵니다."""
        # _init_components가 self.uis를 채운다고 가정
        ui_component = self.uis.get(ui_name)
        if ui_component is None:
             logging.warning(text_manager.get_warning_text("414", ui_name=ui_name)) # 요청된 UI 컴포넌트 누락 경고 메시지 추가 (예: 414)
        return ui_component

    def get_ai_model_manager(self):
        """AI 모델 매니저 인스턴스를 가져옵니다."""
        return self.managers.get("ai_model")

    def get_class(self, module_name: str, class_name: str):
        """모듈에서 클래스를 동적으로 임포트하고 반환합니다."""
        try:
            module = __import__(module_name, fromlist=[class_name])
            return getattr(module, class_name)
        except ImportError:
            logging.error(text_manager.get_error_text("539", module_name=module_name)) # 모듈 임포트 오류 메시지 추가 (예: 539)
            raise
        except AttributeError:
            logging.error(text_manager.get_error_text("540", class_name=class_name, module_name=module_name)) # 클래스 누락 오류 메시지 추가 (예: 540)
            raise
        except Exception as e:
            logging.error(text_manager.get_error_text("541", class_name=class_name, module_name=module_name, e=e)) # 예상치 못한 클래스 로드 오류 메시지 추가 (예: 541)
            raise

# main_window 모듈을 나중에 임포트
from kocrd.window.main_window import MainWindow