# Services Documentation

This document provides comprehensive information about all services available in the LightRAG Backend system and how to connect to them.

## Table of Contents

1. [Services Overview](#services-overview)
2. [Starting Services](#starting-services)
3. [Service Details](#service-details)
   - [API Service](#1-api-service)
   - [Ollama (LLM)](#2-ollama-llm-service)
   - [Qdrant (Vector Database)](#3-qdrant-vector-database)
   - [Redis (Cache & Queue)](#4-redis-cache--queue)
   - [Prometheus (Metrics)](#5-prometheus-metrics)
   - [Grafana (Visualization)](#6-grafana-visualization)
   - [Nginx (API Gateway)](#7-nginx-api-gateway)
4. [Service URLs Summary](#service-urls-summary)
5. [Testing Connections](#testing-connections)
6. [Troubleshooting](#troubleshooting)

## Services Overview

The system consists of 7 Docker services working together:

| Service | Purpose | Default Port | Container Name |
|---------|---------|--------------|----------------|
| API | Main REST API | 8000 | rag_api |
| Ollama | LLM & Embeddings | 11434 | rag_ollama |
| Qdrant | Vector Database | 6333, 6334 | rag_qdrant |
| Redis | Caching & Queuing | 6379 | rag_redis |
| Prometheus | Metrics Collection | 9090 | rag_prometheus |
| Grafana | Dashboards | 3000 | rag_grafana |
| Nginx | API Gateway | 80, 443 | rag_nginx |

## Starting Services

### Start All Services
```bash
# Start all services in background
docker-compose up -d

# View logs for all services
docker-compose logs -f

# View logs for specific service
docker-compose logs -f rag_api
```

### Check Service Status
```bash
# List running containers
docker ps

# Check service health
docker-compose ps

# Run automated health check
python run_tests.py
```

## Service Details

### 1. API Service

**Purpose**: Main REST API for document processing and querying

**Connection Details**:
- **URL**: http://localhost:8000
- **Container**: rag_api
- **Health Check**: http://localhost:8000/health

**Available Endpoints**:
```bash
# Service info
curl http://localhost:8000/

# Health check
curl http://localhost:8000/health

# Readiness check (detailed)
curl http://localhost:8000/health/ready

# Prometheus metrics
curl http://localhost:8000/metrics

# Insert documents
curl -X POST http://localhost:8000/documents \
  -H "Content-Type: application/json" \
  -d '{"documents": ["Your text here"]}'

# Query documents
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Your question here", "mode": "hybrid"}'

# Get knowledge graph
curl http://localhost:8000/graph
```

**API Documentation**:
- When running in development mode, visit: http://localhost:8000/api/docs

### 2. Ollama (LLM Service)

**Purpose**: Provides LLM inference and text embeddings

**Connection Details**:
- **URL**: http://localhost:11434
- **Container**: rag_ollama
- **Models**: qwen2.5:7b-instruct, nomic-embed-text

**Available Endpoints**:
```bash
# Check version
curl http://localhost:11434/api/version

# List available models
curl http://localhost:11434/api/tags

# Generate text completion
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5:7b-instruct",
    "prompt": "What is artificial intelligence?",
    "stream": false
  }'

# Generate embeddings
curl -X POST http://localhost:11434/api/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nomic-embed-text",
    "prompt": "Your text to embed"
  }'

# Chat completion
curl -X POST http://localhost:11434/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5:7b-instruct",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ]
  }'
```

**Model Management**:
```bash
# Pull a new model
docker exec rag_ollama ollama pull llama3.3:70b-instruct-q4_K_M

# List models
docker exec rag_ollama ollama list

# Remove a model
docker exec rag_ollama ollama rm model_name
```

### 3. Qdrant (Vector Database)

**Purpose**: Stores and searches vector embeddings

**Connection Details**:
- **HTTP API**: http://localhost:6333
- **gRPC API**: localhost:6334
- **Container**: rag_qdrant
- **Dashboard**: http://localhost:6333/dashboard

**Available Endpoints**:
```bash
# Health check
curl http://localhost:6333/health

# Service info
curl http://localhost:6333/

# Collections info
curl http://localhost:6333/collections

# Get specific collection
curl http://localhost:6333/collections/your_collection_name

# Metrics (Prometheus format)
curl http://localhost:6333/metrics

# Search vectors
curl -X POST http://localhost:6333/collections/your_collection/points/search \
  -H "Content-Type: application/json" \
  -d '{
    "vector": [0.1, 0.2, 0.3, ...],
    "top": 5
  }'
```

**Python Client Example**:
```python
from qdrant_client import QdrantClient

client = QdrantClient(host="localhost", port=6333)
collections = client.get_collections()
print(collections)
```

### 4. Redis (Cache & Queue)

**Purpose**: Caching LLM responses and managing task queues

**Connection Details**:
- **URL**: redis://localhost:6379
- **Container**: rag_redis
- **Default Database**: 0

**Available Commands**:
```bash
# Using redis-cli
docker exec -it rag_redis redis-cli

# Inside redis-cli:
> PING
> INFO
> KEYS *
> GET key_name
> SET key_name value
> EXPIRE key_name 3600

# Using direct commands
docker exec rag_redis redis-cli PING
docker exec rag_redis redis-cli INFO server
docker exec rag_redis redis-cli DBSIZE
```

**Python Client Example**:
```python
import redis

r = redis.Redis(host='localhost', port=6379, db=0)
r.ping()  # Test connection
r.set('test_key', 'test_value')
value = r.get('test_key')
```

### 5. Prometheus (Metrics)

**Purpose**: Collects and stores metrics from all services

**Connection Details**:
- **URL**: http://localhost:9090
- **Container**: rag_prometheus
- **Config**: configs/prometheus/prometheus.yml

**Available Endpoints**:
```bash
# Web UI
open http://localhost:9090

# Health check
curl http://localhost:9090/-/healthy

# Ready check
curl http://localhost:9090/-/ready

# Targets (services being monitored)
curl http://localhost:9090/api/v1/targets

# Query metrics
curl http://localhost:9090/api/v1/query?query=up

# Get all metrics
curl http://localhost:9090/api/v1/label/__name__/values
```

**Useful Queries** (in Prometheus UI):
```promql
# Service uptime
up

# API request rate
rate(http_requests_total[5m])

# API response time
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Documents processed
documents_processed_total

# Active HTTP requests
http_requests_active
```

### 6. Grafana (Visualization)

**Purpose**: Visualizes metrics with dashboards

**Connection Details**:
- **URL**: http://localhost:3000
- **Container**: rag_grafana
- **Default Login**: admin / admin (change on first login)
- **Config**: configs/grafana/

**Features**:
```bash
# Access dashboard
open http://localhost:3000

# API endpoints
curl http://localhost:3000/api/health
curl -u admin:admin http://localhost:3000/api/datasources
curl -u admin:admin http://localhost:3000/api/dashboards/home
```

**Pre-configured Elements**:
- Data source: Prometheus (http://prometheus:9090)
- Dashboard: RAG System Metrics (auto-provisioned)
- Alerts: Can be configured for system monitoring

### 7. Nginx (API Gateway)

**Purpose**: Reverse proxy and load balancer

**Connection Details**:
- **HTTP**: http://localhost:80
- **HTTPS**: https://localhost:443 (if configured)
- **Container**: rag_nginx
- **Config**: configs/nginx/

**Proxied Routes**:
```nginx
# All API requests
http://localhost/api/* → http://rag_api:8000/*

# Prometheus
http://localhost/prometheus/* → http://rag_prometheus:9090/*

# Grafana
http://localhost/grafana/* → http://rag_grafana:3000/*
```

**Testing Nginx**:
```bash
# Check nginx config
docker exec rag_nginx nginx -t

# Reload nginx
docker exec rag_nginx nginx -s reload

# View access logs
docker logs rag_nginx
```

## Service URLs Summary

| Service | Internal URL (Docker) | External URL (Host) | Purpose |
|---------|----------------------|---------------------|---------|
| API | http://rag_api:8000 | http://localhost:8000 | Main API |
| Ollama | http://rag_ollama:11434 | http://localhost:11434 | LLM Service |
| Qdrant | http://rag_qdrant:6333 | http://localhost:6333 | Vector DB |
| Redis | redis://rag_redis:6379 | redis://localhost:6379 | Cache/Queue |
| Prometheus | http://rag_prometheus:9090 | http://localhost:9090 | Metrics |
| Grafana | http://rag_grafana:3000 | http://localhost:3000 | Dashboards |
| Nginx | - | http://localhost:80 | Gateway |

## Testing Connections

### Quick Test Script

Create `test_services.py`:
```python
import requests
import redis
from qdrant_client import QdrantClient

def test_services():
    services = {
        "API": "http://localhost:8000/health",
        "Ollama": "http://localhost:11434/api/version",
        "Qdrant": "http://localhost:6333/health",
        "Prometheus": "http://localhost:9090/-/healthy",
        "Grafana": "http://localhost:3000/api/health",
        "Nginx": "http://localhost/api/health"
    }
    
    print("Testing service connections...\n")
    
    for name, url in services.items():
        try:
            response = requests.get(url, timeout=5)
            status = "✅ OK" if response.status_code < 400 else f"❌ Error {response.status_code}"
            print(f"{name:12} {status}")
        except Exception as e:
            print(f"{name:12} ❌ Failed: {str(e)}")
    
    # Test Redis
    try:
        r = redis.Redis(host='localhost', port=6379)
        r.ping()
        print(f"{'Redis':12} ✅ OK")
    except:
        print(f"{'Redis':12} ❌ Failed")

if __name__ == "__main__":
    test_services()
```

### Using the Test Runner
```bash
# Comprehensive health check
python run_tests.py

# This automatically checks all services
```

## Troubleshooting

### Common Issues

**1. Service Won't Start**
```bash
# Check logs
docker-compose logs rag_service_name

# Restart specific service
docker-compose restart rag_service_name

# Rebuild service
docker-compose build rag_service_name
docker-compose up -d rag_service_name
```

**2. Port Already in Use**
```bash
# Find what's using the port
sudo lsof -i :PORT_NUMBER

# Kill the process
sudo kill -9 PID

# Or change the port in docker-compose.yml
```

**3. Container Keeps Restarting**
```bash
# Check container status
docker ps -a

# Inspect container
docker inspect rag_service_name

# Check resource usage
docker stats
```

**4. Network Issues**
```bash
# List networks
docker network ls

# Inspect network
docker network inspect llm_backend_rag_network

# Test connectivity between containers
docker exec rag_api ping rag_ollama
```

### Logs and Debugging

```bash
# All service logs
docker-compose logs

# Follow logs
docker-compose logs -f

# Last 100 lines
docker-compose logs --tail=100

# Specific service logs
docker-compose logs rag_api

# Enter container shell
docker exec -it rag_api /bin/bash
```

### Resource Monitoring

```bash
# Real-time stats
docker stats

# Check disk usage
docker system df

# Clean up unused resources
docker system prune -a
```

## Advanced Usage

### Scaling Services
```bash
# Scale API service to 3 instances
docker-compose up -d --scale api=3
```

### Custom Configuration
```bash
# Use custom environment file
docker-compose --env-file .env.production up -d

# Override specific settings
docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d
```

### Backup and Restore
```bash
# Backup Qdrant data
docker exec rag_qdrant qdrant-backup /qdrant/storage /backup/qdrant-backup.tar

# Backup Redis data
docker exec rag_redis redis-cli SAVE
docker cp rag_redis:/data/dump.rdb ./redis-backup.rdb

# Restore (stop services first)
docker-compose stop
# Copy backup files back
docker-compose start
```

---

*Last updated: 2025-05-28*
*For more information, see [ARCHITECTURE.md](ARCHITECTURE.md) and [DEPLOYMENT.md](DEPLOYMENT.md)*