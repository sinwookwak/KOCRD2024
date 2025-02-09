from kocrd.managers.database_manager import DatabaseManager
from kocrd.managers.ocr.ocr_manager import OCRManager
from kocrd.managers.temp_file_manager import TempFileManager
from kocrd.managers.ai_managers.ai_training_manager import AITrainingManager

class ManagerFactory:
    def __init__(self, config_manager):
        self.config_manager = config_manager
    def create_manager(self, manager_name, manager_config):
        module_path = manager_config["module"]
        class_name = manager_config["class"]
        dependencies = manager_config.get("dependencies", [])
        kwargs = manager_config.get("kwargs", {})
        additional_settings = manager_config.get("additional_settings", {})

        module = __import__(module_path, fromlist=[class_name])
        manager_class = getattr(module, class_name)

        # 의존성 객체 생성
        dependency_instances = [
            self.create_manager(dep, self.config_manager.get(f"managers.{dep}")) for dep in dependencies
        ]

        # 추가 설정 적용
        if additional_settings:
            for setting_name, config_key in additional_settings.items():
                config_value = self.config_manager.get(config_key)
                if config_value is not None:
                    kwargs[setting_name] = config_value

        # 매니저 생성
        return manager_class(*dependency_instances, **kwargs)

    def get_class(self, module_name: str, class_name: str):
        """모듈에서 클래스를 동적으로 가져옵니다."""
        module = __import__(module_name, fromlist=[class_name])
        return getattr(module, class_name)
    def create_temp_file_manager(self):
        return TempFileManager(self.settings_manager)

    def create_database_manager(self):
        return DatabaseManager(self.settings_manager.get_setting("db_path"), self.settings_manager.get_setting("backup_path"))

