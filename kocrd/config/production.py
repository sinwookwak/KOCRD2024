
# RabbitMQ 설정
RABBITMQ_HOST = "localhost"  # RabbitMQ 서버 주소
RABBITMQ_PORT = 5672       # RabbitMQ 서버 포트
RABBITMQ_USER = "guest"     # RabbitMQ 사용자 이름
RABBITMQ_PASSWORD = "guest" # RabbitMQ 비밀번호
RABBITMQ_VIRTUAL_HOST = "/" # RabbitMQ Virtual Host (기본값 "/")

# RabbitMQ 큐 이름
OCR_REQUESTS_QUEUE = "dev_ocr_requests"        # OCR 요청 큐
OCR_RESULTS_QUEUE = "dev_ocr_results"          # OCR 결과 큐
PREDICTION_REQUESTS_QUEUE = "dev_prediction_requests" # 예측 요청 큐
PREDICTION_RESULTS_QUEUE = "dev_prediction_results" # 예측 결과 큐
EVENTS_QUEUE = "dev_events"                  # 이벤트 큐
UI_FEEDBACK_REQUESTS_QUEUE = "dev_ui_feedback_requests" # UI 피드백 요청 큐

# 파일 경로
MODELS_PATH = "F:/AI-M2/models/dev_models"              # 모델 저장 경로
DOCUMENT_EMBEDDING_PATH = "F:/AI-M2/model/dev_document_embedding.json" # 문서 임베딩 파일 경로
DOCUMENT_TYPES_PATH = "F:/AI-M2/model/dev_document_types.json"     # 문서 타입 정의 파일 경로
TEMP_FILES_DIR = "F:/AI-M2/temp/dev_temp_files"          # 임시 파일 저장 경로

# 데이터베이스 연결
DATABASE_URL = "dev_database_url"  # 개발용 데이터베이스 URL

# 파일 처리 설정
DEFAULT_REPORT_FILENAME = "report.txt"      # 기본 보고서 파일 이름
DEFAULT_EXCEL_FILENAME = "documents.xlsx"  # 기본 엑셀 파일 이름
VALID_FILE_EXTENSIONS = {'.pdf', '.docx', '.xlsx', '.txt', '.csv', '.png', '.jpg', '.jpeg'} # 허용된 파일 확장자
MAX_FILE_SIZE = 10 * 1024 * 1024          # 최대 파일 크기 (10MB)

RABBITMQ_QUEUES = {
    "prediction_requests": "prediction_requests",
    "prediction_results": "prediction_results",
    "ui_feedback_requests": "ui_feedback_requests",
    "events": "events",
    "document_processing": "document_processing",
    "database_packaging": "database_packaging",
    "result": "result",
    "ai_training_queue": "ai_training_queue", # ai_training_queue 추가
    "temp_file_queue": "temp_file_queue", # temp_file_queue 추가
    "prediction_requests_queue": "prediction_requests_queue", # prediction_requests_queue 추가
    "events_queue": "events_queue", # events_queue 추가
    "ocr_results": "ocr_results" # ocr_results 추가
}
