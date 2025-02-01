# worker.py
import pika
import json
import logging
import os
import sys
import platform
import shutil

# 매니저 임포트
from managers.database_manager import DatabaseManager
from managers.ocr.ocr_manager import OCRManager
from Settings.settings_manager import SettingsManager
from managers.document.document_manager import DocumentManager
from managers.ai_managers.ai_ocr_running import AIOCRRunning
from managers.ai_managers.ai_event_manager import AIEventManager
from managers.temp_file_manager import TempFileManager
from managers.ai_managers.ai_prediction_manager import AIPredictionManager
from managers.analysis_manager import AnalysisManager
from managers.ai_managers.AI_model_manager import AIModelManager

# 로깅 설정
logging.basicConfig(level=logging.DEBUG)

def process_document(channel, method, properties, body, document_manager):
    """문서 처리 함수"""
    try:
        message = json.loads(body.decode())
        file_paths = message.get("file_paths", [])

        if not file_paths:
            logging.warning(f"파일 경로 없음. 메시지 내용: {body.decode()}")
            channel.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
            return

        for file_path in file_paths:
            document_manager.load_document(file_path)

        logging.info(f"문서 처리 완료: {file_paths}")
        channel.basic_ack(delivery_tag=method.delivery_tag)

    except json.JSONDecodeError as e:
        logging.error(f"JSON 파싱 오류: {e}")
        channel.basic_reject(delivery_tag=method.delivery_tag, requeue=False)

    except Exception as e:
        logging.error(f"문서 처리 중 오류 발생: {e}")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

def process_database_packaging(channel, method, properties, body, database_manager):
    """데이터베이스 패키징 함수"""
    try:
        database_manager.package_database()
        logging.info("데이터베이스 패키징 완료")
        channel.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logging.error(f"데이터베이스 패키징 중 오류 발생: {e}")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

def process_ai_training(channel, method, properties, body, ai_manager):
    """AI 학습 처리 함수"""
    try:
        ai_manager.train_ai()
        logging.info("AI 학습 완료")
        channel.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logging.error(f"AI 학습 중 오류 발생: {e}")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

def process_temp_file_manager(channel, method, properties, body, temp_file_manager):
    """임시 파일 관리"""
    try:
        temp_file_manager.handle_message(channel, method, properties, body)
        logging.info("임시 파일 관리 작업 완료")
        channel.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logging.error(f"임시 파일 관리 중 오류 발생: {e}")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

def process_ai_prediction(channel, method, properties, body, ai_prediction_manager):
    """AI 예측 수행"""
    try:
        ai_prediction_manager.handle_message(channel, method, properties, body)
        logging.info("AI 예측 작업 완료")
        channel.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logging.error(f"AI 예측 작업 중 오류 발생: {e}")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

def process_ai_event(channel, method, properties, body, ai_event_manager):
    """AI 이벤트 핸들링"""
    try:
        ai_event_manager.handle_message(channel, method, properties, body)
        logging.info("AI 이벤트 작업 완료")
        channel.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logging.error(f"AI 이벤트 작업 중 오류 발생: {e}")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

def process_ai_ocr_running(channel, method, properties, body, ai_ocr_running):
    """AI OCR 실행"""
    try:
        ai_ocr_running.handle_ocr_result(channel, method, properties, body)
        logging.info("AI OCR 실행 작업 완료")
        channel.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logging.error(f"AI OCR 실행 중 오류 발생: {e}")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

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
    
    # 설정 파일에서 매니저 인스턴스 생성
    config_path = os.path.join(os.path.dirname(__file__), 'config/development.json')
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    managers = {}
    for manager_name, manager_config in config["managers"].items():
        managers[manager_name] = create_manager(manager_config, settings_manager)

    connection = settings_manager.connect_to_rabbitmq()
    if connection is None:
        logging.error("RabbitMQ 연결 실패. 종료합니다.")
        return

    try:
        channel = connection.channel()
        channel.basic_qos(prefetch_count=1)  # 추가: 한 번에 하나의 메시지만 가져오도록 설정

        # 큐 선언을 설정 파일에서 불러오기
        queues = config["queues"].values()
        
        for queue in queues:
            channel.queue_declare(queue=queue, durable=True)

        # 소비자 설정
        channel.basic_consume(queue=config["queues"]["document_processing"], on_message_callback=lambda ch, method, props, body: process_document(ch, method, props, body, managers["document"]), auto_ack=False)
        channel.basic_consume(queue=config["queues"]["database_packaging"], on_message_callback=lambda ch, method, props, body: process_database_packaging(ch, method, props, body, managers["database"]), auto_ack=False)
        channel.basic_consume(queue=config["queues"]["ai_training_queue"], on_message_callback=lambda ch, method, props, body: process_ai_training(ch, method, props, body, managers["ai_model"]), auto_ack=False)

        logging.info("메시지 대기 중... 종료하려면 CTRL+C를 누르세요.")
        channel.start_consuming()

    except KeyboardInterrupt:
        logging.info("작업 중지됨. RabbitMQ 연결 종료.")
        if connection and connection.is_open:
            connection.close()

if __name__ == "__main__":
    main()
