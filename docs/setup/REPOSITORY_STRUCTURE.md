# Repository Structure

This document describes the reorganized structure of the LightRAG backend repository.

## 📁 Directory Structure

```
llm_backend/
├── README.md                   # Main project documentation
├── TODO.md                     # Project tasks and roadmap
├── CLAUDE.md                   # Claude-specific instructions
├── run_api.py                  # API entry point
├── run_tests.py               # Test runner
├── run_tests.sh               # Shell test runner
├── docker-compose.yml         # Service orchestration
├── Dockerfile                 # API container build
├── requirements.txt           # Python dependencies
├── pytest.ini                # Test configuration
│
├── src/                       # 🔧 Source Code
│   ├── api/                   # FastAPI application
│   │   ├── main.py           # API server
│   │   ├── models.py         # Pydantic models
│   │   ├── auth.py           # Authentication
│   │   ├── health.py         # Health checks
│   │   ├── logging.py        # Logging setup
│   │   └── exceptions.py     # Error handling
│   ├── config/               # Configuration
│   │   └── settings.py       # Environment settings
│   ├── llm/                  # LLM providers
│   │   ├── base.py          # Base provider
│   │   ├── factory.py       # Provider factory
│   │   ├── openai_provider.py
│   │   ├── anthropic_provider.py
│   │   └── vllm_provider.py
│   └── rag/                  # RAG service
│       └── lightrag_service.py
│
├── docs/                      # 📚 Documentation
│   ├── architecture/          # System design
│   │   ├── ARCHITECTURE.md
│   │   └── COMPLETE_SETUP_GUIDE.md
│   ├── setup/                # Setup guides
│   │   ├── DEPLOYMENT.md
│   │   ├── SERVICES.md
│   │   ├── QUICK_REFERENCE.md
│   │   ├── PORT_CHANGES.md
│   │   └── REPOSITORY_STRUCTURE.md (this file)
│   ├── tutorials/            # Usage tutorials
│   │   └── TUTORIAL.md
│   └── reports/              # Test reports
│       ├── TESTING.md
│       ├── DATABASE_STATUS.md
│       └── SYSTEM_READY.md
│
├── scripts/                   # 🔧 Utility Scripts
│   ├── demos/                # Demo scripts
│   │   └── build_database.py # Database builder
│   └── tests/                # Test scripts
│       ├── test_basic_functionality.py
│       └── test_docling_direct.py
│
├── configs/                   # ⚙️ Service Configurations
│   ├── nginx/                # NGINX configs
│   ├── grafana/              # Grafana dashboards
│   └── prometheus/           # Prometheus config
│
├── data/                      # 📄 Sample Data
│   └── *.pdf                 # Clinical PDFs (34 files)
│
├── tests/                     # 🧪 Test Suite
│   ├── unit/                 # Unit tests
│   ├── integration/          # Integration tests
│   ├── infrastructure/       # Infrastructure tests
│   ├── performance/          # Performance tests
│   └── conftest.py          # Test configuration
│
├── examples/                  # 💡 Usage Examples
│   └── connect_to_services.py
│
├── generated_data/           # 🗄️ Generated RAG Data
│   ├── rag_data/            # Main RAG database
│   ├── clinical_data_rag/   # Clinical database
│   ├── demo_clinical_rag/   # Demo database
│   └── test_basic_rag/      # Test database
│
├── storage/                  # 💾 Persistent Storage
│   ├── qdrant_storage/      # Vector database
│   └── redis_data/          # Cache data
│
├── models/                   # 🤖 Model Caches
│   ├── ollama_models/       # Ollama model cache
│   └── vllm_cache/          # vLLM model cache
│
├── temp/                     # 🗂️ Temporary Files
│   ├── docling_sample.txt
│   └── pypdf2_sample.txt
│
├── logs/                     # 📋 Application Logs
└── LightRAG/                 # 📦 LightRAG Library
    └── (embedded library with fixes)
```

## 🔄 Changes Made

### Consolidated Documentation
- **Before**: 13 markdown files scattered in root
- **After**: Organized in `/docs/` by category (architecture, setup, tutorials, reports)

### Organized Scripts
- **Before**: Python scripts in root directory
- **After**: Moved to `/scripts/demos/` and `/scripts/tests/`
- **Fixed**: Import paths updated for new structure

### Grouped Storage
- **Before**: Storage directories mixed with code
- **After**: Organized under `/storage/`, `/models/`, `/generated_data/`

### Updated Docker Configuration
- **Before**: Used relative paths like `./qdrant_storage`
- **After**: Uses organized paths like `./storage/qdrant_storage`

## 🎯 Benefits

1. **Cleaner Root Directory**: Only essential files remain in root
2. **Logical Organization**: Related files grouped together
3. **Better Navigation**: Easy to find specific types of files
4. **Maintenance**: Easier to maintain and update
5. **Scalability**: Structure supports future growth

## 🚀 Usage After Restructuring

### Run Tests
```bash
# From root directory
python scripts/tests/test_basic_functionality.py
python scripts/tests/test_docling_direct.py

# Or use the test runner
python run_tests.py
```

### Build Database
```bash
# From root directory
python scripts/demos/build_database.py
```

### Access Documentation
```bash
# Architecture docs
docs/architecture/COMPLETE_SETUP_GUIDE.md

# Setup guides
docs/setup/DEPLOYMENT.md
docs/setup/SERVICES.md

# Tutorials
docs/tutorials/TUTORIAL.md
```

### Docker Services
All Docker configurations automatically use the new directory structure:
```bash
docker-compose up -d  # Works with new paths
```

## 📋 File Locations Quick Reference

| File Type | Old Location | New Location |
|-----------|-------------|--------------|
| Documentation | `/*.md` | `docs/*/` |
| Test scripts | `/test_*.py` | `scripts/tests/` |
| Demo scripts | `/build_*.py` | `scripts/demos/` |
| Storage | `/qdrant_storage/` | `storage/qdrant_storage/` |
| Models | `/ollama_models/` | `models/ollama_models/` |
| RAG data | `/rag_data/` | `generated_data/rag_data/` |
| Samples | `/docling_sample.txt` | `temp/` |

## ✅ Verified Working

- ✅ Docker Compose configuration validates successfully
- ✅ Import paths updated and working
- ✅ Basic functionality test passes
- ✅ Services can read from new directory structure
- ✅ Documentation links updated

The repository is now much cleaner and more maintainable while preserving all functionality!