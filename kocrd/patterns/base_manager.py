# kocrd/patterns/base_manager.py
"""
Unified Base Manager Pattern for KOCRD2024

This module provides a unified base class for all managers to eliminate overlapping logic
and provide consistent initialization, dependency injection, and lifecycle management.
"""

import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, TypeVar, Generic
from dataclasses import dataclass, field
from enum import Enum
import threading
from datetime import datetime
import inspect

from kocrd.config.config import text_manager, AppConfig
from kocrd.config.system_constants import SystemConstants
from kocrd.config.message_broker import publish_system_event


class ManagerState(Enum):
    """Manager lifecycle states"""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class DependencyInjectionMode(Enum):
    """Dependency injection modes"""
    SETTER = "setter"
    CONSTRUCTOR = "constructor"
    PROPERTY = "property"


@dataclass
class ManagerConfig:
    """Configuration for manager initialization"""
    name: str
    module: str
    class_name: str
    dependencies: List[str] = field(default_factory=list)
    inject_settings: bool = True
    inject_main_window: bool = False
    inject_system_manager: bool = False
    initialization_priority: int = 100
    async_init: bool = False
    config_overrides: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DependencySpec:
    """Specification for a dependency"""
    name: str
    type_hint: Type
    required: bool = True
    injection_mode: DependencyInjectionMode = DependencyInjectionMode.SETTER
    default_value: Any = None


class ManagerRegistry:
    """Registry for managing manager instances and dependencies"""
    
    def __init__(self):
        self._managers: Dict[str, 'BaseManager'] = {}
        self._configs: Dict[str, ManagerConfig] = {}
        self._dependency_graph: Dict[str, List[str]] = {}
        self._lock = threading.RLock()
    
    def register_config(self, config: ManagerConfig):
        """Register a manager configuration"""
        with self._lock:
            self._configs[config.name] = config
            self._dependency_graph[config.name] = config.dependencies.copy()
    
    def register_manager(self, name: str, manager: 'BaseManager'):
        """Register a manager instance"""
        with self._lock:
            self._managers[name] = manager
    
    def get_manager(self, name: str) -> Optional['BaseManager']:
        """Get a manager instance by name"""
        with self._lock:
            return self._managers.get(name)
    
    def get_initialization_order(self) -> List[str]:
        """Get managers in dependency-resolved initialization order"""
        visited = set()
        temp_visited = set()
        order = []
        
        def visit(name: str):
            if name in temp_visited:
                raise ValueError(f"Circular dependency detected involving {name}")
            if name in visited:
                return
            
            temp_visited.add(name)
            for dep in self._dependency_graph.get(name, []):
                visit(dep)
            temp_visited.remove(name)
            visited.add(name)
            order.append(name)
        
        for name in self._configs.keys():
            if name not in visited:
                visit(name)
        
        # Sort by initialization priority
        def sort_key(name: str):
            config = self._configs.get(name)
            return config.initialization_priority if config else 999
        
        return sorted(order, key=sort_key)
    
    def get_dependents(self, manager_name: str) -> List[str]:
        """Get managers that depend on the given manager"""
        dependents = []
        for name, deps in self._dependency_graph.items():
            if manager_name in deps:
                dependents.append(name)
        return dependents


# Global registry instance
manager_registry = ManagerRegistry()


class BaseManager(ABC):
    """
    Unified base class for all managers in the KOCRD system.
    
    Provides:
    - Consistent initialization patterns
    - Dependency injection
    - Lifecycle management
    - Error handling
    - Performance monitoring
    - Event publishing
    """
    
    def __init__(self, name: str, settings_manager: Any = None, **kwargs):
        self.name = name
        self.settings_manager = settings_manager
        self.state = ManagerState.UNINITIALIZED
        self._dependencies: Dict[str, Any] = {}
        self._initialization_lock = threading.Lock()
        self._metrics = {
            'initialization_time': None,
            'operation_count': 0,
            'error_count': 0,
            'last_operation_time': None
        }
        
        # Store additional kwargs for subclass use
        self._init_kwargs = kwargs
        
        # Auto-register in global registry
        manager_registry.register_manager(name, self)
        
        logging.info(text_manager.get_log_text("manager_created", manager_name=name))
    
    @property
    def is_ready(self) -> bool:
        """Check if manager is ready for operations"""
        return self.state in [ManagerState.READY, ManagerState.RUNNING]
    
    @property
    def dependencies(self) -> Dict[str, Any]:
        """Get injected dependencies"""
        return self._dependencies.copy()
    
    def inject_dependency(self, name: str, dependency: Any, mode: DependencyInjectionMode = DependencyInjectionMode.SETTER):
        """Inject a dependency"""
        self._dependencies[name] = dependency
        
        if mode == DependencyInjectionMode.SETTER:
            setattr(self, name, dependency)
        elif mode == DependencyInjectionMode.PROPERTY:
            # For property injection, the subclass should handle it
            pass
        # Constructor injection is handled during object creation
        
        logging.debug(f"Injected dependency '{name}' into manager '{self.name}'")
    
    def get_dependency(self, name: str, required: bool = True) -> Any:
        """Get an injected dependency"""
        if name not in self._dependencies:
            if required:
                raise ValueError(f"Required dependency '{name}' not found in manager '{self.name}'")
            return None
        return self._dependencies[name]
    
    async def initialize_async(self) -> bool:
        """Asynchronous initialization"""
        with self._initialization_lock:
            if self.state != ManagerState.UNINITIALIZED:
                return self.state == ManagerState.READY
            
            self.state = ManagerState.INITIALIZING
            start_time = datetime.now()
        
        try:
            await self._initialize_internal()
            
            with self._initialization_lock:
                self.state = ManagerState.READY
                self._metrics['initialization_time'] = (datetime.now() - start_time).total_seconds()
            
            publish_system_event(
                SystemConstants.EventTypes.MANAGER_INITIALIZED,
                manager_name=self.name,
                initialization_time=self._metrics['initialization_time']
            )
            
            logging.info(text_manager.get_log_text("manager_initialized", 
                                                 manager_name=self.name,
                                                 time=self._metrics['initialization_time']))
            return True
            
        except Exception as e:
            with self._initialization_lock:
                self.state = ManagerState.ERROR
                self._metrics['error_count'] += 1
            
            logging.error(text_manager.get_error_text("manager_init_failed", 
                                                     manager_name=self.name, 
                                                     error=str(e)))
            publish_system_event(
                SystemConstants.EventTypes.MANAGER_INITIALIZATION_FAILED,
                manager_name=self.name,
                error=str(e)
            )
            return False
    
    def initialize_sync(self) -> bool:
        """Synchronous initialization wrapper"""
        return asyncio.run(self.initialize_async())
    
    @abstractmethod
    async def _initialize_internal(self):
        """Internal initialization logic - to be implemented by subclasses"""
        pass
    
    async def start(self):
        """Start the manager"""
        if not self.is_ready:
            await self.initialize_async()
        
        if self.state == ManagerState.READY:
            self.state = ManagerState.RUNNING
            await self._start_internal()
            
            publish_system_event(
                SystemConstants.EventTypes.MANAGER_STARTED,
                manager_name=self.name
            )
            logging.info(f"Manager '{self.name}' started")
    
    async def stop(self):
        """Stop the manager"""
        if self.state == ManagerState.RUNNING:
            self.state = ManagerState.STOPPING
            await self._stop_internal()
            self.state = ManagerState.STOPPED
            
            publish_system_event(
                SystemConstants.EventTypes.MANAGER_STOPPED,
                manager_name=self.name
            )
            logging.info(f"Manager '{self.name}' stopped")
    
    async def _start_internal(self):
        """Internal start logic - override in subclasses if needed"""
        pass
    
    async def _stop_internal(self):
        """Internal stop logic - override in subclasses if needed"""
        pass
    
    def record_operation(self, success: bool = True):
        """Record an operation for metrics"""
        self._metrics['operation_count'] += 1
        self._metrics['last_operation_time'] = datetime.now()
        if not success:
            self._metrics['error_count'] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get manager performance metrics"""
        return {
            'name': self.name,
            'state': self.state.value,
            'metrics': self._metrics.copy(),
            'dependency_count': len(self._dependencies)
        }
    
    def handle_error(self, error: Exception, context: Optional[str] = None):
        """Handle errors with logging and event publishing"""
        self._metrics['error_count'] += 1
        error_msg = f"Error in manager '{self.name}'"
        if context:
            error_msg += f" during {context}"
        error_msg += f": {str(error)}"
        
        logging.error(error_msg)
        publish_system_event(
            SystemConstants.EventTypes.MANAGER_ERROR,
            manager_name=self.name,
            error=str(error),
            context=context
        )


class ConfigurableManager(BaseManager):
    """Base manager with configuration support"""
    
    def __init__(self, name: str, settings_manager: Any = None, **kwargs):
        super().__init__(name, settings_manager, **kwargs)
        self.config = self._load_manager_config()
    
    def _load_manager_config(self) -> Dict[str, Any]:
        """Load manager-specific configuration"""
        if self.settings_manager:
            return self.settings_manager.get_manager_config(self.name)
        return AppConfig.MANAGERS.get(self.name, {})
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get a configuration value"""
        return self.config.get(key, default)


class ServiceManager(ConfigurableManager):
    """Manager for service-like components that need lifecycle management"""
    
    def __init__(self, name: str, settings_manager: Any = None, **kwargs):
        super().__init__(name, settings_manager, **kwargs)
        self._services: Dict[str, Any] = {}
        self._service_lock = threading.Lock()
    
    def register_service(self, name: str, service: Any):
        """Register a service"""
        with self._service_lock:
            self._services[name] = service
        logging.debug(f"Registered service '{name}' in manager '{self.name}'")
    
    def get_service(self, name: str) -> Optional[Any]:
        """Get a registered service"""
        with self._service_lock:
            return self._services.get(name)
    
    async def _start_internal(self):
        """Start all registered services"""
        await super()._start_internal()
        
        for service_name, service in self._services.items():
            if hasattr(service, 'start'):
                try:
                    if asyncio.iscoroutinefunction(service.start):
                        await service.start()
                    else:
                        service.start()
                    logging.debug(f"Started service '{service_name}'")
                except Exception as e:
                    logging.error(f"Failed to start service '{service_name}': {e}")
    
    async def _stop_internal(self):
        """Stop all registered services"""
        for service_name, service in self._services.items():
            if hasattr(service, 'stop'):
                try:
                    if asyncio.iscoroutinefunction(service.stop):
                        await service.stop()
                    else:
                        service.stop()
                    logging.debug(f"Stopped service '{service_name}'")
                except Exception as e:
                    logging.error(f"Failed to stop service '{service_name}': {e}")
        
        await super()._stop_internal()


class ResourceManager(ConfigurableManager):
    """Manager for components that manage resources (files, connections, etc.)"""
    
    def __init__(self, name: str, settings_manager: Any = None, **kwargs):
        super().__init__(name, settings_manager, **kwargs)
        self._resources: Dict[str, Any] = {}
        self._resource_lock = threading.Lock()
        self._cleanup_callbacks: List[callable] = []
    
    def register_resource(self, name: str, resource: Any, cleanup_callback: Optional[callable] = None):
        """Register a managed resource"""
        with self._resource_lock:
            self._resources[name] = resource
            if cleanup_callback:
                self._cleanup_callbacks.append(cleanup_callback)
    
    def get_resource(self, name: str) -> Optional[Any]:
        """Get a managed resource"""
        with self._resource_lock:
            return self._resources.get(name)
    
    async def _stop_internal(self):
        """Cleanup all managed resources"""
        for callback in self._cleanup_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                logging.error(f"Error during resource cleanup in '{self.name}': {e}")
        
        with self._resource_lock:
            self._resources.clear()
            self._cleanup_callbacks.clear()
        
        await super()._stop_internal()


def manager_method(operation_name: str = None):
    """Decorator for manager methods to add automatic metrics recording"""
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            if not isinstance(self, BaseManager):
                return func(self, *args, **kwargs)
            
            op_name = operation_name or func.__name__
            start_time = datetime.now()
            success = True
            
            try:
                result = func(self, *args, **kwargs)
                return result
            except Exception as e:
                success = False
                self.handle_error(e, op_name)
                raise
            finally:
                self.record_operation(success)
                duration = (datetime.now() - start_time).total_seconds()
                if duration > 1.0:  # Log slow operations
                    logging.warning(f"Slow operation '{op_name}' in '{self.name}': {duration:.2f}s")
        
        return wrapper
    return decorator


async def initialize_managers_from_config(config_data: Dict[str, Any], settings_manager: Any) -> Dict[str, BaseManager]:
    """Initialize managers from configuration data"""
    managers = {}
    
    # Load manager configurations
    for name, config_dict in config_data.get("managers", {}).items():
        config = ManagerConfig(
            name=name,
            module=config_dict["module"],
            class_name=config_dict["class"],
            dependencies=config_dict.get("dependencies", []),
            inject_settings=config_dict.get("inject_settings", True),
            inject_main_window=config_dict.get("inject_main_window", False),
            inject_system_manager=config_dict.get("inject_system_manager", False),
            initialization_priority=config_dict.get("initialization_priority", 100),
            async_init=config_dict.get("async_init", False)
        )
        manager_registry.register_config(config)
    
    # Initialize managers in dependency order
    initialization_order = manager_registry.get_initialization_order()
    
    for manager_name in initialization_order:
        config = manager_registry._configs[manager_name]
        try:
            # Dynamic import and instantiation
            module = __import__(config.module, fromlist=[config.class_name])
            manager_class = getattr(module, config.class_name)
            
            # Prepare constructor arguments
            kwargs = config.config_overrides.copy()
            if config.inject_settings:
                kwargs['settings_manager'] = settings_manager
            
            # Create manager instance
            manager = manager_class(manager_name, **kwargs)
            
            # Inject dependencies
            for dep_name in config.dependencies:
                if dep_name in managers:
                    manager.inject_dependency(dep_name, managers[dep_name])
            
            # Initialize
            if config.async_init:
                await manager.initialize_async()
            else:
                manager.initialize_sync()
            
            managers[manager_name] = manager
            logging.info(f"Successfully initialized manager: {manager_name}")
            
        except Exception as e:
            logging.error(f"Failed to initialize manager '{manager_name}': {e}")
            raise
    
    return managers