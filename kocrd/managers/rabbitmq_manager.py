# rabbitmq_manager.py
import logging
import json
import pika
import pika.channel  # 추가된 임포트
import pika.spec     # 추가된 임포트
from typing import Callable, Optional, Dict, Any

class RabbitMQManager:
    def __init__(self, settings_manager) -> None:
        self.settings_manager = settings_manager
        self.connection: Optional[pika.BlockingConnection] = None
        self.channel: Optional[pika.channel.Channel] = None
        self._connect_to_rabbitmq()
        self._declare_queues()
        logging.info("RabbitMQManager 초기화 완료.")

    def _connect_to_rabbitmq(self) -> None:
        """RabbitMQ 서버에 연결하고 채널을 생성합니다."""
        try:
            credentials = pika.PlainCredentials(
                self.settings_manager.get("rabbitmq_user"),
                self.settings_manager.get("rabbitmq_password")
            )
            parameters = pika.ConnectionParameters(
                host=self.settings_manager.get("rabbitmq_host"),
                virtual_host=self.settings_manager.get("rabbitmq_virtual_host"),
                credentials=credentials
            )
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            logging.info("RabbitMQ 연결 성공")
        except pika.exceptions.AMQPConnectionError as e:
            logging.error(f"RabbitMQ 연결 실패: {e}")
            self.connection = None
            self.channel = None
            raise
        except Exception as e:
            logging.error(f"기타 오류 발생: {e}")
            self.connection = None
            self.channel = None
            raise

    def _declare_queues(self) -> None:
        """필요한 큐들을 선언합니다."""
        if not self.channel or not self.channel.is_open:
            logging.error("채널이 연결되지 않아 큐를 선언할 수 없습니다.")
            return

        try:
            queues = self.settings_manager.get("queues")
            for queue_name in queues.values():
                self.channel.queue_declare(queue=queue_name, durable=True)
            logging.info("모든 큐 선언 완료.")
        except pika.exceptions.AMQPChannelError as e:
            logging.error(f"큐 선언 실패: {e}")
            raise

    def process_message(self, ch: pika.channel.Channel, method: pika.spec.Basic.Deliver,
                        properties: pika.BasicProperties, body: bytes,
                        message_type: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """메시지를 처리하고 ACK/REJECT 합니다."""
        if not ch or not ch.is_open:
            logging.error("RabbitMQ 채널이 None이거나 닫혀 있습니다. 메시지를 처리할 수 없습니다.")
            return

        try:
            message: Dict[str, Any] = json.loads(body.decode())
            callback(message)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            logging.info(f"메시지 처리 성공 ({message_type}): {message}")
        except json.JSONDecodeError as e:
            logging.error(f"메시지 파싱 오류 ({message_type}): {e}. 메시지: {body.decode()}")
            ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
        except Exception as e:
            logging.error(f"메시지 처리 중 오류 ({message_type}): {e}. 메시지: {body.decode()}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    def _handle_message(self, queue_name: str, callback: Callable[[Dict[str, Any]], None], *args):
        """메시지 처리 로직을 추상화한 내부 함수"""
        if not self.channel or not self.channel.is_open:
            self._connect_to_rabbitmq()
            if not self.channel:
                logging.error("RabbitMQ 연결 실패로 메시지를 처리할 수 없습니다.")
                return

        def on_message_callback(ch, method, properties, body):
            self.process_message(ch, method, properties, body, queue_name, callback)

        self.channel.basic_consume(queue=queue_name, on_message_callback=on_message_callback, auto_ack=False)

    def handle_document_message(self, *args):
        """문서 처리 메시지를 처리합니다."""
        queues = self.settings_manager.get("queues")
        def process(message: Dict[str, Any]) -> None:
            """문서 처리 로직"""
            file_paths = message.get("file_paths")
            if file_paths:
                try:
                    document_infos = args[-1].document_processor.process_multiple_documents(file_paths)
                    response_message = {"document_infos": document_infos}
                    self.send_message("document_processed", response_message, queues["result"])
                except Exception as e:
                    logging.error(f"문서 처리 중 오류: {e}")
            else:
                logging.warning("메시지에 파일 경로가 제공되지 않았습니다.")

        self._handle_message(queues["document_processing"], process, *args)

    def handle_database_packaging_message(self, *args):
        """데이터베이스 패키징 메시지를 처리합니다."""
        queues = self.settings_manager.get("queues")
        def process(message: Dict[str, Any]) -> None:
            """데이터베이스 패키징 로직"""
            try:
                args[-1].package_database()
                self.send_message("database_packaged", {}, queues["result"])
            except Exception as e:
                logging.error(f"데이터베이스 패키징 중 오류: {e}")

        self._handle_message(queues["database_packaging"], process, *args)

    def send_message(self, message_type: str, message_data: Dict[str, Any], routing_key: str) -> None:
        """메시지를 전송합니다."""
        if not self.channel or self.channel.is_closed:
            self._connect_to_rabbitmq()
            if not self.channel:
                logging.error("RabbitMQ 연결 실패로 메시지를 전송할 수 없습니다.")
                return

        message: Dict[str, Any] = {
            "type": message_type,
            "data": message_data,
        }
        try:
            self.channel.confirm_delivery()
            self.channel.basic_publish(exchange='', routing_key=routing_key, body=json.dumps(message).encode())
            logging.info(f"{routing_key}로 메시지 전송: {message}")
        except (pika.exceptions.AMQPConnectionError, pika.exceptions.AMQPChannelError) as e:
            logging.error(f"RabbitMQ 연결/채널 오류: {e}")
            self._connect_to_rabbitmq()
        except Exception as e:
            logging.error(f"메시지 전송 중 오류: {e}")

    def start_consuming(self, queue_name: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """RabbitMQ 메시지 소비 시작"""
        if not self.channel or not self.channel.is_open:
            self._connect_to_rabbitmq()
            if not self.channel:
                logging.error("RabbitMQ 연결 실패로 메시지 소비를 시작할 수 없습니다.")
                return

        self._handle_message(queue_name, callback)

    def close_connection(self) -> None:
        """RabbitMQ 연결을 종료합니다."""
        if self.connection and self.connection.is_open:
            self.connection.close()
            logging.info("RabbitMQ 연결 종료.")