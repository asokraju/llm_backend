"""Configuration management for the RAG API."""

import os
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0", description="API host address")
    api_port: int = Field(default=8000, description="API port")
    api_workers: int = Field(default=4, description="Number of API workers")
    api_reload: bool = Field(default=False, description="Enable auto-reload for development")
    api_title: str = Field(default="LightRAG API", description="API title")
    api_version: str = Field(default="1.0.0", description="API version")
    api_description: str = Field(default="Production-ready RAG system API", description="API description")
    
    # Security Configuration
    api_key_enabled: bool = Field(default=True, description="Enable API key authentication")
    api_keys_str: str = Field(default="", alias="api_keys", description="Comma-separated API keys")
    cors_origins_str: str = Field(default="*", alias="cors_origins", description="Comma-separated CORS origins")
    max_request_size: int = Field(default=10485760, description="Max request size in bytes (10MB)")
    
    # LightRAG Configuration
    rag_working_dir: str = Field(default="./rag_data", description="RAG working directory")
    llm_host: str = Field(default="http://localhost:11434", description="Ollama LLM host")
    llm_model: str = Field(default="qwen2.5:7b-instruct", description="LLM model name")
    embedding_model: str = Field(default="nomic-embed-text", description="Embedding model name")
    embedding_dim: int = Field(default=768, description="Embedding dimensions")
    
    # Document Processing
    document_loading_engine: str = Field(default="DOCLING", description="Document loading engine")
    max_documents_per_request: int = Field(default=100, description="Max documents per API request")
    max_document_size: int = Field(default=1048576, description="Max document size in bytes (1MB)")
    chunk_size: int = Field(default=1200, description="Text chunk size for processing")
    chunk_overlap: int = Field(default=100, description="Text chunk overlap")
    
    # External Services
    qdrant_host: str = Field(default="http://localhost:6333", description="Qdrant vector DB host")
    redis_host: str = Field(default="redis://localhost:6379", description="Redis cache host")
    prometheus_host: str = Field(default="http://localhost:9090", description="Prometheus metrics host")
    
    # Monitoring and Logging
    enable_metrics: bool = Field(default=True, description="Enable Prometheus metrics")
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format (json or text)")
    enable_request_logging: bool = Field(default=True, description="Enable request logging")
    
    # Performance Settings
    llm_timeout: int = Field(default=300, description="LLM request timeout in seconds")
    embedding_timeout: int = Field(default=60, description="Embedding request timeout in seconds")
    health_check_timeout: int = Field(default=5, description="Health check timeout in seconds")
    enable_caching: bool = Field(default=True, description="Enable response caching")
    cache_ttl: int = Field(default=3600, description="Cache TTL in seconds")
    
    # Rate Limiting
    rate_limit_requests: int = Field(default=60, description="Requests per minute per API key")
    rate_limit_window: int = Field(default=60, description="Rate limit window in seconds")
    
    @property
    def api_keys(self) -> List[str]:
        """Get API keys as a list."""
        # Check if value is in api_keys_str field
        if self.api_keys_str:
            return [key.strip() for key in self.api_keys_str.split(',') if key.strip()]
        # Check if value is in model_extra with full prefix
        if hasattr(self, 'model_extra') and 'rag_api_keys' in self.model_extra:
            keys_str = self.model_extra['rag_api_keys']
            return [key.strip() for key in keys_str.split(',') if key.strip()]
        return []
    
    @property
    def cors_origins(self) -> List[str]:
        """Get CORS origins as a list."""
        # Check if value is in cors_origins_str field
        if self.cors_origins_str:
            return [origin.strip() for origin in self.cors_origins_str.split(',') if origin.strip()]
        # Check if value is in model_extra with full prefix
        if hasattr(self, 'model_extra') and 'rag_cors_origins' in self.model_extra:
            origins_str = self.model_extra['rag_cors_origins']
            return [origin.strip() for origin in origins_str.split(',') if origin.strip()]
        return ["*"]
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Invalid log level. Must be one of: {valid_levels}')
        return v.upper()
    
    @field_validator('log_format')
    @classmethod
    def validate_log_format(cls, v):
        """Validate log format."""
        valid_formats = ['json', 'text']
        if v.lower() not in valid_formats:
            raise ValueError(f'Invalid log format. Must be one of: {valid_formats}')
        return v.lower()
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="RAG_",
        case_sensitive=False,
        extra="allow",  # Allow extra fields for aliases
        populate_by_name=True,  # Allow population by field name
        json_schema_extra={
            "json_encode_default": lambda v: v,
        }
    )
        
    def get_ollama_url(self) -> str:
        """Get full Ollama API URL."""
        return f"{self.llm_host.rstrip('/')}/api"
    
    def get_qdrant_url(self) -> str:
        """Get full Qdrant API URL."""
        return f"{self.qdrant_host.rstrip('/')}"
    
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return not self.api_reload and self.log_level in ['INFO', 'WARNING', 'ERROR']


# Global settings instance
settings = Settings()