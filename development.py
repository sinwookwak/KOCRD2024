# config/development.py
# 개발 환경 설정 파일
from sympy import true
{
  "managers": {
    "database": {
      "class": "DatabaseManager",
      "module": "kocrd.managers.database_manager", # 모듈 경로 추가
      "kwargs": {
        "db_path": "DATABASE_PATH",
        "backup_path": "DATABASE_BACKUP_PATH"
      }
    },
    "temp_file": {
      "class": "TempFileManager",
      "module": "kocrd.managers.temp_file_manager", # 모듈 경로 추가
      "dependencies": [],
      "inject_settings": True
    },
    "ocr": {
      "class": "OCRManager",
      "module": "kocrd.managers.ocr.ocr_manager", # 모듈 경로 추가
      "dependencies": [],
      "kwargs": {
        "tesseract_cmd": "TESSERACT_CMD",
        "tessdata_dir": "TESSDATA_DIR"
      },
      "inject_settings": True,
      "inject_main_window": True
    },
    "menubar": {
      "class": "MenubarManager",
      "module": "kocrd.managers.menubar_manager", # 모듈 경로 추가
      "dependencies": [],
      "inject_system_manager": True
    },
    "ai_model": {
      "class": "AIModelManager",
      "module": "kocrd.managers.ai_managers.ai_model_manager", # 모듈 경로 추가
      "kwargs": {
        "model_path": "MODELS_PATH",
        "model_type": "gpt2",
        "inject_settings": True
      }
    },
    "ai_data": {
      "class": "AIDataManager",
      "module": "kocrd.managers.ai_managers.ai_data_manager", # 모듈 경로 추가
      "dependencies": ["database"]
    },
    "ai_prediction": {
      "class": "AIPredictionManager",
      "module": "kocrd.managers.ai_managers.ai_prediction_manager", # 모듈 경로 추가
      "dependencies": ["ai_model", "ai_data", "database"],
      "inject_settings": True
    },
    "monitoring": {
      "class": "MonitoringManager",
      "module": "kocrd.managers.monitoring_manager", # 모듈 경로 추가
      "dependencies": ["document", "ocr", "ai_prediction"]
    },
    "message_queue": {
      "class": "RabbitMQManager",
      "module": "kocrd.managers.rabbitmq_manager", # 모듈 경로 추가
      "dependencies": []
    },
    "document": {
      "class": "DocumentManager",
      "module": "kocrd.managers.document.document_manager", # 모듈 경로 추가
      "dependencies": ["ocr", "database", "message_queue"],
      "inject_main_window": True,
      "inject_system_manager": True
    },
    "ai_trainer": {
      "class": "AITrainer",
      "module": "kocrd.managers.ai_managers.ai_training_manager", # 모듈 경로 추가
      "dependencies": ["ai_model", "ai_data", "message_queue", "database", "settings_manager"],
      "kwargs": {},
      "inject_settings": True
    },
    "settings_manager": {
      "class": "SettingsManager",
      "module": "kocrd.managers.settings_manager", # 모듈 경로 추가
      "kwargs": {
        "config_file": "config/development.json"
      }
    },
    "document_processor":{ # document_processor 추가
        "class": "DocumentProcessor",
        "module": "kocrd.managers.document.document_processor"
    },
     "analysis_manager":{ # analysis_manager 추가
        "class": "AnalysisManager",
        "module": "kocrd.managers.analysis_manager"
    }
  },
  "uis": {
    "menubar": {
      "class": "MenubarUI",
      "module": "kocrd.ui.menubar_ui", # 모듈 경로 추가
      "dependencies": [],
      "inject_system_manager": True
    },
    "document": {
      "class": "DocumentUI",
      "module": "kocrd.ui.document_ui", # 모듈 경로 추가
      "dependencies": [],
      "inject_system_manager": True
    },
    "monitoring": {
      "class": "MonitoringUI",
      "module": "kocrd.ui.monitoring_ui", # 모듈 경로 추가
      "dependencies": [],
      "inject_system_manager": True
    }
  },
      "settings":{
        "document_types_path" : "path/to/document_types.json",
        "ai_model_path": "path/to/your/ai_model" # AI 모델 경로 추가
      },
  "queues": {
    "prediction_requests": "prediction_requests",
    "prediction_results": "prediction_results",
    "ui_feedback_requests": "ui_feedback_requests",
    "events": "events",
    "document_processing": "document_processing",
    "database_packaging": "database_packaging",
    "result": "result",
    "ai_training_queue": "ai_training_queue",
    "temp_file_queue": "temp_file_queue",
    "prediction_requests_queue": "prediction_requests_queue",
    "events_queue": "events_queue",
    "ocr_results": "ocr_results",
    "ocr_requests": "ocr_requests",
    "ai_result_handling" : "ai_result_handling",
    "feedback_queue": "feedback_queue"
  }
}
