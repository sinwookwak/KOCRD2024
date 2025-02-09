# kocrd/managers/rabbitmq_manager.py (예시)
class RabbitMQManager:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self._configure_rabbitmq()

    def _configure_rabbitmq(self):
        # ... (RabbitMQ 설정 로직)

    # ... (다른 메서드)
    def _configure_rabbitmq(self):
        rabbitmq_settings = self.settings["managers"]["message_queue"]["kwargs"]
        credentials = pika.PlainCredentials(rabbitmq_settings["username"], rabbitmq_settings["password"])
        parameters = pika.ConnectionParameters(rabbitmq_settings["host"], rabbitmq_settings["port"], '/', credentials)
        self.rabbitmq_connection = pika.BlockingConnection(parameters)
        self.rabbitmq_channel = self.rabbitmq_connection.channel()
        logging.info("🟢 RabbitMQ 설정 완료.")
