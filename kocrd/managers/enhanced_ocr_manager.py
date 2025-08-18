# kocrd/managers/enhanced_ocr_manager.py
"""
Enhanced OCR Manager with Persat Pattern Integration

This module replaces the existing OCR manager with a pattern-based implementation
that provides GPU acceleration, async processing, batch capabilities, and 
unified error handling through the Persat pattern.
"""

import asyncio
import logging
import os
import tempfile
from typing import List, Optional, Dict, Any, Union, Callable
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import json

from PIL import Image
import fitz  # PyMuPDF for PDF processing

from kocrd.patterns.base_manager import ServiceManager, manager_method
from kocrd.patterns.persat_pattern import (
    global_persat_processor, 
    process_document_ocr, 
    process_batch_ocr,
    TesseractOCRStrategy,
    EasyOCRStrategy,
    OCRStrategy
)
from kocrd.patterns.messaging_system import (
    global_message_bus, 
    CommandHandler, 
    EventHandler,
    Message, 
    MessageType
)
from kocrd.managers.unified_temp_manager import UnifiedTempManager, TempFileType
from kocrd.config.config import text_manager, AppConfig
from kocrd.config.system_constants import SystemConstants


class OCRJobStatus(Enum):
    """Status of OCR jobs"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OCRQuality(Enum):
    """OCR quality levels"""
    FAST = "fast"
    BALANCED = "balanced"
    HIGH = "high"
    MAXIMUM = "maximum"


@dataclass
class OCRJobConfig:
    """Configuration for OCR jobs"""
    quality: OCRQuality = OCRQuality.BALANCED
    language: str = "kor+eng"
    enable_gpu: bool = True
    timeout: int = 300  # 5 minutes
    retry_count: int = 2
    save_intermediate: bool = False
    preprocessing_enabled: bool = True
    postprocessing_enabled: bool = True


@dataclass
class OCRResult:
    """Result of OCR processing"""
    job_id: str
    text: str
    confidence: float
    processing_time: float
    strategy_used: str
    metadata: Dict[str, Any]
    status: OCRJobStatus
    error: Optional[str] = None


@dataclass
class OCRJob:
    """OCR job tracking"""
    id: str
    input_data: Any
    config: OCRJobConfig
    status: OCRJobStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[OCRResult] = None
    progress: float = 0.0


class EnhancedOCRManager(ServiceManager):
    """
    Enhanced OCR Manager with pattern-based architecture
    
    Features:
    - Persat pattern integration for strategy selection
    - Async processing with batch support
    - GPU acceleration when available
    - Job queue management
    - Progress tracking and monitoring
    - Automatic strategy fallback
    - Result caching
    """
    
    def __init__(self, name: str = "enhanced_ocr", settings_manager: Any = None, **kwargs):
        super().__init__(name, settings_manager, **kwargs)
        
        # Dependencies (will be injected)
        self.temp_manager: Optional[UnifiedTempManager] = None
        self.monitoring_window: Any = None
        
        # OCR Configuration
        self.tesseract_cmd = self.get_config_value("tesseract_cmd", AppConfig.OCR_SETTINGS.get("tesseract_cmd"))
        self.tessdata_dir = self.get_config_value("tessdata_dir", AppConfig.OCR_SETTINGS.get("tessdata_dir"))
        
        # Job management
        self._jobs: Dict[str, OCRJob] = {}
        self._job_queue: asyncio.Queue = asyncio.Queue()
        self._job_lock = threading.RLock()
        self._worker_tasks: List[asyncio.Task] = []
        self._worker_count = self.get_config_value("worker_count", 2)
        
        # Executors for different types of processing
        self._thread_executor = ThreadPoolExecutor(max_workers=4)
        self._process_executor = ProcessPoolExecutor(max_workers=2)
        
        # Performance tracking
        self._performance_stats = {
            'jobs_completed': 0,
            'jobs_failed': 0,
            'total_processing_time': 0.0,
            'average_processing_time': 0.0,
            'documents_processed': 0,
            'pages_processed': 0
        }
        
        # Caching
        self._enable_caching = self.get_config_value("enable_caching", True)
        self._cache_dir = None
        
        # Quality pipeline mappings
        self._quality_pipelines = {
            OCRQuality.FAST: "fast_ocr",
            OCRQuality.BALANCED: "fast_ocr",
            OCRQuality.HIGH: "robust_ocr",
            OCRQuality.MAXIMUM: "parallel_ocr"
        }
    
    async def _initialize_internal(self):
        """Initialize the OCR manager"""
        # Configure cache directory if caching is enabled
        if self._enable_caching and self.temp_manager:
            cache_id = await self.temp_manager.create_temp_file(
                file_type=TempFileType.CACHE,
                retention_time=7 * 24 * 3600  # 7 days
            )
            self._cache_dir = os.path.dirname(self.temp_manager.get_temp_file_path(cache_id))
        
        # Register custom OCR strategies with Persat processor
        await self._register_custom_strategies()
        
        # Register message handlers
        await self._register_message_handlers()
        
        # Register services
        self.register_service("persat_processor", global_persat_processor)
        self.register_service("job_queue", self._job_queue)
        
        logging.info("Enhanced OCR Manager initialized")
    
    async def _start_internal(self):
        """Start OCR processing workers"""
        await super()._start_internal()
        
        # Start worker tasks
        for i in range(self._worker_count):
            task = asyncio.create_task(self._worker_loop(f"ocr-worker-{i}"))
            self._worker_tasks.append(task)
        
        logging.info(f"Started {self._worker_count} OCR workers")
    
    async def _stop_internal(self):
        """Stop OCR processing workers"""
        # Cancel all worker tasks
        for task in self._worker_tasks:
            task.cancel()
        
        if self._worker_tasks:
            await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        
        self._worker_tasks.clear()
        
        # Shutdown executors
        self._thread_executor.shutdown(wait=True)
        self._process_executor.shutdown(wait=True)
        
        await super()._stop_internal()
    
    async def _register_custom_strategies(self):
        """Register custom OCR strategies with the Persat processor"""
        # Register enhanced Tesseract strategy
        enhanced_tesseract_config = {
            "tesseract_cmd": self.tesseract_cmd,
            "tessdata_dir": self.tessdata_dir,
            "gpu_enabled": False,
            "batch_size": 1,
            "preprocessing": True,
            "dpi": 300
        }
        
        global_persat_processor.register_strategy(
            "enhanced_tesseract", 
            EnhancedTesseractStrategy(enhanced_tesseract_config)
        )
        
        # Register GPU-accelerated EasyOCR if available
        try:
            import easyocr
            gpu_easyocr_config = {
                "gpu_enabled": True,
                "batch_size": 8,
                "confidence_threshold": 0.6
            }
            global_persat_processor.register_strategy(
                "gpu_easyocr",
                EnhancedEasyOCRStrategy(gpu_easyocr_config)
            )
        except ImportError:
            logging.warning("EasyOCR not available, skipping GPU strategy registration")
    
    async def _register_message_handlers(self):
        """Register message handlers for OCR operations"""
        commands = {
            'process_document': self._handle_process_document,
            'process_batch': self._handle_process_batch,
            'get_job_status': self._handle_get_job_status,
            'cancel_job': self._handle_cancel_job,
            'get_performance_stats': self._handle_get_performance_stats
        }
        
        command_handler = CommandHandler(commands)
        global_message_bus.register_handler(f"command.{self.name}", command_handler)
        
        # Register for OCR-related events
        def handle_ocr_event(event_type: str, data: Dict[str, Any]):
            asyncio.create_task(self._handle_ocr_event(event_type, data))
        
        event_handler = EventHandler(handle_ocr_event)
        global_message_bus.register_handler("event.ocr.*", event_handler)
    
    @manager_method("process_document")
    async def process_document(self, 
                              input_data: Union[str, Image.Image, bytes],
                              config: Optional[OCRJobConfig] = None) -> str:
        """
        Process a single document for OCR
        
        Args:
            input_data: File path, PIL Image, or image bytes
            config: OCR configuration
            
        Returns:
            Job ID for tracking
        """
        job_config = config or OCRJobConfig()
        job_id = f"ocr_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        job = OCRJob(
            id=job_id,
            input_data=input_data,
            config=job_config,
            status=OCRJobStatus.PENDING,
            created_at=datetime.now()
        )
        
        with self._job_lock:
            self._jobs[job_id] = job
        
        # Add to processing queue
        await self._job_queue.put(job_id)
        
        # Publish event
        await global_message_bus.send_event("ocr_job_created", {
            'job_id': job_id,
            'config': {
                'quality': job_config.quality.value,
                'language': job_config.language,
                'gpu_enabled': job_config.enable_gpu
            }
        })
        
        logging.info(f"Created OCR job: {job_id}")
        return job_id
    
    @manager_method("process_batch")
    async def process_batch(self,
                           input_list: List[Union[str, Image.Image, bytes]],
                           config: Optional[OCRJobConfig] = None) -> List[str]:
        """
        Process multiple documents in batch
        
        Args:
            input_list: List of documents to process
            config: OCR configuration
            
        Returns:
            List of job IDs
        """
        job_ids = []
        batch_config = config or OCRJobConfig()
        
        for i, input_data in enumerate(input_list):
            job_id = await self.process_document(input_data, batch_config)
            job_ids.append(job_id)
        
        # Publish batch event
        await global_message_bus.send_event("ocr_batch_created", {
            'job_ids': job_ids,
            'batch_size': len(input_list)
        })
        
        return job_ids
    
    @manager_method("get_job_status")
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status of an OCR job"""
        with self._job_lock:
            job = self._jobs.get(job_id)
            if job:
                return {
                    'job_id': job.id,
                    'status': job.status.value,
                    'progress': job.progress,
                    'created_at': job.created_at.isoformat(),
                    'started_at': job.started_at.isoformat() if job.started_at else None,
                    'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                    'result': {
                        'text': job.result.text,
                        'confidence': job.result.confidence,
                        'processing_time': job.result.processing_time,
                        'strategy_used': job.result.strategy_used
                    } if job.result and job.status == OCRJobStatus.COMPLETED else None,
                    'error': job.result.error if job.result and job.status == OCRJobStatus.FAILED else None
                }
        return None
    
    @manager_method("get_job_result")
    async def get_job_result(self, job_id: str, timeout: float = 300) -> Optional[OCRResult]:
        """Wait for and get the result of an OCR job"""
        start_time = datetime.now()
        
        while (datetime.now() - start_time).total_seconds() < timeout:
            with self._job_lock:
                job = self._jobs.get(job_id)
                if job and job.status in [OCRJobStatus.COMPLETED, OCRJobStatus.FAILED]:
                    return job.result
            
            await asyncio.sleep(0.5)
        
        return None
    
    @manager_method("cancel_job")
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel an OCR job"""
        with self._job_lock:
            job = self._jobs.get(job_id)
            if job and job.status in [OCRJobStatus.PENDING, OCRJobStatus.PROCESSING]:
                job.status = OCRJobStatus.CANCELLED
                
                await global_message_bus.send_event("ocr_job_cancelled", {
                    'job_id': job_id
                })
                
                return True
        return False
    
    async def _worker_loop(self, worker_name: str):
        """Worker loop for processing OCR jobs"""
        logging.debug(f"OCR worker {worker_name} started")
        
        while self.state.value == 'running':
            try:
                # Get job from queue with timeout
                job_id = await asyncio.wait_for(self._job_queue.get(), timeout=1.0)
                await self._process_job(job_id)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"OCR worker {worker_name} error: {e}")
        
        logging.debug(f"OCR worker {worker_name} stopped")
    
    async def _process_job(self, job_id: str):
        """Process a single OCR job"""
        with self._job_lock:
            job = self._jobs.get(job_id)
            if not job or job.status != OCRJobStatus.PENDING:
                return
            
            job.status = OCRJobStatus.PROCESSING
            job.started_at = datetime.now()
        
        try:
            # Prepare input data
            processed_input = await self._prepare_input_data(job.input_data)
            
            # Update progress
            job.progress = 0.2
            
            # Select pipeline based on quality setting
            pipeline_name = self._quality_pipelines[job.config.quality]
            
            # Create processing context
            context = {
                'language': job.config.language,
                'job_id': job_id,
                'quality': job.config.quality.value,
                'enable_gpu': job.config.enable_gpu,
                'preprocessing': job.config.preprocessing_enabled,
                'postprocessing': job.config.postprocessing_enabled
            }
            
            # Update progress
            job.progress = 0.4
            
            # Process with Persat pattern
            start_time = datetime.now()
            
            if isinstance(processed_input, list):
                # Batch processing
                text_results = await process_batch_ocr(
                    processed_input, 
                    pipeline_name, 
                    job.config.language
                )
                text = '\n'.join(text_results)
            else:
                # Single document processing
                text = await process_document_ocr(
                    processed_input,
                    pipeline_name,
                    job.config.language
                )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Update progress
            job.progress = 0.8
            
            # Post-process result if enabled
            if job.config.postprocessing_enabled:
                text = await self._post_process_text(text, context)
            
            # Create result
            result = OCRResult(
                job_id=job_id,
                text=text,
                confidence=0.95,  # Placeholder - would need actual confidence from OCR engine
                processing_time=processing_time,
                strategy_used=pipeline_name,
                metadata=context,
                status=OCRJobStatus.COMPLETED
            )
            
            # Update job
            with self._job_lock:
                job.result = result
                job.status = OCRJobStatus.COMPLETED
                job.completed_at = datetime.now()
                job.progress = 1.0
            
            # Update statistics
            self._performance_stats['jobs_completed'] += 1
            self._performance_stats['total_processing_time'] += processing_time
            self._performance_stats['average_processing_time'] = (
                self._performance_stats['total_processing_time'] / 
                self._performance_stats['jobs_completed']
            )
            
            # Cache result if enabled
            if self._enable_caching:
                await self._cache_result(job_id, result)
            
            # Publish completion event
            await global_message_bus.send_event("ocr_job_completed", {
                'job_id': job_id,
                'processing_time': processing_time,
                'text_length': len(text),
                'strategy_used': pipeline_name
            })
            
            logging.info(f"OCR job {job_id} completed in {processing_time:.2f}s")
            
        except Exception as e:
            # Handle failure
            error_msg = str(e)
            logging.error(f"OCR job {job_id} failed: {error_msg}")
            
            result = OCRResult(
                job_id=job_id,
                text="",
                confidence=0.0,
                processing_time=0.0,
                strategy_used="none",
                metadata={},
                status=OCRJobStatus.FAILED,
                error=error_msg
            )
            
            with self._job_lock:
                job.result = result
                job.status = OCRJobStatus.FAILED
                job.completed_at = datetime.now()
            
            self._performance_stats['jobs_failed'] += 1
            
            # Publish failure event
            await global_message_bus.send_event("ocr_job_failed", {
                'job_id': job_id,
                'error': error_msg
            })
    
    async def _prepare_input_data(self, input_data: Any) -> Any:
        """Prepare input data for OCR processing"""
        if isinstance(input_data, str):
            # File path
            if input_data.lower().endswith('.pdf'):
                return await self._convert_pdf_to_images(input_data)
            else:
                return Image.open(input_data)
        elif isinstance(input_data, bytes):
            # Image bytes
            import io
            return Image.open(io.BytesIO(input_data))
        elif isinstance(input_data, Image.Image):
            return input_data
        else:
            raise ValueError(f"Unsupported input data type: {type(input_data)}")
    
    async def _convert_pdf_to_images(self, pdf_path: str) -> List[Image.Image]:
        """Convert PDF to images"""
        loop = asyncio.get_event_loop()
        
        def _convert():
            doc = fitz.open(pdf_path)
            images = []
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better quality
                img_data = pix.tobytes("ppm")
                
                import io
                img = Image.open(io.BytesIO(img_data))
                images.append(img)
            
            doc.close()
            return images
        
        return await loop.run_in_executor(self._thread_executor, _convert)
    
    async def _post_process_text(self, text: str, context: Dict[str, Any]) -> str:
        """Post-process extracted text"""
        # Basic post-processing
        processed_text = text.strip()
        
        # Remove excessive whitespace
        import re
        processed_text = re.sub(r'\s+', ' ', processed_text)
        
        # Additional post-processing based on context
        if context.get('quality') == 'maximum':
            # More aggressive cleaning for maximum quality
            processed_text = re.sub(r'[^\w\s\.,;:!?\-\(\)]', '', processed_text)
        
        return processed_text
    
    async def _cache_result(self, job_id: str, result: OCRResult):
        """Cache OCR result"""
        if not self._cache_dir:
            return
        
        cache_file = os.path.join(self._cache_dir, f"{job_id}.json")
        cache_data = {
            'job_id': result.job_id,
            'text': result.text,
            'confidence': result.confidence,
            'processing_time': result.processing_time,
            'strategy_used': result.strategy_used,
            'metadata': result.metadata,
            'cached_at': datetime.now().isoformat()
        }
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.warning(f"Failed to cache OCR result for job {job_id}: {e}")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        with self._job_lock:
            active_jobs = sum(1 for job in self._jobs.values() 
                            if job.status == OCRJobStatus.PROCESSING)
            pending_jobs = sum(1 for job in self._jobs.values() 
                             if job.status == OCRJobStatus.PENDING)
        
        return {
            **self._performance_stats,
            'active_jobs': active_jobs,
            'pending_jobs': pending_jobs,
            'queue_size': self._job_queue.qsize(),
            'worker_count': len(self._worker_tasks),
            'cache_enabled': self._enable_caching
        }
    
    # Message handler methods
    async def _handle_process_document(self, input_data: Any, config: Dict[str, Any] = None):
        job_config = OCRJobConfig(**config) if config else OCRJobConfig()
        return await self.process_document(input_data, job_config)
    
    async def _handle_process_batch(self, input_list: List[Any], config: Dict[str, Any] = None):
        job_config = OCRJobConfig(**config) if config else OCRJobConfig()
        return await self.process_batch(input_list, job_config)
    
    async def _handle_get_job_status(self, job_id: str):
        return self.get_job_status(job_id)
    
    async def _handle_cancel_job(self, job_id: str):
        return await self.cancel_job(job_id)
    
    async def _handle_get_performance_stats(self):
        return self.get_performance_stats()
    
    async def _handle_ocr_event(self, event_type: str, data: Dict[str, Any]):
        """Handle OCR-related events"""
        if event_type == "document_added":
            # Auto-process new documents if configured
            if self.get_config_value("auto_process_new_documents", False):
                file_path = data.get("file_path")
                if file_path:
                    await self.process_document(file_path)


class EnhancedTesseractStrategy(TesseractOCRStrategy):
    """Enhanced Tesseract strategy with preprocessing"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.preprocessing_enabled = config.get("preprocessing", True)
        self.dpi = config.get("dpi", 300)
    
    async def extract_text(self, image_data: Any, language: str = "kor+eng") -> str:
        if self.preprocessing_enabled:
            image_data = await self._preprocess_image(image_data)
        
        return await super().extract_text(image_data, language)
    
    async def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """Preprocess image for better OCR results"""
        from PIL import ImageEnhance, ImageFilter
        
        # Convert to grayscale
        if image.mode != 'L':
            image = image.convert('L')
        
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)
        
        # Apply noise reduction
        image = image.filter(ImageFilter.MedianFilter(size=3))
        
        # Resize if too small
        width, height = image.size
        if width < 1000 or height < 1000:
            scale_factor = max(1000 / width, 1000 / height)
            new_size = (int(width * scale_factor), int(height * scale_factor))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
        
        return image


class EnhancedEasyOCRStrategy(EasyOCRStrategy):
    """Enhanced EasyOCR strategy with confidence filtering"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.confidence_threshold = config.get("confidence_threshold", 0.6)
    
    async def extract_text(self, image_data: Any, language: str = "kor+eng") -> str:
        if not self.reader:
            raise RuntimeError("EasyOCR reader not initialized")
        
        loop = asyncio.get_event_loop()
        
        def _ocr_sync():
            if isinstance(image_data, str):
                result = self.reader.readtext(image_data)
            else:
                import numpy as np
                from PIL import Image
                if isinstance(image_data, Image.Image):
                    image_array = np.array(image_data)
                else:
                    image_array = image_data
                result = self.reader.readtext(image_array)
            
            # Filter by confidence
            filtered_result = [
                text[1] for text in result 
                if text[2] >= self.confidence_threshold
            ]
            
            return '\n'.join(filtered_result)
        
        return await loop.run_in_executor(None, _ocr_sync)