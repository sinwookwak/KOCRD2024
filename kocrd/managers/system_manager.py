# file_name: system_manager.py
import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMessageBox, QApplication

from kocrd.config.config import AppConfig, text_manager
from kocrd.config.message_broker import (
    display_alert, display_warning, display_error, ask_question, 
    confirm_delete, publish_system_event, subscribe
)
from kocrd.config.system_constants import SystemConstants
from kocrd.managers.database_manager import DatabaseManager
from kocrd.managers.document.document_manager import DocumentManager
from kocrd.managers.ocr.ocr_manager import OCRManager
from kocrd.managers.unified_temp_manager import UnifiedTempManager
from kocrd.setting.settings_manager import SettingsManager
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
        logging.info(text_manager.get_log_text("345")) # 345: "SystemManager initialization completed"

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
        manager_configs = self.config.get(SystemConstants.ConfigKeys.MANAGERS, {})

        # 의존성 주입을 고려하여 매니저 인스턴스 생성
        manager_instances: Dict[str, Any] = {}
        failed_managers = []

        for manager_name, manager_config in manager_configs.items():
            try:
                manager_class = self._get_manager_class(manager_config)
                manager_instance = self._create_manager_instance(
                    manager_class, manager_config, manager_name
                )
                manager_instances[manager_name] = manager_instance
                logging.debug(
                    text_manager.get_log_text("358", manager_name=manager_name)
                )
            except (KeyError, ImportError, AttributeError) as e:
                error_msg = text_manager.get_error_text("529", manager_name=manager_name, e=e)
                logging.error(error_msg)
                failed_managers.append(manager_name)
            except Exception as e:
                error_msg = text_manager.get_error_text("530", manager_name=manager_name, e=e)
                logging.error(error_msg)
                failed_managers.append(manager_name)

        if failed_managers:
            logging.warning(f"Failed to initialize managers: {', '.join(failed_managers)}")

        self._inject_dependencies(manager_instances, manager_configs)

    def _get_manager_class(self, manager_config: Dict[str, Any]):
        """매니저 설정에서 클래스를 가져옵니다."""
        module_name = manager_config[SystemConstants.ConfigKeys.MODULE]
        class_name = manager_config[SystemConstants.ConfigKeys.CLASS]
        return self.get_class(module_name, class_name)

    def _create_manager_instance(self, manager_class, manager_config: Dict[str, Any], manager_name: str):
        """매니저 인스턴스를 생성합니다."""
        kwargs = manager_config.get(SystemConstants.ConfigKeys.KWARGS, {})
        
        if manager_config.get(SystemConstants.ConfigKeys.INJECT_SETTINGS):
            return manager_class(self.settings_manager, **kwargs)
        else:
            return manager_class(**kwargs)

    def _inject_dependencies(self, manager_instances: Dict[str, Any], manager_configs: Dict[str, Any]):
        """매니저 인스턴스들에 의존성을 주입합니다."""
        for manager_name, manager_instance in manager_instances.items():
            manager_config = manager_configs.get(manager_name, {})
            
            # 의존성 주입
            self._inject_manager_dependencies(
                manager_instance, manager_config, manager_instances, manager_name
            )
            
            # main_window 주입
            if manager_config.get(SystemConstants.ConfigKeys.INJECT_MAIN_WINDOW) and self.main_window:
                setattr(manager_instance, "main_window", self.main_window)
                logging.debug(text_manager.get_log_text("356", manager_name=manager_name))

            # system_manager (self) 주입
            if manager_config.get(SystemConstants.ConfigKeys.INJECT_SYSTEM_MANAGER):
                setattr(manager_instance, "system_manager", self)
                logging.debug(text_manager.get_log_text("357", manager_name=manager_name))

            self.managers[manager_name] = manager_instance
            logging.info(text_manager.get_log_text("328", component_type="Manager", component_name=manager_name))

    def _inject_manager_dependencies(self, manager_instance, manager_config: Dict[str, Any], 
                                   manager_instances: Dict[str, Any], manager_name: str):
        """개별 매니저의 의존성을 주입합니다."""
        for dep_name in manager_config.get(SystemConstants.ConfigKeys.DEPENDENCIES, []):
            if dep_name in manager_instances:
                setattr(manager_instance, dep_name, manager_instances[dep_name])
                logging.debug(text_manager.get_log_text("355", dep_name=dep_name, manager_name=manager_name))
            else:
                logging.warning(text_manager.get_warning_text("409", dep_name=dep_name, manager_name=manager_name))

    def _execute_manager_operation(self, manager_name: str, operation_name: str, 
                                 *args, error_code: str = "500", **kwargs) -> bool:
        """매니저에서 지정된 작업을 실행하는 공통 헬퍼 메서드."""
        manager = self.get_manager(manager_name)
        if manager:
            try:
                operation = getattr(manager, operation_name)
                operation(*args, **kwargs)
                return True
            except AttributeError:
                logging.error(f"Manager '{manager_name}' does not have operation '{operation_name}'")
                return False
            except Exception as e:
                logging.error(f"Error executing {operation_name} on {manager_name}: {e}")
                return False
        else:
            logging.error(text_manager.get_error_text(error_code))
            return False

    def get_temp_file_manager(self):
        return self.managers.get(SystemConstants.ManagerNames.TEMP_FILE)

    def get_database_manager(self):
        return self.managers.get(SystemConstants.ManagerNames.DATABASE)

    def _configure_tesseract(self):
        """Tesseract 경로를 설정합니다."""
        # Tesseract 경로는 AppConfig 또는 settings_manager에서 가져옴
        tesseract_cmd = AppConfig.OCR_SETTINGS.get("tesseract_cmd", self.tesseract_cmd)
        tessdata_dir = AppConfig.OCR_SETTINGS.get("tessdata_dir", self.tessdata_dir)

        if tesseract_cmd:
             pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
             logging.info(text_manager.get_log_text("342", tesseract_cmd=tesseract_cmd)) # "Tesseract configuration completed: {tesseract_cmd}"
        else:
             logging.warning(text_manager.get_warning_text("410")) # 410: "Tesseract command path..."

        if tessdata_dir:
            pytesseract.pytesseract.tessdata_dir = tessdata_dir
            logging.info(text_manager.get_log_text("343", tessdata_dir=tessdata_dir)) # "Tessdata configuration completed: {tessdata_dir}"

    def _process_document(self, message: Dict[str, Any]):
        """문서 처리 메시지를 처리합니다."""
        file_paths = message.get("file_paths", [])
        if not file_paths:
            logging.warning(text_manager.get_warning_text("403")) # 403: "No file path provided"
            return
        document_manager = self.get_manager(SystemConstants.ManagerNames.DOCUMENT)
        if document_manager:
            for file_path in file_paths:
                document_manager.load_document(file_path) # DocumentManager에 load_document 메서드가 있다고 가정
            logging.info(text_manager.get_log_text("344", file_paths=file_paths)) # "Document processing completed for {file_paths}"
        else:
            logging.error(text_manager.get_error_text("528")) # 528: "DocumentManager not found"

    def _process_database_packaging(self, message: Dict[str, Any]):
        """데이터베이스 패키징 메시지를 처리합니다."""
        if self._execute_manager_operation(
            SystemConstants.ManagerNames.DATABASE, 
            "package_database",  # DatabaseManager에 package_database 메서드가 있다고 가정
            error_code="522"
        ):
            logging.info(text_manager.get_log_text("330")) # 330: "Database packaging..."

    def _process_ai_training(self, message: Dict[str, Any]):
        """AI 학습 메시지를 처리합니다."""
        ai_trainer = self.get_manager(SystemConstants.ManagerNames.AI_TRAINER) # config에서 매니저 이름이 'ai_trainer'라고 가정
        if ai_trainer:
            ai_trainer.train_ai(message) # AITrainer에 train_ai 메서드가 있다고 가정
            logging.info(text_manager.get_log_text("347")) # 347: "AI training completed"
        else:
            logging.error(text_manager.get_error_text("529")) # 529: "Failed to create instance..."

    def _process_temp_file_manager(self, message: Dict[str, Any]):
        """임시 파일 관리 메시지를 처리합니다."""
        temp_file_manager = self.get_manager(SystemConstants.ManagerNames.TEMP_FILE)
        if temp_file_manager:
            temp_file_manager.handle_message(message) # TempFileManager에 handle_message 메서드가 있다고 가정
            logging.info(text_manager.get_log_text("315")) # 315: "Temporary files cleaned up"
        else:
            logging.error(text_manager.get_error_text("534")) # 534: "TempFileManager not found"

    def _process_ai_prediction(self, message: Dict[str, Any]):
        """AI 예측 메시지를 처리합니다."""
        ai_prediction_manager = self.get_manager(SystemConstants.ManagerNames.AI_PREDICTION)
        if ai_prediction_manager:
            ai_prediction_manager.handle_message(message) # AIPredictionManager에 handle_message 메서드가 있다고 가정
            logging.info(text_manager.get_log_text("348")) # 348: "AI prediction processed"
        else:
            logging.error(text_manager.get_error_text("535")) # 535: "AIPredictionManager..."

    def _process_ai_event(self, message: Dict[str, Any]):
        """AI 이벤트 메시지를 처리합니다."""
        # AI 이벤트 매니저가 있거나 AI 예측/모델 매니저가 처리한다고 가정
        # 여기서는 AI 예측 매니저가 이벤트를 처리한다고 가정
        ai_prediction_manager = self.get_manager(SystemConstants.ManagerNames.AI_PREDICTION)
        if ai_prediction_manager:
            ai_prediction_manager.handle_ai_event(message) # handle_ai_event 메서드가 있다고 가정
            logging.info(text_manager.get_log_text("354", message="AI event processed")) # "System process completed: AI event processed" (일반적인 로그)
        else:
            logging.error(text_manager.get_error_text("536")) # AI 이벤트 핸들러 누락 오류 메시지 추가 (예: 536)

    def _process_ai_ocr_running(self, message: Dict[str, Any]):
        """AI OCR 실행 메시지 (OCR 결과 처리)를 처리합니다."""
        ocr_manager = self.get_manager(SystemConstants.ManagerNames.OCR)
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
            return confirm_delete(self.main_window, delete_target if delete_target else text_manager.get_general_text("265"), message_key, detail_info, show_do_not_show_again)  # 265: "selected item"
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
        self._execute_manager_operation(
            SystemConstants.ManagerNames.DATABASE, 
            "package_database",  # DatabaseManager에 package_database 메서드가 있다고 가정
            error_code="522"
        )

    def trigger_process(self, process_type: str, data: Optional[Dict[str, Any]] = None):
        """프로세스 유형에 따라 적절한 매니저로 요청을 라우팅합니다."""
        if process_type == "database_packaging":
            db_manager = self.get_manager(SystemConstants.ManagerNames.DATABASE)
            if db_manager:
                db_manager.request_database_packaging(data)
                publish_system_event("database_packaged", status="success", timestamp=datetime.now().isoformat())
            else:
                logging.error(text_manager.get_error_text("522"))
                self.display_message_box(SystemConstants.EventTypes.ERROR,"501","522",)

        elif process_type == "document_processing":
            doc_manager = self.get_manager(SystemConstants.ManagerNames.DOCUMENT)
            if doc_manager:
                doc_manager.request_document_processing(data)
                publish_system_event("document_processed", doc_id=data.get("id"), status="completed")
            else:
                logging.error(text_manager.get_error_text("528"))
                self.display_message_box(SystemConstants.EventTypes.ERROR,"501","528",)

        elif process_type == "ai_training":
            ai_trainer = self.get_manager(SystemConstants.ManagerNames.AI_TRAINER)
            if ai_trainer:
                ai_trainer.request_ai_training(data)
                publish_system_event("ai_training_completed", model_type=data.get("model_type"))
            else:
                logging.error(text_manager.get_error_text("529"))
                self.display_message_box(
                    SystemConstants.EventTypes.ERROR,"501","529",)

        elif process_type == "generate_text":
            ai_prediction_manager = self.get_manager(SystemConstants.ManagerNames.AI_PREDICTION)
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
        return self.managers.get(SystemConstants.ManagerNames.AI_PREDICTION)

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
        return self.managers.get(SystemConstants.ManagerNames.AI_MODEL)

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
# Removed MainWindow import to avoid circular import - will import when needed