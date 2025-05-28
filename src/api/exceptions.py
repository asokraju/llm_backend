"""Custom exceptions for the RAG API."""

from typing import Optional, Dict, Any


class RAGException(Exception):
    """Base exception for RAG service."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ServiceUnavailableError(RAGException):
    """Raised when dependent services are unavailable."""
    pass


class InvalidRequestError(RAGException):
    """Raised when request parameters are invalid."""
    pass


class DocumentProcessingError(RAGException):
    """Raised when document processing fails."""
    pass


class AuthenticationError(RAGException):
    """Raised when authentication fails."""
    pass


class RateLimitExceededError(RAGException):
    """Raised when rate limit is exceeded."""
    pass


class ModelNotFoundError(RAGException):
    """Raised when required model is not available."""
    pass


class EmbeddingError(RAGException):
    """Raised when embedding generation fails."""
    pass


class QueryError(RAGException):
    """Raised when query processing fails."""
    pass


class ConfigurationError(RAGException):
    """Raised when configuration is invalid."""
    pass