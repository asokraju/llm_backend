# LightRAG Remote Client Guide

A comprehensive guide for using the LightRAG service remotely from client applications.

## Table of Contents

1. [Overview](#overview)
2. [Service Endpoints](#service-endpoints)
3. [Quick Start](#quick-start)
4. [Dependencies](#dependencies)
5. [Environment Configuration](#environment-configuration)
6. [Python Client Examples](#python-client-examples)
7. [Integration Patterns](#integration-patterns)
8. [Testing Approaches](#testing-approaches)
9. [Error Handling](#error-handling)
10. [Performance Considerations](#performance-considerations)
11. [Security](#security)
12. [Troubleshooting](#troubleshooting)

## Overview

The LightRAG service provides a production-ready REST API for document ingestion, knowledge graph construction, and intelligent querying using Retrieval-Augmented Generation (RAG). This guide explains how to integrate with the service from external client applications.

### Key Features

- **Document Processing**: Upload and process various document formats
- **Knowledge Graph**: Automatic entity and relationship extraction
- **Multiple Query Modes**: Naive, local, global, and hybrid querying
- **Vector Search**: Semantic similarity search capabilities
- **Production Ready**: Health checks, metrics, rate limiting, and monitoring

## Service Endpoints

The LightRAG service runs on configurable ports with the following default endpoints:

### Core Service URLs
- **API Gateway**: `http://localhost:80` (NGINX proxy)
- **Direct API**: `http://localhost:9000` (FastAPI service)
- **Monitoring**: `http://localhost:4000` (Grafana dashboard)
- **Metrics**: `http://localhost:10090` (Prometheus)

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information and capabilities |
| `/health` | GET | Basic health check |
| `/health/ready` | GET | Readiness check with dependencies |
| `/documents` | POST | Upload documents for processing |
| `/query` | POST | Query the knowledge base |
| `/graph` | GET | Retrieve knowledge graph data |
| `/metrics` | GET | Prometheus metrics |

## Quick Start

### 1. Verify Service Availability

```bash
# Check if the service is running
curl http://localhost:9000/health

# Expected response:
{
  "status": "healthy",
  "timestamp": "2025-01-08T12:00:00Z",
  "version": "1.0.0",
  "uptime": 3600.0
}
```

### 2. Basic Document Upload

```bash
curl -X POST http://localhost:9000/documents \
  -H "Content-Type: application/json" \
  -d '{
    "documents": ["Artificial Intelligence is transforming industries worldwide."]
  }'
```

### 3. Query the Knowledge Base

```bash
curl -X POST http://localhost:9000/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is transforming industries?",
    "mode": "hybrid"
  }'
```

## Dependencies

### Python Requirements

Create a `requirements.txt` file for your client project:

```txt
# HTTP client libraries
requests>=2.31.0
httpx>=0.25.0          # Alternative async HTTP client

# Data handling
pydantic>=2.0.0        # Request/response validation
pandas>=2.0.0          # Data manipulation (optional)

# Vector operations (if doing local processing)
numpy>=1.24.0
qdrant-client>=1.6.0   # Direct Qdrant access (optional)

# Async support
asyncio>=3.4.3
aiofiles>=23.0.0       # Async file operations

# Testing frameworks
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-httpx>=0.26.0

# Monitoring and logging
structlog>=23.0.0      # Structured logging
prometheus-client>=0.17.0  # Custom metrics
```

### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Environment Configuration

### Client Environment Variables

Create a `.env` file in your client project:

```env
# LightRAG Service Configuration
LIGHTRAG_API_URL=http://localhost:9000
LIGHTRAG_API_KEY=your-api-key-here
LIGHTRAG_TIMEOUT=300

# Optional: Direct service access
LIGHTRAG_QDRANT_URL=http://localhost:7333
LIGHTRAG_REDIS_URL=redis://localhost:7379
LIGHTRAG_PROMETHEUS_URL=http://localhost:10090

# Client Configuration
CLIENT_LOG_LEVEL=INFO
CLIENT_RETRY_ATTEMPTS=3
CLIENT_RETRY_DELAY=1.0
CLIENT_CACHE_ENABLED=true
CLIENT_CACHE_TTL=3600
```

### Environment Loading

```python
import os
from pathlib import Path
from typing import Optional

class ClientConfig:
    """Client configuration with environment variable support."""
    
    def __init__(self):
        # Load .env file if it exists
        env_file = Path(".env")
        if env_file.exists():
            self._load_env_file(env_file)
    
    def _load_env_file(self, env_file: Path):
        """Load environment variables from file."""
        with open(env_file) as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
    
    @property
    def api_url(self) -> str:
        return os.getenv("LIGHTRAG_API_URL", "http://localhost:9000")
    
    @property
    def api_key(self) -> Optional[str]:
        return os.getenv("LIGHTRAG_API_KEY")
    
    @property
    def timeout(self) -> int:
        return int(os.getenv("LIGHTRAG_TIMEOUT", "300"))
    
    @property
    def retry_attempts(self) -> int:
        return int(os.getenv("CLIENT_RETRY_ATTEMPTS", "3"))

# Global config instance
config = ClientConfig()
```

## Python Client Examples

### 1. Basic Synchronous Client

```python
import requests
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class QueryResult:
    """Query result data structure."""
    success: bool
    answer: str
    mode: str
    sources: Optional[List[Dict]] = None
    processing_time: float = 0.0
    timestamp: Optional[datetime] = None

class LightRAGClient:
    """Synchronous client for LightRAG service."""
    
    def __init__(self, base_url: str = "http://localhost:9000", api_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        
        if api_key:
            self.session.headers.update({"Authorization": f"Bearer {api_key}"})
        
        # Set default timeouts
        self.session.timeout = (10, 300)  # (connect, read)
    
    def health_check(self) -> Dict[str, Any]:
        """Check service health."""
        response = self.session.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    def upload_documents(self, documents: List[str]) -> Dict[str, Any]:
        """Upload documents for processing."""
        payload = {"documents": documents}
        response = self.session.post(f"{self.base_url}/documents", json=payload)
        response.raise_for_status()
        return response.json()
    
    def query(self, question: str, mode: str = "hybrid", **kwargs) -> QueryResult:
        """Query the knowledge base."""
        payload = {
            "question": question,
            "mode": mode,
            **kwargs
        }
        
        start_time = time.time()
        response = self.session.post(f"{self.base_url}/query", json=payload)
        response.raise_for_status()
        
        data = response.json()
        processing_time = time.time() - start_time
        
        return QueryResult(
            success=data.get("success", False),
            answer=data.get("answer", ""),
            mode=data.get("mode", mode),
            sources=data.get("sources"),
            processing_time=processing_time,
            timestamp=datetime.fromisoformat(data.get("timestamp", "").replace('Z', '+00:00'))
        )
    
    def get_graph(self) -> Dict[str, Any]:
        """Retrieve knowledge graph data."""
        response = self.session.get(f"{self.base_url}/graph")
        response.raise_for_status()
        return response.json()
    
    def close(self):
        """Close the session."""
        self.session.close()

# Usage example
if __name__ == "__main__":
    client = LightRAGClient()
    
    try:
        # Check health
        health = client.health_check()
        print(f"Service status: {health['status']}")
        
        # Upload documents
        documents = [
            "Python is a versatile programming language.",
            "Machine learning enables computers to learn from data.",
            "Neural networks are inspired by biological brain structures."
        ]
        
        upload_result = client.upload_documents(documents)
        print(f"Uploaded {upload_result['documents_processed']} documents")
        
        # Query
        result = client.query("What is Python used for?", mode="hybrid")
        print(f"Answer: {result.answer}")
        
    finally:
        client.close()
```

### 2. Async Client

```python
import asyncio
import aiohttp
import time
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager

class AsyncLightRAGClient:
    """Asynchronous client for LightRAG service."""
    
    def __init__(self, base_url: str = "http://localhost:9000", api_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def connect(self):
        """Create HTTP session."""
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        timeout = aiohttp.ClientTimeout(total=300, connect=10)
        self.session = aiohttp.ClientSession(
            headers=headers,
            timeout=timeout,
            raise_for_status=True
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Check service health."""
        async with self.session.get(f"{self.base_url}/health") as response:
            return await response.json()
    
    async def upload_documents(self, documents: List[str]) -> Dict[str, Any]:
        """Upload documents for processing."""
        payload = {"documents": documents}
        async with self.session.post(f"{self.base_url}/documents", json=payload) as response:
            return await response.json()
    
    async def query(self, question: str, mode: str = "hybrid", **kwargs) -> QueryResult:
        """Query the knowledge base."""
        payload = {
            "question": question,
            "mode": mode,
            **kwargs
        }
        
        start_time = time.time()
        async with self.session.post(f"{self.base_url}/query", json=payload) as response:
            data = await response.json()
        
        processing_time = time.time() - start_time
        
        return QueryResult(
            success=data.get("success", False),
            answer=data.get("answer", ""),
            mode=data.get("mode", mode),
            sources=data.get("sources"),
            processing_time=processing_time,
            timestamp=datetime.fromisoformat(data.get("timestamp", "").replace('Z', '+00:00'))
        )
    
    async def query_batch(self, questions: List[str], mode: str = "hybrid") -> List[QueryResult]:
        """Query multiple questions concurrently."""
        tasks = [self.query(question, mode) for question in questions]
        return await asyncio.gather(*tasks)
    
    async def close(self):
        """Close the session."""
        if self.session:
            await self.session.close()

# Usage example
async def main():
    async with AsyncLightRAGClient() as client:
        # Health check
        health = await client.health_check()
        print(f"Service status: {health['status']}")
        
        # Batch queries
        questions = [
            "What is artificial intelligence?",
            "How does machine learning work?",
            "What are neural networks?"
        ]
        
        results = await client.query_batch(questions)
        for i, result in enumerate(results):
            print(f"Q{i+1}: {result.answer[:100]}...")

if __name__ == "__main__":
    asyncio.run(main())
```

### 3. Production Client with Retry Logic

```python
import requests
import time
import logging
from typing import List, Dict, Any, Optional, Callable
from functools import wraps
from dataclasses import dataclass, field
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

@dataclass
class ClientMetrics:
    """Client-side metrics tracking."""
    requests_total: int = 0
    requests_failed: int = 0
    total_response_time: float = 0.0
    retries_total: int = 0
    
    @property
    def average_response_time(self) -> float:
        return self.total_response_time / max(self.requests_total, 1)
    
    @property
    def success_rate(self) -> float:
        return (self.requests_total - self.requests_failed) / max(self.requests_total, 1)

def retry_on_failure(max_retries: int = 3, backoff_factor: float = 1.0):
    """Decorator for retrying failed requests."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(self, *args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        wait_time = backoff_factor * (2 ** attempt)
                        self.logger.warning(f"Request failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                        self.metrics.retries_total += 1
                        time.sleep(wait_time)
                    else:
                        self.logger.error(f"Request failed after {max_retries + 1} attempts: {e}")
                        self.metrics.requests_failed += 1
            
            raise last_exception
        return wrapper
    return decorator

class ProductionLightRAGClient:
    """Production-ready client with error handling, retries, and metrics."""
    
    def __init__(self, 
                 base_url: str = "http://localhost:9000",
                 api_key: Optional[str] = None,
                 timeout: int = 300,
                 max_retries: int = 3,
                 backoff_factor: float = 1.0):
        
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        # Setup session with retry strategy
        self.session = requests.Session()
        
        if api_key:
            self.session.headers.update({"Authorization": f"Bearer {api_key}"})
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Metrics tracking
        self.metrics = ClientMetrics()
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make HTTP request with metrics tracking."""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        
        try:
            response = self.session.request(method, url, timeout=self.timeout, **kwargs)
            response.raise_for_status()
            return response
        finally:
            self.metrics.requests_total += 1
            self.metrics.total_response_time += time.time() - start_time
    
    @retry_on_failure(max_retries=3)
    def health_check(self) -> Dict[str, Any]:
        """Check service health with retry."""
        response = self._make_request("GET", "/health")
        return response.json()
    
    @retry_on_failure(max_retries=2)  # Fewer retries for upload
    def upload_documents(self, documents: List[str]) -> Dict[str, Any]:
        """Upload documents with retry."""
        payload = {"documents": documents}
        response = self._make_request("POST", "/documents", json=payload)
        return response.json()
    
    @retry_on_failure(max_retries=3)
    def query(self, question: str, mode: str = "hybrid", **kwargs) -> QueryResult:
        """Query with retry and full response parsing."""
        payload = {
            "question": question,
            "mode": mode,
            **kwargs
        }
        
        response = self._make_request("POST", "/query", json=payload)
        data = response.json()
        
        return QueryResult(
            success=data.get("success", False),
            answer=data.get("answer", ""),
            mode=data.get("mode", mode),
            sources=data.get("sources"),
            processing_time=data.get("processing_time", 0.0),
            timestamp=datetime.fromisoformat(data.get("timestamp", "").replace('Z', '+00:00'))
        )
    
    def get_client_metrics(self) -> Dict[str, Any]:
        """Get client-side metrics."""
        return {
            "requests_total": self.metrics.requests_total,
            "requests_failed": self.metrics.requests_failed,
            "success_rate": self.metrics.success_rate,
            "average_response_time": self.metrics.average_response_time,
            "retries_total": self.metrics.retries_total
        }
    
    def close(self):
        """Close the session and log final metrics."""
        metrics = self.get_client_metrics()
        self.logger.info(f"Client session closed. Final metrics: {metrics}")
        self.session.close()

# Usage example
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    client = ProductionLightRAGClient(timeout=60, max_retries=3)
    
    try:
        # Test with error handling
        health = client.health_check()
        print(f"Service healthy: {health['status']}")
        
        # Upload and query
        docs = ["Test document for production client."]
        upload_result = client.upload_documents(docs)
        
        query_result = client.query("What is this test about?")
        print(f"Query result: {query_result.answer}")
        
        # Print metrics
        print(f"Client metrics: {client.get_client_metrics()}")
        
    except Exception as e:
        logging.error(f"Client operation failed: {e}")
    finally:
        client.close()
```

## Integration Patterns

### 1. Document Processing Pipeline

```python
import os
import asyncio
from pathlib import Path
from typing import List, Iterator
import aiofiles

class DocumentProcessor:
    """Process documents through LightRAG pipeline."""
    
    def __init__(self, client: AsyncLightRAGClient):
        self.client = client
        self.batch_size = 50  # Process documents in batches
    
    async def process_directory(self, directory: Path, pattern: str = "*.txt") -> Dict[str, Any]:
        """Process all documents in a directory."""
        files = list(directory.glob(pattern))
        
        results = {
            "files_processed": 0,
            "total_documents": 0,
            "errors": []
        }
        
        for batch in self._batch_files(files, self.batch_size):
            try:
                documents = await self._load_files(batch)
                upload_result = await self.client.upload_documents(documents)
                
                results["files_processed"] += len(batch)
                results["total_documents"] += upload_result["documents_processed"]
                
            except Exception as e:
                error_info = {
                    "files": [str(f) for f in batch],
                    "error": str(e)
                }
                results["errors"].append(error_info)
        
        return results
    
    def _batch_files(self, files: List[Path], batch_size: int) -> Iterator[List[Path]]:
        """Split files into batches."""
        for i in range(0, len(files), batch_size):
            yield files[i:i + batch_size]
    
    async def _load_files(self, files: List[Path]) -> List[str]:
        """Load file contents asynchronously."""
        documents = []
        
        for file_path in files:
            try:
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    documents.append(content)
            except Exception as e:
                # Log error but continue processing
                print(f"Error loading {file_path}: {e}")
        
        return documents

# Usage
async def main():
    async with AsyncLightRAGClient() as client:
        processor = DocumentProcessor(client)
        
        # Process documents
        data_dir = Path("./documents")
        results = await processor.process_directory(data_dir, "*.txt")
        
        print(f"Processed {results['files_processed']} files")
        print(f"Total documents: {results['total_documents']}")
        
        if results['errors']:
            print(f"Errors encountered: {len(results['errors'])}")

asyncio.run(main())
```

### 2. Question-Answering Service

```python
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import json
from datetime import datetime

@dataclass
class QASession:
    """Question-answering session with context."""
    session_id: str
    context: List[Dict[str, Any]]
    created_at: datetime
    last_activity: datetime

class QAService:
    """Question-answering service with session management."""
    
    def __init__(self, client: LightRAGClient):
        self.client = client
        self.sessions: Dict[str, QASession] = {}
    
    def create_session(self, session_id: str) -> QASession:
        """Create a new Q&A session."""
        session = QASession(
            session_id=session_id,
            context=[],
            created_at=datetime.now(),
            last_activity=datetime.now()
        )
        self.sessions[session_id] = session
        return session
    
    def ask_question(self, 
                    session_id: str, 
                    question: str, 
                    mode: str = "hybrid",
                    include_context: bool = True) -> Dict[str, Any]:
        """Ask a question with session context."""
        
        # Get or create session
        if session_id not in self.sessions:
            self.create_session(session_id)
        
        session = self.sessions[session_id]
        
        # Add context to question if enabled
        contextual_question = question
        if include_context and session.context:
            context_text = self._format_context(session.context[-3:])  # Last 3 exchanges
            contextual_question = f"Context: {context_text}\n\nQuestion: {question}"
        
        # Query the service
        try:
            result = self.client.query(contextual_question, mode=mode)
            
            # Update session
            session.context.append({
                "question": question,
                "answer": result.answer,
                "mode": mode,
                "timestamp": datetime.now().isoformat(),
                "sources": result.sources
            })
            session.last_activity = datetime.now()
            
            return {
                "session_id": session_id,
                "question": question,
                "answer": result.answer,
                "mode": result.mode,
                "context_used": include_context,
                "processing_time": result.processing_time,
                "sources": result.sources
            }
            
        except Exception as e:
            return {
                "session_id": session_id,
                "question": question,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _format_context(self, context: List[Dict]) -> str:
        """Format context for inclusion in questions."""
        formatted = []
        for item in context:
            formatted.append(f"Q: {item['question']}\nA: {item['answer']}")
        return "\n\n".join(formatted)
    
    def get_session_history(self, session_id: str) -> Optional[List[Dict]]:
        """Get session conversation history."""
        if session_id in self.sessions:
            return self.sessions[session_id].context
        return None
    
    def export_session(self, session_id: str, format: str = "json") -> Optional[str]:
        """Export session data."""
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        data = {
            "session_id": session_id,
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat(),
            "context": session.context
        }
        
        if format == "json":
            return json.dumps(data, indent=2)
        elif format == "markdown":
            return self._export_markdown(data)
        
        return None
    
    def _export_markdown(self, data: Dict) -> str:
        """Export session as markdown."""
        lines = [
            f"# Q&A Session: {data['session_id']}",
            f"**Created:** {data['created_at']}",
            f"**Last Activity:** {data['last_activity']}",
            "",
            "## Conversation",
            ""
        ]
        
        for i, item in enumerate(data['context'], 1):
            lines.extend([
                f"### Exchange {i}",
                f"**Question:** {item['question']}",
                f"**Answer:** {item['answer']}",
                f"**Mode:** {item['mode']}",
                f"**Timestamp:** {item['timestamp']}",
                ""
            ])
        
        return "\n".join(lines)

# Usage example
if __name__ == "__main__":
    client = LightRAGClient()
    qa_service = QAService(client)
    
    try:
        # Create session and ask questions
        session_id = "user_123_session"
        
        # First question
        result1 = qa_service.ask_question(session_id, "What is machine learning?")
        print(f"Answer 1: {result1['answer']}")
        
        # Follow-up question with context
        result2 = qa_service.ask_question(session_id, "How is it different from traditional programming?")
        print(f"Answer 2: {result2['answer']}")
        
        # Export session
        export_data = qa_service.export_session(session_id, "markdown")
        with open(f"{session_id}_export.md", "w") as f:
            f.write(export_data)
        
    finally:
        client.close()
```

## Testing Approaches

### 1. Unit Tests for Client Code

```python
import pytest
import requests_mock
from unittest.mock import Mock, patch
from datetime import datetime

class TestLightRAGClient:
    """Unit tests for LightRAG client."""
    
    @pytest.fixture
    def client(self):
        """Create client instance for testing."""
        return LightRAGClient("http://test-server:9000")
    
    @pytest.fixture
    def mock_health_response(self):
        """Mock health check response."""
        return {
            "status": "healthy",
            "timestamp": "2025-01-08T12:00:00Z",
            "version": "1.0.0",
            "uptime": 3600.0
        }
    
    @pytest.fixture
    def mock_query_response(self):
        """Mock query response."""
        return {
            "success": True,
            "answer": "Python is a versatile programming language used for web development, data science, and automation.",
            "mode": "hybrid",
            "processing_time": 1.5,
            "timestamp": "2025-01-08T12:00:00Z",
            "sources": [{"text": "Python documentation", "score": 0.95}]
        }
    
    def test_health_check_success(self, client, mock_health_response):
        """Test successful health check."""
        with requests_mock.Mocker() as m:
            m.get("http://test-server:9000/health", json=mock_health_response)
            
            result = client.health_check()
            
            assert result["status"] == "healthy"
            assert result["version"] == "1.0.0"
    
    def test_health_check_failure(self, client):
        """Test health check failure handling."""
        with requests_mock.Mocker() as m:
            m.get("http://test-server:9000/health", status_code=503)
            
            with pytest.raises(requests.HTTPError):
                client.health_check()
    
    def test_upload_documents_success(self, client):
        """Test successful document upload."""
        mock_response = {
            "success": True,
            "message": "Documents processed successfully",
            "documents_processed": 2,
            "processing_time": 5.2,
            "timestamp": "2025-01-08T12:00:00Z"
        }
        
        with requests_mock.Mocker() as m:
            m.post("http://test-server:9000/documents", json=mock_response)
            
            documents = ["Doc 1", "Doc 2"]
            result = client.upload_documents(documents)
            
            assert result["success"] is True
            assert result["documents_processed"] == 2
    
    def test_query_success(self, client, mock_query_response):
        """Test successful query."""
        with requests_mock.Mocker() as m:
            m.post("http://test-server:9000/query", json=mock_query_response)
            
            result = client.query("What is Python?", mode="hybrid")
            
            assert result.success is True
            assert result.mode == "hybrid"
            assert "versatile programming language" in result.answer
            assert result.sources is not None
    
    def test_query_with_options(self, client, mock_query_response):
        """Test query with additional options."""
        with requests_mock.Mocker() as m:
            m.post("http://test-server:9000/query", json=mock_query_response)
            
            result = client.query(
                "What is Python?",
                mode="local",
                top_k=5,
                include_sources=True
            )
            
            # Verify request payload
            request = m.last_request
            payload = request.json()
            
            assert payload["question"] == "What is Python?"
            assert payload["mode"] == "local"
            assert payload["top_k"] == 5
            assert payload["include_sources"] is True

# Integration test with real service
@pytest.mark.integration
class TestLightRAGIntegration:
    """Integration tests with actual service."""
    
    @pytest.fixture(scope="class")
    def client(self):
        """Create client for integration tests."""
        client = LightRAGClient()
        yield client
        client.close()
    
    def test_service_connectivity(self, client):
        """Test basic service connectivity."""
        try:
            health = client.health_check()
            assert health["status"] in ["healthy", "degraded"]
        except requests.exceptions.ConnectionError:
            pytest.skip("LightRAG service not available")
    
    def test_full_workflow(self, client):
        """Test complete workflow: upload -> query."""
        try:
            # Upload test document
            test_docs = ["Integration test document about machine learning algorithms."]
            upload_result = client.upload_documents(test_docs)
            assert upload_result["success"] is True
            
            # Wait for processing
            import time
            time.sleep(2)
            
            # Query
            query_result = client.query("What is this test about?")
            assert query_result.success is True
            assert len(query_result.answer) > 0
            
        except requests.exceptions.ConnectionError:
            pytest.skip("LightRAG service not available")

# Performance tests
@pytest.mark.performance
class TestPerformance:
    """Performance and load tests."""
    
    def test_concurrent_queries(self):
        """Test concurrent query performance."""
        import asyncio
        import time
        
        async def run_concurrent_test():
            async with AsyncLightRAGClient() as client:
                questions = [f"Test question {i}" for i in range(10)]
                
                start_time = time.time()
                results = await client.query_batch(questions)
                end_time = time.time()
                
                # Verify all queries succeeded
                assert len(results) == 10
                assert all(r.success for r in results)
                
                # Check performance
                total_time = end_time - start_time
                avg_time = total_time / len(questions)
                
                print(f"Concurrent queries: {total_time:.2f}s total, {avg_time:.2f}s average")
                
                # Performance assertions
                assert total_time < 30  # Should complete within 30 seconds
                assert avg_time < 5    # Average under 5 seconds per query
        
        try:
            asyncio.run(run_concurrent_test())
        except Exception:
            pytest.skip("Performance test requires running service")
```

### 2. End-to-End Testing

```python
import pytest
import tempfile
import shutil
from pathlib import Path
import json

@pytest.mark.e2e
class TestEndToEnd:
    """End-to-end testing scenarios."""
    
    @pytest.fixture
    def test_data_dir(self):
        """Create temporary directory with test documents."""
        temp_dir = Path(tempfile.mkdtemp())
        
        # Create test documents
        docs = {
            "ai_basics.txt": "Artificial Intelligence (AI) is the simulation of human intelligence in machines.",
            "ml_overview.txt": "Machine Learning is a subset of AI that focuses on algorithms that improve through experience.",
            "dl_intro.txt": "Deep Learning uses neural networks with multiple layers to model complex patterns."
        }
        
        for filename, content in docs.items():
            (temp_dir / filename).write_text(content)
        
        yield temp_dir
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def qa_scenarios(self):
        """Define Q&A test scenarios."""
        return [
            {
                "question": "What is Artificial Intelligence?",
                "expected_keywords": ["artificial", "intelligence", "simulation", "machines"],
                "mode": "hybrid"
            },
            {
                "question": "How does machine learning work?",
                "expected_keywords": ["machine", "learning", "algorithms", "experience"],
                "mode": "local"
            },
            {
                "question": "What is deep learning?",
                "expected_keywords": ["deep", "learning", "neural", "networks"],
                "mode": "global"
            }
        ]
    
    def test_document_upload_and_query_workflow(self, test_data_dir, qa_scenarios):
        """Test complete document processing workflow."""
        client = LightRAGClient()
        
        try:
            # Step 1: Verify service health
            health = client.health_check()
            assert health["status"] == "healthy"
            
            # Step 2: Load and upload documents
            documents = []
            for file_path in test_data_dir.glob("*.txt"):
                content = file_path.read_text()
                documents.append(content)
            
            upload_result = client.upload_documents(documents)
            assert upload_result["success"] is True
            assert upload_result["documents_processed"] == len(documents)
            
            # Step 3: Wait for processing to complete
            import time
            time.sleep(5)  # Allow time for indexing
            
            # Step 4: Test various query scenarios
            for scenario in qa_scenarios:
                result = client.query(
                    scenario["question"],
                    mode=scenario["mode"]
                )
                
                assert result.success is True
                assert len(result.answer) > 0
                
                # Check for expected keywords in answer
                answer_lower = result.answer.lower()
                keyword_matches = sum(1 for keyword in scenario["expected_keywords"] 
                                    if keyword in answer_lower)
                
                # At least half the keywords should be present
                assert keyword_matches >= len(scenario["expected_keywords"]) / 2
            
            # Step 5: Test knowledge graph retrieval
            graph = client.get_graph()
            assert "nodes" in graph
            assert "edges" in graph
            assert len(graph["nodes"]) > 0
            
        except requests.exceptions.ConnectionError:
            pytest.skip("LightRAG service not available for E2E testing")
        finally:
            client.close()
    
    def test_api_error_scenarios(self):
        """Test various error scenarios."""
        client = LightRAGClient()
        
        try:
            # Test empty document list
            with pytest.raises(requests.HTTPError):
                client.upload_documents([])
            
            # Test empty question
            with pytest.raises(requests.HTTPError):
                client.query("")
            
            # Test invalid mode
            with pytest.raises(requests.HTTPError):
                client.query("Test question", mode="invalid_mode")
            
            # Test oversized document
            large_doc = "x" * (2 * 1024 * 1024)  # 2MB document
            with pytest.raises(requests.HTTPError):
                client.upload_documents([large_doc])
            
        except requests.exceptions.ConnectionError:
            pytest.skip("LightRAG service not available for error testing")
        finally:
            client.close()
```

### 3. Test Configuration

Create a `pytest.ini` file:

```ini
[tool:pytest]
markers =
    unit: Unit tests (fast, no external dependencies)
    integration: Integration tests (require running services)
    e2e: End-to-end tests (full workflow testing)
    performance: Performance and load tests
    slow: Tests that take more than 5 seconds

testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Test output
addopts = 
    --verbose
    --strict-markers
    --disable-warnings
    --tb=short

# Coverage reporting
addopts = 
    --cov=src
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80

# Timeout for tests
timeout = 300

# Parallel execution
addopts = -n auto

filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
```

Run tests with different markers:

```bash
# Run only unit tests (fast)
pytest -m unit

# Run integration tests (requires services)
pytest -m integration

# Run end-to-end tests
pytest -m e2e

# Run performance tests
pytest -m performance

# Run all tests except slow ones
pytest -m "not slow"

# Run with coverage
pytest --cov=src --cov-report=html
```

## Error Handling

### Common Error Scenarios

```python
import requests
from typing import Dict, Any, Optional
import logging

class LightRAGError(Exception):
    """Base exception for LightRAG client errors."""
    pass

class ServiceUnavailableError(LightRAGError):
    """Service is unavailable or unhealthy."""
    pass

class RateLimitError(LightRAGError):
    """Rate limit exceeded."""
    pass

class DocumentTooLargeError(LightRAGError):
    """Document exceeds size limits."""
    pass

class InvalidQueryError(LightRAGError):
    """Query is invalid or malformed."""
    pass

def handle_api_error(response: requests.Response) -> None:
    """Handle API errors and raise appropriate exceptions."""
    if response.status_code == 429:
        raise RateLimitError(f"Rate limit exceeded: {response.text}")
    elif response.status_code == 413:
        raise DocumentTooLargeError(f"Document too large: {response.text}")
    elif response.status_code == 422:
        raise InvalidQueryError(f"Invalid request: {response.text}")
    elif response.status_code >= 500:
        raise ServiceUnavailableError(f"Service error: {response.text}")
    else:
        response.raise_for_status()

class RobustLightRAGClient:
    """Client with comprehensive error handling."""
    
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.logger = logging.getLogger(__name__)
        
        if api_key:
            self.session.headers.update({"Authorization": f"Bearer {api_key}"})
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make request with error handling."""
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.request(method, url, **kwargs)
            handle_api_error(response)
            return response.json()
            
        except requests.exceptions.ConnectionError:
            self.logger.error(f"Failed to connect to {url}")
            raise ServiceUnavailableError(f"Cannot connect to LightRAG service at {url}")
        
        except requests.exceptions.Timeout:
            self.logger.error(f"Request to {url} timed out")
            raise ServiceUnavailableError(f"Request to {url} timed out")
        
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTP error for {url}: {e}")
            raise
        
        except Exception as e:
            self.logger.error(f"Unexpected error for {url}: {e}")
            raise LightRAGError(f"Unexpected error: {e}")
    
    def health_check(self) -> Dict[str, Any]:
        """Health check with error handling."""
        try:
            return self._make_request("GET", "/health")
        except ServiceUnavailableError:
            return {"status": "unhealthy", "error": "Service unavailable"}
    
    def query_with_fallback(self, question: str, modes: List[str] = None) -> Optional[QueryResult]:
        """Query with fallback modes if primary mode fails."""
        if modes is None:
            modes = ["hybrid", "local", "global", "naive"]
        
        last_error = None
        
        for mode in modes:
            try:
                result = self.query(question, mode=mode)
                self.logger.info(f"Query successful with mode: {mode}")
                return result
                
            except Exception as e:
                self.logger.warning(f"Query failed with mode {mode}: {e}")
                last_error = e
                continue
        
        # All modes failed
        self.logger.error(f"All query modes failed for question: {question}")
        if last_error:
            raise last_error
        
        return None

# Usage with error handling
def safe_query_example():
    """Example of safe querying with error handling."""
    client = RobustLightRAGClient("http://localhost:9000")
    
    try:
        # Check health first
        health = client.health_check()
        if health.get("status") != "healthy":
            print(f"Service is not healthy: {health}")
            return
        
        # Try query with fallback
        result = client.query_with_fallback("What is machine learning?")
        
        if result:
            print(f"Answer: {result.answer}")
        else:
            print("Failed to get answer from service")
            
    except RateLimitError:
        print("Rate limit exceeded. Please wait before making more requests.")
    except DocumentTooLargeError:
        print("Document is too large. Please split into smaller chunks.")
    except ServiceUnavailableError:
        print("Service is currently unavailable. Please try again later.")
    except LightRAGError as e:
        print(f"LightRAG client error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    safe_query_example()
```

## Performance Considerations

### 1. Connection Pooling

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager

class OptimizedLightRAGClient:
    """Client optimized for high-throughput scenarios."""
    
    def __init__(self, base_url: str, pool_size: int = 10, max_retries: int = 3):
        self.base_url = base_url.rstrip('/')
        
        # Configure session with connection pooling
        self.session = requests.Session()
        
        # Custom adapter with larger connection pool
        adapter = HTTPAdapter(
            pool_connections=pool_size,
            pool_maxsize=pool_size * 2,
            max_retries=max_retries,
            pool_block=False
        )
        
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Keep connections alive
        self.session.headers.update({"Connection": "keep-alive"})
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def close(self):
        """Close session and cleanup connections."""
        self.session.close()

# Usage for high-throughput scenarios
def high_throughput_example():
    """Example of processing many documents efficiently."""
    
    with OptimizedLightRAGClient("http://localhost:9000", pool_size=20) as client:
        # Process large number of documents
        documents = [f"Document {i}" for i in range(1000)]
        
        # Process in batches to avoid memory issues
        batch_size = 50
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            
            try:
                result = client.upload_documents(batch)
                print(f"Processed batch {i//batch_size + 1}: {result['documents_processed']} documents")
            except Exception as e:
                print(f"Error processing batch {i//batch_size + 1}: {e}")
```

### 2. Async Batch Processing

```python
import asyncio
import aiohttp
from typing import List, Dict, Any
import time

class AsyncBatchProcessor:
    """Async processor for high-volume operations."""
    
    def __init__(self, base_url: str, max_concurrent: int = 10):
        self.base_url = base_url.rstrip('/')
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        connector = aiohttp.TCPConnector(
            limit=100,  # Total connection pool size
            limit_per_host=30,  # Connections per host
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
        
        timeout = aiohttp.ClientTimeout(total=300, connect=10)
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            raise_for_status=True
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def upload_batch(self, documents: List[str]) -> Dict[str, Any]:
        """Upload a batch of documents with concurrency control."""
        async with self.semaphore:
            payload = {"documents": documents}
            async with self.session.post(f"{self.base_url}/documents", json=payload) as response:
                return await response.json()
    
    async def query_batch(self, questions: List[str], mode: str = "hybrid") -> List[Dict[str, Any]]:
        """Process multiple queries concurrently."""
        tasks = []
        
        for question in questions:
            task = self.query_single(question, mode)
            tasks.append(task)
        
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    async def query_single(self, question: str, mode: str) -> Dict[str, Any]:
        """Query single question with concurrency control."""
        async with self.semaphore:
            payload = {"question": question, "mode": mode}
            async with self.session.post(f"{self.base_url}/query", json=payload) as response:
                return await response.json()
    
    async def process_document_batches(self, all_documents: List[str], batch_size: int = 50) -> List[Dict[str, Any]]:
        """Process documents in batches efficiently."""
        batches = [all_documents[i:i + batch_size] for i in range(0, len(all_documents), batch_size)]
        
        tasks = []
        for batch in batches:
            task = self.upload_batch(batch)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results

# Performance monitoring
class PerformanceMonitor:
    """Monitor client performance metrics."""
    
    def __init__(self):
        self.start_time = time.time()
        self.request_count = 0
        self.error_count = 0
        self.total_response_time = 0.0
    
    def record_request(self, response_time: float, success: bool = True):
        """Record request metrics."""
        self.request_count += 1
        self.total_response_time += response_time
        if not success:
            self.error_count += 1
    
    def get_metrics(self) -> Dict[str, float]:
        """Get performance metrics."""
        elapsed = time.time() - self.start_time
        
        return {
            "duration": elapsed,
            "requests_total": self.request_count,
            "requests_per_second": self.request_count / max(elapsed, 0.001),
            "average_response_time": self.total_response_time / max(self.request_count, 1),
            "error_rate": self.error_count / max(self.request_count, 1),
            "errors_total": self.error_count
        }

# Usage example
async def performance_test():
    """Performance test with monitoring."""
    monitor = PerformanceMonitor()
    
    async with AsyncBatchProcessor("http://localhost:9000", max_concurrent=20) as processor:
        # Test document upload performance
        documents = [f"Performance test document {i}" for i in range(500)]
        
        start_time = time.time()
        results = await processor.process_document_batches(documents, batch_size=25)
        upload_time = time.time() - start_time
        
        successful_uploads = sum(1 for r in results if not isinstance(r, Exception))
        print(f"Uploaded {successful_uploads} batches in {upload_time:.2f}s")
        
        # Test query performance
        questions = [f"What is test question {i}?" for i in range(100)]
        
        start_time = time.time()
        query_results = await processor.query_batch(questions)
        query_time = time.time() - start_time
        
        successful_queries = sum(1 for r in query_results if not isinstance(r, Exception))
        print(f"Processed {successful_queries} queries in {query_time:.2f}s")
        print(f"Average query time: {query_time/len(questions):.3f}s")

if __name__ == "__main__":
    asyncio.run(performance_test())
```

## Security

### 1. API Key Management

```python
import os
from typing import Optional
from cryptography.fernet import Fernet
import keyring
import getpass

class SecureAPIKeyManager:
    """Secure API key management."""
    
    def __init__(self, service_name: str = "lightrag_client"):
        self.service_name = service_name
        self.username = "api_key"
    
    def store_api_key(self, api_key: str) -> None:
        """Store API key securely in system keyring."""
        try:
            keyring.set_password(self.service_name, self.username, api_key)
            print("API key stored securely")
        except Exception as e:
            print(f"Failed to store API key: {e}")
    
    def get_api_key(self) -> Optional[str]:
        """Retrieve API key from secure storage."""
        # Try keyring first
        try:
            key = keyring.get_password(self.service_name, self.username)
            if key:
                return key
        except Exception:
            pass
        
        # Fallback to environment variable
        key = os.getenv("LIGHTRAG_API_KEY")
        if key:
            return key
        
        # Fallback to user input
        return getpass.getpass("Enter LightRAG API key: ")
    
    def delete_api_key(self) -> None:
        """Delete stored API key."""
        try:
            keyring.delete_password(self.service_name, self.username)
            print("API key deleted")
        except Exception as e:
            print(f"Failed to delete API key: {e}")

class EncryptedConfigManager:
    """Manage encrypted configuration files."""
    
    def __init__(self, config_file: str = ".lightrag_config.enc"):
        self.config_file = config_file
        self.key = self._get_or_create_key()
        self.cipher = Fernet(self.key)
    
    def _get_or_create_key(self) -> bytes:
        """Get or create encryption key."""
        key_file = ".lightrag_key"
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            os.chmod(key_file, 0o600)  # Owner read/write only
            return key
    
    def save_config(self, config: Dict[str, Any]) -> None:
        """Save encrypted configuration."""
        import json
        
        config_json = json.dumps(config)
        encrypted_data = self.cipher.encrypt(config_json.encode())
        
        with open(self.config_file, 'wb') as f:
            f.write(encrypted_data)
        
        os.chmod(self.config_file, 0o600)  # Owner read/write only
    
    def load_config(self) -> Dict[str, Any]:
        """Load and decrypt configuration."""
        import json
        
        if not os.path.exists(self.config_file):
            return {}
        
        with open(self.config_file, 'rb') as f:
            encrypted_data = f.read()
        
        decrypted_data = self.cipher.decrypt(encrypted_data)
        return json.loads(decrypted_data.decode())

# Usage
def setup_secure_client():
    """Setup client with secure credential management."""
    key_manager = SecureAPIKeyManager()
    config_manager = EncryptedConfigManager()
    
    # Get API key securely
    api_key = key_manager.get_api_key()
    
    # Load secure configuration
    config = config_manager.load_config()
    
    # Create client
    client = LightRAGClient(
        base_url=config.get("api_url", "http://localhost:9000"),
        api_key=api_key
    )
    
    return client
```

### 2. TLS/SSL Configuration

```python
import ssl
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

class SecureLightRAGClient:
    """Client with enhanced security features."""
    
    def __init__(self, 
                 base_url: str,
                 api_key: Optional[str] = None,
                 verify_ssl: bool = True,
                 client_cert: Optional[str] = None,
                 client_key: Optional[str] = None):
        
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        
        # Configure SSL/TLS
        if verify_ssl:
            self.session.verify = True
            
            # Custom SSL context for enhanced security
            ssl_context = create_urllib3_context()
            ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
            ssl_context.maximum_version = ssl.TLSVersion.TLSv1_3
            
            adapter = HTTPAdapter()
            adapter.init_poolmanager(ssl_context=ssl_context)
            
            self.session.mount("https://", adapter)
        else:
            self.session.verify = False
            # Disable SSL warnings for development
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Client certificate authentication
        if client_cert and client_key:
            self.session.cert = (client_cert, client_key)
        
        # API key authentication
        if api_key:
            # Use secure header
            self.session.headers.update({
                "Authorization": f"Bearer {api_key}",
                "User-Agent": "LightRAG-Client/1.0"
            })
        
        # Security headers
        self.session.headers.update({
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json",
            "Content-Type": "application/json"
        })
    
    def _validate_response(self, response: requests.Response) -> None:
        """Validate response security headers."""
        security_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options", 
            "X-XSS-Protection",
            "Strict-Transport-Security"
        ]
        
        missing_headers = [h for h in security_headers if h not in response.headers]
        if missing_headers:
            self.logger.warning(f"Missing security headers: {missing_headers}")
```

## Troubleshooting

### Common Issues and Solutions

| Issue | Symptoms | Solution |
|-------|----------|----------|
| Connection Refused | `ConnectionError: [Errno 111] Connection refused` | Check if service is running: `curl http://localhost:9000/health` |
| Timeout Errors | Requests hanging or timing out | Increase timeout values, check network latency |
| Rate Limiting | HTTP 429 responses | Implement exponential backoff, check rate limits |
| Large Documents | HTTP 413 or 422 errors | Split documents into smaller chunks |
| Authentication | HTTP 401/403 errors | Verify API key is correct and not expired |
| SSL Errors | SSL certificate verification failed | Check certificates or disable SSL verification for development |

### Diagnostic Tools

```python
import requests
import time
from typing import Dict, Any

class LightRAGDiagnostics:
    """Diagnostic tools for troubleshooting."""
    
    def __init__(self, base_url: str = "http://localhost:9000"):
        self.base_url = base_url.rstrip('/')
    
    def comprehensive_health_check(self) -> Dict[str, Any]:
        """Comprehensive health check with diagnostics."""
        results = {
            "timestamp": time.time(),
            "base_url": self.base_url,
            "tests": {}
        }
        
        # Basic connectivity
        try:
            start_time = time.time()
            response = requests.get(f"{self.base_url}/health", timeout=10)
            response_time = time.time() - start_time
            
            results["tests"]["connectivity"] = {
                "status": "pass",
                "response_time": response_time,
                "status_code": response.status_code,
                "response": response.json()
            }
        except Exception as e:
            results["tests"]["connectivity"] = {
                "status": "fail",
                "error": str(e)
            }
        
        # Readiness check
        try:
            response = requests.get(f"{self.base_url}/health/ready", timeout=10)
            results["tests"]["readiness"] = {
                "status": "pass",
                "status_code": response.status_code,
                "response": response.json()
            }
        except Exception as e:
            results["tests"]["readiness"] = {
                "status": "fail",
                "error": str(e)
            }
        
        # API info
        try:
            response = requests.get(f"{self.base_url}/", timeout=10)
            results["tests"]["api_info"] = {
                "status": "pass",
                "response": response.json()
            }
        except Exception as e:
            results["tests"]["api_info"] = {
                "status": "fail",
                "error": str(e)
            }
        
        return results
    
    def test_document_pipeline(self) -> Dict[str, Any]:
        """Test the complete document processing pipeline."""
        results = {"tests": {}}
        
        # Test document upload
        test_doc = "This is a test document for diagnostic purposes."
        
        try:
            response = requests.post(
                f"{self.base_url}/documents",
                json={"documents": [test_doc]},
                timeout=30
            )
            results["tests"]["document_upload"] = {
                "status": "pass",
                "response": response.json()
            }
        except Exception as e:
            results["tests"]["document_upload"] = {
                "status": "fail",
                "error": str(e)
            }
            return results
        
        # Wait and test query
        time.sleep(2)
        
        try:
            response = requests.post(
                f"{self.base_url}/query",
                json={"question": "What is this test about?", "mode": "hybrid"},
                timeout=60
            )
            results["tests"]["query"] = {
                "status": "pass",
                "response": response.json()
            }
        except Exception as e:
            results["tests"]["query"] = {
                "status": "fail",
                "error": str(e)
            }
        
        return results
    
    def network_diagnostics(self) -> Dict[str, Any]:
        """Network connectivity diagnostics."""
        import socket
        from urllib.parse import urlparse
        
        parsed = urlparse(self.base_url)
        host = parsed.hostname
        port = parsed.port or (80 if parsed.scheme == 'http' else 443)
        
        results = {
            "host": host,
            "port": port,
            "tests": {}
        }
        
        # DNS resolution
        try:
            ip = socket.gethostbyname(host)
            results["tests"]["dns_resolution"] = {
                "status": "pass",
                "ip_address": ip
            }
        except Exception as e:
            results["tests"]["dns_resolution"] = {
                "status": "fail",
                "error": str(e)
            }
        
        # Port connectivity
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                results["tests"]["port_connectivity"] = {"status": "pass"}
            else:
                results["tests"]["port_connectivity"] = {
                    "status": "fail",
                    "error": f"Port {port} is not accessible"
                }
        except Exception as e:
            results["tests"]["port_connectivity"] = {
                "status": "fail",
                "error": str(e)
            }
        
        return results

# CLI diagnostic tool
def run_diagnostics():
    """Run comprehensive diagnostics."""
    import json
    
    diagnostics = LightRAGDiagnostics()
    
    print("=== LightRAG Client Diagnostics ===\n")
    
    # Network diagnostics
    print("1. Network Diagnostics")
    network_results = diagnostics.network_diagnostics()
    for test_name, result in network_results["tests"].items():
        status = "✓" if result["status"] == "pass" else "✗"
        print(f"   {status} {test_name.replace('_', ' ').title()}")
        if result["status"] == "fail":
            print(f"     Error: {result['error']}")
    print()
    
    # Health check
    print("2. Service Health Check")
    health_results = diagnostics.comprehensive_health_check()
    for test_name, result in health_results["tests"].items():
        status = "✓" if result["status"] == "pass" else "✗"
        print(f"   {status} {test_name.replace('_', ' ').title()}")
        if result["status"] == "fail":
            print(f"     Error: {result['error']}")
    print()
    
    # Pipeline test
    print("3. Document Pipeline Test")
    pipeline_results = diagnostics.test_document_pipeline()
    for test_name, result in pipeline_results["tests"].items():
        status = "✓" if result["status"] == "pass" else "✗"
        print(f"   {status} {test_name.replace('_', ' ').title()}")
        if result["status"] == "fail":
            print(f"     Error: {result['error']}")
    
    # Save detailed results
    all_results = {
        "network": network_results,
        "health": health_results,
        "pipeline": pipeline_results
    }
    
    with open("lightrag_diagnostics.json", "w") as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\nDetailed results saved to: lightrag_diagnostics.json")

if __name__ == "__main__":
    run_diagnostics()
```

### Debug Configuration

```python
import logging
import sys
from typing import Optional

def setup_debug_logging(level: str = "DEBUG", 
                       log_file: Optional[str] = None,
                       include_requests: bool = True):
    """Setup debug logging for troubleshooting."""
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            *(logging.FileHandler(log_file) if log_file else [])
        ]
    )
    
    # Enable HTTP debug logging
    if include_requests:
        import http.client as http_client
        http_client.HTTPConnection.debuglevel = 1
        
        logging.getLogger("urllib3.connectionpool").setLevel(logging.DEBUG)
        logging.getLogger("requests.packages.urllib3").setLevel(logging.DEBUG)

# Usage for debugging
def debug_client_example():
    """Example with debug logging enabled."""
    setup_debug_logging(level="DEBUG", log_file="lightrag_debug.log")
    
    client = LightRAGClient()
    
    try:
        # This will log all HTTP traffic
        health = client.health_check()
        print(f"Health: {health}")
        
    except Exception as e:
        logging.exception("Client operation failed")
    finally:
        client.close()

if __name__ == "__main__":
    debug_client_example()
```

This comprehensive guide provides everything needed to integrate with the LightRAG service from remote client applications, including examples, testing strategies, error handling, performance optimization, and troubleshooting tools.
