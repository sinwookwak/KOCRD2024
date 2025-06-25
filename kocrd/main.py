# main.py
import sys
import logging
import multiprocessing
from PyQt5.QtWidgets import QApplication, QMessageBox
import os
# 프로젝트 루트 디렉토리를 sys.path에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# 로깅 설정 (애플리케이션 전체에서 사용)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from kocrd.managers.system_manager import SystemManager # 새로운 SystemManager 임포트
from kocrd.Settings.settings_manager import SettingsManager # SettingsManager 임포트
from kocrd.window.main_window import MainWindow # MainWindow 임포트
from kocrd.config.config import text_manager # text_manager 임포트

def run_worker(config_path):
    """Worker 프로세스를 실행하는 함수 (메시지 소비 담당)."""
    # 워커 프로세스 로깅 설정 (필요시 메인 프로세스와 다르게 설정 가능)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info("Worker process started.")

    try:
        # 워커 프로세스에서 설정 로드
        settings_manager = SettingsManager(config_path=config_path)
        # AppConfig는 SettingsManager에 의해 로드된다고 가정
        # SystemManager 생성 (GUI 인스턴스는 None으로 전달)
        system_manager = SystemManager(settings_manager=settings_manager, main_window=None)

        # 메시지 소비 시작
        system_manager.start_message_consumption()

    except Exception as e:
        logging.critical(f"Worker process failed: {e}")
        # 오류 처리 로직 추가 (예: 부모 프로세스에 알림)

def start_worker_process(config_path):
    """Worker 프로세스를 시작하고 프로세스 객체를 반환합니다."""
    worker_process = multiprocessing.Process(target=run_worker, args=(config_path,))
    worker_process.start()
    return worker_process

def main():
    app = QApplication(sys.argv)

    # 1. 설정 로드 및 SettingsManager 생성
    config_path = "config/development.json" # 설정 파일 경로
    try:
        settings_manager = SettingsManager(config_path=config_path)
        # settings_manager.load_config() # SystemManager 생성 시 내부에서 로드됨
        # AppConfig는 SettingsManager에 의해 로드된다고 가정
    except Exception as e:
        logging.critical(text_manager.get_error_text("502", file=config_path, e=e)) # text_manager 사용
        QMessageBox.critical(None, text_manager.get_general_text("configuration_error"), # text_manager 사용
                             text_manager.get_error_text("502", file=config_path, e=e)) # text_manager 사용
        sys.exit(1) # 설정 로드 실패 시 종료

    # 2. SystemManager 생성 (MainWindow 인스턴스는 나중에 설정)
    # SystemManager는 초기화 시 settings_manager를 받음
    # Tesseract 경로는 SystemManager 내부에서 AppConfig를 통해 로드
    system_manager = SystemManager(settings_manager=settings_manager, main_window=None)

    # 3. MainWindow 생성 및 SystemManager 연결
    # MainWindow 생성자에 필요한 다른 매니저들은 SystemManager에서 가져와 전달
    # 예: ocr_manager = system_manager.get_manager("ocr")
    # 예: event_manager = system_manager.get_manager("event") # EventManager가 있다면
    # MainWindow 생성자 시그니처에 맞게 수정 필요
    # 현재 MainWindow 생성자: __init__(self, system_manager: SystemManager, ocr_manager, event_manager)
    ocr_manager = system_manager.get_manager("ocr")
    # event_manager는 config에 정의되어 있지 않거나 다른 방식으로 관리될 수 있음.
    # 임시로 None 또는 적절한 매니저를 가져오도록 수정
    event_manager = system_manager.get_manager("event") # config에 'event' 매니저가 정의되어 있다면

    if not ocr_manager:
         logging.critical("OCRManager not found in SystemManager.")
         QMessageBox.critical(None, "Initialization Error", "OCRManager not found.")
         sys.exit(1)

    # event_manager가 필수적이지 않다면 체크 생략 가능
    # if not event_manager:
    #      logging.warning("EventManager not found in SystemManager.")

    main_window = MainWindow(system_manager=system_manager, ocr_manager=ocr_manager, event_manager=event_manager)

    # SystemManager에 MainWindow 인스턴스 설정
    system_manager.main_window = main_window

    # 4. AI 모델 적용 (SystemManager 또는 AI 모델 매니저를 통해)
    # 이전 코드에서 main에서 직접 모델 파일을 로드하고 적용하는 로직이 있었습니다.
    # 이 로직은 AI 모델 매니저 내부로 이동하는 것이 더 적절합니다.
    # SystemManager의 initialize_managers 과정에서 AI 모델 매니저가 생성되고,
    # AI 모델 매니저의 __init__ 또는 별도의 메서드에서 모델 로딩 및 적용을 수행해야 합니다.
    # main에서는 AI 모델 매니저를 가져와 필요한 초기화 메서드를 호출하는 방식으로 변경합니다.
    try:
        ai_model_manager = system_manager.get_manager("ai_model")
        if ai_model_manager:
            # AI 모델 매니저에 모델 로딩/적용 메서드가 있다고 가정
            # 모델 경로는 AppConfig 또는 settings_manager에서 가져와야 합니다.
            # 예: model_path = settings_manager.get_setting("MODEL_PATH")
            # ai_model_manager.load_and_apply_model(model_path) # AI 모델 매니저에 구현 필요
            logging.info(text_manager.get_log_text("354", message="AI Model Manager initialized. Model loading/application should happen internally.")) # text_manager 사용
        else:
            logging.warning(text_manager.get_warning_text("416")) # AI Model Manager 누락 경고 (새 ID 필요)
            # AI 모델이 필수적이라면 여기서 오류 처리 및 종료

    except FileNotFoundError as e:
        logging.critical(text_manager.get_error_text("507", e=e)) # text_manager 사용
        QMessageBox.critical(None, text_manager.get_general_text("error"), # text_manager 사용
                             text_manager.get_error_text("507", e=e)) # text_manager 사용
        sys.exit(1) # 모델 파일 로드 실패 시 종료
    except Exception as e:
        logging.exception(text_manager.get_error_text("508", e=e)) # text_manager 사용
        QMessageBox.critical(None, text_manager.get_general_text("error"), # text_manager 사용
                             text_manager.get_error_text("508", e=e)) # text_manager 사용
        sys.exit(1) # 모델 적용 중 오류 발생 시 종료

    main_window.show()
    sys.exit(app.exec_()) # 애플리케이션 실행


if __name__ == "__main__":
    # 멀티프로세싱 시작 메서드 설정 (Windows에서는 'spawn'이 안전) - 멀티프로세싱 제거 시 필요 없음
    # multiprocessing.freeze_support() # 실행 파일 생성 시 필요
    # multiprocessing.set_start_method('spawn', force=True)
    try:
        # 설정 로드는 main 함수 내부에서 수행
        main()
    except KeyError as e:
        logging.critical(text_manager.get_error_text("509", key=e)) # text_manager 사용
        QMessageBox.critical(None, text_manager.get_general_text("configuration_error"), # text_manager 사용
                             text_manager.get_error_text("509", key=e)) # text_manager 사용
        sys.exit(1)
    except Exception as e:
        logging.critical(text_manager.get_error_text("510", e=e), exc_info=True) # text_manager 사용
        QMessageBox.critical(None, text_manager.get_general_text("application_error"), # text_manager 사용
                             text_manager.get_error_text("510", e=e)) # text_manager 사용
        sys.exit(1)