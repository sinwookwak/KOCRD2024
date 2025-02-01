<<<<<<< HEAD
# AI-M2/
# ├── kocrd/                    # 최상위 패키지
# │   ├── __init__.py           # kocrd 패키지 초기화
# │   ├── main.py               # 프로그램 실행 진입점
# │   ├── worker.py             # 워크 스크립트
# │   ├── main_window.py        # 메인 윈도우 UI 및 로직
# │   ├── SystemManager.py      # 시스템 전반 관리
# │   ├── User.py               # 사용자 정보와 권한 관리 
# │   ├── managers/             # 각 기능별 매니저 모듈
# │   │  ├────    __init__.py
# │   │  ├── document/                   # 문서 관리
# │   │  │   ├── __init__.py
# │   │  │   ├── document_manager.py     # 문서 관리 (열기, 저장 등)
# │   │  │   ├── document_processor.py   # 문서 처리
# │   │  │   ├── document_table_view.py
# │   │  │   └── Document_Controller.py  
# │   │  ├── ocr/                   # OCR
# │   │  │   ├── __init__.py
# │   │  │   ├── ocr_manager.py         # OCR 작업
# │   │  │   └── ocr_utils.py           # OCR 유틸리티 함수들
# │   │  ├── ai_managers/          # AI 관련 매니저들
# │   │  │   ├── __init__.py
# │   │  │   ├── ai_model_manager.py     # AI 모델 로드 및 관리
# │   │  │   ├── ai_prediction_manager.py# AI 예측
# │   │  │   ├── ai_event_manager.py    # AI 이벤트 처리
# │   │  │   └── ai_training_manager.py  # AI 모델 훈련
# │   │  ├── __init__.py
# │   │  ├── database_manager.py     # 데이터베이스 관리
# │   │  ├── rabbitmq_manager.py     # RabbitMQ 관리
# │   │  ├── monitoring_manager.py   # 모니터링 UI 관리  
# │   │  ├── menubar_manager.py      # 메뉴바 관리
# │   │  ├── temp_file_manager.py    # 임시 파일 관리 (큐 메시지 처리)
# │   │  ├── settings_manager.py     # 설정 관리
# │   │  └── analysis_manager.py     # 분석 기능 관리
# │   └── ui/                 # UI 관련 모듈
# │       ├── __init__.py
# │       ├── document_ui.py
# │       ├── ocr_ui.py
# │       ├── menubar_ui.py
# │       ├── monitoring_ui.py
# │       └── settings_dialog_ui.py
# ├── setup_env.bat
# ├── utils/              # 라이브러리
# │   ├── __init__.py
# │   └── file_utils.py     # 파일 유틸리티 함수들
# │   └── embedding_utils.py  # 접근 유틸리티 함수들
# ├── tool/               # 외부 도구 (Tesseract-OCR)
# │   └── Tesseract-OCR/
# │       └── ...Tesseract files...
# ├── model/              # AI 모델 파일
# │   └── model.safetensors
# └──  config/
#     ├── __init__.py
#     ├── development.py
#     ├── production.py
#     └── testing.py



# MainApplication 4
# ├── main.py             # 애플리케이션 시작 및 worker 프로세스 관리
# ├── worker.py           # 메시지 큐에서 작업 처리
# ├── OCR_AI_0_05.py     # MainApplication (UI 및 SystemManager 포함)
# │   ├── DatabaseManager   # 독립 모듈, 데이터베이스 관리
# │   ├── SystemManager     # 시스템과 로직의 중심
# │   │   ├── DocumentManager # 문서 관리처리
# │   │   │   └── DocumentTableUI
# │   │   ├── OCRManager      # OCR 처리 담당
# │   │   │   └── OCRUI
# │   │   ├── MenubarManager  # 메뉴바 이벤트 관리
# │   │   │   └── MenubarUI
# │   │   ├── MonitoringManager # 모니터링 로직 관리
# │   │   │   └── MonitoringUI
# │   │   ├── AI_Manager      # AI 관련 처리
# │   │   │   ├── AI_Database
# │   │   │   ├── AI_OCR_Running
# │   │   │   └── AI_Monitoring_event
# │   │   └── TempFileManager # 임시 파일 관리
# │   ├── SettingsManager   # 설정 관리
# │   │   ├── User
# │   │   └── SettingsDialogUI
# │   └── AnalysisManager   # 문서 분석 관리
# └── ... other files/directories

# MainApplication 3
# ├── DatabaseManage              # 독립 모듈, 데이터베이스 관리
# ├── SystemManager               # 시스템과 로직의 중심
# │   ├── DocumentManager         # 문서 관리 모듈
# │   │   ├── DocumentProcessor   # 문서 처리 담당
# │   │   └── DocumentTableUI     # 문서 테이블 UI 관리
# │   ├── OCRManager              # OCR 처리 담당
# │   │   └── OCRUI               # OCR UI 관련 작업
# │   ├── MenubarManager          # 메뉴바 이벤트 관리
# │   │   └── MenubarUI           # 메뉴바 UI
# │   ├── MonitoringManager       # 모니터링 로직 관리
# │   │   └── MonitoringUI        # 모니터링 UI
# │   ├── AI_Manager              # AI 관련 처리
# │   │   ├──AI_Database          #데이타 베이스에 접근하거나 정보를 처리하는 업무를  위한 기능 모듈​
# │   │   ├──AI_OCR_Running       #OCR 과정에서 학습한 정보를 관리하거나 추가하는 프로세스로 OCRManager 에 과정을 관찰하면서 컨트롤함
# │   │   └──AI_Monitoring_event  #MonitoringManager를 통한 이벤트 발생시 MonitoringManager를 통해 응답하고 반응하는 기능 모듈
# │   └── TempFileManager         # 임시 파일 관리
# ├── SettingsManager             # 설정 관리
# │   ├── User                    # 사용자 정보 및 권한 관리
# │   └── SettingsDialogUI        # 환경설정 UI
# └── AnalysisManager             # 문서 분석 관리

# MainApplication 2
# ├── DatabaseManager           # 독립 모듈, 데이터베이스 관리
# ├── SystemManager             # 시스템과 로직의 중심
# │   ├── DocumentManager       # 문서 관리 모듈
# │   │   ├── DocumentProcessor # 문서 처리 담당
# │   │   └── DocumentTableUI   # 문서 테이블 UI 관리
# │   ├── OCRManager            # OCR 처리 담당
# │   ├── MenubarManager        # 메뉴바 이벤트 관리
# │   │   └──MenubarUI          # 메뉴바 UI
# │   ├── MonitoringManager     # 모니터링 로직 관리
# │   ├── AI_Manager            # AI 관련 처리
# │   ├── TempFileManager       # 임시 파일 관리
# │   └── UIControlManager      # UI 배치 및 관리
# │       ├── DocumentUI        # 문서 테이블 UI
# │       ├── OCRUI             # OCR UI 관련 작업
# │       ├── MenubarUI         # 메뉴바 UI
# │       ├── SettingsDialogUI  # 환경설정 UI
# │       └── MonitoringUI      # 모니터링 UI
# └── SettingsManager           # 설정 관리
#     └── SettingsDialog        # 설정 UI 및 값 저장

# MainApplication
# ├── Presentation 계층
# │   ├── UIControlManager         # 모든 UI 관련 요소를 관리
# │   │   ├── DocumentUIController # 문서 관련 UI 제어 및 SystemManager와 연동
# │   │   ├── OCRUIController      # OCR 관련 UI 제어
# │   │   └── MonitoringUIController# 모니터링 UI 제어
# │   ├── DocumentUI               # 문서 UI 화면
# │   ├── OCRUI                    # OCR 관련 UI 화면
# │   └── MonitoringUI             # 모니터링 UI 화면
# ├── Logic 계층
# │   ├── SystemManager            # 전체 시스템의 중심 관리
# │   │   ├── DocumentManager
# │   │   │   ├── DocumentStorageManager    # 문서의 저장 및 불러오기 관련 기능
# │   │   │   ├── DocumentProcessingManager # OCR 및 분석 관련 기능
# │   │   │   └── DocumentUIManager         # 문서 관련 UI 제어
# │   │   ├── OCRManager           # OCR 처리 기능
# │   │   ├── MenubarManager       # 메뉴바와 관련된 이벤트 관리
# │   │   ├── MonitoringManager    # 시스템 상태 모니터링
# │   │   ├── AI_Manager           # AI 학습 및 예측 관련 로직
# │   │   └── TempFileManager      # 임시 파일 관리
# ├── Data 계층
# │   ├── DocumentDatabaseManager  # 문서 데이터 관리
# │   ├── FeedbackDatabaseManager  # 피드백 데이터 관리
# │   └── CommonDatabaseManager    # 공통 데이터 처리 (필요시)
# └── Utility 계층
#     ├── SettingsManager          # 설정 값 관리
#     │   ├── OCRSettingsManager   # OCR 관련 설정 관리
#     │   └── UISettingsManager    # UI 관련 설정 관리
#     └── TempFileManager          # 임시 파일 저장 및 삭제

# # MainApplication
# # 프로그램의 메인 진입점으로, 전체 시스템을 초기화하고 관리.
# class MainApplication:
#     # Presentation 계층
#     # UI와 사용자 상호작용을 담당하는 계층으로, 사용자 인터페이스를 관리함.
    
#     # UIControlManager
#     # 모든 UI 관련 요소를 관리하며, UI 요소와 SystemManager 간의 연결을 중재하는 역할을 수행.
#     # ├── DocumentUIController: 문서 관련 UI 제어 및 SystemManager와 연동
#     # ├── OCRUIController: OCR 관련 UI 제어
#     # └── MonitoringUIController: 모니터링 관련 UI 제어
    
#     # DocumentUI
#     # 문서의 목록 및 상태를 테이블 형태로 사용자에게 보여주는 UI 화면을 담당.
#     # └── Document 테이블 위젯을 초기화하고, UIControlManager와 협력해 화면에 표시.
    
#     # OCRUI
#     # OCR 작업과 관련된 UI 화면을 담당하며, OCR의 실행, 진행 상황 등을 사용자에게 제공.
    
#     # MonitoringUI
#     # 작업의 진행 상태를 실시간으로 모니터링하며 사용자에게 제공. 예를 들어 진행 바(Progress Bar)와 로그 메시지 표시.
    
#     # Logic 계층
#     # 주요 비즈니스 로직을 처리하고 시스템의 흐름을 관리함.
    
#     # SystemManager
#     # 애플리케이션의 핵심 관리자 역할. 각 모듈 간의 의존성을 조율하며, 문서 처리, AI 학습, 시스템 관리 등 주요 로직 실행.
    
#     # ├── DocumentManager
#     # │   문서와 관련된 로직을 담당. 문서의 목록을 관리하고, 사용자 요청을 받아 문서를 추가, 삭제, 수정하며,
#     # │   필요에 따라 DocumentProcessor와 연동하여 문서를 처리함.
#     # │   ├── DocumentStorageManager
#     # │   │   문서의 저장 및 검색과 같은 기능을 담당하며, DocumentDatabaseManager와 연계.
#     # │   │   예를 들어, 문서를 데이터베이스에 저장하고 불러오는 작업을 관리.
#     # │   ├── DocumentProcessingManager
#     # │   │   문서에 대한 OCR 수행, 분석, 전처리 등의 기능을 담당.
#     # │   │   Tesseract 등을 사용해 PDF나 이미지 문서에서 텍스트를 추출하고, 필요에 따라 문서를 분류함.
#     # │   └── DocumentUIManager
#     # │       DocumentUI와의 상호작용을 담당. 예를 들어, 문서 목록이 변경될 때 UI 업데이트를 실행.
    
#     # ├── OCRManager
#     # │   OCR 처리를 전담하는 매니저. OCR 엔진(Tesseract 등)을 호출해 PDF 및 이미지에서 텍스트를 추출.
#     # │   전처리 과정도 포함될 수 있으며, 추출된 텍스트의 유효성을 검사.
    
#     # ├── MenubarManager
#     # │   메뉴바에서 발생하는 사용자 이벤트를 처리.
#     # │   예를 들어, 파일 열기, 저장, 프로그램 정보 보기 등의 작업을 SystemManager로 전달.
    
#     # ├── MonitoringManager
#     # │   시스템의 상태를 실시간으로 감시하며, 로그 메시지를 사용자에게 표시하고 작업 진행률을 관리.
    
#     # ├── AI_Manager
#     # │   머신러닝 모델 관련 로직을 처리. 학습, 예측, 평가 등과 같은 AI 모델을 활용한 기능을 제공.
#     # │   사용자 피드백 데이터를 수집하여 모델을 학습시키는 등 시스템 성능을 개선.
    
#     # └── TempFileManager
#     #     작업 중 발생하는 임시 파일을 생성하고 정리하는 역할을 수행.
#     #     문서 처리 중 생성된 중간 파일을 효율적으로 관리함.
    
#     # Data 계층
#     # 시스템의 데이터 저장 및 조회를 담당하는 계층.
    
#     # ├── DocumentDatabaseManager
#     # │   문서 메타데이터와 내용을 저장, 검색, 업데이트, 삭제하는 작업을 담당.
#     # │   예를 들어, 문서의 파일 이름, 유형, 저장 경로 등을 데이터베이스에 저장하고 필요한 데이터를 불러옴.
    
#     # ├── FeedbackDatabaseManager
#     # │   사용자 피드백과 관련된 데이터를 관리하며, 피드백 정보를 데이터베이스에 저장하고 AI 학습에 활용.
#     # │   예를 들어, 사용자가 제공한 문서 유형 분류 정보를 저장하고 이를 AI 학습 데이터로 사용하는 역할.
    
#     # └── CommonDatabaseManager
#     #     (필요시) 공통 데이터 관리를 위한 클래스. 여러 데이터베이스 관련 기능이 여러 모듈에서 공유될 경우 사용.
    
#     # Utility 계층
#     # 공통 작업이나 설정을 관리하는 계층.
    
#     # ├── SettingsManager
#     # │   애플리케이션 설정 값을 관리하며, 설정의 읽기, 쓰기, 업데이트 기능을 제공.
#     # │   ├── OCRSettingsManager
#     # │   │   OCR과 관련된 설정을 관리. 예를 들어 Tesseract의 경로, 사용 언어 등의 설정 값을 관리.
#     # │   └── UISettingsManager
#     # │       UI와 관련된 설정을 관리. 예를 들어 화면의 테마, 폰트 크기 등을 저장하고 관리.
    
#     # └── TempFileManager
#     #     프로그램에서 생성된 임시 파일을 관리하고 필요시 삭제. 작업 흐름을 보다 효율적으로 유지하기 위해 사용.
#     class OCRScanActions:
#     """문서 스캔 및 OCR 처리 작업을 담당하는 통합 클래스."""

#     def __init__(self, system_manager, monitoring_window=None):
#         """
#         OCRScanActions 초기화.
#         :param system_manager: SystemManager 인스턴스
#         :param monitoring_window: MonitoringWindow 인스턴스 (옵션)
#         """
#         self.system_manager = system_manager  # SystemManager를 통해 OCRManager 접근
#         self.monitoring_window = monitoring_window
#         self.output_dir = r"C:\AI-M1\database\image"

#         # ProgressBar 초기화
#         self.progress_bar = monitoring_window.progress_bar if monitoring_window else None

#     def start_scan(self, file_paths):
#         """
#         문서 스캔 시작.
#         :param file_paths: 스캔할 파일 경로 목록
#         :return: OCR 결과 또는 None
#         """
#         if not file_paths:
#             logging.warning("No file paths provided for scanning.")
#             return None

#         logging.info(f"Starting scan for {len(file_paths)} files...")
#         try:
#             # SystemManager를 통해 OCR 작업 수행
#             ocr_results = []
#             for file_path in file_paths:
#                 ocr_result = self.system_manager.ocr_manager.perform_ocr({"file_path": file_path})
#                 ocr_results.append(ocr_result)
#                 logging.info(f"OCR result for {file_path}: {ocr_result}")

#                 # ProgressBar 업데이트
#                 if self.progress_bar:
#                     progress = int((file_paths.index(file_path) + 1) / len(file_paths) * 100)
#                     self.progress_bar.setValue(progress)

#             return ocr_results
#         except Exception as e:
#             logging.error(f"Error during scan: {e}")
#             return None

#     def log_scan_results(self, results):
#         """
#         OCR 결과를 로그로 기록.
#         :param results: OCR 결과 리스트
#         """
#         if not results:
#             logging.warning("No results to log.")
#             return

#         for result in results:
#             logging.info(f"OCR Result: {result}")
=======
# AI-M2/
# ├── kocrd/                    # 최상위 패키지
# │   ├── __init__.py           # kocrd 패키지 초기화
# │   ├── main.py               # 프로그램 실행 진입점
# │   ├── worker.py             # 워크 스크립트
# │   ├── main_window.py        # 메인 윈도우 UI 및 로직
# │   ├── SystemManager.py      # 시스템 전반 관리
# │   ├── User.py               # 사용자 정보와 권한 관리 
# │   ├── managers/             # 각 기능별 매니저 모듈
# │   │  ├────    __init__.py
# │   │  ├── document/                   # 문서 관리
# │   │  │   ├── __init__.py
# │   │  │   ├── document_manager.py     # 문서 관리 (열기, 저장 등)
# │   │  │   ├── document_processor.py   # 문서 처리
# │   │  │   ├── document_table_view.py
# │   │  │   └── Document_Controller.py  
# │   │  ├── ocr/                   # OCR
# │   │  │   ├── __init__.py
# │   │  │   ├── ocr_manager.py         # OCR 작업
# │   │  │   └── ocr_utils.py           # OCR 유틸리티 함수들
# │   │  ├── ai_managers/          # AI 관련 매니저들
# │   │  │   ├── __init__.py
# │   │  │   ├── ai_model_manager.py     # AI 모델 로드 및 관리
# │   │  │   ├── ai_prediction_manager.py# AI 예측
# │   │  │   ├── ai_event_manager.py    # AI 이벤트 처리
# │   │  │   └── ai_training_manager.py  # AI 모델 훈련
# │   │  ├── __init__.py
# │   │  ├── database_manager.py     # 데이터베이스 관리
# │   │  ├── rabbitmq_manager.py     # RabbitMQ 관리
# │   │  ├── monitoring_manager.py   # 모니터링 UI 관리  
# │   │  ├── menubar_manager.py      # 메뉴바 관리
# │   │  ├── temp_file_manager.py    # 임시 파일 관리 (큐 메시지 처리)
# │   │  ├── settings_manager.py     # 설정 관리
# │   │  └── analysis_manager.py     # 분석 기능 관리
# │   └── ui/                 # UI 관련 모듈
# │       ├── __init__.py
# │       ├── document_ui.py
# │       ├── ocr_ui.py
# │       ├── menubar_ui.py
# │       ├── monitoring_ui.py
# │       └── settings_dialog_ui.py
# ├── setup_env.bat
# ├── utils/              # 라이브러리
# │   ├── __init__.py
# │   └── file_utils.py     # 파일 유틸리티 함수들
# │   └── embedding_utils.py  # 접근 유틸리티 함수들
# ├── tool/               # 외부 도구 (Tesseract-OCR)
# │   └── Tesseract-OCR/
# │       └── ...Tesseract files...
# ├── model/              # AI 모델 파일
# │   └── model.safetensors
# └──  config/
#     ├── __init__.py
#     ├── development.py
#     ├── production.py
#     └── testing.py



# MainApplication 4
# ├── main.py             # 애플리케이션 시작 및 worker 프로세스 관리
# ├── worker.py           # 메시지 큐에서 작업 처리
# ├── OCR_AI_0_05.py     # MainApplication (UI 및 SystemManager 포함)
# │   ├── DatabaseManager   # 독립 모듈, 데이터베이스 관리
# │   ├── SystemManager     # 시스템과 로직의 중심
# │   │   ├── DocumentManager # 문서 관리처리
# │   │   │   └── DocumentTableUI
# │   │   ├── OCRManager      # OCR 처리 담당
# │   │   │   └── OCRUI
# │   │   ├── MenubarManager  # 메뉴바 이벤트 관리
# │   │   │   └── MenubarUI
# │   │   ├── MonitoringManager # 모니터링 로직 관리
# │   │   │   └── MonitoringUI
# │   │   ├── AI_Manager      # AI 관련 처리
# │   │   │   ├── AI_Database
# │   │   │   ├── AI_OCR_Running
# │   │   │   └── AI_Monitoring_event
# │   │   └── TempFileManager # 임시 파일 관리
# │   ├── SettingsManager   # 설정 관리
# │   │   ├── User
# │   │   └── SettingsDialogUI
# │   └── AnalysisManager   # 문서 분석 관리
# └── ... other files/directories

# MainApplication 3
# ├── DatabaseManage              # 독립 모듈, 데이터베이스 관리
# ├── SystemManager               # 시스템과 로직의 중심
# │   ├── DocumentManager         # 문서 관리 모듈
# │   │   ├── DocumentProcessor   # 문서 처리 담당
# │   │   └── DocumentTableUI     # 문서 테이블 UI 관리
# │   ├── OCRManager              # OCR 처리 담당
# │   │   └── OCRUI               # OCR UI 관련 작업
# │   ├── MenubarManager          # 메뉴바 이벤트 관리
# │   │   └── MenubarUI           # 메뉴바 UI
# │   ├── MonitoringManager       # 모니터링 로직 관리
# │   │   └── MonitoringUI        # 모니터링 UI
# │   ├── AI_Manager              # AI 관련 처리
# │   │   ├──AI_Database          #데이타 베이스에 접근하거나 정보를 처리하는 업무를  위한 기능 모듈​
# │   │   ├──AI_OCR_Running       #OCR 과정에서 학습한 정보를 관리하거나 추가하는 프로세스로 OCRManager 에 과정을 관찰하면서 컨트롤함
# │   │   └──AI_Monitoring_event  #MonitoringManager를 통한 이벤트 발생시 MonitoringManager를 통해 응답하고 반응하는 기능 모듈
# │   └── TempFileManager         # 임시 파일 관리
# ├── SettingsManager             # 설정 관리
# │   ├── User                    # 사용자 정보 및 권한 관리
# │   └── SettingsDialogUI        # 환경설정 UI
# └── AnalysisManager             # 문서 분석 관리

# MainApplication 2
# ├── DatabaseManager           # 독립 모듈, 데이터베이스 관리
# ├── SystemManager             # 시스템과 로직의 중심
# │   ├── DocumentManager       # 문서 관리 모듈
# │   │   ├── DocumentProcessor # 문서 처리 담당
# │   │   └── DocumentTableUI   # 문서 테이블 UI 관리
# │   ├── OCRManager            # OCR 처리 담당
# │   ├── MenubarManager        # 메뉴바 이벤트 관리
# │   │   └──MenubarUI          # 메뉴바 UI
# │   ├── MonitoringManager     # 모니터링 로직 관리
# │   ├── AI_Manager            # AI 관련 처리
# │   ├── TempFileManager       # 임시 파일 관리
# │   └── UIControlManager      # UI 배치 및 관리
# │       ├── DocumentUI        # 문서 테이블 UI
# │       ├── OCRUI             # OCR UI 관련 작업
# │       ├── MenubarUI         # 메뉴바 UI
# │       ├── SettingsDialogUI  # 환경설정 UI
# │       └── MonitoringUI      # 모니터링 UI
# └── SettingsManager           # 설정 관리
#     └── SettingsDialog        # 설정 UI 및 값 저장

# MainApplication
# ├── Presentation 계층
# │   ├── UIControlManager         # 모든 UI 관련 요소를 관리
# │   │   ├── DocumentUIController # 문서 관련 UI 제어 및 SystemManager와 연동
# │   │   ├── OCRUIController      # OCR 관련 UI 제어
# │   │   └── MonitoringUIController# 모니터링 UI 제어
# │   ├── DocumentUI               # 문서 UI 화면
# │   ├── OCRUI                    # OCR 관련 UI 화면
# │   └── MonitoringUI             # 모니터링 UI 화면
# ├── Logic 계층
# │   ├── SystemManager            # 전체 시스템의 중심 관리
# │   │   ├── DocumentManager
# │   │   │   ├── DocumentStorageManager    # 문서의 저장 및 불러오기 관련 기능
# │   │   │   ├── DocumentProcessingManager # OCR 및 분석 관련 기능
# │   │   │   └── DocumentUIManager         # 문서 관련 UI 제어
# │   │   ├── OCRManager           # OCR 처리 기능
# │   │   ├── MenubarManager       # 메뉴바와 관련된 이벤트 관리
# │   │   ├── MonitoringManager    # 시스템 상태 모니터링
# │   │   ├── AI_Manager           # AI 학습 및 예측 관련 로직
# │   │   └── TempFileManager      # 임시 파일 관리
# ├── Data 계층
# │   ├── DocumentDatabaseManager  # 문서 데이터 관리
# │   ├── FeedbackDatabaseManager  # 피드백 데이터 관리
# │   └── CommonDatabaseManager    # 공통 데이터 처리 (필요시)
# └── Utility 계층
#     ├── SettingsManager          # 설정 값 관리
#     │   ├── OCRSettingsManager   # OCR 관련 설정 관리
#     │   └── UISettingsManager    # UI 관련 설정 관리
#     └── TempFileManager          # 임시 파일 저장 및 삭제

# # MainApplication
# # 프로그램의 메인 진입점으로, 전체 시스템을 초기화하고 관리.
# class MainApplication:
#     # Presentation 계층
#     # UI와 사용자 상호작용을 담당하는 계층으로, 사용자 인터페이스를 관리함.
    
#     # UIControlManager
#     # 모든 UI 관련 요소를 관리하며, UI 요소와 SystemManager 간의 연결을 중재하는 역할을 수행.
#     # ├── DocumentUIController: 문서 관련 UI 제어 및 SystemManager와 연동
#     # ├── OCRUIController: OCR 관련 UI 제어
#     # └── MonitoringUIController: 모니터링 관련 UI 제어
    
#     # DocumentUI
#     # 문서의 목록 및 상태를 테이블 형태로 사용자에게 보여주는 UI 화면을 담당.
#     # └── Document 테이블 위젯을 초기화하고, UIControlManager와 협력해 화면에 표시.
    
#     # OCRUI
#     # OCR 작업과 관련된 UI 화면을 담당하며, OCR의 실행, 진행 상황 등을 사용자에게 제공.
    
#     # MonitoringUI
#     # 작업의 진행 상태를 실시간으로 모니터링하며 사용자에게 제공. 예를 들어 진행 바(Progress Bar)와 로그 메시지 표시.
    
#     # Logic 계층
#     # 주요 비즈니스 로직을 처리하고 시스템의 흐름을 관리함.
    
#     # SystemManager
#     # 애플리케이션의 핵심 관리자 역할. 각 모듈 간의 의존성을 조율하며, 문서 처리, AI 학습, 시스템 관리 등 주요 로직 실행.
    
#     # ├── DocumentManager
#     # │   문서와 관련된 로직을 담당. 문서의 목록을 관리하고, 사용자 요청을 받아 문서를 추가, 삭제, 수정하며,
#     # │   필요에 따라 DocumentProcessor와 연동하여 문서를 처리함.
#     # │   ├── DocumentStorageManager
#     # │   │   문서의 저장 및 검색과 같은 기능을 담당하며, DocumentDatabaseManager와 연계.
#     # │   │   예를 들어, 문서를 데이터베이스에 저장하고 불러오는 작업을 관리.
#     # │   ├── DocumentProcessingManager
#     # │   │   문서에 대한 OCR 수행, 분석, 전처리 등의 기능을 담당.
#     # │   │   Tesseract 등을 사용해 PDF나 이미지 문서에서 텍스트를 추출하고, 필요에 따라 문서를 분류함.
#     # │   └── DocumentUIManager
#     # │       DocumentUI와의 상호작용을 담당. 예를 들어, 문서 목록이 변경될 때 UI 업데이트를 실행.
    
#     # ├── OCRManager
#     # │   OCR 처리를 전담하는 매니저. OCR 엔진(Tesseract 등)을 호출해 PDF 및 이미지에서 텍스트를 추출.
#     # │   전처리 과정도 포함될 수 있으며, 추출된 텍스트의 유효성을 검사.
    
#     # ├── MenubarManager
#     # │   메뉴바에서 발생하는 사용자 이벤트를 처리.
#     # │   예를 들어, 파일 열기, 저장, 프로그램 정보 보기 등의 작업을 SystemManager로 전달.
    
#     # ├── MonitoringManager
#     # │   시스템의 상태를 실시간으로 감시하며, 로그 메시지를 사용자에게 표시하고 작업 진행률을 관리.
    
#     # ├── AI_Manager
#     # │   머신러닝 모델 관련 로직을 처리. 학습, 예측, 평가 등과 같은 AI 모델을 활용한 기능을 제공.
#     # │   사용자 피드백 데이터를 수집하여 모델을 학습시키는 등 시스템 성능을 개선.
    
#     # └── TempFileManager
#     #     작업 중 발생하는 임시 파일을 생성하고 정리하는 역할을 수행.
#     #     문서 처리 중 생성된 중간 파일을 효율적으로 관리함.
    
#     # Data 계층
#     # 시스템의 데이터 저장 및 조회를 담당하는 계층.
    
#     # ├── DocumentDatabaseManager
#     # │   문서 메타데이터와 내용을 저장, 검색, 업데이트, 삭제하는 작업을 담당.
#     # │   예를 들어, 문서의 파일 이름, 유형, 저장 경로 등을 데이터베이스에 저장하고 필요한 데이터를 불러옴.
    
#     # ├── FeedbackDatabaseManager
#     # │   사용자 피드백과 관련된 데이터를 관리하며, 피드백 정보를 데이터베이스에 저장하고 AI 학습에 활용.
#     # │   예를 들어, 사용자가 제공한 문서 유형 분류 정보를 저장하고 이를 AI 학습 데이터로 사용하는 역할.
    
#     # └── CommonDatabaseManager
#     #     (필요시) 공통 데이터 관리를 위한 클래스. 여러 데이터베이스 관련 기능이 여러 모듈에서 공유될 경우 사용.
    
#     # Utility 계층
#     # 공통 작업이나 설정을 관리하는 계층.
    
#     # ├── SettingsManager
#     # │   애플리케이션 설정 값을 관리하며, 설정의 읽기, 쓰기, 업데이트 기능을 제공.
#     # │   ├── OCRSettingsManager
#     # │   │   OCR과 관련된 설정을 관리. 예를 들어 Tesseract의 경로, 사용 언어 등의 설정 값을 관리.
#     # │   └── UISettingsManager
#     # │       UI와 관련된 설정을 관리. 예를 들어 화면의 테마, 폰트 크기 등을 저장하고 관리.
    
#     # └── TempFileManager
#     #     프로그램에서 생성된 임시 파일을 관리하고 필요시 삭제. 작업 흐름을 보다 효율적으로 유지하기 위해 사용.
#     class OCRScanActions:
#     """문서 스캔 및 OCR 처리 작업을 담당하는 통합 클래스."""

#     def __init__(self, system_manager, monitoring_window=None):
#         """
#         OCRScanActions 초기화.
#         :param system_manager: SystemManager 인스턴스
#         :param monitoring_window: MonitoringWindow 인스턴스 (옵션)
#         """
#         self.system_manager = system_manager  # SystemManager를 통해 OCRManager 접근
#         self.monitoring_window = monitoring_window
#         self.output_dir = r"C:\AI-M1\database\image"

#         # ProgressBar 초기화
#         self.progress_bar = monitoring_window.progress_bar if monitoring_window else None

#     def start_scan(self, file_paths):
#         """
#         문서 스캔 시작.
#         :param file_paths: 스캔할 파일 경로 목록
#         :return: OCR 결과 또는 None
#         """
#         if not file_paths:
#             logging.warning("No file paths provided for scanning.")
#             return None

#         logging.info(f"Starting scan for {len(file_paths)} files...")
#         try:
#             # SystemManager를 통해 OCR 작업 수행
#             ocr_results = []
#             for file_path in file_paths:
#                 ocr_result = self.system_manager.ocr_manager.perform_ocr({"file_path": file_path})
#                 ocr_results.append(ocr_result)
#                 logging.info(f"OCR result for {file_path}: {ocr_result}")

#                 # ProgressBar 업데이트
#                 if self.progress_bar:
#                     progress = int((file_paths.index(file_path) + 1) / len(file_paths) * 100)
#                     self.progress_bar.setValue(progress)

#             return ocr_results
#         except Exception as e:
#             logging.error(f"Error during scan: {e}")
#             return None

#     def log_scan_results(self, results):
#         """
#         OCR 결과를 로그로 기록.
#         :param results: OCR 결과 리스트
#         """
#         if not results:
#             logging.warning("No results to log.")
#             return

#         for result in results:
#             logging.info(f"OCR Result: {result}")
>>>>>>> 0b45195 (S)
