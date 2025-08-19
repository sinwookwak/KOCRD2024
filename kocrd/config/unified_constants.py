# kocrd/config/system_constants.py
class SystemConstants:
    class EventTypes:
        # 문서 처리 관련 이벤트
        PROCESS_DOCUMENT_TASK = "process_document_task"
        DOCUMENT_PROCESSING_COMPLETED = "document_processing_completed"
        DOCUMENT_PROCESSING_FAILED = "document_processing_failed"
        DOCUMENT_SAVED = "document_saved"
        DOCUMENT_SAVE_FAILED = "document_save_failed"
        DOCUMENT_UPDATED = "document_updated"
        DOCUMENT_UPDATE_FAILED = "document_update_failed"
        DOCUMENT_DELETED = "document_deleted"
        DOCUMENT_DELETE_FAILED = "document_delete_failed"
        DOCUMENTS_LOADED = "documents_loaded"
        DOCUMENTS_LOAD_FAILED = "documents_load_failed"
        DOCUMENT_SEARCHED = "document_searched"
        DOCUMENTS_EXPORTED_PDF = "documents_exported_pdf"
        SINGLE_DOCUMENT_LOADED = "single_document_loaded"
        SINGLE_DOCUMENT_LOAD_FAILED = "single_document_load_failed"
        TABLE_CLEARED = "table_cleared"
        DOCUMENTS_FILTERED = "documents_filtered"

        # 데이터베이스 관련 이벤트
        PROCESS_DATABASE_PACKAGING_TASK = "process_database_packaging_task"
        DATABASE_PACKAGING_COMPLETED = "database_packaging_completed"
        DATABASE_PACKAGING_FAILED = "database_packaging_failed"

        # 임시 파일 관련 이벤트
        TEMP_FILES_CLEANED = "temp_files_cleaned"
        TEMP_FILE_CREATED = "temp_file_created"
        TEMP_FILE_READ = "temp_file_read"
        TEMP_FILE_DELETED = "temp_file_deleted"
        ALL_TEMP_FILES_CLEANED = "all_temp_files_cleaned"
        TEMP_FILES_BACKED_UP = "temp_files_backed_up"
        TEMP_FILES_RESTORED = "temp_files_restored"
        ALL_TEMP_FILES_CLEANED_RETENTION = "all_temp_files_cleaned_retention"
        SPECIFIC_TEMP_FILES_CLEANED = "specific_temp_files_cleaned"

        # 기타 시스템 이벤트 (MessageBroker의 display_message_box 관련)
        ALERT = "alert"
        WARNING = "warning"
        ERROR = "error"
        QUESTION = "question"
        CONFIRM_DELETE = "confirm_delete"

        # Manager lifecycle events
        MANAGER_INITIALIZED = "manager_initialized"
        MANAGER_INITIALIZATION_FAILED = "manager_initialization_failed"
        MANAGER_STARTED = "manager_started"
        MANAGER_STOPPED = "manager_stopped"
        MANAGER_ERROR = "manager_error"
        
        # 기타
        OCR_IMAGES_SAVED = "ocr_images_saved"
        FEEDBACK_SAVED = "feedback_saved"
        AI_TRAINING_COMPLETED = "ai_training_completed"
        TEXT_GENERATED = "text_generated"
    class EventResults:
        # 메시지 박스 결과
        OK = "ok"
        YES = "yes"
        NO = "no"
        CANCEL = "cancel"
        ABORT = "abort" # 중단
        RETRY = "retry" # 재시도
        IGNORE = "ignore" # 무시
        DO_NOT_SHOW_AGAIN = "do_not_show_again" # 다시 보지 않기 체크박스
        DELETE = "delete" # 삭제
        NOT_SHOW_AGAIN = "not_show_again" # 다시 보지 않기
    class ButtonKeys:
        # 버튼 키 상수
        OK = "OK"
        YES = "YES"
        NO = "NO"
        CANCEL = "CANCEL"
        DELETE = "DELETE"
        DO_NOT_SHOW_AGAIN = "DO_NOT_SHOW_AGAIN"
    class UISettings:
        # UI 관련 설정 상수
        DEFAULT_MESSAGE_WINDOW_WIDTH = 400
        DEFAULT_MESSAGE_WINDOW_HEIGHT = 200
    class MessageHandlers:
        # 메시지 핸들러 상수
        DOCUMENT_PROCESSING = "_process_document"
        DATABASE_PACKAGING = "_process_database_packaging"
        AI_TRAINING = "_process_ai_training"
        TEMP_FILE_MANAGER = "_process_temp_file_manager"
        AI_PREDICTION = "_process_ai_prediction"
        AI_OCR_RUNNING = "_process_ai_ocr_running"
        AI_EVENT = "_process_ai_event"
    class ManagerNames:
        # 매니저 이름 상수
        OCR = "ocr"
        TEMP_FILE = "temp_file"
        DATABASE = "database"
        DOCUMENT = "document"
        AI_MODEL = "ai_model"
        AI_TRAINER = "ai_trainer"
        AI_PREDICTION = "ai_prediction"
    class ConfigKeys:
        # 설정 키 상수
        MANAGERS = "managers"
        MODULE = "module"
        CLASS = "class"
        KWARGS = "kwargs"
        DEPENDENCIES = "dependencies"
        INJECT_SETTINGS = "inject_settings"
        INJECT_MAIN_WINDOW = "inject_main_window"
        INJECT_SYSTEM_MANAGER = "inject_system_manager"
