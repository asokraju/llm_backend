"""Unit tests for settings configuration."""

import pytest
import os
from unittest.mock import patch

from src.config.settings import Settings


class TestSettings:
    """Test settings configuration and validation."""
    
    def test_default_settings(self):
        """Test default settings values."""
        # Start with a clean environment for this test, without .env file
        clean_env = {k: v for k, v in os.environ.items() if not k.startswith("RAG_")}
        
        with patch.dict(os.environ, clean_env, clear=True):
            # Create settings without loading .env file
            settings = Settings(_env_file=None)
        
        # API settings
        assert settings.api_host == "0.0.0.0"
        assert settings.api_port == 8000
        assert settings.api_workers == 4
        assert settings.api_reload is False
        
        # Security settings
        assert settings.api_key_enabled is True
        assert settings.cors_origins == ["*"]
        
        # LightRAG settings
        assert settings.rag_working_dir == "./rag_data"
        assert settings.llm_host == "http://localhost:11434"
        assert settings.llm_model == "qwen2.5:7b-instruct"
        assert settings.embedding_model == "nomic-embed-text"
        assert settings.embedding_dim == 768
    
    def test_api_keys_parsing_from_string(self):
        """Test parsing API keys from comma-separated string."""
        with patch.dict(os.environ, {"RAG_API_KEYS_STR": "key1,key2,key3"}, clear=False):
            settings = Settings(_env_file=None)
            assert settings.api_keys == ["key1", "key2", "key3"]
    
    def test_api_keys_empty_string(self):
        """Test parsing empty API keys string."""
        with patch.dict(os.environ, {"RAG_API_KEYS": ""}, clear=False):
            settings = Settings(_env_file=None)
            assert settings.api_keys == []
    
    def test_api_keys_with_spaces(self):
        """Test parsing API keys with spaces."""
        with patch.dict(os.environ, {"RAG_API_KEYS_STR": "key1, key2 , key3"}, clear=False):
            settings = Settings(_env_file=None)
            assert settings.api_keys == ["key1", "key2", "key3"]
    
    def test_cors_origins_parsing(self):
        """Test parsing CORS origins from comma-separated string."""
        with patch.dict(os.environ, {"RAG_CORS_ORIGINS_STR": "http://localhost:3000,https://app.example.com"}, clear=False):
            settings = Settings(_env_file=None)
            assert settings.cors_origins == ["http://localhost:3000", "https://app.example.com"]
    
    def test_cors_origins_single_wildcard(self):
        """Test CORS origins with wildcard."""
        with patch.dict(os.environ, {"RAG_CORS_ORIGINS": "*"}):
            settings = Settings()
            assert settings.cors_origins == ["*"]
    
    def test_log_level_validation(self):
        """Test log level validation."""
        # Valid log level
        with patch.dict(os.environ, {"RAG_LOG_LEVEL": "debug"}):
            settings = Settings()
            assert settings.log_level == "DEBUG"
        
        # Invalid log level should raise error
        with patch.dict(os.environ, {"RAG_LOG_LEVEL": "invalid"}):
            with pytest.raises(ValueError) as exc_info:
                Settings()
            assert "Invalid log level" in str(exc_info.value)
    
    def test_log_format_validation(self):
        """Test log format validation."""
        # Valid log format
        with patch.dict(os.environ, {"RAG_LOG_FORMAT": "json"}):
            settings = Settings()
            assert settings.log_format == "json"
        
        # Invalid log format should raise error
        with patch.dict(os.environ, {"RAG_LOG_FORMAT": "xml"}):
            with pytest.raises(ValueError) as exc_info:
                Settings()
            assert "Invalid log format" in str(exc_info.value)
    
    def test_environment_variable_prefix(self):
        """Test that environment variables use RAG_ prefix."""
        env_vars = {
            "RAG_API_HOST": "127.0.0.1",
            "RAG_API_PORT": "8080",
            "RAG_LLM_MODEL": "custom-model",
            "RAG_EMBEDDING_DIM": "1024"
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            assert settings.api_host == "127.0.0.1"
            assert settings.api_port == 8080
            assert settings.llm_model == "custom-model"
            assert settings.embedding_dim == 1024
    
    def test_get_ollama_url(self):
        """Test Ollama URL generation."""
        settings = Settings()
        assert settings.get_ollama_url() == "http://localhost:11434/api"
        
        # Test with trailing slash
        with patch.dict(os.environ, {"RAG_LLM_HOST": "http://ollama:11434/"}):
            settings = Settings()
            assert settings.get_ollama_url() == "http://ollama:11434/api"
    
    def test_get_qdrant_url(self):
        """Test Qdrant URL generation."""
        settings = Settings()
        assert settings.get_qdrant_url() == "http://localhost:6333"
        
        # Test with trailing slash
        with patch.dict(os.environ, {"RAG_QDRANT_HOST": "http://qdrant:6333/"}):
            settings = Settings()
            assert settings.get_qdrant_url() == "http://qdrant:6333"
    
    def test_is_production(self):
        """Test production mode detection."""
        # Development mode (reload enabled)
        with patch.dict(os.environ, {"RAG_API_RELOAD": "true", "RAG_LOG_LEVEL": "DEBUG"}):
            settings = Settings()
            assert settings.is_production() is False
        
        # Production mode (reload disabled, non-debug log level)
        with patch.dict(os.environ, {"RAG_API_RELOAD": "false", "RAG_LOG_LEVEL": "INFO"}):
            settings = Settings()
            assert settings.is_production() is True
        
        # Development mode (debug log level)
        with patch.dict(os.environ, {"RAG_API_RELOAD": "false", "RAG_LOG_LEVEL": "DEBUG"}):
            settings = Settings()
            assert settings.is_production() is False
    
    def test_boolean_parsing(self):
        """Test parsing of boolean environment variables."""
        # Test various true values
        for true_value in ["true", "True", "TRUE", "1", "yes", "Yes"]:
            with patch.dict(os.environ, {"RAG_API_KEY_ENABLED": true_value}):
                settings = Settings()
                assert settings.api_key_enabled is True
        
        # Test various false values
        for false_value in ["false", "False", "FALSE", "0", "no", "No"]:
            with patch.dict(os.environ, {"RAG_API_KEY_ENABLED": false_value}):
                settings = Settings()
                assert settings.api_key_enabled is False
    
    def test_integer_parsing(self):
        """Test parsing of integer environment variables."""
        with patch.dict(os.environ, {
            "RAG_API_PORT": "9000",
            "RAG_API_WORKERS": "8",
            "RAG_RATE_LIMIT_REQUESTS": "120"
        }):
            settings = Settings()
            assert settings.api_port == 9000
            assert settings.api_workers == 8
            assert settings.rate_limit_requests == 120
    
    def test_model_extra_fields(self):
        """Test that extra fields are stored in model_extra."""
        with patch.dict(os.environ, {
            "RAG_API_KEYS_STR": "test-key",
            "RAG_CORS_ORIGINS_STR": "http://localhost"
        }, clear=False):
            settings = Settings(_env_file=None)
            # The aliased fields should be accessible via properties
            assert settings.api_keys == ["test-key"]
            assert settings.cors_origins == ["http://localhost"]