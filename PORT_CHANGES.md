# Port Configuration Changes

## Summary
Updated all port configurations to avoid conflict with port 3000. All services now use different ports.

## New Port Mapping

| Service | Old Port | New Port | Purpose |
|---------|----------|----------|---------|
| **API Service** | 8000 | **9000** | LightRAG FastAPI backend |
| **Ollama** | 11434 | **12434** | LLM and embedding server |
| **Qdrant** | 6333/6334 | **7333/7334** | Vector database |
| **Redis** | 6379 | **7379** | Cache and queue system |
| **Prometheus** | 9090 | **10090** | Metrics collection |
| **Grafana** | 3000 | **4000** | Monitoring dashboard |
| **NGINX** | 80/443 | **80/443** | API Gateway (unchanged) |

## Access URLs

### Core Services
- **Main API**: http://localhost:9000
- **Ollama LLM**: http://localhost:12434
- **Qdrant Vector DB**: http://localhost:7333
- **Redis Cache**: localhost:7379

### Monitoring
- **Grafana Dashboard**: http://localhost:4000
- **Prometheus Metrics**: http://localhost:10090

### Health Checks
```bash
# Test all services
curl http://localhost:9000/health          # API
curl http://localhost:12434/api/version    # Ollama  
curl http://localhost:7333/health          # Qdrant
curl http://localhost:4000/api/health      # Grafana
curl http://localhost:10090/-/healthy      # Prometheus
redis-cli -h localhost -p 7379 ping       # Redis
```

## Files Updated

### Docker Configuration
- `docker-compose.yml` - Updated all port mappings

### Example Scripts  
- `examples/connect_to_services.py` - Updated all service URLs
- `build_database.py` - Updated Ollama and API URLs
- `demo_database.py` - Updated service URLs
- `test_basic_functionality.py` - Updated all endpoints

### Service Configuration
- `src/rag/lightrag_service.py` - Updated default Ollama host

### Documentation
- `TUTORIAL.md` - Updated all port references and examples
- `PORT_CHANGES.md` - This documentation

## To Start Services

```bash
# Stop any running services first
docker-compose down

# Start with new port configuration
docker-compose up -d

# Verify all services are running
docker-compose ps
```

## Benefits

1. **No Port Conflicts**: Port 3000 is now free for your other applications
2. **Logical Grouping**: Related services use similar port ranges
3. **Easy to Remember**: Clear port patterns (7xxx for databases, 1xxxx for LLMs, etc.)
4. **Backward Compatibility**: Internal container communication unchanged

## Notes

- Internal Docker network communication uses original ports
- Only external host mappings have changed
- All functionality remains exactly the same
- Update any external integrations to use new ports