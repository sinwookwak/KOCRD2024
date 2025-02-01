# main.py
import sys
import logging
import multiprocessing
from PyQt5.QtWidgets import QApplication, QMessageBox
import os
import json

# 프로젝트 루트 디렉토리를 sys.path에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from kocrd.Settings.settings_manager import SettingsManager
from managers.system_manager import SystemManager

def run_worker():
    """Worker 프로세스를 실행하는 함수."""
    import worker
    worker.main()

def initialize_settings(settings_path):
    config_path = os.path.join(os.path.dirname(__file__), settings_path)
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    settings_manager = SettingsManager(config_path)
    return settings_manager, config

def get_required_setting(settings, key, error_message):
    value = settings.get(key)
    if value is None:
        logging.critical(error_message)
        sys.exit(1)
    return value

def main():
    app = QApplication(sys.argv)
    settings_manager, config = initialize_settings("config/development.json")  # Update the config file path
    global development
    development = config  # JSON 객체로 로드된 설정을 전역 변수로 설정

    # Worker 프로세스 시작
    worker_process = multiprocessing.Process(target=run_worker)
    worker_process.start()
    logging.info("Worker process started.")

    try:
        # Magic String 제거를 위한 상수 정의
        MODEL_PATH_KEY = "model_path"
        TESSERACT_CMD_KEY = "tessera_cmd"
        TESSDATA_DIR_KEY = "tessdata_dir"
        MANAGERS_KEY = "managers"
        AI_MODEL_KEY = "ai_model"
        KWARGS_KEY = "kwargs"

        # 설정 값 가져오기
        managers = settings_manager.get_setting(MANAGERS_KEY)
        if managers is None:
            logging.critical(f"Critical error: '{MANAGERS_KEY}' not found in settings")
            sys.exit(1)
        
        ai_model = managers.get(AI_MODEL_KEY)
        if ai_model is None:
            logging.critical(f"Critical error: '{AI_MODEL_KEY}' not found in managers")
            sys.exit(1)
        
        kwargs = ai_model.get(KWARGS_KEY)
        if kwargs is None:
            logging.critical(f"Critical error: '{KWARGS_KEY}' not found in ai_model")
            sys.exit(1)
        
        model_path = kwargs.get(MODEL_PATH_KEY)
        if model_path is None:
            logging.critical(f"Critical error: '{MODEL_PATH_KEY}' not found in kwargs")
            sys.exit(1)
        
        ocr = managers.get("ocr")
        if ocr is None:
            logging.critical(f"Critical error: 'ocr' not found in managers")
            sys.exit(1)
        
        ocr_kwargs = ocr.get(KWARGS_KEY)
        if ocr_kwargs is None:
            logging.critical(f"Critical error: '{KWARGS_KEY}' not found in ocr")
            sys.exit(1)
        
        tesseract_cmd = ocr_kwargs.get(TESSERACT_CMD_KEY)
        if tesseract_cmd is None:
            logging.critical(f"Critical error: '{TESSERACT_CMD_KEY}' not found in ocr_kwargs")
            sys.exit(1)
        
        tessdata_dir = ocr_kwargs.get(TESSDATA_DIR_KEY)
        if tessdata_dir is None:
            logging.critical(f"Critical error: '{TESSDATA_DIR_KEY}' not found in ocr_kwargs")
            sys.exit(1)

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