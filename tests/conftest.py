"""Pytest configuration and shared fixtures."""

import pytest
import pytest_asyncio
import asyncio
import os
from typing import AsyncGenerator, Generator
from unittest.mock import Mock, AsyncMock, patch

from fastapi.testclient import TestClient
from httpx import AsyncClient

# Set test environment
os.environ["RAG_API_KEY_ENABLED"] = "false"
os.environ["RAG_API_KEYS"] = "test-key-1,test-key-2"
os.environ["RAG_LLM_HOST"] = "http://localhost:11434"
os.environ["RAG_RAG_WORKING_DIR"] = "./test_rag_data"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_ollama():
    """Mock Ollama API responses."""
    with patch("lightrag.llm.ollama.ollama_model_complete") as mock_complete, \
         patch("lightrag.llm.ollama.ollama_embed") as mock_embed:
        
        # Mock LLM completion
        async def mock_complete_func(*args, **kwargs):
            return "This is a mocked response from the LLM."
        
        # Mock embedding generation
        async def mock_embed_func(texts, *args, **kwargs):
            # Return mock embeddings (768 dimensions for nomic-embed-text)
            return [[0.1] * 768 for _ in texts]
        
        mock_complete.side_effect = mock_complete_func
        mock_embed.side_effect = mock_embed_func
        
        yield {
            "complete": mock_complete,
            "embed": mock_embed
        }


@pytest.fixture
def mock_lightrag_service():
    """Mock LightRAG service."""
    service = AsyncMock()
    service.initialize = AsyncMock()
    service.insert_documents = AsyncMock()
    service.query = AsyncMock(return_value="Mocked query response")
    service.get_graph_data = AsyncMock(return_value={
        "nodes": [],
        "edges": [],
        "stats": {"node_count": 0, "edge_count": 0}
    })
    service.close = AsyncMock()
    return service


@pytest.fixture
def test_client(mock_lightrag_service) -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI app."""
    # Import the app first, then patch the global rag_service
    from src.api.main import app
    with patch("src.api.main.rag_service", mock_lightrag_service):
        with TestClient(app) as client:
            yield client


@pytest_asyncio.fixture
async def async_client(mock_lightrag_service) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client for the FastAPI app."""
    # Import the app first, then patch the global rag_service
    from src.api.main import app
    with patch("src.api.main.rag_service", mock_lightrag_service):
        # Use httpx.AsyncClient for ASGI testing
        from httpx import ASGITransport
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest.fixture
def sample_documents():
    """Sample documents for testing."""
    return [
        "LightRAG is a powerful framework for building RAG systems.",
        "It uses knowledge graphs to enhance retrieval accuracy.",
        "The system supports multiple query modes including naive, local, global, and hybrid."
    ]


@pytest.fixture
def cleanup_test_data():
    """Clean up test data after tests."""
    yield
    # Clean up test working directory if it exists
    import shutil
    if os.path.exists("./test_rag_data"):
        shutil.rmtree("./test_rag_data")