"""Logging configuration for the RAG API."""

import logging
import sys
import uuid
import threading
from typing import Dict, Any
from datetime import datetime
from contextlib import contextmanager

import structlog
from pythonjsonlogger import jsonlogger

from ..config.settings import settings


def setup_logging():
    """Configure structured logging based on settings."""
    
    # Configure standard library logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        stream=sys.stdout,
        format="%(message)s" if settings.log_format == "json" else None
    )
    
    # Configure structlog processors
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        add_correlation_id,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    if settings.log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def add_correlation_id(logger, name, event_dict):
    """Add correlation ID to log entries."""
    # Try to get correlation ID from context
    correlation_id = getattr(threading.current_thread(), 'correlation_id', None)
    if correlation_id:
        event_dict['correlation_id'] = correlation_id
    return event_dict


class CorrelationIdFilter(logging.Filter):
    """Filter to add correlation ID to log records."""
    
    def filter(self, record):
        correlation_id = getattr(threading.current_thread(), 'correlation_id', None)
        record.correlation_id = correlation_id or str(uuid.uuid4())
        return True


@contextmanager
def correlation_context(correlation_id: str = None):
    """Context manager to set correlation ID for the current thread."""
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())
    
    current_thread = threading.current_thread()
    old_correlation_id = getattr(current_thread, 'correlation_id', None)
    current_thread.correlation_id = correlation_id
    
    try:
        yield correlation_id
    finally:
        if old_correlation_id is not None:
            current_thread.correlation_id = old_correlation_id
        else:
            delattr(current_thread, 'correlation_id')


def get_logger(name: str = None) -> structlog.BoundLogger:
    """Get a configured logger instance."""
    return structlog.get_logger(name)


def log_request(method: str, url: str, headers: Dict[str, str], 
                body: Any = None, correlation_id: str = None):
    """Log incoming request details."""
    if not settings.enable_request_logging:
        return
    
    logger = get_logger("api.request")
    logger.info(
        "Request received",
        method=method,
        url=url,
        headers={k: v for k, v in headers.items() if k.lower() not in ['authorization', 'x-api-key']},
        body_size=len(str(body)) if body else 0,
        correlation_id=correlation_id,
        timestamp=datetime.utcnow().isoformat()
    )


def log_response(status_code: int, response_time: float, 
                 correlation_id: str = None, error: str = None):
    """Log response details."""
    if not settings.enable_request_logging:
        return
    
    logger = get_logger("api.response")
    log_data = {
        "status_code": status_code,
        "response_time_ms": round(response_time * 1000, 2),
        "correlation_id": correlation_id,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if error:
        log_data["error"] = error
        logger.error("Request failed", **log_data)
    else:
        logger.info("Request completed", **log_data)


def log_service_call(service: str, operation: str, duration: float, 
                     success: bool = True, error: str = None):
    """Log external service calls."""
    logger = get_logger("api.service")
    log_data = {
        "service": service,
        "operation": operation,
        "duration_ms": round(duration * 1000, 2),
        "success": success,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if error:
        log_data["error"] = error
        logger.error("Service call failed", **log_data)
    else:
        logger.info("Service call completed", **log_data)


def log_document_processing(doc_count: int, processing_time: float, 
                           success: bool = True, error: str = None):
    """Log document processing events."""
    logger = get_logger("api.documents")
    log_data = {
        "document_count": doc_count,
        "processing_time_ms": round(processing_time * 1000, 2),
        "success": success,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if error:
        log_data["error"] = error
        logger.error("Document processing failed", **log_data)
    else:
        logger.info("Documents processed", **log_data)


def log_query_processing(question: str, mode: str, processing_time: float,
                        success: bool = True, error: str = None):
    """Log query processing events."""
    logger = get_logger("api.query")
    log_data = {
        "question_length": len(question),
        "mode": mode,
        "processing_time_ms": round(processing_time * 1000, 2),
        "success": success,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if error:
        log_data["error"] = error
        logger.error("Query processing failed", **log_data)
    else:
        logger.info("Query processed", **log_data)