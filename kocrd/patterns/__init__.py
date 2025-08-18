# kocrd/patterns/__init__.py
"""
Pattern-based architecture for KOCRD2024

This package provides pattern-based implementations that address the core gaps
identified in the original codebase:

1. Persat Pattern - Unified interface for complex operations with composability
2. Base Manager Pattern - Consistent manager architecture with dependency injection
3. Messaging System - Event-driven communication between components
4. Unified Temp Manager - Consolidated temporary file management

Key improvements:
- Eliminates manager overlaps and duplicated logic
- Provides GPU acceleration and async processing for OCR
- Implements unified error handling and live previews
- Enables distributed processing and resource optimization
"""

from .persat_pattern import (
    PersetProcessor,
    ProcessingStrategy,
    OCRStrategy,
    TesseractOCRStrategy,
    EasyOCRStrategy,
    ProcessingPipeline,
    global_persat_processor,
    process_document_ocr,
    process_batch_ocr
)

from .base_manager import (
    BaseManager,
    ConfigurableManager,
    ServiceManager,
    ResourceManager,
    ManagerState,
    ManagerConfig,
    manager_registry,
    manager_method,
    initialize_managers_from_config
)

from .messaging_system import (
    Message,
    MessageType,
    MessagePriority,
    DeliveryMode,
    MessageBus,
    MessageHandler,
    CommandHandler,
    EventHandler,
    global_message_bus,
    send_system_command,
    publish_system_event,
    query_system,
    subscribe_to_events,
    subscribe_to_commands
)

__all__ = [
    # Persat Pattern
    'PersetProcessor',
    'ProcessingStrategy',
    'OCRStrategy',
    'TesseractOCRStrategy',
    'EasyOCRStrategy',
    'ProcessingPipeline',
    'global_persat_processor',
    'process_document_ocr',
    'process_batch_ocr',
    
    # Base Manager Pattern
    'BaseManager',
    'ConfigurableManager',
    'ServiceManager',
    'ResourceManager',
    'ManagerState',
    'ManagerConfig',
    'manager_registry',
    'manager_method',
    'initialize_managers_from_config',
    
    # Messaging System
    'Message',
    'MessageType',
    'MessagePriority',
    'DeliveryMode',
    'MessageBus',
    'MessageHandler',
    'CommandHandler',
    'EventHandler',
    'global_message_bus',
    'send_system_command',
    'publish_system_event',
    'query_system',
    'subscribe_to_events',
    'subscribe_to_commands'
]

# Version info
__version__ = "1.0.0"
__author__ = "KOCRD2024 Pattern Team"
__description__ = "Pattern-based architecture for Korean OCR Document processing"