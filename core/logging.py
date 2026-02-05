"""Structured logging and monitoring system for audit platform."""

import logging
import json
from typing import Any, Dict, Optional
from datetime import datetime
from enum import Enum
import time
from functools import wraps
from dataclasses import dataclass, asdict


class LogLevel(str, Enum):
    """Log level enum."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogCategory(str, Enum):
    """Log category for categorization."""
    AUDIT = "AUDIT"
    API = "API"
    WEBHOOK = "WEBHOOK"
    DATABASE = "DATABASE"
    CACHE = "CACHE"
    SECURITY = "SECURITY"
    PERFORMANCE = "PERFORMANCE"
    ERROR = "ERROR"


@dataclass
class StructuredLogEntry:
    """Structured log entry with metadata."""
    timestamp: datetime
    level: LogLevel
    category: LogCategory
    message: str
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    audit_id: Optional[str] = None
    repository: Optional[str] = None
    duration_ms: Optional[float] = None
    status_code: Optional[int] = None
    error_code: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_json(self) -> str:
        """Convert to JSON string.
        
        Returns:
            JSON string
        """
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["level"] = self.level.value
        data["category"] = self.category.value
        return json.dumps(data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.
        
        Returns:
            Dict representation
        """
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["level"] = self.level.value
        data["category"] = self.category.value
        return data


class StructuredLogger:
    """Structured logging system with audit trails."""
    
    def __init__(self, name: str, log_to_file: bool = True):
        """Initialize structured logger.
        
        Args:
            name: Logger name
            log_to_file: Whether to log to file
        """
        self.name = name
        self.logger = logging.getLogger(name)
        self.log_to_file = log_to_file
        self.audit_trail: list[StructuredLogEntry] = []
    
    def log(self, 
            level: LogLevel,
            category: LogCategory,
            message: str,
            user_id: Optional[str] = None,
            request_id: Optional[str] = None,
            audit_id: Optional[str] = None,
            repository: Optional[str] = None,
            duration_ms: Optional[float] = None,
            status_code: Optional[int] = None,
            error_code: Optional[str] = None,
            metadata: Optional[Dict[str, Any]] = None) -> None:
        """Log structured entry.
        
        Args:
            level: Log level
            category: Log category
            message: Log message
            user_id: Optional user ID
            request_id: Optional request ID
            audit_id: Optional audit ID
            repository: Optional repository name
            duration_ms: Optional duration in milliseconds
            status_code: Optional HTTP status code
            error_code: Optional error code
            metadata: Optional additional metadata
        """
        entry = StructuredLogEntry(
            timestamp=datetime.utcnow(),
            level=level,
            category=category,
            message=message,
            user_id=user_id,
            request_id=request_id,
            audit_id=audit_id,
            repository=repository,
            duration_ms=duration_ms,
            status_code=status_code,
            error_code=error_code,
            metadata=metadata or {},
        )
        
        # Store in audit trail
        self.audit_trail.append(entry)
        
        # Log using standard logger
        log_method = getattr(self.logger, level.value.lower())
        log_method(entry.to_json())
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message.
        
        Args:
            message: Log message
            **kwargs: Additional log fields
        """
        self.log(LogLevel.DEBUG, kwargs.pop('category', LogCategory.API), message, **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message.
        
        Args:
            message: Log message
            **kwargs: Additional log fields
        """
        self.log(LogLevel.INFO, kwargs.pop('category', LogCategory.API), message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message.
        
        Args:
            message: Log message
            **kwargs: Additional log fields
        """
        self.log(LogLevel.WARNING, kwargs.pop('category', LogCategory.API), message, **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """Log error message.
        
        Args:
            message: Log message
            **kwargs: Additional log fields
        """
        self.log(LogLevel.ERROR, kwargs.pop('category', LogCategory.ERROR), message, **kwargs)
    
    def critical(self, message: str, **kwargs) -> None:
        """Log critical message.
        
        Args:
            message: Log message
            **kwargs: Additional log fields
        """
        self.log(LogLevel.CRITICAL, kwargs.pop('category', LogCategory.ERROR), message, **kwargs)
    
    def get_audit_trail(self, limit: int = 100) -> list[Dict[str, Any]]:
        """Get audit trail entries.
        
        Args:
            limit: Maximum entries to return
        
        Returns:
            List of audit trail entries
        """
        entries = self.audit_trail[-limit:]
        return [entry.to_dict() for entry in entries]


class PerformanceMonitor:
    """Monitor and track performance metrics."""
    
    def __init__(self, logger: StructuredLogger):
        """Initialize performance monitor.
        
        Args:
            logger: StructuredLogger instance
        """
        self.logger = logger
        self.metrics: Dict[str, list[float]] = {}
    
    def record_metric(self, metric_name: str, value: float) -> None:
        """Record performance metric.
        
        Args:
            metric_name: Name of metric
            value: Metric value
        """
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []
        
        self.metrics[metric_name].append(value)
        
        # Keep only last 1000 entries
        if len(self.metrics[metric_name]) > 1000:
            self.metrics[metric_name] = self.metrics[metric_name][-1000:]
    
    def get_statistics(self, metric_name: str) -> Dict[str, float]:
        """Get statistics for metric.
        
        Args:
            metric_name: Name of metric
        
        Returns:
            Statistics dict (min, max, avg, median)
        """
        if metric_name not in self.metrics or not self.metrics[metric_name]:
            return {}
        
        values = sorted(self.metrics[metric_name])
        n = len(values)
        
        return {
            "count": n,
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / n,
            "median": values[n // 2] if n % 2 == 1 else (values[n // 2 - 1] + values[n // 2]) / 2,
            "p95": values[int(n * 0.95)] if n > 0 else 0,
            "p99": values[int(n * 0.99)] if n > 0 else 0,
        }
    
    def get_all_metrics(self) -> Dict[str, Dict[str, float]]:
        """Get statistics for all metrics.
        
        Returns:
            Dict of metric statistics
        """
        return {
            metric_name: self.get_statistics(metric_name)
            for metric_name in self.metrics.keys()
        }


def log_performance(logger: StructuredLogger, 
                   category: LogCategory = LogCategory.PERFORMANCE,
                   metric_name: Optional[str] = None):
    """Decorator to log performance metrics.
    
    Args:
        logger: StructuredLogger instance
        category: Log category
        metric_name: Optional metric name
    
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                logger.log(
                    level=LogLevel.INFO,
                    category=category,
                    message=f"Function executed: {func.__name__}",
                    duration_ms=duration_ms,
                    metadata={"function": func.__name__}
                )
                
                if metric_name:
                    logger.logger.debug(f"Recording metric {metric_name}: {duration_ms}ms")
                
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(
                    f"Function failed: {func.__name__}: {str(e)}",
                    category=category,
                    duration_ms=duration_ms,
                    error_code="EXECUTION_ERROR"
                )
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                logger.log(
                    level=LogLevel.INFO,
                    category=category,
                    message=f"Function executed: {func.__name__}",
                    duration_ms=duration_ms,
                    metadata={"function": func.__name__}
                )
                
                if metric_name:
                    logger.logger.debug(f"Recording metric {metric_name}: {duration_ms}ms")
                
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(
                    f"Function failed: {func.__name__}: {str(e)}",
                    category=category,
                    duration_ms=duration_ms,
                    error_code="EXECUTION_ERROR"
                )
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


class AuditTrail:
    """Maintain audit trail of sensitive operations."""
    
    def __init__(self, logger: StructuredLogger):
        """Initialize audit trail.
        
        Args:
            logger: StructuredLogger instance
        """
        self.logger = logger
        self.events: list[Dict[str, Any]] = []
    
    def record_access(self, 
                     user_id: Optional[str],
                     resource: str,
                     action: str,
                     success: bool,
                     metadata: Optional[Dict[str, Any]] = None) -> None:
        """Record resource access event.
        
        Args:
            user_id: User ID
            resource: Resource being accessed
            action: Action performed
            success: Whether action succeeded
            metadata: Optional additional metadata
        """
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "resource": resource,
            "action": action,
            "success": success,
            "metadata": metadata or {}
        }
        
        self.events.append(event)
        
        self.logger.log(
            level=LogLevel.INFO,
            category=LogCategory.SECURITY,
            message=f"Audit event: {action} on {resource}",
            user_id=user_id,
            metadata=event
        )
    
    def get_trail(self, user_id: Optional[str] = None, 
                 resource: Optional[str] = None,
                 limit: int = 100) -> list[Dict[str, Any]]:
        """Get audit trail events.
        
        Args:
            user_id: Filter by user ID
            resource: Filter by resource
            limit: Maximum events to return
        
        Returns:
            List of audit events
        """
        events = self.events
        
        if user_id:
            events = [e for e in events if e["user_id"] == user_id]
        
        if resource:
            events = [e for e in events if e["resource"] == resource]
        
        return events[-limit:]


import asyncio
