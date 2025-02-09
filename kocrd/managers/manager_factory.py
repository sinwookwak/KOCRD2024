from kocrd.managers.database_manager import DatabaseManager
from kocrd.managers.ocr.ocr_manager import OCRManager
# ... (다른 매니저 import)

class ManagerFactory:
    def __init__(self, config_manager):
        self.config_manager = config_manager

    def create_manager(self, manager_name, manager_config):
        module_path = manager_config["module"]
        class_name = manager_config["class"]
        dependencies = manager_config.get("dependencies", [])
        kwargs = manager_config.get("kwargs", {})

        module = __import__(module_path, fromlist=[class_name])
        manager_class = getattr(module, class_name)

        # 의존성 해결
        dependency_instances = [self.create_manager(dep, self.config_manager.get("managers."+dep)) for dep in dependencies] # 재귀 호출
        if manager_name == "database": # 예시: DatabaseManager에 대한 추가 설정
            db_path = self.config_manager.get("database_url")
            backup_path = self.config_manager.get("file_settings.default_report_filename")
            return manager_class(*dependency_instances, db_path=db_path, backup_path=backup_path, **kwargs)
        elif manager_name == "ocr":
            tesseract_cmd = self.config_manager.get("file_paths.tesseract_cmd")
            tessdata_dir = self.config_manager.get("file_paths.tessdata_dir")
            return manager_class(*dependency_instances, tesseract_cmd=tesseract_cmd, tessdata_dir=tessdata_dir, **kwargs)
        # ... 다른 매니저에 대한 조건 추가
        return manager_class(*dependency_instances, **kwargs)

    def get_class(self, module_name: str, class_name: str):
        """모듈에서 클래스를 동적으로 가져옵니다."""
        module = __import__(module_name, fromlist=[class_name])
        return getattr(module, class_name)
    def create_temp_file_manager(self):
        return TempFileManager(self.settings_manager)

    def create_database_manager(self):
        return DatabaseManager(self.settings_manager.get_setting("db_path"), self.settings_manager.get_setting("backup_path"))

