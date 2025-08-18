# kocrd/patterns/messaging_system.py
"""
Unified Messaging System for KOCRD2024

This module provides a pattern-based messaging system that replaces the scattered
message handling throughout the codebase with a unified, extensible architecture.
"""

import asyncio
import logging
import threading
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable, Union, Type
from dataclasses import dataclass, field
from enum import Enum
import json
from datetime import datetime
import weakref
from collections import defaultdict, deque
import uuid

from kocrd.config.config import text_manager, AppConfig
from kocrd.config.system_constants import SystemConstants


class MessagePriority(Enum):
    """Message priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class MessageType(Enum):
    """Types of messages in the system"""
    COMMAND = "command"
    EVENT = "event"
    QUERY = "query"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"


class DeliveryMode(Enum):
    """Message delivery modes"""
    DIRECT = "direct"
    ASYNC = "async"
    QUEUED = "queued"
    BROADCAST = "broadcast"


@dataclass
class Message:
    """Unified message structure"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: MessageType = MessageType.EVENT
    topic: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    sender: Optional[str] = None
    target: Optional[str] = None
    priority: MessagePriority = MessagePriority.NORMAL
    delivery_mode: DeliveryMode = DeliveryMode.ASYNC
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    expires_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    headers: Dict[str, Any] = field(default_factory=dict)


class MessageHandler(ABC):
    """Abstract base class for message handlers"""
    
    @abstractmethod
    async def handle(self, message: Message) -> Optional[Message]:
        """Handle a message and optionally return a response"""
        pass
    
    @abstractmethod
    def can_handle(self, message: Message) -> bool:
        """Check if this handler can process the message"""
        pass


class MessageFilter(ABC):
    """Abstract base class for message filters"""
    
    @abstractmethod
    def should_process(self, message: Message) -> bool:
        """Determine if a message should be processed"""
        pass


class TopicFilter(MessageFilter):
    """Filter messages by topic pattern"""
    
    def __init__(self, pattern: str):
        self.pattern = pattern
    
    def should_process(self, message: Message) -> bool:
        if self.pattern == "*":
            return True
        if self.pattern.endswith("*"):
            return message.topic.startswith(self.pattern[:-1])
        return message.topic == self.pattern


class TypeFilter(MessageFilter):
    """Filter messages by type"""
    
    def __init__(self, message_types: List[MessageType]):
        self.message_types = set(message_types)
    
    def should_process(self, message: Message) -> bool:
        return message.type in self.message_types


class PriorityFilter(MessageFilter):
    """Filter messages by minimum priority"""
    
    def __init__(self, min_priority: MessagePriority):
        self.min_priority = min_priority
    
    def should_process(self, message: Message) -> bool:
        return message.priority.value >= self.min_priority.value


class MessageQueue:
    """Priority-based message queue"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._queues = {priority: deque() for priority in MessagePriority}
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
        self._closed = False
    
    def put(self, message: Message) -> bool:
        """Add message to queue"""
        with self._condition:
            if self._closed:
                return False
            
            queue = self._queues[message.priority]
            if len(queue) >= self.max_size // len(MessagePriority):
                # Remove oldest message of same priority
                queue.popleft()
            
            queue.append(message)
            self._condition.notify()
            return True
    
    def get(self, timeout: Optional[float] = None) -> Optional[Message]:
        """Get highest priority message from queue"""
        with self._condition:
            if self._closed:
                return None
            
            # Wait for messages
            if not self._has_messages():
                if not self._condition.wait(timeout):
                    return None
            
            # Get highest priority message
            for priority in reversed(list(MessagePriority)):
                queue = self._queues[priority]
                if queue:
                    return queue.popleft()
            
            return None
    
    def _has_messages(self) -> bool:
        """Check if any queue has messages"""
        return any(queue for queue in self._queues.values())
    
    def size(self) -> int:
        """Get total number of messages in all queues"""
        with self._lock:
            return sum(len(queue) for queue in self._queues.values())
    
    def close(self):
        """Close the queue"""
        with self._condition:
            self._closed = True
            self._condition.notify_all()


class MessageBus:
    """Central message bus for the application"""
    
    def __init__(self):
        self._handlers: Dict[str, List[MessageHandler]] = defaultdict(list)
        self._filters: Dict[str, List[MessageFilter]] = defaultdict(list)
        self._subscribers: Dict[str, List[weakref.WeakMethod]] = defaultdict(list)
        self._message_queue = MessageQueue()
        self._worker_tasks: List[asyncio.Task] = []
        self._running = False
        self._lock = threading.RLock()
        self._metrics = {
            'messages_sent': 0,
            'messages_processed': 0,
            'messages_failed': 0,
            'handlers_count': 0
        }
    
    def register_handler(self, topic_pattern: str, handler: MessageHandler):
        """Register a message handler for a topic pattern"""
        with self._lock:
            self._handlers[topic_pattern].append(handler)
            self._metrics['handlers_count'] += 1
        logging.debug(f"Registered handler for topic: {topic_pattern}")
    
    def unregister_handler(self, topic_pattern: str, handler: MessageHandler):
        """Unregister a message handler"""
        with self._lock:
            if topic_pattern in self._handlers:
                try:
                    self._handlers[topic_pattern].remove(handler)
                    self._metrics['handlers_count'] -= 1
                except ValueError:
                    pass
    
    def add_filter(self, topic_pattern: str, filter_obj: MessageFilter):
        """Add a message filter for a topic pattern"""
        with self._lock:
            self._filters[topic_pattern].append(filter_obj)
    
    def subscribe(self, topic_pattern: str, callback: Callable[[Message], None]):
        """Subscribe to messages with a callback function"""
        with self._lock:
            if hasattr(callback, '__self__'):
                # It's a bound method, use WeakMethod
                weak_callback = weakref.WeakMethod(callback)
            else:
                # It's a function, use regular weakref
                weak_callback = weakref.ref(callback)
            self._subscribers[topic_pattern].append(weak_callback)
    
    def unsubscribe(self, topic_pattern: str, callback: Callable[[Message], None]):
        """Unsubscribe from messages"""
        with self._lock:
            subscribers = self._subscribers.get(topic_pattern, [])
            # Clean up dead references and remove the specific callback
            self._subscribers[topic_pattern] = [
                ref for ref in subscribers 
                if ref() is not None and ref() != callback
            ]
    
    async def send(self, message: Message) -> bool:
        """Send a message through the bus"""
        self._metrics['messages_sent'] += 1
        
        try:
            if message.delivery_mode == DeliveryMode.DIRECT:
                await self._process_message_direct(message)
            elif message.delivery_mode == DeliveryMode.QUEUED:
                return self._message_queue.put(message)
            elif message.delivery_mode == DeliveryMode.BROADCAST:
                await self._broadcast_message(message)
            else:  # ASYNC
                asyncio.create_task(self._process_message_async(message))
            
            return True
            
        except Exception as e:
            self._metrics['messages_failed'] += 1
            logging.error(f"Failed to send message {message.id}: {e}")
            return False
    
    async def send_command(self, target: str, command: str, params: Dict[str, Any] = None) -> bool:
        """Send a command message"""
        message = Message(
            type=MessageType.COMMAND,
            topic=f"command.{target}",
            target=target,
            payload={
                'command': command,
                'params': params or {}
            },
            priority=MessagePriority.HIGH
        )
        return await self.send(message)
    
    async def send_event(self, event_type: str, data: Dict[str, Any] = None) -> bool:
        """Send an event message"""
        message = Message(
            type=MessageType.EVENT,
            topic=f"event.{event_type}",
            payload=data or {},
            delivery_mode=DeliveryMode.BROADCAST
        )
        return await self.send(message)
    
    async def send_query(self, target: str, query: str, params: Dict[str, Any] = None, timeout: float = 5.0) -> Optional[Message]:
        """Send a query message and wait for response"""
        correlation_id = str(uuid.uuid4())
        message = Message(
            type=MessageType.QUERY,
            topic=f"query.{target}",
            target=target,
            payload={
                'query': query,
                'params': params or {}
            },
            correlation_id=correlation_id,
            priority=MessagePriority.HIGH
        )
        
        # Set up response handler
        response_future = asyncio.Future()
        
        def response_handler(response_msg: Message):
            if response_msg.correlation_id == correlation_id:
                response_future.set_result(response_msg)
        
        self.subscribe("response.*", response_handler)
        
        try:
            await self.send(message)
            return await asyncio.wait_for(response_future, timeout=timeout)
        except asyncio.TimeoutError:
            return None
        finally:
            self.unsubscribe("response.*", response_handler)
    
    async def _process_message_direct(self, message: Message):
        """Process message directly without queueing"""
        await self._route_message(message)
    
    async def _process_message_async(self, message: Message):
        """Process message asynchronously"""
        try:
            await self._route_message(message)
            self._metrics['messages_processed'] += 1
        except Exception as e:
            self._metrics['messages_failed'] += 1
            logging.error(f"Error processing message {message.id}: {e}")
    
    async def _broadcast_message(self, message: Message):
        """Broadcast message to all matching subscribers"""
        with self._lock:
            # Clean up dead references
            for topic_pattern in list(self._subscribers.keys()):
                self._subscribers[topic_pattern] = [
                    ref for ref in self._subscribers[topic_pattern] 
                    if ref() is not None
                ]
        
        # Send to subscribers
        for topic_pattern, subscribers in self._subscribers.items():
            if self._topic_matches(message.topic, topic_pattern):
                for weak_ref in subscribers:
                    callback = weak_ref()
                    if callback:
                        try:
                            if asyncio.iscoroutinefunction(callback):
                                await callback(message)
                            else:
                                callback(message)
                        except Exception as e:
                            logging.error(f"Error in subscriber callback: {e}")
    
    async def _route_message(self, message: Message):
        """Route message to appropriate handlers"""
        handlers_found = False
        
        for topic_pattern, handlers in self._handlers.items():
            if self._topic_matches(message.topic, topic_pattern):
                # Apply filters
                if not self._should_process_message(message, topic_pattern):
                    continue
                
                handlers_found = True
                for handler in handlers:
                    try:
                        if handler.can_handle(message):
                            response = await handler.handle(message)
                            if response and message.reply_to:
                                response.correlation_id = message.correlation_id
                                response.topic = f"response.{message.reply_to}"
                                await self.send(response)
                    except Exception as e:
                        logging.error(f"Handler error for message {message.id}: {e}")
        
        if not handlers_found:
            logging.warning(f"No handlers found for message topic: {message.topic}")
    
    def _topic_matches(self, topic: str, pattern: str) -> bool:
        """Check if topic matches pattern"""
        if pattern == "*":
            return True
        if pattern.endswith("*"):
            return topic.startswith(pattern[:-1])
        return topic == pattern
    
    def _should_process_message(self, message: Message, topic_pattern: str) -> bool:
        """Check if message should be processed based on filters"""
        filters = self._filters.get(topic_pattern, [])
        return all(f.should_process(message) for f in filters)
    
    async def start(self, worker_count: int = 2):
        """Start the message bus workers"""
        if self._running:
            return
        
        self._running = True
        
        # Start worker tasks
        for i in range(worker_count):
            task = asyncio.create_task(self._worker_loop(f"worker-{i}"))
            self._worker_tasks.append(task)
        
        logging.info(f"Message bus started with {worker_count} workers")
    
    async def stop(self):
        """Stop the message bus"""
        if not self._running:
            return
        
        self._running = False
        self._message_queue.close()
        
        # Cancel and wait for worker tasks
        for task in self._worker_tasks:
            task.cancel()
        
        if self._worker_tasks:
            await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        
        self._worker_tasks.clear()
        logging.info("Message bus stopped")
    
    async def _worker_loop(self, worker_name: str):
        """Worker loop for processing queued messages"""
        logging.debug(f"Message bus worker {worker_name} started")
        
        while self._running:
            try:
                message = self._message_queue.get(timeout=1.0)
                if message:
                    await self._process_message_async(message)
            except Exception as e:
                logging.error(f"Worker {worker_name} error: {e}")
        
        logging.debug(f"Message bus worker {worker_name} stopped")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get message bus metrics"""
        return {
            'messages_sent': self._metrics['messages_sent'],
            'messages_processed': self._metrics['messages_processed'],
            'messages_failed': self._metrics['messages_failed'],
            'handlers_count': self._metrics['handlers_count'],
            'queue_size': self._message_queue.size(),
            'running': self._running,
            'worker_count': len(self._worker_tasks)
        }


# Global message bus instance
global_message_bus = MessageBus()


class CommandHandler(MessageHandler):
    """Handler for command messages"""
    
    def __init__(self, command_map: Dict[str, Callable]):
        self.command_map = command_map
    
    def can_handle(self, message: Message) -> bool:
        return (message.type == MessageType.COMMAND and
                message.payload.get('command') in self.command_map)
    
    async def handle(self, message: Message) -> Optional[Message]:
        command = message.payload.get('command')
        params = message.payload.get('params', {})
        
        handler_func = self.command_map[command]
        
        try:
            if asyncio.iscoroutinefunction(handler_func):
                result = await handler_func(**params)
            else:
                result = handler_func(**params)
            
            if message.reply_to:
                return Message(
                    type=MessageType.RESPONSE,
                    payload={'result': result, 'success': True},
                    correlation_id=message.correlation_id
                )
        except Exception as e:
            logging.error(f"Command '{command}' failed: {e}")
            if message.reply_to:
                return Message(
                    type=MessageType.RESPONSE,
                    payload={'error': str(e), 'success': False},
                    correlation_id=message.correlation_id
                )
        
        return None


class EventHandler(MessageHandler):
    """Handler for event messages"""
    
    def __init__(self, event_callback: Callable[[str, Dict[str, Any]], None]):
        self.event_callback = event_callback
    
    def can_handle(self, message: Message) -> bool:
        return message.type == MessageType.EVENT
    
    async def handle(self, message: Message) -> Optional[Message]:
        event_type = message.topic.replace('event.', '', 1)
        
        try:
            if asyncio.iscoroutinefunction(self.event_callback):
                await self.event_callback(event_type, message.payload)
            else:
                self.event_callback(event_type, message.payload)
        except Exception as e:
            logging.error(f"Event handler failed for '{event_type}': {e}")
        
        return None


# Convenience functions for common messaging patterns
async def send_system_command(target: str, command: str, **params) -> bool:
    """Send a system command"""
    return await global_message_bus.send_command(target, command, params)


async def publish_system_event(event_type: str, **data) -> bool:
    """Publish a system event"""
    return await global_message_bus.send_event(event_type, data)


async def query_system(target: str, query: str, timeout: float = 5.0, **params) -> Optional[Any]:
    """Query the system and wait for response"""
    response = await global_message_bus.send_query(target, query, params, timeout)
    if response and response.payload.get('success'):
        return response.payload.get('result')
    return None


def subscribe_to_events(event_pattern: str, callback: Callable[[Message], None]):
    """Subscribe to system events"""
    global_message_bus.subscribe(f"event.{event_pattern}", callback)


def subscribe_to_commands(command_pattern: str, handler: MessageHandler):
    """Subscribe to system commands"""
    global_message_bus.register_handler(f"command.{command_pattern}", handler)