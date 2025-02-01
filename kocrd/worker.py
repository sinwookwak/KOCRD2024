# worker.py
import logging
import json
import os
import sys

from managers.database_manager import DatabaseManager
from managers.ocr.ocr_manager import OCRManager
from Settings.settings_manager import SettingsManager
from managers.document.document_manager import DocumentManager
from managers.ai_managers.ai_ocr_running import AIOCRRunning
from managers.ai_managers.ai_event_manager import AIEventManager
from managers.temp_file_manager import TempFileManager
from managers.ai_managers.ai_prediction_manager import AIPredictionManager

logging.basicConfig(level=logging.DEBUG)

def create_manager(manager_config, settings_manager):
    """설정 파일에서 매니저 인스턴스를 생성합니다."""
    module_name = manager_config["module"]
    class_name = manager_config["class"]
    kwargs = manager_config.get("kwargs", {})
    module = __import__(module_name, fromlist=[class_name])
    manager_class = getattr(module, class_name)
    return manager_class(settings_manager, **kwargs)

def main():
    """메인 실행 함수"""
    settings_manager = SettingsManager()
    
    connection, channel = settings_manager.connect_to_rabbitmq()
    if connection is None:
        logging.error("RabbitMQ 연결 실패. 종료합니다.")
        return

    try:
        channel.basic_qos(prefetch_count=1)

        config = settings_manager.load_development_settings()
        queues = config["queues"].values()
        for queue in queues:
            channel.queue_declare(queue=queue, durable=True)

        logging.info("메시지 대기 중... 종료하려면 CTRL+C를 누르세요.")
        channel.start_consuming()

    except KeyboardInterrupt:
        logging.info("작업 중지됨. RabbitMQ 연결 종료.")
        if connection and connection.is_open:
            connection.close()

if __name__ == "__main__":
    main()
