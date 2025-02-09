# kocrd/managers/rabbitmq_manager.py (예시)
class RabbitMQManager:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self._configure_rabbitmq()

    def _configure_rabbitmq(self):
        # ... (RabbitMQ 설정 로직)

    # ... (다른 메서드)
