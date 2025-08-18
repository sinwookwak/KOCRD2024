# kocrd/patterns/persat_pattern.py
"""
Persat Pattern Implementation for KOCRD2024

The Persat pattern provides a unified interface for complex operations while maintaining
composability and extensibility. This implementation addresses the core gaps in OCR processing,
document management, and system integration.
"""

import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable, Protocol, Union
from dataclasses import dataclass
from enum import Enum
import json
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import threading
from datetime import datetime

from kocrd.config.config import text_manager, AppConfig
from kocrd.config.system_constants import SystemConstants


class ProcessingStrategy(ABC):
    """Abstract base class for processing strategies"""
    
    @abstractmethod
    async def process(self, data: Any, context: Dict[str, Any]) -> Any:
        pass
    
    @abstractmethod
    def validate(self, data: Any) -> bool:
        pass


class OCRStrategy(ProcessingStrategy):
    """Base class for OCR processing strategies"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.is_gpu_enabled = config.get("gpu_enabled", False)
        self.batch_size = config.get("batch_size", 1)
    
    @abstractmethod
    async def extract_text(self, image_data: Any, language: str = "kor+eng") -> str:
        pass


class TesseractOCRStrategy(OCRStrategy):
    """Tesseract OCR implementation with async support"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("tesseract", config)
        self.tesseract_cmd = config.get("tesseract_cmd", AppConfig.OCR_SETTINGS.get("tesseract_cmd"))
        self.tessdata_dir = config.get("tessdata_dir", AppConfig.OCR_SETTINGS.get("tessdata_dir"))
    
    def validate(self, data: Any) -> bool:
        return hasattr(data, 'mode') or isinstance(data, str)
    
    async def process(self, data: Any, context: Dict[str, Any]) -> Any:
        language = context.get("language", "kor+eng")
        return await self.extract_text(data, language)
    
    async def extract_text(self, image_data: Any, language: str = "kor+eng") -> str:
        import pytesseract
        from PIL import Image
        
        loop = asyncio.get_event_loop()
        
        def _ocr_sync():
            if self.tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
            
            if isinstance(image_data, str):
                image = Image.open(image_data)
            else:
                image = image_data
            
            return pytesseract.image_to_string(image, lang=language)
        
        return await loop.run_in_executor(None, _ocr_sync)


class EasyOCRStrategy(OCRStrategy):
    """EasyOCR implementation with GPU support"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("easyocr", config)
        self.reader = None
        self._initialize_reader()
    
    def _initialize_reader(self):
        try:
            import easyocr
            self.reader = easyocr.Reader(['ko', 'en'], gpu=self.is_gpu_enabled)
        except ImportError:
            logging.warning("EasyOCR not available, falling back to Tesseract")
            self.reader = None
    
    def validate(self, data: Any) -> bool:
        return self.reader is not None and (hasattr(data, 'mode') or isinstance(data, str))
    
    async def process(self, data: Any, context: Dict[str, Any]) -> Any:
        return await self.extract_text(data)
    
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
            
            return '\n'.join([text[1] for text in result])
        
        return await loop.run_in_executor(None, _ocr_sync)


@dataclass
class ProcessingPipeline:
    """Represents a processing pipeline configuration"""
    name: str
    strategies: List[str]
    parallel: bool = False
    fallback_strategy: Optional[str] = None
    timeout: Optional[int] = None


class PerformanceMetrics:
    """Tracks performance metrics for processing strategies"""
    
    def __init__(self):
        self.metrics = {}
        self._lock = threading.Lock()
    
    def record_execution(self, strategy_name: str, duration: float, success: bool):
        with self._lock:
            if strategy_name not in self.metrics:
                self.metrics[strategy_name] = {
                    'total_executions': 0,
                    'successful_executions': 0,
                    'total_duration': 0.0,
                    'average_duration': 0.0
                }
            
            metrics = self.metrics[strategy_name]
            metrics['total_executions'] += 1
            metrics['total_duration'] += duration
            if success:
                metrics['successful_executions'] += 1
            metrics['average_duration'] = metrics['total_duration'] / metrics['total_executions']
    
    def get_best_strategy(self, strategy_names: List[str]) -> Optional[str]:
        """Returns the strategy with best performance"""
        best_strategy = None
        best_score = -1
        
        with self._lock:
            for name in strategy_names:
                if name in self.metrics:
                    metrics = self.metrics[name]
                    if metrics['total_executions'] > 0:
                        success_rate = metrics['successful_executions'] / metrics['total_executions']
                        speed_score = 1.0 / (metrics['average_duration'] + 0.1)
                        score = success_rate * speed_score
                        
                        if score > best_score:
                            best_score = score
                            best_strategy = name
        
        return best_strategy


class PerformanceOptimizer:
    """Optimizes processing performance based on metrics"""
    
    def __init__(self, metrics: PerformanceMetrics):
        self.metrics = metrics
        self.adaptive_enabled = True
    
    def should_use_gpu(self, data_size: int) -> bool:
        """Determines if GPU should be used based on data size"""
        return self.adaptive_enabled and data_size > 1024 * 1024  # > 1MB
    
    def get_optimal_batch_size(self, strategy_name: str, available_memory: int) -> int:
        """Calculates optimal batch size based on available memory"""
        base_batch_size = 4
        memory_factor = min(available_memory // (512 * 1024 * 1024), 8)  # 512MB per batch
        return base_batch_size * memory_factor


class PersetProcessor:
    """
    Main Persat pattern processor that coordinates multiple processing strategies
    """
    
    def __init__(self):
        self.strategies: Dict[str, ProcessingStrategy] = {}
        self.pipelines: Dict[str, ProcessingPipeline] = {}
        self.metrics = PerformanceMetrics()
        self.optimizer = PerformanceOptimizer(self.metrics)
        self.executor = ThreadPoolExecutor(max_workers=4)
        self._initialize_default_strategies()
        self._initialize_default_pipelines()
    
    def _initialize_default_strategies(self):
        """Initialize default OCR strategies"""
        tesseract_config = {
            "tesseract_cmd": AppConfig.OCR_SETTINGS.get("tesseract_cmd"),
            "tessdata_dir": AppConfig.OCR_SETTINGS.get("tessdata_dir"),
            "gpu_enabled": False,
            "batch_size": 1
        }
        
        easyocr_config = {
            "gpu_enabled": True,
            "batch_size": 4
        }
        
        self.register_strategy("tesseract", TesseractOCRStrategy(tesseract_config))
        self.register_strategy("easyocr", EasyOCRStrategy(easyocr_config))
    
    def _initialize_default_pipelines(self):
        """Initialize default processing pipelines"""
        self.register_pipeline(ProcessingPipeline(
            name="fast_ocr",
            strategies=["easyocr", "tesseract"],
            parallel=False,
            fallback_strategy="tesseract",
            timeout=30
        ))
        
        self.register_pipeline(ProcessingPipeline(
            name="robust_ocr",
            strategies=["tesseract", "easyocr"],
            parallel=False,
            fallback_strategy="tesseract",
            timeout=60
        ))
        
        self.register_pipeline(ProcessingPipeline(
            name="parallel_ocr",
            strategies=["tesseract", "easyocr"],
            parallel=True,
            timeout=45
        ))
    
    def register_strategy(self, name: str, strategy: ProcessingStrategy):
        """Register a new processing strategy"""
        self.strategies[name] = strategy
        logging.info(f"Registered strategy: {name}")
    
    def register_pipeline(self, pipeline: ProcessingPipeline):
        """Register a new processing pipeline"""
        self.pipelines[pipeline.name] = pipeline
        logging.info(f"Registered pipeline: {pipeline.name}")
    
    async def process(self, data: Any, pipeline_name: str = "fast_ocr", context: Optional[Dict[str, Any]] = None) -> Any:
        """Process data through the specified pipeline"""
        if context is None:
            context = {}
        
        pipeline = self.pipelines.get(pipeline_name)
        if not pipeline:
            raise ValueError(f"Pipeline '{pipeline_name}' not found")
        
        start_time = datetime.now()
        
        try:
            if pipeline.parallel:
                result = await self._process_parallel(data, pipeline, context)
            else:
                result = await self._process_sequential(data, pipeline, context)
            
            duration = (datetime.now() - start_time).total_seconds()
            logging.info(f"Pipeline '{pipeline_name}' completed in {duration:.2f}s")
            return result
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logging.error(f"Pipeline '{pipeline_name}' failed after {duration:.2f}s: {e}")
            
            # Try fallback strategy if available
            if pipeline.fallback_strategy and pipeline.fallback_strategy in self.strategies:
                logging.info(f"Attempting fallback strategy: {pipeline.fallback_strategy}")
                strategy = self.strategies[pipeline.fallback_strategy]
                return await strategy.process(data, context)
            
            raise
    
    async def _process_sequential(self, data: Any, pipeline: ProcessingPipeline, context: Dict[str, Any]) -> Any:
        """Process data sequentially through strategies"""
        current_data = data
        
        for strategy_name in pipeline.strategies:
            strategy = self.strategies.get(strategy_name)
            if not strategy:
                logging.warning(f"Strategy '{strategy_name}' not found, skipping")
                continue
            
            if not strategy.validate(current_data):
                logging.warning(f"Strategy '{strategy_name}' validation failed, skipping")
                continue
            
            start_time = datetime.now()
            try:
                if pipeline.timeout:
                    current_data = await asyncio.wait_for(
                        strategy.process(current_data, context),
                        timeout=pipeline.timeout
                    )
                else:
                    current_data = await strategy.process(current_data, context)
                
                duration = (datetime.now() - start_time).total_seconds()
                self.metrics.record_execution(strategy_name, duration, True)
                
                # For OCR strategies, return the result immediately
                if isinstance(strategy, OCRStrategy):
                    return current_data
                    
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds()
                self.metrics.record_execution(strategy_name, duration, False)
                logging.error(f"Strategy '{strategy_name}' failed: {e}")
                continue
        
        return current_data
    
    async def _process_parallel(self, data: Any, pipeline: ProcessingPipeline, context: Dict[str, Any]) -> Any:
        """Process data in parallel through strategies"""
        tasks = []
        
        for strategy_name in pipeline.strategies:
            strategy = self.strategies.get(strategy_name)
            if strategy and strategy.validate(data):
                task = asyncio.create_task(
                    self._execute_strategy_with_metrics(strategy, strategy_name, data, context)
                )
                tasks.append((strategy_name, task))
        
        if not tasks:
            raise RuntimeError("No valid strategies found for parallel processing")
        
        # Wait for the first successful result
        try:
            if pipeline.timeout:
                done, pending = await asyncio.wait(
                    [task for _, task in tasks],
                    return_when=asyncio.FIRST_COMPLETED,
                    timeout=pipeline.timeout
                )
            else:
                done, pending = await asyncio.wait(
                    [task for _, task in tasks],
                    return_when=asyncio.FIRST_COMPLETED
                )
            
            # Cancel pending tasks
            for task in pending:
                task.cancel()
            
            # Return first successful result
            for task in done:
                try:
                    return await task
                except Exception as e:
                    logging.error(f"Parallel task failed: {e}")
                    continue
            
            raise RuntimeError("All parallel strategies failed")
            
        except asyncio.TimeoutError:
            # Cancel all tasks on timeout
            for _, task in tasks:
                task.cancel()
            raise RuntimeError(f"Parallel processing timed out after {pipeline.timeout}s")
    
    async def _execute_strategy_with_metrics(self, strategy: ProcessingStrategy, name: str, data: Any, context: Dict[str, Any]) -> Any:
        """Execute strategy with performance metrics tracking"""
        start_time = datetime.now()
        try:
            result = await strategy.process(data, context)
            duration = (datetime.now() - start_time).total_seconds()
            self.metrics.record_execution(name, duration, True)
            return result
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self.metrics.record_execution(name, duration, False)
            raise
    
    async def process_batch(self, data_list: List[Any], pipeline_name: str = "fast_ocr", context: Optional[Dict[str, Any]] = None) -> List[Any]:
        """Process a batch of data items"""
        if context is None:
            context = {}
        
        # Determine optimal batch size
        pipeline = self.pipelines.get(pipeline_name)
        if not pipeline:
            raise ValueError(f"Pipeline '{pipeline_name}' not found")
        
        # Process in batches for memory efficiency
        batch_size = self.optimizer.get_optimal_batch_size(pipeline_name, 1024 * 1024 * 1024)  # 1GB
        results = []
        
        for i in range(0, len(data_list), batch_size):
            batch = data_list[i:i + batch_size]
            batch_tasks = [self.process(item, pipeline_name, context.copy()) for item in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            results.extend(batch_results)
        
        return results
    
    def get_metrics_report(self) -> Dict[str, Any]:
        """Get performance metrics report"""
        return {
            "metrics": self.metrics.metrics,
            "timestamp": datetime.now().isoformat(),
            "strategies_count": len(self.strategies),
            "pipelines_count": len(self.pipelines)
        }
    
    def cleanup(self):
        """Cleanup resources"""
        self.executor.shutdown(wait=True)
        logging.info("PersetProcessor cleaned up")


# Global instance for easy access
global_persat_processor = PersetProcessor()


async def process_document_ocr(image_data: Any, pipeline: str = "fast_ocr", language: str = "kor+eng") -> str:
    """Convenience function for OCR processing"""
    context = {"language": language}
    return await global_persat_processor.process(image_data, pipeline, context)


async def process_batch_ocr(image_list: List[Any], pipeline: str = "fast_ocr", language: str = "kor+eng") -> List[str]:
    """Convenience function for batch OCR processing"""
    context = {"language": language}
    return await global_persat_processor.process_batch(image_list, pipeline, context)