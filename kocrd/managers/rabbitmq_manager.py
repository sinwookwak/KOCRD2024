# rabbitmq_manager.py
import logging
import json
import pika
import pika.channel  # Added import
import pika.spec     # Added import
from typing import Callable, Optional, Dict, Any

class RabbitMQManager:
    def __init__(self, settings_manager) -> None:
        self.settings_manager = settings_manager
        self.connection: Optional[pika.BlockingConnection] = None
        self.channel: Optional[pika.channel.Channel] = None
        self._connect_to_rabbitmq()
        self._declare_queues()
        logging.info("RabbitMQManager initialization complete.")

    def _connect_to_rabbitmq(self) -> None:
        """Connects to the RabbitMQ server and creates a channel."""
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
            logging.info("RabbitMQ connection successful")
        except pika.exceptions.AMQPConnectionError as e:
            logging.error(f"RabbitMQ connection failed: {e}")
            self.connection = None
            self.channel = None
            raise
        except Exception as e:
            logging.error(f"Other error occurred: {e}")
            self.connection = None
            self.channel = None
            raise

    def _declare_queues(self) -> None:
        """Declares the necessary queues."""
        if not self.channel or not self.channel.is_open:
            logging.error("Channel is not connected, unable to declare queues.")
            return

        try:
            with open('development.json', 'r') as f:
                config = json.load(f)

            for queue_name in config["queues"]:
                self.channel.queue_declare(queue=queue_name, durable=True)
            logging.info("All queues declared successfully.")
        except pika.exceptions.AMQPChannelError as e:
            logging.error(f"Queue declaration failed: {e}")
            raise

    def process_message(self, ch: pika.channel.Channel, method: pika.spec.Basic.Deliver,
                        properties: pika.BasicProperties, body: bytes,
                        message_type: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Processes the message and performs ACK/REJECT."""
        if not ch or not ch.is_open:
            logging.error("RabbitMQ channel is None or closed. Unable to process the message.")
            return

        try:
            message: Dict[str, Any] = json.loads(body.decode())
            callback(message)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            logging.info(f"Message processed successfully ({message_type}): {message}")
        except json.JSONDecodeError as e:
            logging.error(f"Message parsing error ({message_type}): {e}. Message: {body.decode()}")
            ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
        except Exception as e:
            logging.error(f"Error processing message ({message_type}): {e}. Message: {body.decode()}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    def _handle_message(self, queue_name: str, callback: Callable[[Dict[str, Any]], None], *args):
        """Internal function to manage message processing."""
        if not self.channel or not self.channel.is_open:
            self._connect_to_rabbitmq()
            if not self.channel:
                logging.error("RabbitMQ connection failed, unable to process the message.")
                return

        def on_message_callback(ch, method, properties, body):
            self.process_message(ch, method, properties, body, queue_name, callback)

        self.channel.basic_consume(queue=queue_name, on_message_callback=on_message_callback, auto_ack=False)

    def handle_document_message(self, *args):
        """Processes document-related messages."""
        queues = self.settings_manager.get("queues")
        def process(message: Dict[str, Any]) -> None:
            """Document processing logic."""
            file_paths = message.get("file_paths")
            if file_paths:
                try:
                    document_infos = args[-1].document_processor.process_multiple_documents(file_paths)
                    response_message = {"document_infos": document_infos}
                    self.send_message("document_processed", response_message, queues["result"])
                except Exception as e:
                    logging.error(f"Error processing document: {e}")
            else:
                logging.warning("Message did not provide file paths.")

        self._handle_message(queues["document_processing"], process, *args)

    def handle_database_packaging_message(self, *args):
        """Processes database packaging messages."""
        queues = self.settings_manager.get("queues")
        def process(message: Dict[str, Any]) -> None:
            """Database packaging logic."""
            try:
                args[-1].package_database()
                self.send_message("database_packaged", {}, queues["result"])
            except Exception as e:
                logging.error(f"Error during database packaging: {e}")

        self._handle_message(queues["database_packaging"], process, *args)

    def send_message(self, message_type: str, message_data: Dict[str, Any], routing_key: str) -> None:
        """Sends a message."""
        if not self.channel or self.channel.is_closed:
            self._connect_to_rabbitmq()
            if not self.channel:
                logging.error("RabbitMQ connection failed, unable to send the message.")
                return

        message: Dict[str, Any] = {
            "type": message_type,
            "data": message_data,
        }
        try:
            self.channel.confirm_delivery()
            self.channel.basic_publish(exchange='', routing_key=routing_key, body=json.dumps(message).encode())
            logging.info(f"Message sent to {routing_key}: {message}")
        except (pika.exceptions.AMQPConnectionError, pika.exceptions.AMQPChannelError) as e:
            logging.error(f"RabbitMQ connection/channel error: {e}")
            self._connect_to_rabbitmq()
        except Exception as e:
            logging.error(f"Error sending message: {e}")

    def start_consuming(self, queue_name: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Starts consuming RabbitMQ messages."""
        if not self.channel or not self.channel.is_open:
            self._connect_to_rabbitmq()
            if not self.channel:
                logging.error("RabbitMQ connection failed, unable to start consuming.")
                return

        self._handle_message(queue_name, callback)

    def close_connection(self) -> None:
        """Closes the RabbitMQ connection."""
        if self.connection and self.connection.is_open:
            self.connection.close()
            logging.info("RabbitMQ connection closed.")