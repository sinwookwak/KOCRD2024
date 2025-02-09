# kocrd/                            # 최상위 패키지
# ├── __init__.py              # kocrd 패키지 초기화
# ├── main.py               # 프로그램 실행 진입점
# ├── worker.py             # 워크 스크립트
# ├── system.py             # 시스템 전반 관리
# ├── User.py               # 사용자 정보와 권한 관리 
# ├── window/               # UI 관련 모듈
# │   ├── __init__.py
# │   ├── main_window.py        # 메인 윈도우 UI 및 로직
# │   ├── document_ui_system.py # 문서 UI 관리
# │   ├── menubar_manager.py    # 메뉴바 관리
# │   └── monitoring_ui_system.py # 모니터링 UI 관리
# ├── settings/             # 설정 관리
# │   ├── __init__.py
# │   ├── settings_manager.py   # 설정 관리
# │   └── settingsdialogui/     # 설정 다이얼로그 UI
# │       ├── __init__.py
# │       ├── SettingsDialogUI.py   # 설정 다이얼로그 UI
# │       └── OCRUI.py         # OCR 설정 UI
# ├── managers/                  # 각 기능별 매니저 모듈
# │  ├── __init__.py
# │  ├── database_manager.py     # 데이터베이스 관리
# │  ├── temp_file_manager.py    # 임시 파일 관리 (큐 메시지 처리)
# │  ├── system_manager.py       # 메니저 모듈 시스템
# │  ├── rabbitmq_manager.py     # RabbitMQ 관리
# │  ├── manager_factory.py      # 매니저 팩토리
# │  ├── document/                   # 문서 관리
# │  │   ├── __init__.py
# │  │   ├── document_manager.py     # 문서 관리 (열기, 저장 등)
# │  │   ├── document_processor.py   # 문서 처리
# │  │   ├── document_table_view.py  # 문서 테이블 뷰
# │  │   └── document_Controller.py  # 문서 컨트롤러
# │  ├── ocr/                   # OCR 디렉토리
# │  │   ├── __init__.py
# │  │   ├── ocr_manager.py         # OCR 작업
# │  │   └── ocr_utils.py           # OCR 유틸리티 함수들
# │  └── ai_managers/          # AI 관련 매니저들
# │      ├── __init__.py
# │      ├── ai_model_manager.py     # AI 모델 로드 및 관리
# │      ├── ai_prediction_manager.py# AI 예측
# │      ├── ai_data_manager.py    # AI 이벤트 처리
# │      └── ai_training_manager.py  # AI 모델 훈련
# ├── utils/             # 유틸리티 함수들
# │  ├── __init__.py
# │  ├── embedding_utils.py  # 접근 유틸리티 함수들
# │  └── file_utils.py     # 파일 유틸리티 함수들
# ├── handlers/           # 이벤트 핸들러
# │  ├── __init__.py
# │  ├── message_handler.py  # 메시지 핸들러
# │  └── training_event_handler.py  # AI 이벤트 핸들러
# └── config/             # 설정 파일
#    ├── __init__.py
#    ├── config.py
#    ├── managers.json
#    ├── messagers.json
#    ├── queues.json
#    ├── ui.json
#    └── language/
#        ├── __init__.py
#        ├── ko.json
#        └── en.json