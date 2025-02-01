# worker.py
import pika
import json
import logging
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
from managers.analysis_manager import AnalysisManager
from managers.ai_managers.ai_model_manager import AIModelManager

logging.basicConfig(level=logging.DEBUG)

def process_message(channel, method, properties, body, manager, process_func):
    """메시지를 처리하는 공통 함수"""
    try:
        process_func(channel, method, properties, body, manager)
        channel.basic_ack(delivery_tag=method.delivery_tag)
    except json.JSONDecodeError as e:
        logging.error(f"JSON 파싱 오류: {e}")
        channel.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
    except Exception as e:
        logging.error(f"메시지 처리 중 오류 발생: {e}")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

def process_document(channel, method, properties, body, document_manager):
    """문서 처리 함수"""
    message = json.loads(body.decode())
    file_paths = message.get("file_paths", [])
    if not file_paths:
        logging.warning(f"파일 경로 없음. 메시지 내용: {body.decode()}")
        return
    for file_path in file_paths:
        document_manager.load_document(file_path)
    logging.info(f"문서 처리 완료: {file_paths}")

def process_database_packaging(channel, method, properties, body, database_manager):
    """데이터베이스 패키징 함수"""
    database_manager.package_database()
    logging.info("데이터베이스 패키징 완료")

def process_ai_training(channel, method, properties, body, ai_manager):
    """AI 학습 처리 함수"""
    ai_manager.train_ai()
    logging.info("AI 학습 완료")

def process_temp_file_manager(channel, method, properties, body, temp_file_manager):
    """임시 파일 관리"""
    temp_file_manager.handle_message(channel, method, properties, body)
    logging.info("임시 파일 관리 작업 완료")

def process_ai_prediction(channel, method, properties, body, ai_prediction_manager):
    """AI 예측 수행"""
    ai_prediction_manager.handle_message(channel, method, properties, body)
    logging.info("AI 예측 작업 완료")

def process_ai_event(channel, method, properties, body, ai_event_manager):
    """AI 이벤트 핸들링"""
    ai_event_manager.handle_message(channel, method, properties, body)
    logging.info("AI 이벤트 작업 완료")

def process_ai_ocr_running(channel, method, properties, body, ai_ocr_running):
    """AI OCR 실행"""
    ai_ocr_running.handle_ocr_result(channel, method, properties, body)
    logging.info("AI OCR 실행 작업 완료")

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
    
    config_path = os.path.join(os.path.dirname(__file__), 'config/development.json')
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    managers = {}
    for manager_name, manager_config in config["managers"].items():
        managers[manager_name] = create_manager(manager_config, settings_manager)

    connection, channel = settings_manager.connect_to_rabbitmq()
    if connection is None:
        logging.error("RabbitMQ 연결 실패. 종료합니다.")
        return

    try:
        channel.basic_qos(prefetch_count=1)

        queues = config["queues"].values()
        for queue in queues:
            channel.queue_declare(queue=queue, durable=True)

        channel.basic_consume(queue=config["queues"]["document_processing"], on_message_callback=lambda ch, method, props, body: process_message(ch, method, props, body, managers["document"], process_document), auto_ack=False)
        channel.basic_consume(queue=config["queues"]["database_packaging"], on_message_callback=lambda ch, method, props, body: process_message(ch, method, props, body, managers["database"], process_database_packaging), auto_ack=False)
        channel.basic_consume(queue=config["queues"]["ai_training_queue"], on_message_callback=lambda ch, method, props, body: process_message(ch, method, props, body, managers["ai_model"], process_ai_training), auto_ack=False)

        logging.info("메시지 대기 중... 종료하려면 CTRL+C를 누르세요.")
        channel.start_consuming()

    except KeyboardInterrupt:
        logging.info("작업 중지됨. RabbitMQ 연결 종료.")
        if connection and connection.is_open:
            connection.close()

if __name__ == "__main__":
    main()
