# LightRAG Backend Tutorial

This tutorial covers all the features of the LightRAG Backend system and how to use them.

## Quick Start

### 1. Setup and Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd llm_backend

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
```

### 2. Start Services

```bash
# Start all services with Docker Compose
docker-compose up -d

# Check services are running
docker-compose ps
```

### 3. Wait for Initialization

The system needs a few minutes to initialize:
- Ollama pulls models (qwen2.5:7b-instruct and nomic-embed-text)
- Services establish connections
- LightRAG initializes storage

Wait approximately 5-10 minutes for full initialization.

## Core Features

### 1. Document Management

#### Insert Documents via API
```bash
curl -X POST "http://localhost:9000/documents" \
  -H "Content-Type: application/json" \
  -d '{"documents": ["Your document content here"]}'
```

#### Python Example
```python
import requests

response = requests.post(
    "http://localhost:9000/documents",
    json={"documents": ["AI is transforming healthcare through machine learning."]}
)
print(response.json())
```

### 2. Querying with Different Modes

LightRAG supports 4 query modes:

#### Naive Mode (Simple search)
```bash
curl -X POST "http://localhost:9000/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is AI?", "mode": "naive"}'
```

#### Local Mode (Entity-focused)
```bash
curl -X POST "http://localhost:9000/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is AI?", "mode": "local"}'
```

#### Global Mode (Relationship-focused)
```bash
curl -X POST "http://localhost:9000/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is AI?", "mode": "global"}'
```

#### Hybrid Mode (Best of both)
```bash
curl -X POST "http://localhost:9000/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is AI?", "mode": "hybrid"}'
```

### 3. Knowledge Graph

LightRAG automatically builds a knowledge graph from your documents:
- Extracts entities and relationships
- Creates graph-based representation
- Enables sophisticated querying

```bash
# Get graph statistics
curl "http://localhost:9000/graph/stats"
```

### 4. Direct LLM Access

Access Ollama directly for custom use cases:

```python
import requests

# Generate text
response = requests.post(
    "http://localhost:12434/api/generate",
    json={
        "model": "qwen2.5:7b-instruct",
        "prompt": "Explain quantum computing",
        "stream": False
    }
)
print(response.json()['response'])

# Generate embeddings
response = requests.post(
    "http://localhost:12434/api/embeddings",
    json={
        "model": "nomic-embed-text",
        "prompt": "quantum computing"
    }
)
print(f"Embedding dimension: {len(response.json()['embedding'])}")
```

## Service Architecture

### Core Services

1. **API Service** (Port 9000)
   - FastAPI-based REST API
   - Handles document insertion and querying
   - Integrates with LightRAG

2. **Ollama** (Port 12434)
   - Local LLM server
   - Provides text generation and embeddings
   - Models: qwen2.5:7b-instruct, nomic-embed-text

3. **Qdrant** (Port 7333)
   - Vector database for embeddings
   - Enables similarity search
   - Stores document vectors

4. **Redis** (Port 7379)
   - Caching layer
   - Session storage
   - Queue management

### Monitoring Services

5. **Prometheus** (Port 10090)
   - Metrics collection
   - Performance monitoring
   - Service health tracking

6. **Grafana** (Port 4000)
   - Visualization dashboard
   - Metrics visualization
   - Service monitoring

## Advanced Usage

### 1. Using the Python Service Directly

```python
import asyncio
from src.rag.lightrag_service import LightRAGService

async def main():
    # Initialize service
    service = LightRAGService()
    await service.initialize()
    
    # Insert documents
    documents = ["Your document content here"]
    await service.insert_documents(documents)
    
    # Query with different modes
    response = await service.query("Your question", mode="hybrid")
    print(response)
    
    # Cleanup
    await service.close()

asyncio.run(main())
```

### 2. Testing All Services

Use the provided connection test script:

```bash
# Test all services
python examples/connect_to_services.py

# Test specific service
python examples/connect_to_services.py ollama
python examples/connect_to_services.py qdrant
```

### 3. Custom LightRAG Configuration

Modify service parameters:

```python
service = LightRAGService(
    working_dir="./custom_rag_data",
    llm_model="qwen2.5:32b-instruct-q4_K_M",  # Different model
    embedding_model="nomic-embed-text",
    embedding_dim=768
)
```

## Test Documents

The repository includes sample PDF documents in the `data/` directory for testing:

```python
# Example: Insert a PDF document
import PyPDF2
import requests

# Read PDF
with open('data/01_Good_Clinical_Data_Management_Practices.pdf', 'rb') as file:
    pdf_reader = PyPDF2.PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()

# Insert into RAG
response = requests.post(
    "http://localhost:9000/documents",
    json={"documents": [text[:10000]]}  # First 10k chars
)
```

## Troubleshooting

### Common Issues

1. **Services not starting**
   ```bash
   # Check Docker logs
   docker-compose logs ollama
   docker-compose logs api
   ```

2. **Model not found**
   ```bash
   # Pull models manually
   docker exec rag_ollama ollama pull qwen2.5:7b-instruct
   docker exec rag_ollama ollama pull nomic-embed-text
   ```

3. **Permission errors on data directories**
   ```bash
   # These directories are created by Docker and auto-managed
   # They're in .gitignore and will be recreated as needed
   ```

4. **API connection errors**
   - Wait 5-10 minutes for full initialization
   - Check service health: `curl http://localhost:8000/health`

### Health Checks

```bash
# API Service
curl http://localhost:9000/health

# Ollama Service
curl http://localhost:12434/api/version

# Qdrant Service
curl http://localhost:7333/health

# Redis Service
redis-cli -h localhost -p 7379 ping

# Prometheus Service
curl http://localhost:10090/-/healthy

# Grafana Service
curl http://localhost:4000/api/health
```

## Configuration

### Environment Variables

Key settings in `.env`:

```bash
# LLM Configuration
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5:7b-instruct
EMBEDDING_MODEL=nomic-embed-text

# API Configuration
API_HOST=0.0.0.0
API_PORT=9000

# Database Configuration
QDRANT_HOST=localhost
QDRANT_PORT=7333
REDIS_HOST=localhost
REDIS_PORT=7379

# Ollama Configuration
OLLAMA_HOST=http://localhost:12434
```

### Docker Compose Configuration

Main services defined in `docker-compose.yml`:
- All services with proper networking
- Volume mounts for persistence
- Health checks and dependencies

## Performance Tips

1. **Model Selection**
   - Use quantized models for better performance
   - Balance model size vs. accuracy needs

2. **Batch Operations**
   - Insert multiple documents at once
   - Use appropriate chunk sizes

3. **Query Optimization**
   - Choose appropriate query mode for use case
   - Use hybrid mode for best results

4. **Resource Management**
   - Monitor memory usage with Grafana
   - Scale services as needed

## Next Steps

- Explore the monitoring dashboard at http://localhost:4000
- Check out the LightRAG examples in `LightRAG/examples/`
- Customize the service for your specific use case
- Add authentication and authorization for production use

For more details, see:
- `ARCHITECTURE.md` - System architecture details
- `SERVICES.md` - Individual service documentation
- `DEPLOYMENT.md` - Production deployment guide