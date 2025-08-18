# kocrd/managers/pattern_based_system_manager.py
"""
Pattern-Based System Manager

This module replaces the existing system_manager.py with a pattern-based implementation
that eliminates overlapping logic and provides unified system coordination.
"""

import asyncio
import logging
import threading
from typing import Dict, Any, Optional, List, Type
from datetime import datetime
import json
import os

from kocrd.patterns.base_manager import (
    ServiceManager, 
    manager_registry, 
    initialize_managers_from_config,
    manager_method
)
from kocrd.patterns.messaging_system import (
    global_message_bus,
    CommandHandler,
    EventHandler,
    Message,
    MessageType,
    send_system_command,
    publish_system_event
)
from kocrd.managers.unified_temp_manager import UnifiedTempManager
from kocrd.managers.enhanced_ocr_manager import EnhancedOCRManager
from kocrd.config.config import text_manager, AppConfig
from kocrd.config.system_constants import SystemConstants


class PatternBasedSystemManager(ServiceManager):
    """
    Pattern-based system manager that coordinates all system components
    using the new pattern-based architecture
    """
    
    def __init__(self, name: str = "system", settings_manager: Any = None, main_window: Any = None, **kwargs):
        super().__init__(name, settings_manager, **kwargs)
        
        # Core references
        self.main_window = main_window
        self.settings_manager = settings_manager
        
        # Manager instances
        self._managed_components: Dict[str, Any] = {}
        self._initialization_order: List[str] = []
        
        # System state
        self._system_ready = False
        self._startup_time: Optional[datetime] = None
        self._shutdown_in_progress = False
        
        # Configuration
        self.tesseract_cmd = AppConfig.OCR_SETTINGS.get("tesseract_cmd")
        self.tessdata_dir = AppConfig.OCR_SETTINGS.get("tessdata_dir")
        
        # Performance monitoring
        self._system_metrics = {
            'startup_time': None,
            'managers_initialized': 0,
            'total_managers': 0,
            'messages_processed': 0,
            'errors_encountered': 0,
            'last_health_check': None
        }
    
    async def _initialize_internal(self):
        """Initialize the system manager and all subsystems"""
        self._startup_time = datetime.now()
        
        # Start message bus
        await global_message_bus.start(worker_count=4)
        
        # Register system-level message handlers
        await self._register_system_handlers()
        
        # Initialize core managers
        await self._initialize_core_managers()
        
        # Initialize configured managers from settings
        await self._initialize_configured_managers()
        
        # Configure Tesseract if available
        self._configure_tesseract()
        
        # Perform system health check
        await self._perform_health_check()
        
        self._system_ready = True
        startup_duration = (datetime.now() - self._startup_time).total_seconds()
        self._system_metrics['startup_time'] = startup_duration
        
        # Publish system ready event
        await publish_system_event("system_ready", {
            'startup_time': startup_duration,
            'managers_count': len(self._managed_components),
            'tesseract_available': bool(self.tesseract_cmd)
        })
        
        logging.info(f"Pattern-based system manager initialized in {startup_duration:.2f}s")
    
    async def _start_internal(self):
        """Start all managed components"""
        await super()._start_internal()
        
        # Start all managed components
        for name, component in self._managed_components.items():
            if hasattr(component, 'start') and callable(component.start):
                try:
                    if asyncio.iscoroutinefunction(component.start):
                        await component.start()
                    else:
                        component.start()
                    logging.debug(f"Started component: {name}")
                except Exception as e:
                    logging.error(f"Failed to start component {name}: {e}")
                    self._system_metrics['errors_encountered'] += 1
        
        # Start periodic health checks
        asyncio.create_task(self._health_check_loop())
        
        logging.info("All system components started")
    
    async def _stop_internal(self):
        """Stop all managed components"""
        self._shutdown_in_progress = True
        
        # Stop components in reverse order
        for name in reversed(self._initialization_order):
            component = self._managed_components.get(name)
            if component and hasattr(component, 'stop') and callable(component.stop):
                try:
                    if asyncio.iscoroutinefunction(component.stop):
                        await component.stop()
                    else:
                        component.stop()
                    logging.debug(f"Stopped component: {name}")
                except Exception as e:
                    logging.error(f"Failed to stop component {name}: {e}")
        
        # Stop message bus
        await global_message_bus.stop()
        
        await super()._stop_internal()
        logging.info("Pattern-based system manager stopped")
    
    async def _register_system_handlers(self):
        """Register system-level message handlers"""
        system_commands = {
            'get_system_status': self._handle_get_system_status,
            'get_system_metrics': self._handle_get_system_metrics,
            'shutdown_system': self._handle_shutdown_system,
            'restart_component': self._handle_restart_component,
            'get_component_list': self._handle_get_component_list,
            'perform_health_check': self._handle_perform_health_check
        }
        
        command_handler = CommandHandler(system_commands)
        global_message_bus.register_handler(f"command.{self.name}", command_handler)
        
        # Handle system events
        def handle_system_event(event_type: str, data: Dict[str, Any]):
            asyncio.create_task(self._handle_system_event(event_type, data))
        
        event_handler = EventHandler(handle_system_event)
        global_message_bus.register_handler("event.system.*", event_handler)
    
    async def _initialize_core_managers(self):
        """Initialize core system managers"""
        core_managers = [
            ('unified_temp', UnifiedTempManager),
            ('enhanced_ocr', EnhancedOCRManager)
        ]
        
        for name, manager_class in core_managers:
            try:
                manager = manager_class(name, self.settings_manager)
                
                # Inject dependencies
                if name == 'enhanced_ocr':
                    temp_manager = self._managed_components.get('unified_temp')
                    if temp_manager:
                        manager.inject_dependency('temp_manager', temp_manager)
                    if self.main_window:
                        manager.inject_dependency('monitoring_window', self.main_window)
                
                # Initialize the manager
                await manager.initialize_async()
                
                self._managed_components[name] = manager
                self._initialization_order.append(name)
                self._system_metrics['managers_initialized'] += 1
                
                logging.info(f"Initialized core manager: {name}")
                
            except Exception as e:
                logging.error(f"Failed to initialize core manager {name}: {e}")
                self._system_metrics['errors_encountered'] += 1
                raise
        
        self._system_metrics['total_managers'] = len(self._managed_components)
    
    async def _initialize_configured_managers(self):
        """Initialize managers from configuration"""
        try:
            # Load manager configuration
            if self.settings_manager:
                config_data = self.settings_manager.load_config()
            else:
                config_data = {"managers": AppConfig.MANAGERS}
            
            # Use pattern-based initialization
            configured_managers = await initialize_managers_from_config(
                config_data, 
                self.settings_manager
            )
            
            # Inject system dependencies
            for name, manager in configured_managers.items():
                if name not in self._managed_components:  # Don't override core managers
                    # Inject common dependencies
                    if hasattr(manager, 'inject_dependency'):
                        if self.main_window:
                            manager.inject_dependency('main_window', self.main_window)
                        manager.inject_dependency('system_manager', self)
                        
                        # Inject core managers as dependencies
                        temp_manager = self._managed_components.get('unified_temp')
                        if temp_manager:
                            manager.inject_dependency('temp_manager', temp_manager)
                        
                        ocr_manager = self._managed_components.get('enhanced_ocr')
                        if ocr_manager:
                            manager.inject_dependency('ocr_manager', ocr_manager)
                    
                    self._managed_components[name] = manager
                    if name not in self._initialization_order:
                        self._initialization_order.append(name)
                    self._system_metrics['managers_initialized'] += 1
            
            self._system_metrics['total_managers'] = len(self._managed_components)
            
        except Exception as e:
            logging.error(f"Failed to initialize configured managers: {e}")
            self._system_metrics['errors_encountered'] += 1
    
    def _configure_tesseract(self):
        """Configure Tesseract OCR"""
        try:
            import pytesseract
            
            if self.tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
                logging.info(f"Tesseract configured: {self.tesseract_cmd}")
            
            if self.tessdata_dir:
                pytesseract.pytesseract.tessdata_dir = self.tessdata_dir
                logging.info(f"Tessdata configured: {self.tessdata_dir}")
                
        except ImportError:
            logging.warning("pytesseract not available, OCR functionality may be limited")
        except Exception as e:
            logging.error(f"Failed to configure Tesseract: {e}")
            self._system_metrics['errors_encountered'] += 1
    
    @manager_method("get_manager")
    def get_manager(self, name: str) -> Optional[Any]:
        """Get a managed component by name"""
        component = self._managed_components.get(name)
        if not component:
            logging.warning(f"Component '{name}' not found")
        return component
    
    @manager_method("get_ocr_manager")
    def get_ocr_manager(self) -> Optional[Any]:
        """Get the OCR manager"""
        return self.get_manager('enhanced_ocr')
    
    @manager_method("get_temp_manager")
    def get_temp_manager(self) -> Optional[Any]:
        """Get the temp file manager"""
        return self.get_manager('unified_temp')
    
    @manager_method("get_database_manager")
    def get_database_manager(self) -> Optional[Any]:
        """Get the database manager"""
        return self.get_manager('database')
    
    @manager_method("get_document_manager")
    def get_document_manager(self) -> Optional[Any]:
        """Get the document manager"""
        return self.get_manager('document')
    
    @manager_method("get_ai_model_manager")
    def get_ai_model_manager(self) -> Optional[Any]:
        """Get the AI model manager"""
        return self.get_manager('ai_model')
    
    async def _perform_health_check(self) -> Dict[str, Any]:
        """Perform system health check"""
        health_status = {
            'timestamp': datetime.now().isoformat(),
            'system_ready': self._system_ready,
            'managers_status': {},
            'overall_health': 'healthy'
        }
        
        unhealthy_count = 0
        
        for name, component in self._managed_components.items():
            try:
                if hasattr(component, 'get_metrics'):
                    metrics = component.get_metrics()
                    status = 'healthy' if metrics.get('state') in ['ready', 'running'] else 'unhealthy'
                else:
                    status = 'healthy' if hasattr(component, 'is_ready') and component.is_ready else 'unknown'
                
                health_status['managers_status'][name] = status
                
                if status != 'healthy':
                    unhealthy_count += 1
                    
            except Exception as e:
                health_status['managers_status'][name] = 'error'
                unhealthy_count += 1
                logging.error(f"Health check failed for {name}: {e}")
        
        # Determine overall health
        if unhealthy_count == 0:
            health_status['overall_health'] = 'healthy'
        elif unhealthy_count < len(self._managed_components) * 0.3:
            health_status['overall_health'] = 'degraded'
        else:
            health_status['overall_health'] = 'unhealthy'
        
        self._system_metrics['last_health_check'] = datetime.now().isoformat()
        
        return health_status
    
    async def _health_check_loop(self):
        """Periodic health check loop"""
        while self.state.value == 'running' and not self._shutdown_in_progress:
            try:
                await asyncio.sleep(300)  # 5 minutes
                health_status = await self._perform_health_check()
                
                if health_status['overall_health'] != 'healthy':
                    await publish_system_event("system_health_degraded", health_status)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"Health check loop error: {e}")
    
    @manager_method("trigger_process")
    async def trigger_process(self, process_type: str, data: Optional[Dict[str, Any]] = None):
        """Trigger a process through the appropriate manager"""
        if process_type == "database_packaging":
            db_manager = self.get_manager("database")
            if db_manager:
                if hasattr(db_manager, 'package_database'):
                    await db_manager.package_database()
                await publish_system_event("database_packaged", {"status": "success"})
            else:
                logging.error("Database manager not available")
                
        elif process_type == "document_processing":
            doc_manager = self.get_manager("document")
            if doc_manager:
                if data and 'file_paths' in data:
                    for file_path in data['file_paths']:
                        if hasattr(doc_manager, 'load_document'):
                            await doc_manager.load_document(file_path)
                await publish_system_event("document_processed", data or {})
            else:
                logging.error("Document manager not available")
                
        elif process_type == "ocr_processing":
            ocr_manager = self.get_manager("enhanced_ocr")
            if ocr_manager and data:
                if 'file_path' in data:
                    job_id = await ocr_manager.process_document(data['file_path'])
                    await publish_system_event("ocr_job_created", {"job_id": job_id})
                elif 'file_paths' in data:
                    job_ids = await ocr_manager.process_batch(data['file_paths'])
                    await publish_system_event("ocr_batch_created", {"job_ids": job_ids})
            else:
                logging.error("OCR manager not available or invalid data")
                
        else:
            logging.warning(f"Unknown process type: {process_type}")
    
    @manager_method("handle_error")
    async def handle_error(self, error_code: str, error_detail: str = None, context: str = None):
        """Handle system errors"""
        self._system_metrics['errors_encountered'] += 1
        
        error_msg = text_manager.get_error_text(error_code, error=error_detail)
        logging.error(f"System error [{error_code}]: {error_msg}")
        
        await publish_system_event("system_error", {
            'error_code': error_code,
            'error_detail': error_detail,
            'context': context,
            'timestamp': datetime.now().isoformat()
        })
        
        # Show error to user if main window is available
        if self.main_window and hasattr(self.main_window, 'display_message_box'):
            self.main_window.display_message_box(
                SystemConstants.EventTypes.ERROR,
                "501",  # General error title
                error_code,
                detail_info=error_detail
            )
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get comprehensive system metrics"""
        metrics = {
            'system_metrics': self._system_metrics.copy(),
            'message_bus_metrics': global_message_bus.get_metrics(),
            'manager_metrics': {}
        }
        
        # Collect metrics from all managers
        for name, component in self._managed_components.items():
            try:
                if hasattr(component, 'get_metrics'):
                    metrics['manager_metrics'][name] = component.get_metrics()
                elif hasattr(component, 'get_statistics'):
                    metrics['manager_metrics'][name] = component.get_statistics()
            except Exception as e:
                metrics['manager_metrics'][name] = {'error': str(e)}
        
        return metrics
    
    # Message handler methods
    async def _handle_get_system_status(self):
        """Handle system status query"""
        return {
            'ready': self._system_ready,
            'startup_time': self._startup_time.isoformat() if self._startup_time else None,
            'managers_count': len(self._managed_components),
            'state': self.state.value
        }
    
    async def _handle_get_system_metrics(self):
        """Handle system metrics query"""
        return self.get_system_metrics()
    
    async def _handle_shutdown_system(self):
        """Handle system shutdown command"""
        logging.info("System shutdown requested")
        await self.stop()
        return {'status': 'shutdown_initiated'}
    
    async def _handle_restart_component(self, component_name: str):
        """Handle component restart command"""
        component = self.get_manager(component_name)
        if component and hasattr(component, 'stop') and hasattr(component, 'start'):
            try:
                await component.stop()
                await component.start()
                return {'status': 'restarted', 'component': component_name}
            except Exception as e:
                return {'status': 'failed', 'component': component_name, 'error': str(e)}
        return {'status': 'not_found', 'component': component_name}
    
    async def _handle_get_component_list(self):
        """Handle component list query"""
        return {
            'components': list(self._managed_components.keys()),
            'initialization_order': self._initialization_order
        }
    
    async def _handle_perform_health_check(self):
        """Handle health check command"""
        return await self._perform_health_check()
    
    async def _handle_system_event(self, event_type: str, data: Dict[str, Any]):
        """Handle system events"""
        self._system_metrics['messages_processed'] += 1
        
        if event_type == "component_error":
            component_name = data.get('component')
            error = data.get('error')
            logging.error(f"Component error in {component_name}: {error}")
            
        elif event_type == "performance_degraded":
            component_name = data.get('component')
            logging.warning(f"Performance degradation detected in {component_name}")
            
        # Add more event handling as needed