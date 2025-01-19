# main.py
import sys
import os
import logging
import multiprocessing
import time
from PyQt5.QtWidgets import QApplication, QMessageBox

from main_window import MainWindow
from managers.system_manager import SystemManager
from managers.settings_manager import SettingsManager

# 로깅 설정 (이전과 동일)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("ocr_ai.log", mode="a", encoding="utf-8")
    ]
)

# 환경 변수 확인 및 config 로드 (이전과 동일)
env = os.environ.get("PYTHON_ENV", "development")
try:
    if env == "development":
        from config.development import *
        logging.info("Development config loaded.")
    else:
        raise ValueError(f"Invalid environment: {env}")
except ImportError as e:
    logging.error(f"Config import error: {e}")
    sys.exit()

def run_worker():
    """Worker 프로세스를 실행하는 함수."""
    import worker
    worker.main()
def main():
    app = QApplication(sys.argv)
    settings_manager = SettingsManager("config/development.json") # 설정 파일 경로 전달
    config = settings_manager.load_config() # 설정 로드

    # Worker 프로세스 시작
    worker_process = multiprocessing.Process(target=run_worker)
    worker_process.start()
    logging.info("Worker process started.")
    try:
        # Magic String 제거를 위한 상수 정의
        MODEL_PATH_KEY = "model_path"
        TESSERACT_CMD_KEY = "tesseract_cmd"
        TESSDATA_DIR_KEY = "tessdata_dir"
        MANAGERS_KEY = "managers"
        AI_MODEL_KEY = "ai_model"
        KWARGS_KEY = "kwargs"

        # get_setting 메서드 활용 및 settings_manager 인스턴스 전달
        model_path = settings_manager.get_setting(MANAGERS_KEY).get(AI_MODEL_KEY).get(KWARGS_KEY).get(MODEL_PATH_KEY)
        tesseract_cmd = settings_manager.get_setting(MANAGERS_KEY).get("ocr").get(KWARGS_KEY).get(TESSERACT_CMD_KEY)
        tessdata_dir = settings_manager.get_setting(MANAGERS_KEY).get("ocr").get(KWARGS_KEY).get(TESSDATA_DIR_KEY)
        system_manager = SystemManager(settings_manager, None, tesseract_cmd, tessdata_dir)

        try:
            ai_model_manager = system_manager.get_manager("ai_model")
            ai_model_manager.apply_trained_model(model_path + "/model_weights.h5")
        except FileNotFoundError as e:
            logging.error(f"모델 파일 로드 실패: {e}")
            QMessageBox.critical(None, "오류", f"모델 파일 로드 실패: {e}")
            sys.exit(1)
        except Exception as e:
            logging.exception(f"모델 적용 중 오류 발생: {e}")
            QMessageBox.critical(None, "오류", f"모델 적용 중 오류 발생: {e}")
            sys.exit(1)

        main_window = MainWindow(system_manager) # MainWindow 생성 시점에 SystemManager 전달
        system_manager.main_window = main_window # SystemManager에 MainWindow 할당
        main_window.show()
        logging.info("OCR AI Application started.")
        sys.exit(app.exec_())

    except Exception as e:
        logging.critical(f"Critical error: {e}")
        QMessageBox.critical(None, "오류", f"치명적인 오류가 발생했습니다: {e}")
        sys.exit(1)
    finally:
        worker_process.terminate()
        worker_process.join(timeout=5)  # worker 프로세스가 5초 안에 종료되지 않으면 강제 종료
        if worker_process.is_alive():
            logging.warning("Worker process did not terminate gracefully.")
        logging.info("Worker process terminated.")

if __name__ == "__main__":
    main()
