# Port Mappings - All Fixed ✅

## Issue Resolution

**Problem:** Service health checks were using old/incorrect ports causing false failures.  
**Solution:** Updated all test scripts, documentation, and examples to use correct ports.

## Correct Port Mappings

| Service | External Port | Internal Port | Health Check Endpoint |
|---------|---------------|---------------|----------------------|
| **API** | 9000 | 8000 | `http://localhost:9000/health` |
| **Ollama** | 12434 | 11434 | `http://localhost:12434/api/version` |
| **Qdrant** | 7333 | 6333 | `http://localhost:7333/` (NOT /health) |
| **Redis** | 7379 | 6379 | `redis-cli -h localhost -p 7379 ping` |
| **Prometheus** | 10090 | 9090 | `http://localhost:10090/-/healthy` |
| **Grafana** | 4000 | 3000 | `http://localhost:4000/api/health` |
| **NGINX** | 80, 443 | 80, 443 | `http://localhost:80/` |

## Files Updated ✅

### Test Scripts
- ✅ `run_tests.py` - Updated all service URLs and ports
- ✅ `run_tests.sh` - Updated all service checks including Redis port
- ✅ `scripts/demos/create_graph_rag_demo.py` - Fixed Qdrant endpoint

### Documentation  
- ✅ `docs/setup/QUICK_REFERENCE.md` - Updated all service URLs
- ✅ `examples/connect_to_services.py` - Already had correct ports

### Key Fixes Made

1. **Qdrant Health Check**: Changed from `/health` to `/` (Qdrant doesn't have /health endpoint)
2. **Port Updates**: Updated from old ports (8000, 6333, 6379, 9090, 3000) to new ports
3. **Redis CLI**: Added proper port specification `-p 7379`
4. **Documentation**: Updated all URL references in docs

## Verification Commands

```bash
# Test all services with correct endpoints
curl -s http://localhost:9000/health | jq .status
curl -s http://localhost:12434/api/version | jq .version  
curl -s http://localhost:7333/ | jq .title
redis-cli -h localhost -p 7379 ping
curl -s http://localhost:10090/-/healthy
curl -s http://localhost:4000/api/health | jq .database
```

## Test Runner Commands

```bash
# All tests with correct ports
python run_tests.py --infrastructure --verbose

# Individual service tests  
python examples/connect_to_services.py
python examples/connect_to_services.py ollama
python examples/connect_to_services.py qdrant
```

## Docker Compose Verification

The `docker-compose.yml` port mappings are correct:
```yaml
services:
  lightrag-api:
    ports: ["9000:8000"]
  ollama:  
    ports: ["12434:11434"]
  qdrant:
    ports: ["7333:6333", "7334:6334"]
  redis:
    ports: ["7379:6379"] 
  prometheus:
    ports: ["10090:9090"]
  grafana:
    ports: ["4000:3000"]
```

**All port mappings are now consistent across the entire system!** ✅