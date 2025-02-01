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
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except UnicodeDecodeError as e:
        logging.critical(f"설정 파일을 읽는 중 오류 발생: {e}")
        raise
    settings_manager = SettingsManager(config_path)
    settings_manager.load_from_env()  # 환경 변수에서 설정 로드 추가
    return settings_manager, config

def get_required_setting(settings, key, error_message):
    value = settings.get(key)
    if value is None:
        logging.critical(error_message)
        raise KeyError(error_message)
    return value

def main():
    app = QApplication(sys.argv)
    try:
        settings_manager, config = initialize_settings("config/development.json")  # Update the config file path
    except Exception as e:
        logging.critical(f"Failed to initialize settings: {e}")
        return

    global development
    development = config  # JSON 객체로 로드된 설정을 전역 변수로 설정

    # 상수 가져오기
    if "constants" not in config:
        logging.critical("Critical error: 'constants' not found in settings")
        return

    constants = config["constants"]
    MODEL_PATH_KEY = constants["MODEL_PATH_KEY"]
    TESSERACT_CMD_KEY = constants["TESSERACT_CMD_KEY"]
    TESSDATA_DIR_KEY = constants["TESSDATA_DIR_KEY"]
    MANAGERS_KEY = constants["MANAGERS_KEY"]
    AI_MODEL_KEY = constants["AI_MODEL_KEY"]
    KWARGS_KEY = constants["KWARGS_KEY"]

    # Worker 프로세스 시작
    worker_process = multiprocessing.Process(target=run_worker)
    worker_process.start()
    logging.info("Worker process started.")

    try:
        # 설정 값 가져오기
        managers = get_required_setting(config, MANAGERS_KEY, f"Critical error: '{MANAGERS_KEY}' not found in settings")
        ai_model = get_required_setting(managers, AI_MODEL_KEY, f"Critical error: '{AI_MODEL_KEY}' not found in managers")
        kwargs = get_required_setting(ai_model, KWARGS_KEY, f"Critical error: '{KWARGS_KEY}' not found in ai_model")
        model_path = get_required_setting(kwargs, MODEL_PATH_KEY, f"Critical error: '{MODEL_PATH_KEY}' not found in kwargs")
        ocr = get_required_setting(managers, "ocr", "Critical error: 'ocr' not found in managers")
        ocr_kwargs = get_required_setting(ocr, KWARGS_KEY, f"Critical error: '{KWARGS_KEY}' not found in ocr")
        tesseract_cmd = get_required_setting(ocr_kwargs, TESSERACT_CMD_KEY, f"Critical error: '{TESSERACT_CMD_KEY}' not found in ocr_kwargs")
        tessdata_dir = get_required_setting(ocr_kwargs, TESSDATA_DIR_KEY, f"Critical error: '{TESSDATA_DIR_KEY}' not found in ocr_kwargs")

        system_manager = SystemManager(settings_manager, None, tesseract_cmd, tessdata_dir)

        try:
            ai_model_manager = system_manager.get_manager("ai_model")
            ai_model_manager.apply_trained_model(model_path + "/model_weights.h5")
        except FileNotFoundError as e:
            logging.error(f"모델 파일 로드 실패: {e}")
            QMessageBox.critical(None, "오류", f"모델 파일 로드 실패: {e}")
            return
        except Exception as e:
            logging.exception(f"모델 적용 중 오류 발생: {e}")
            return
    except Exception as e:
        logging.exception(f"Unexpected error: {e}")
        return

if __name__ == "__main__":
    main()