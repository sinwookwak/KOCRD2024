# kocrd/managers/unified_temp_manager.py
"""
Unified Temporary File Manager

This module consolidates the overlapping functionality from DocumentTempManager, 
TempFileManager, and document manager temp file operations into a single, 
pattern-based manager using the new base manager architecture.
"""

import os
import tempfile
import shutil
import uuid
import json
import time
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Union, BinaryIO, TextIO
from pathlib import Path
from dataclasses import dataclass
import threading
from enum import Enum
from contextlib import contextmanager, asynccontextmanager

from kocrd.patterns.base_manager import ConfigurableManager, ResourceManager, manager_method
from kocrd.patterns.messaging_system import global_message_bus, Message, MessageType
from kocrd.config.config import text_manager, AppConfig
from kocrd.config.unified_constants import SystemConstants


class TempFileType(Enum):
    """Types of temporary files"""
    DOCUMENT = "document"
    IMAGE = "image"
    OCR_RESULT = "ocr_result"
    PROCESSING = "processing"
    BACKUP = "backup"
    CACHE = "cache"


class TempFilePermission(Enum):
    """Permission levels for temporary files"""
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"
    EXECUTE = "execute"


@dataclass
class TempFileInfo:
    """Information about a temporary file"""
    id: str
    path: str
    file_type: TempFileType
    size: int
    created_at: datetime
    accessed_at: datetime
    expires_at: Optional[datetime]
    permissions: TempFilePermission
    metadata: Dict[str, Any]
    ref_count: int = 0


class TempFileContext:
    """Context manager for temporary files"""
    
    def __init__(self, manager: 'UnifiedTempManager', file_info: TempFileInfo):
        self.manager = manager
        self.file_info = file_info
        self._file_handle = None
    
    def __enter__(self):
        self.manager._increment_ref_count(self.file_info.id)
        return self.file_info.path
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.manager._decrement_ref_count(self.file_info.id)
        if self._file_handle:
            self._file_handle.close()


class AsyncTempFileContext:
    """Async context manager for temporary files"""
    
    def __init__(self, manager: 'UnifiedTempManager', file_info: TempFileInfo):
        self.manager = manager
        self.file_info = file_info
        self._file_handle = None
    
    async def __aenter__(self):
        self.manager._increment_ref_count(self.file_info.id)
        return self.file_info.path
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.manager._decrement_ref_count(self.file_info.id)
        if self._file_handle:
            self._file_handle.close()


class UnifiedTempManager(ResourceManager):
    """
    Unified temporary file manager that consolidates all temp file operations
    """
    
    def __init__(self, name: str = "unified_temp", settings_manager: Any = None, **kwargs):
        super().__init__(name, settings_manager, **kwargs)
        
        # Configuration
        self.base_temp_dir = self.get_config_value("temp_dir", tempfile.gettempdir())
        self.app_temp_dir = os.path.join(self.base_temp_dir, "kocrd_temp")
        self.backup_dir = os.path.join(self.app_temp_dir, "backup")
        self.cache_dir = os.path.join(self.app_temp_dir, "cache")
        
        # Retention settings
        self.default_retention_time = self.get_config_value("default_retention_hours", 24) * 3600
        self.backup_retention_time = self.get_config_value("backup_retention_hours", 168) * 3600  # 7 days
        self.cache_retention_time = self.get_config_value("cache_retention_hours", 72) * 3600  # 3 days
        
        # Auto-cleanup settings
        self.cleanup_interval = self.get_config_value("cleanup_interval_minutes", 60) * 60
        self.auto_cleanup_enabled = self.get_config_value("auto_cleanup_enabled", True)
        
        # Storage
        self._temp_files: Dict[str, TempFileInfo] = {}
        self._file_lock = threading.RLock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._cleanup_timer: Optional[threading.Timer] = None
        
        # Statistics
        self._stats = {
            'files_created': 0,
            'files_deleted': 0,
            'bytes_created': 0,
            'bytes_deleted': 0,
            'cleanup_runs': 0
        }
    
    async def _initialize_internal(self):
        """Initialize the temporary file manager"""
        # Create necessary directories
        for directory in [self.app_temp_dir, self.backup_dir, self.cache_dir]:
            os.makedirs(directory, exist_ok=True)
        
        # Load existing temp file registry if it exists
        await self._load_registry()
        
        # Auto-cleanup will be started in _start_internal method
        
        # Register message handlers
        await self._register_message_handlers()
        
        logging.info(f"UnifiedTempManager initialized with base dir: {self.app_temp_dir}")
    
    async def _start_internal(self):
        """Start the manager"""
        await super()._start_internal()
        if self.auto_cleanup_enabled and not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self._auto_cleanup_loop())
    
    async def _stop_internal(self):
        """Stop the manager"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        if self._cleanup_timer:
            self._cleanup_timer.cancel()
        
        # Save registry before shutdown
        await self._save_registry()
        
        await super()._stop_internal()
    
    async def _register_message_handlers(self):
        """Register message handlers for temp file operations"""
        from kocrd.patterns.messaging_system import CommandHandler
        
        commands = {
            'create_temp_file': self._handle_create_temp_file,
            'delete_temp_file': self._handle_delete_temp_file,
            'cleanup_temp_files': self._handle_cleanup_temp_files,
            'get_temp_file_info': self._handle_get_temp_file_info,
            'backup_temp_files': self._handle_backup_temp_files,
            'restore_temp_files': self._handle_restore_temp_files
        }
        
        handler = CommandHandler(commands)
        global_message_bus.register_handler(f"command.{self.name}", handler)
    
    @manager_method("create_temp_file")
    async def create_temp_file(self, 
                              content: Union[str, bytes] = None,
                              suffix: str = ".tmp",
                              file_type: TempFileType = TempFileType.PROCESSING,
                              retention_time: Optional[int] = None,
                              metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a temporary file and return its ID"""
        
        file_id = str(uuid.uuid4())
        timestamp = datetime.now()
        
        # Determine file path
        type_dir = os.path.join(self.app_temp_dir, file_type.value)
        os.makedirs(type_dir, exist_ok=True)
        
        file_path = os.path.join(type_dir, f"{file_id}{suffix}")
        
        # Create the file
        if content is not None:
            mode = 'wb' if isinstance(content, bytes) else 'w'
            encoding = None if isinstance(content, bytes) else 'utf-8'
            
            with open(file_path, mode, encoding=encoding) as f:
                f.write(content)
        else:
            # Create empty file
            Path(file_path).touch()
        
        # Calculate file size
        file_size = os.path.getsize(file_path)
        
        # Determine expiration time
        retention = retention_time or self.default_retention_time
        expires_at = timestamp + timedelta(seconds=retention)
        
        # Create file info
        file_info = TempFileInfo(
            id=file_id,
            path=file_path,
            file_type=file_type,
            size=file_size,
            created_at=timestamp,
            accessed_at=timestamp,
            expires_at=expires_at,
            permissions=TempFilePermission.READ_WRITE,
            metadata=metadata or {}
        )
        
        # Register the file
        with self._file_lock:
            self._temp_files[file_id] = file_info
        
        # Update statistics
        self._stats['files_created'] += 1
        self._stats['bytes_created'] += file_size
        
        # Publish event
        await global_message_bus.send_event("temp_file_created", {
            'file_id': file_id,
            'file_type': file_type.value,
            'size': file_size,
            'path': file_path
        })
        
        logging.debug(f"Created temp file: {file_id} at {file_path}")
        return file_id
    
    @manager_method("get_temp_file_path")
    def get_temp_file_path(self, file_id: str) -> Optional[str]:
        """Get the file path for a temporary file"""
        with self._file_lock:
            file_info = self._temp_files.get(file_id)
            if file_info:
                file_info.accessed_at = datetime.now()
                return file_info.path
        return None
    
    @manager_method("get_temp_file_info")
    def get_temp_file_info(self, file_id: str) -> Optional[TempFileInfo]:
        """Get information about a temporary file"""
        with self._file_lock:
            file_info = self._temp_files.get(file_id)
            if file_info:
                file_info.accessed_at = datetime.now()
                return file_info
        return None
    
    @contextmanager
    def temp_file_context(self, file_id: str):
        """Context manager for accessing temporary files"""
        file_info = self.get_temp_file_info(file_id)
        if not file_info:
            raise FileNotFoundError(f"Temporary file not found: {file_id}")
        
        return TempFileContext(self, file_info)
    
    @asynccontextmanager
    async def async_temp_file_context(self, file_id: str):
        """Async context manager for accessing temporary files"""
        file_info = self.get_temp_file_info(file_id)
        if not file_info:
            raise FileNotFoundError(f"Temporary file not found: {file_id}")
        
        return AsyncTempFileContext(self, file_info)
    
    @manager_method("read_temp_file")
    async def read_temp_file(self, file_id: str, mode: str = 'r') -> Union[str, bytes]:
        """Read content from a temporary file"""
        file_path = self.get_temp_file_path(file_id)
        if not file_path or not os.path.exists(file_path):
            raise FileNotFoundError(f"Temporary file not found: {file_id}")
        
        encoding = None if 'b' in mode else 'utf-8'
        
        with open(file_path, mode, encoding=encoding) as f:
            return f.read()
    
    @manager_method("write_temp_file")
    async def write_temp_file(self, file_id: str, content: Union[str, bytes], mode: str = 'w') -> bool:
        """Write content to a temporary file"""
        file_path = self.get_temp_file_path(file_id)
        if not file_path:
            raise FileNotFoundError(f"Temporary file not found: {file_id}")
        
        encoding = None if 'b' in mode else 'utf-8'
        
        try:
            with open(file_path, mode, encoding=encoding) as f:
                f.write(content)
            
            # Update file info
            with self._file_lock:
                file_info = self._temp_files.get(file_id)
                if file_info:
                    file_info.size = os.path.getsize(file_path)
                    file_info.accessed_at = datetime.now()
            
            return True
        except Exception as e:
            logging.error(f"Failed to write to temp file {file_id}: {e}")
            return False
    
    @manager_method("delete_temp_file")
    async def delete_temp_file(self, file_id: str, force: bool = False) -> bool:
        """Delete a temporary file"""
        with self._file_lock:
            file_info = self._temp_files.get(file_id)
            if not file_info:
                return False
            
            # Check reference count
            if not force and file_info.ref_count > 0:
                logging.warning(f"Cannot delete temp file {file_id}: still in use (ref_count: {file_info.ref_count})")
                return False
            
            # Remove from registry
            del self._temp_files[file_id]
        
        # Delete physical file
        try:
            if os.path.exists(file_info.path):
                os.remove(file_info.path)
                self._stats['files_deleted'] += 1
                self._stats['bytes_deleted'] += file_info.size
            
            # Publish event
            await global_message_bus.send_event("temp_file_deleted", {
                'file_id': file_id,
                'file_type': file_info.file_type.value,
                'size': file_info.size
            })
            
            logging.debug(f"Deleted temp file: {file_id}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to delete temp file {file_id}: {e}")
            return False
    
    @manager_method("cleanup_expired_files")
    async def cleanup_expired_files(self) -> int:
        """Clean up expired temporary files"""
        current_time = datetime.now()
        expired_files = []
        
        with self._file_lock:
            for file_id, file_info in self._temp_files.items():
                if file_info.expires_at and current_time > file_info.expires_at:
                    if file_info.ref_count == 0:  # Only clean up unused files
                        expired_files.append(file_id)
        
        # Delete expired files
        deleted_count = 0
        for file_id in expired_files:
            if await self.delete_temp_file(file_id):
                deleted_count += 1
        
        self._stats['cleanup_runs'] += 1
        
        if deleted_count > 0:
            logging.info(f"Cleaned up {deleted_count} expired temporary files")
            await global_message_bus.send_event("temp_files_cleaned", {
                'deleted_count': deleted_count,
                'cleanup_type': 'expired'
            })
        
        return deleted_count
    
    @manager_method("cleanup_by_type")
    async def cleanup_by_type(self, file_type: TempFileType, older_than_hours: int = 24) -> int:
        """Clean up temporary files of a specific type older than specified hours"""
        cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
        files_to_delete = []
        
        with self._file_lock:
            for file_id, file_info in self._temp_files.items():
                if (file_info.file_type == file_type and 
                    file_info.created_at < cutoff_time and
                    file_info.ref_count == 0):
                    files_to_delete.append(file_id)
        
        # Delete files
        deleted_count = 0
        for file_id in files_to_delete:
            if await self.delete_temp_file(file_id):
                deleted_count += 1
        
        if deleted_count > 0:
            logging.info(f"Cleaned up {deleted_count} {file_type.value} files older than {older_than_hours} hours")
        
        return deleted_count
    
    @manager_method("backup_temp_files")
    async def backup_temp_files(self, file_types: Optional[List[TempFileType]] = None) -> int:
        """Backup temporary files to backup directory"""
        backed_up_count = 0
        backup_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_subdir = os.path.join(self.backup_dir, backup_timestamp)
        os.makedirs(backup_subdir, exist_ok=True)
        
        with self._file_lock:
            files_to_backup = self._temp_files.copy()
        
        for file_id, file_info in files_to_backup.items():
            if file_types and file_info.file_type not in file_types:
                continue
            
            if os.path.exists(file_info.path):
                try:
                    backup_path = os.path.join(backup_subdir, f"{file_id}_{os.path.basename(file_info.path)}")
                    shutil.copy2(file_info.path, backup_path)
                    backed_up_count += 1
                except Exception as e:
                    logging.error(f"Failed to backup temp file {file_id}: {e}")
        
        if backed_up_count > 0:
            # Create backup manifest
            manifest = {
                'timestamp': backup_timestamp,
                'backed_up_count': backed_up_count,
                'file_types': [ft.value for ft in file_types] if file_types else None,
                'files': [
                    {
                        'id': file_id,
                        'original_path': file_info.path,
                        'file_type': file_info.file_type.value,
                        'size': file_info.size,
                        'created_at': file_info.created_at.isoformat()
                    }
                    for file_id, file_info in files_to_backup.items()
                    if not file_types or file_info.file_type in file_types
                ]
            }
            
            manifest_path = os.path.join(backup_subdir, "manifest.json")
            with open(manifest_path, 'w') as f:
                json.dump(manifest, f, indent=2)
            
            logging.info(f"Backed up {backed_up_count} temporary files to {backup_subdir}")
            await global_message_bus.send_event("temp_files_backed_up", {
                'backed_up_count': backed_up_count,
                'backup_path': backup_subdir
            })
        
        return backed_up_count
    
    async def _auto_cleanup_loop(self):
        """Auto-cleanup loop that runs periodically"""
        while self.state.value in ['ready', 'running']:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self.cleanup_expired_files()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"Error in auto-cleanup loop: {e}")
    
    def _increment_ref_count(self, file_id: str):
        """Increment reference count for a file"""
        with self._file_lock:
            file_info = self._temp_files.get(file_id)
            if file_info:
                file_info.ref_count += 1
    
    def _decrement_ref_count(self, file_id: str):
        """Decrement reference count for a file"""
        with self._file_lock:
            file_info = self._temp_files.get(file_id)
            if file_info:
                file_info.ref_count = max(0, file_info.ref_count - 1)
    
    async def _load_registry(self):
        """Load temporary file registry from disk"""
        registry_path = os.path.join(self.app_temp_dir, "registry.json")
        if os.path.exists(registry_path):
            try:
                with open(registry_path, 'r') as f:
                    registry_data = json.load(f)
                
                # Validate and load files
                for file_data in registry_data.get('files', []):
                    if os.path.exists(file_data['path']):
                        file_info = TempFileInfo(
                            id=file_data['id'],
                            path=file_data['path'],
                            file_type=TempFileType(file_data['file_type']),
                            size=file_data['size'],
                            created_at=datetime.fromisoformat(file_data['created_at']),
                            accessed_at=datetime.fromisoformat(file_data['accessed_at']),
                            expires_at=datetime.fromisoformat(file_data['expires_at']) if file_data.get('expires_at') else None,
                            permissions=TempFilePermission(file_data.get('permissions', 'read_write')),
                            metadata=file_data.get('metadata', {})
                        )
                        self._temp_files[file_info.id] = file_info
                
                logging.info(f"Loaded {len(self._temp_files)} temporary files from registry")
                
            except Exception as e:
                logging.error(f"Failed to load temp file registry: {e}")
    
    async def _save_registry(self):
        """Save temporary file registry to disk"""
        registry_path = os.path.join(self.app_temp_dir, "registry.json")
        
        try:
            registry_data = {
                'timestamp': datetime.now().isoformat(),
                'files': [
                    {
                        'id': file_info.id,
                        'path': file_info.path,
                        'file_type': file_info.file_type.value,
                        'size': file_info.size,
                        'created_at': file_info.created_at.isoformat(),
                        'accessed_at': file_info.accessed_at.isoformat(),
                        'expires_at': file_info.expires_at.isoformat() if file_info.expires_at else None,
                        'permissions': file_info.permissions.value,
                        'metadata': file_info.metadata
                    }
                    for file_info in self._temp_files.values()
                ]
            }
            
            with open(registry_path, 'w') as f:
                json.dump(registry_data, f, indent=2)
                
        except Exception as e:
            logging.error(f"Failed to save temp file registry: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get temporary file statistics"""
        with self._file_lock:
            active_files = len(self._temp_files)
            total_size = sum(file_info.size for file_info in self._temp_files.values())
            files_by_type = {}
            for file_info in self._temp_files.values():
                file_type = file_info.file_type.value
                files_by_type[file_type] = files_by_type.get(file_type, 0) + 1
        
        return {
            **self._stats,
            'active_files': active_files,
            'total_size_bytes': total_size,
            'files_by_type': files_by_type,
            'base_temp_dir': self.app_temp_dir
        }
    
    # Message handler methods
    async def _handle_create_temp_file(self, **params):
        return await self.create_temp_file(**params)
    
    async def _handle_delete_temp_file(self, file_id: str, force: bool = False):
        return await self.delete_temp_file(file_id, force)
    
    async def _handle_cleanup_temp_files(self, **params):
        return await self.cleanup_expired_files()
    
    async def _handle_get_temp_file_info(self, file_id: str):
        file_info = self.get_temp_file_info(file_id)
        if file_info:
            return {
                'id': file_info.id,
                'path': file_info.path,
                'file_type': file_info.file_type.value,
                'size': file_info.size,
                'created_at': file_info.created_at.isoformat(),
                'expires_at': file_info.expires_at.isoformat() if file_info.expires_at else None
            }
        return None
    
    async def _handle_backup_temp_files(self, file_types: Optional[List[str]] = None):
        types = [TempFileType(ft) for ft in file_types] if file_types else None
        return await self.backup_temp_files(types)
    
    async def _handle_restore_temp_files(self, backup_path: str):
        # Implementation for restoring temp files from backup
        return 0  # Placeholder