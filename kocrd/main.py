# main.py
import sys
import logging
import multiprocessing
from PyQt5.QtWidgets import QApplication, QMessageBox
from managers.settings_manager import SettingsManager
from managers.system_manager import SystemManager

def run_worker():
    """Worker 프로세스를 실행하는 함수."""
    import worker
    worker.main()

def initialize_settings(settings_path):
    settings_manager = SettingsManager(settings_path)
    config = settings_manager.load_config()
    return settings_manager, config

def get_required_setting(settings, key, error_message):
    value = settings.get(key)
    if value is None:
        logging.critical(error_message)
        sys.exit(1)
    return value

def main():
    app = QApplication(sys.argv)
    settings_manager, config = initialize_settings("config/development.json")

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

        # 설정 값 가져오기
        managers = get_required_setting(settings_manager.get_setting(MANAGERS_KEY), MANAGERS_KEY, f"Critical error: '{MANAGERS_KEY}' not found in settings")
        ai_model = get_required_setting(managers.get(AI_MODEL_KEY), AI_MODEL_KEY, f"Critical error: '{AI_MODEL_KEY}' not found in managers")
        kwargs = get_required_setting(ai_model.get(KWARGS_KEY), KWARGS_KEY, f"Critical error: '{KWARGS_KEY}' not found in ai_model")
        model_path = get_required_setting(kwargs.get(MODEL_PATH_KEY), MODEL_PATH_KEY, f"Critical error: '{MODEL_PATH_KEY}' not found in kwargs")
        ocr = get_required_setting(managers.get("ocr"), "ocr", f"Critical error: 'ocr' not found in managers")
        ocr_kwargs = get_required_setting(ocr.get(KWARGS_KEY), KWARGS_KEY, f"Critical error: '{KWARGS_KEY}' not found in ocr")
        tesseract_cmd = get_required_setting(ocr_kwargs.get(TESSERACT_CMD_KEY), TESSERACT_CMD_KEY, f"Critical error: '{TESSERACT_CMD_KEY}' not found in ocr_kwargs")
        tessdata_dir = get_required_setting(ocr_kwargs.get(TESSDATA_DIR_KEY), TESSDATA_DIR_KEY, f"Critical error: '{TESSDATA_DIR_KEY}' not found in ocr_kwargs")

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
            sys.exit(1)
    except Exception as e:
        logging.exception(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()