# file_name: settings_manager.py
import os
import json
import tempfile
import logging
import pika
import time
import sys
from PyQt5.QtWidgets import QDialog, QMessageBox, QFileDialog
from ui.SettingsDialogUI import SettingsDialogUI
from typing import Union, List, Tuple, Callable, Dict, Optional
from pika.exceptions import AMQPConnectionError

class SettingsManager:
    """설정 관리 클래스."""
    def __init__(self, config_file="config/development.json"): # 기본값 설정
        self.config_file = config_file
        self.config = self.load_config()
        self.settings: Dict[str, Union[str, int, list, dict]] = {} # type hint 추가
        self.load_config()
        self.connection: Optional[pika.BlockingConnection] = None # 메시지 큐 연결 객체 추가
        self.channel: Optional[pika.BlockingConnection] = None

    def load_config(self):
        """JSON 설정 파일을 로드합니다."""
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logging.error(f"설정 파일 '{self.config_file}'을 찾을 수 없습니다.")
            sys.exit(1)
        except json.JSONDecodeError as e:
            logging.error(f"설정 파일 파싱 오류: {e}")
            sys.exit(1)
        except Exception as e:
            logging.error(f"설정 파일 로드 중 오류: {e}")
            sys.exit(1)

    def load_from_env(self):
        """환경 변수에서 설정을 로드합니다."""
        env_vars: dict[str, Tuple[Callable, Union[str, int, list, dict]]] = {
            "MAX_FILE_SIZE": (int, 10 * 1024 * 1024),
            "DEFAULT_REPORT_FILENAME": (str, "report.txt"),
            "DEFAULT_EXCEL_FILENAME": (str, "documents.xlsx"),
            "VALID_FILE_EXTENSIONS": (json.loads, [".txt", ".pdf", ".png", ".jpg", ".xlsx", ".docx"]),
            "MODEL_PATH": (str, r"F:\AI-M1\model\Korean_CNN_model(97.8).h5"),
            "document_embedding_path": (str, r"F:\AI-M1\model\document_embedding.json"),
            "document_types_path": (str, r"F:\AI-M1\model\document_types.json"),
            "temp_dir": (str, tempfile.gettempdir()),
            # 메시지 큐 설정 추가
            "RABBITMQ_HOST": (str, "localhost"),
            "RABBITMQ_PORT": (int, 5672),
            "RABBITMQ_QUEUE": (str, "task_queue"),
            "RABBITMQ_USER": (str, "guest"),
            "RABBITMQ_PASSWORD": (str, "guest")
        }
        for var_name, (cast_func, default_value) in env_vars.items():
            env_value = os.environ.get(var_name)
            try:
                self.settings[var_name] = cast_func(env_value) if env_value is not None else default_value
                log_message = f"Loaded {var_name} from {'environment' if env_value is not None else 'default'}: {self.settings[var_name]}"
                logging.info(log_message)
            except (ValueError, json.JSONDecodeError, TypeError) as e:  # TypeError 추가
                logging.warning(f"Invalid {var_name} environment variable: {e}. Using default.")
                self.settings[var_name] = default_value
    def set_defaults(self):
        """기본 설정값을 설정합니다."""
        self.settings = {
            "MAX_FILE_SIZE": 10 * 1024 * 1024,
            "DEFAULT_REPORT_FILENAME": "report.txt",
            "DEFAULT_EXCEL_FILENAME": "documents.xlsx",
            "VALID_FILE_EXTENSIONS": [".txt", ".pdf", ".png", ".jpg", ".xlsx", ".docx"],
            "MODEL_PATH": r"F:\AI-M1\model\Korean_CNN_model(97.8).h5", # 기본 모델 경로 설정
            "document_embedding_path": r"F:\AI-M1\model\document_embedding.",
            "document_types_path": r"F:\AI-M1\model\document_types.json",
            "temp_dir": tempfile.gettempdir(),
            # 메시지 큐 설정 추가
            "RABBITMQ_HOST": "localhost",
            "RABBITMQ_PORT": 5672,
            "RABBITMQ_QUEUE": "task_queue",
            "RABBITMQ_USER": "guest",
            "RABBITMQ_PASSWORD": "guest",
            "RABBITMQ_EVENTS_QUEUE": "events_queue", # events queue 추가
            "RABBITMQ_PREDICTION_REQUESTS_QUEUE" : "prediction_requests_queue", # prediction_requests_queue 추가
            "RABBITMQ_PREDICTION_RESULTS_QUEUE" : "prediction_results_queue", # prediction_results_queue 추가
            "RABBITMQ_FEEDBACK_QUEUE": "feedback_queue" # feedback queue 추가

        }
        self.set_rabbitmq_defaults() # rabbitmq 설정 추가

    def set_rabbitmq_defaults(self):
        """RabbitMQ 기본 설정값을 설정합니다."""
        self.rabbitmq_settings = {
            "RABBITMQ_HOST": "localhost",
            "RABBITMQ_PORT": 5672,
            "RABBITMQ_USER": "guest",
            "RABBITMQ_PASSWORD": "guest",
            "RABBITMQ_EVENTS_QUEUE": "events_queue",
            "RABBITMQ_PREDICTION_REQUESTS_QUEUE": "prediction_requests_queue",
            "RABBITMQ_PREDICTION_RESULTS_QUEUE": "prediction_results_queue",
            "RABBITMQ_FEEDBACK_QUEUE": "feedback_queue"
        }
        self.settings.update(self.rabbitmq_settings) # settings에 rabbitmq 설정 추가

    def get_setting(self, setting_name: str, default: Union[str, int, list, dict, None] = None) -> Union[str, int, list, dict, None]:
        """설정 값을 반환합니다."""
        return self.settings.get(setting_name, default)

    def set_setting(self, setting_name: str, value: Union[str, int, list, dict]) -> None:
        """설정 값을 설정하고 저장합니다."""
        self.settings[setting_name] = value
        self.save_settings()

    def save_settings(self):
        """설정을 파일에 저장합니다."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=4)
            logging.info(f"Settings saved to {self.config_file}")
        except Exception as e:
            logging.error(f"설정 파일 저장 오류: {e}")

    def get_setting_path(self, setting_name: str) -> Union[str, None]:
        """경로 관련 설정을 반환합니다."""
        return self.get_setting(setting_name)

    def get_temp_dir(self) -> str:
        """임시 디렉토리 경로를 반환합니다."""
        return self.get_setting("temp_dir")

    def set_temp_dir(self, temp_dir: str) -> None:
        """임시 디렉토리 경로를 설정합니다."""
        self.set_setting("temp_dir", temp_dir)
        logging.info(f"Temporary directory set to {temp_dir}")

    def open_settings_dialog(self, parent=None):
        """설정 다이얼로그를 엽니다."""
        logging.info(f"Opening settings dialog. Parent: {parent}")
        dialog = SettingsDialogUI(settings_manager=self, parent=parent)
        dialog.exec_()

    def set_file_path(self, parent, setting_name: str, file_filter: str = "All Files (*)",
                      engine_attr_name: str = None, init_func: Callable = None, open_file: bool = False):
        """파일 경로를 설정하고, 필요시 데이터베이스 엔진을 초기화합니다."""
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog

        file_dialog = QFileDialog.getOpenFileName if open_file else QFileDialog.getSaveFileName
        file_path, _ = file_dialog(parent, "파일 선택" if open_file else "파일 경로 선택", "", file_filter, options=options)

        if file_path:
            old_path = self.get_setting(setting_name)
            self.set_setting(setting_name, file_path)
            logging.info(f"{setting_name} path updated to: {file_path}")

            if engine_attr_name and init_func:
                try:
                    # 데이터베이스 엔진 초기화 로직 (필요한 경우 구현)
                    # new_engine = create_engine(f'sqlite:///{file_path}')
                    # setattr(parent, engine_attr_name, new_engine)
                    # init_func(new_engine)
                    QMessageBox.information(parent, "성공", f"새로운 경로가 설정되었습니다:\n{file_path}")
                except Exception as e:
                    logging.error(f"데이터베이스 엔진 초기화 실패: {e}")
                    QMessageBox.critical(parent, "오류", f"데이터베이스 엔진 초기화에 실패했습니다: {e}")
                    self.set_setting(setting_name, old_path)  # 설정 롤백
                    logging.info(f"{setting_name} path reverted to: {old_path}")
        else:
            logging.info(f"{setting_name} path selection cancelled.")

    def connect_to_rabbitmq(self) -> Tuple[pika.BlockingConnection, pika.channel.Channel]:
        """RabbitMQ에 연결하고 연결 객체와 채널 객체를 반환합니다."""
        try:
            host = self.get_setting("RABBITMQ_HOST")
            port = int(self.get_setting("RABBITMQ_PORT"))
            user = self.get_setting("RABBITMQ_USER")
            password = self.get_setting("RABBITMQ_PASSWORD")
            virtual_host = self.get_setting("RABBITMQ_VIRTUAL_HOST", "/")  # virtual_host 설정 가져오기, 기본값 '/'
            credentials = pika.PlainCredentials(user, password)

            parameters = pika.ConnectionParameters(
                host=host,
                port=port,
                virtual_host=virtual_host,  # virtual_host 설정
                credentials=credentials
            )

            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            logging.info(f"Connected to RabbitMQ: {host}:{port}:{virtual_host}")  # virtual_host 로깅 추가
            return connection, channel

        except AMQPConnectionError as e:
            logging.error(f"Failed to connect to RabbitMQ: {e}")
            return None, None
        except Exception as e:
            logging.error(f"RabbitMQ 연결 중 오류 발생: {e}")
            return None, None

    def send_message(self, queue_name: str, message: str):
        """메시지를 지정된 RabbitMQ 큐에 보냅니다."""
        connection, channel = self.connect_to_rabbitmq()
        if channel is None:
            logging.error("RabbitMQ 연결 실패. 메시지 전송 불가")
            return

        try:
            channel.queue_declare(queue=queue_name)  # 큐가 없으면 생성
            channel.basic_publish(exchange='', routing_key=queue_name, body=message)
            logging.info(f"Sent message to {queue_name}: {message}")
        except pika.exceptions.AMQPConnectionError as e:
            logging.error(f"Failed to send message: {e}")
            raise # 예외를 다시 발생시켜 상위에서 처리하도록 함
        finally:
            connection.close()
            logging.info("RabbitMQ connection closed.")

    def consume_messages(self, queue_name: str, callback: Callable):
        """지정된 RabbitMQ 큐에서 메시지를 소비합니다."""

        connection, channel = self.connect_to_rabbitmq()
        if channel is None:
            logging.error("RabbitMQ 연결 실패. 메시지를 받을 수 없습니다.")
            return

        try:
            channel.queue_declare(queue=queue_name)
            channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
            logging.info(f"Start Consuming from RabbitMQ: {queue_name}")
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError as e:
            logging.error(f"Failed to consume messages: {e}")
            raise
        finally:
            connection.close()
            logging.info("RabbitMQ connection closed.")

    def disconnect_from_rabbitmq(self):
      """RabbitMQ 연결을 종료합니다."""
      if self.connection and self.connection.is_open:
        self.connection.close()
        logging.info("Disconnected from RabbitMQ.")
      self.connection = None
      self.channel = None
