# file_name: system_constants.py
# Kocrd 프로젝트의 루트 또는 config/constants 경로에 위치한다고 가정

# --- 이벤트 윈도우 관련 상수 ---
class EventTypes:
    """이벤트 윈도우 메시지 유형 상수."""
    ALERT = "alert"             # 알림 (정보성 메시지, OK 버튼)
    WARNING = "warning"         # 경고 (사용자 주의 필요, OK 버튼)
    ERROR = "error"             # 에러 (심각한 문제, OK 버튼)
    QUESTION = "question"       # 질문 (예/아니오, 확인/취소 등 사용자 선택 필요)
    CONFIRM_DELETE = "confirm_delete" # 삭제 확인 (삭제/취소, 삭제 대상 명시)

class EventResults:
    """이벤트 윈도우에서 반환될 결과 값 상수."""
    OK = "ok"
    YES = "yes"
    NO = "no"
    CANCEL = "cancel"
    DELETE = "delete"
    DISCARD = "discard"         # 예: 저장하지 않고 닫기
    NOT_SHOW_AGAIN = "not_show_again" # "다시 보지 않기" 체크박스 선택 시 (예: "RESULT_YES,NOT_SHOW_AGAIN" 형태로 조합)

class ButtonKeys:
    """text_manager에서 버튼 텍스트를 가져올 때 사용할 키 상수."""
    OK = "OK"
    YES = "Yes"
    NO = "No"
    CANCEL = "Cancel"
    DELETE = "Delete"
    DO_NOT_SHOW_AGAIN = "DoNotShowAgain" # "다시 보지 않기" 체크박스 텍스트

# --- UI 관련 기타 상수 (필요시 추가) ---
class UISettings:
    """UI 관련 기본 설정 상수."""
    DEFAULT_MESSAGE_WINDOW_WIDTH = 400
    DEFAULT_MESSAGE_WINDOW_HEIGHT = 200

# --- 그 외 시스템 전반에 사용될 상수 (추가 예정) ---
class SystemConfig:
    """시스템 전반의 설정 및 경로 상수."""
    # 예: OCR_ENGINE_PATH = "/usr/local/bin/tesseract"
    # 예: DATABASE_FILE_NAME = "app_data.db"
    pass

# 상수 관리의 편의를 위해 모든 상수 클래스를 포함하는 단일 진입점 제공
class SystemConstants:
    EventTypes = EventTypes
    EventResults = EventResults
    ButtonKeys = ButtonKeys
    UISettings = UISettings
    SystemConfig = SystemConfig