# Testing Documentation

This document provides comprehensive information about the test suite for the LightRAG Backend project.

## Table of Contents

1. [Overview](#overview)
2. [Test Structure](#test-structure)
3. [Running Tests](#running-tests)
4. [Test Categories](#test-categories)
5. [Test Coverage](#test-coverage)
6. [Writing New Tests](#writing-new-tests)
7. [Troubleshooting](#troubleshooting)

## Overview

The LightRAG Backend includes a comprehensive test suite with **103+ tests** covering:
- Unit tests for core functionality
- Integration tests for API endpoints
- Infrastructure tests for all services
- Performance tests for load testing

### Test Statistics
- **Total Tests**: 103+
- **Success Rate**: 100% (when run with proper setup)
- **Test Categories**: 4 (Unit, Integration, Infrastructure, Performance)
- **Test Files**: 15

## Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures and configuration
├── unit/                    # Unit tests (no external dependencies)
│   ├── test_lightrag_service.py
│   └── test_settings.py
├── integration/             # API integration tests
│   ├── test_api_endpoints.py
│   ├── test_advanced_scenarios.py
│   ├── test_authentication_edge_cases.py
│   └── test_network_and_timeouts.py
├── infrastructure/          # Service integration tests
│   ├── test_full_stack_integration.py
│   ├── test_grafana_integration.py
│   ├── test_ollama_integration.py
│   ├── test_prometheus_integration.py
│   ├── test_qdrant_integration.py
│   └── test_redis_integration.py
└── performance/             # Load and performance tests
    └── test_load_and_performance.py
```

## Running Tests

### Prerequisites

1. **Activate Virtual Environment**:
   ```bash
   cd ~/llm_backend
   source venv/bin/activate
   ```

2. **Start Docker Services**:
   ```bash
   docker-compose up -d
   ```

3. **Verify Services**:
   ```bash
   docker ps
   ```

### Test Execution Methods

#### Method 1: Using Test Runner Scripts (Recommended)

**Python Test Runner**:
```bash
# Run all tests
python run_tests.py

# Run specific test suites
python run_tests.py --unit              # Fast, no services needed
python run_tests.py --integration       # API tests
python run_tests.py --infrastructure    # Service tests

# Run with options
python run_tests.py -v                  # Verbose output
python run_tests.py --coverage          # Coverage report
python run_tests.py --parallel          # Parallel execution
python run_tests.py --html              # HTML reports
```

**Bash Test Runner**:
```bash
# Make executable (first time only)
chmod +x run_tests.sh

# Run tests
./run_tests.sh
./run_tests.sh --unit
./run_tests.sh --integration
./run_tests.sh --infrastructure
```

#### Method 2: Using pytest Directly

```bash
# Run all tests
pytest

# Run specific directories
pytest tests/unit/
pytest tests/integration/
pytest tests/infrastructure/

# Run with options
pytest -v                    # Verbose
pytest -q                    # Quiet
pytest --tb=short           # Short traceback
pytest -s                   # Show print statements
pytest --cov=src            # Coverage report
pytest -n auto              # Parallel execution
```

#### Method 3: Run Specific Test Files

```bash
# Test individual components
pytest tests/unit/test_settings.py -v
pytest tests/infrastructure/test_redis_integration.py -v
pytest tests/integration/test_api_endpoints.py::TestHealthEndpoints -v
```

## Test Categories

### 1. Unit Tests (27 tests)
Location: `tests/unit/`

**Purpose**: Test individual components in isolation without external dependencies.

**Coverage**:
- LightRAG service initialization and methods
- Configuration settings validation
- Environment variable parsing
- Error handling

**Example Tests**:
- `test_service_initialization`
- `test_api_keys_parsing`
- `test_environment_variable_prefix`

### 2. Integration Tests (21+ tests)
Location: `tests/integration/`

**Purpose**: Test API endpoints and their interactions.

**Coverage**:
- Health check endpoints
- Document insertion endpoints
- Query endpoints (all modes)
- Authentication and rate limiting
- Error responses
- Concurrent operations
- Streaming responses

**Example Tests**:
- `test_health_endpoint`
- `test_insert_documents_success`
- `test_query_different_modes`
- `test_concurrent_queries`

### 3. Infrastructure Tests (55 tests)
Location: `tests/infrastructure/`

**Purpose**: Verify all external services are working correctly.

**Coverage**:
- **Qdrant**: Vector database operations, collection management
- **Redis**: Caching, queuing, data structures
- **Ollama**: LLM inference, embedding generation
- **Prometheus**: Metrics collection, queries
- **Grafana**: Dashboards, datasources, alerting
- **Full Stack**: End-to-end workflows

**Example Tests**:
- `test_qdrant_vector_operations`
- `test_redis_queue_operations`
- `test_ollama_text_generation`
- `test_prometheus_metrics_collection`
- `test_end_to_end_document_processing`

### 4. Performance Tests
Location: `tests/performance/`

**Purpose**: Test system performance and load handling.

**Coverage**:
- Concurrent request handling
- Response time benchmarks
- Memory usage patterns
- Throughput testing

## Test Coverage

### Current Coverage Stats
- **Unit Tests**: 100% of core business logic
- **API Endpoints**: 100% of public endpoints
- **Infrastructure**: All 6 major services tested
- **Error Cases**: Comprehensive error scenario coverage

### Generating Coverage Reports

```bash
# Generate terminal coverage report
pytest --cov=src --cov-report=term-missing

# Generate HTML coverage report
pytest --cov=src --cov-report=html
# Open htmlcov/index.html in browser

# Using test runner
python run_tests.py --coverage
```

## Writing New Tests

### Test Structure Template

```python
import pytest
from unittest.mock import Mock, patch

class TestNewFeature:
    """Test suite for new feature."""
    
    @pytest.fixture
    def setup_data(self):
        """Fixture for test data."""
        return {"key": "value"}
    
    def test_feature_success(self, setup_data):
        """Test successful case."""
        # Arrange
        expected = "expected_result"
        
        # Act
        result = your_function(setup_data)
        
        # Assert
        assert result == expected
    
    def test_feature_error(self):
        """Test error handling."""
        with pytest.raises(ExpectedException):
            your_function(invalid_input)
```

### Best Practices

1. **Use Fixtures**: Define reusable test data in `conftest.py`
2. **Mock External Services**: Use `unittest.mock` for unit tests
3. **Test Both Success and Failure**: Cover happy path and edge cases
4. **Use Descriptive Names**: `test_<feature>_<scenario>_<expected_result>`
5. **Keep Tests Fast**: Mock heavy operations in unit tests
6. **Test in Isolation**: Each test should be independent

## Troubleshooting

### Common Issues and Solutions

#### 1. Import Errors
```bash
ModuleNotFoundError: No module named 'src'
```
**Solution**: Ensure you're in the project root and have installed the package:
```bash
pip install -e .
```

#### 2. Service Connection Errors
```bash
Failed to connect to Ollama at http://localhost:11434
```
**Solution**: Ensure Docker services are running:
```bash
docker-compose up -d
docker ps  # Verify all containers are up
```

#### 3. Redis Detection Issues
```bash
Checking Redis... ✗ Not running
```
**Solution**: Redis might be running but `redis-cli` not installed. The test runner will try alternative detection methods.

#### 4. Timeout Errors
```bash
TimeoutError: Test exceeded 30 second timeout
```
**Solution**: Some infrastructure tests take longer. Increase timeout:
```bash
pytest --timeout=60
```

#### 5. Async Test Warnings
```bash
RuntimeWarning: coroutine 'test_async' was never awaited
```
**Solution**: Use `@pytest.mark.asyncio` decorator for async tests.

### Debug Mode

Run tests with maximum verbosity for debugging:
```bash
pytest -vvs --tb=long --log-cli-level=DEBUG
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
      qdrant:
        image: qdrant/qdrant:latest
        ports:
          - 6333:6333
    
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.13'
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -e .
    - name: Run tests
      run: python run_tests.py --coverage
```

## Test Maintenance

### Regular Tasks
1. **Update Tests**: When adding new features
2. **Review Coverage**: Monthly coverage report review
3. **Performance Baseline**: Quarterly performance test updates
4. **Dependency Updates**: Test with new package versions

### Test Review Checklist
- [ ] All new features have tests
- [ ] Tests are passing locally
- [ ] No hardcoded values or paths
- [ ] Mocks are properly cleaned up
- [ ] Test names are descriptive
- [ ] Documentation is updated

---

*Last updated: 2025-05-28*
*Test suite version: 1.0.0*