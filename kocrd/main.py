# main.py
import sys
import logging
import multiprocessing
from PyQt5.QtWidgets import QApplication, QMessageBox
import os

# 프로젝트 루트 디렉토리를 sys.path에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import system

def run_worker():
    """Worker 프로세스를 실행하는 함수."""
    import system
    system.main()

def get_required_setting(settings, key, error_message):
    value = settings.get(key)
    if value is None:
        raise KeyError(error_message)
    return value

def start_worker_process():
    worker_process = multiprocessing.Process(target=run_worker)
    worker_process.start()
    return worker_process

def main():
    logging.basicConfig(level=logging.INFO)
    app = QApplication(sys.argv)
    try:
        settings_manager, config = system.SystemManager.initialize_settings("config/development.json")
    except Exception as e:
        logging.critical(f"Failed to initialize settings: {e}")
        return

    global development
    development = config

    constants = config.get("constants", {})
    if not constants:
        logging.critical("Missing 'constants' in configuration file.")
        return

    try:
        managers = get_required_setting(config, constants.get("MANAGERS_KEY", ""), f"Critical error: '{constants.get('MANAGERS_KEY', '')}' not found in settings")
        ai_model = get_required_setting(managers, constants.get("AI_MODEL_KEY", ""), f"Critical error: '{constants.get('AI_MODEL_KEY', '')}' not found in managers")
        kwargs = get_required_setting(ai_model, constants.get("KWARGS_KEY", ""), f"Critical error: '{constants.get('KWARGS_KEY', '')}' not found in ai_model")
        model_path = get_required_setting(kwargs, constants.get("MODEL_PATH_KEY", ""), f"Critical error: '{constants.get('MODEL_PATH_KEY', '')}' not found in kwargs")
        ocr = get_required_setting(managers, "ocr", "Critical error: 'ocr' not found in managers")
        ocr_kwargs = get_required_setting(ocr, constants.get("KWARGS_KEY", ""), f"Critical error: '{constants.get('KWARGS_KEY', '')}' not found in ocr")
        tesseract_cmd = get_required_setting(ocr_kwargs, constants.get("TESSERACT_CMD_KEY", ""), f"Critical error: '{constants.get('TESSERACT_CMD_KEY', '')}' not found in ocr_kwargs")
        tessdata_dir = get_required_setting(ocr_kwargs, constants.get("TESSDATA_DIR_KEY", ""), f"Critical error: '{constants.get('TESSDATA_DIR_KEY', '')}' not found in ocr_kwargs")

        system_manager = system.SystemManager(settings_manager, None, tesseract_cmd, tessdata_dir)

        try:
            ai_model_manager = system_manager.get_manager("ai_model")
            ai_model_manager.apply_trained_model(model_path + "/model_weights.h5")
        except FileNotFoundError as e:
            QMessageBox.critical(None, "오류", f"모델 파일 로드 실패: {e}")
            return
        except Exception as e:
            logging.exception(f"모델 적용 중 오류 발생: {e}")
            return

        worker_process = start_worker_process()
    except Exception as e:
        logging.exception(f"Unexpected error: {e}")
        return

if __name__ == "__main__":
    try:
        settings_manager, config = system.SystemManager.initialize_settings()
        main()
    except KeyError as e:
        logging.critical(f"Configuration error: {e}")
    except Exception as e:
        logging.critical(f"Failed to initialize application: {e}")