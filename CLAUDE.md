# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a RAG (Retrieval-Augmented Generation) ecosystem implementation project that aims to build a production-ready document processing and question-answering system. The project uses Docker-based microservices architecture with GPU acceleration for LLM inference.

## Architecture Components

The system consists of the following key services:
- **Qdrant**: Vector database for embedding storage and similarity search
- **Ollama**: LLM inference service supporting Llama 3.3 70B and Qwen 2.5 models
- **LightRAG**: Core RAG framework with knowledge graph capabilities
- **Docling**: Document parsing service for PDF, DOCX, HTML, and Markdown
- **Redis**: Queue system for async document processing
- **Prometheus/Grafana**: Monitoring and metrics visualization
- **NGINX**: API gateway and reverse proxy

## Development Commands

Since this is a new project without implemented code yet, here are the expected commands based on the planned architecture:

### Docker Services
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f [service-name]

# Stop services
docker-compose down

# Rebuild specific service
docker-compose build [service-name]
```

### Model Management (Ollama)
```bash
# Pull primary model
docker exec ollama ollama pull llama3.3:70b-instruct-q4_K_M

# Pull backup model
docker exec ollama ollama pull qwen2.5-coder:32b-instruct-q4_K_M

# List models
docker exec ollama ollama list
```

### Testing
```bash
# Run integration tests (once implemented)
python -m pytest tests/integration/

# Run performance tests
python -m pytest tests/performance/

# Test specific service
python -m pytest tests/integration/test_[service].py
```

## Project Structure

The planned repository structure follows a microservices pattern:
- `services/`: Individual service implementations
- `configs/`: Service configuration files
- `scripts/`: Deployment and maintenance scripts
- `tests/`: Integration and performance tests
- `docs/`: Architecture and deployment documentation

## Implementation Phases

The project follows a phased approach as detailed in `todo.md`:
1. **Phase 1**: Core infrastructure (Weeks 1-2) - Basic RAG pipeline
2. **Phase 2**: Production features (Weeks 3-4) - Async processing, monitoring
3. **Phase 3**: Advanced features (Weeks 5-6) - Multi-agent system, hybrid search
4. **Phase 4**: Multimodal & Scaling (Weeks 7-8) - Audio/image support, horizontal scaling

## Key Technical Decisions

- **GPU Requirements**: 24GB VRAM for running Llama 3.3 70B quantized model
- **Vector Dimensions**: Will be determined by the embedding model (likely 1024-4096)
- **Async Processing**: Celery with Redis for document processing queue
- **API Framework**: FastAPI for service endpoints
- **Monitoring**: Prometheus metrics with Grafana dashboards

## Development Guidelines

When implementing features:
1. Follow the task breakdown in `todo.md` for systematic progress. Update `todo.md` with your steps and notes for each task.
2. Each service should have its own Dockerfile and be independently deployable
3. Use environment variables for configuration (12-factor app principles)
4. Implement health check endpoints for all services
5. Add comprehensive logging for debugging and monitoring
6. Write integration tests for service interactions
7. Document API endpoints using OpenAPI/Swagger
8. Update the issues faced and what has been tried and what worked in `todo.md`.

## Current Status

The project is in the planning phase with a comprehensive roadmap defined in `todo.md`. Implementation should begin with Phase 0 prerequisites and Phase 1 core infrastructure.