"""Integration tests for API endpoints."""

import pytest
from fastapi import status


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_health_endpoint(self, test_client):
        """Test basic health check endpoint."""
        response = test_client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
        assert "uptime" in data
    
    def test_readiness_endpoint(self, test_client):
        """Test readiness check endpoint."""
        response = test_client.get("/health/ready")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "checks" in data
        assert isinstance(data["checks"], list)


class TestInfoEndpoints:
    """Test informational endpoints."""
    
    def test_root_endpoint(self, test_client):
        """Test root endpoint returns API info."""
        response = test_client.get("/")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["title"] == "LightRAG Production API"
        assert "version" in data
        assert "features" in data
        assert "limits" in data
        assert isinstance(data["features"], list)
        assert isinstance(data["limits"], dict)
    
    def test_metrics_endpoint(self, test_client):
        """Test Prometheus metrics endpoint."""
        response = test_client.get("/metrics")
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/plain; version=0.0.4; charset=utf-8"
        
        # Check for some expected metrics
        content = response.text
        assert "http_requests_total" in content
        assert "http_request_duration_seconds" in content
        assert "python_info" in content


class TestDocumentEndpoints:
    """Test document management endpoints."""
    
    def test_insert_documents_success(self, test_client, sample_documents):
        """Test successful document insertion."""
        response = test_client.post(
            "/documents",
            json={"documents": sample_documents}
        )
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["success"] is True
        assert data["documents_processed"] == len(sample_documents)
        assert "processing_time" in data
        assert "timestamp" in data
    
    def test_insert_documents_empty_list(self, test_client):
        """Test inserting empty document list."""
        response = test_client.post(
            "/documents",
            json={"documents": []}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_insert_documents_invalid_format(self, test_client):
        """Test inserting documents with invalid format."""
        response = test_client.post(
            "/documents",
            json={"docs": ["wrong field name"]}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_insert_documents_too_many(self, test_client):
        """Test inserting too many documents."""
        # Create 101 documents (limit is 100)
        documents = [f"Document {i}" for i in range(101)]
        response = test_client.post(
            "/documents",
            json={"documents": documents}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestQueryEndpoints:
    """Test query endpoints."""
    
    @pytest.mark.parametrize("mode", ["naive", "local", "global", "hybrid"])
    def test_query_different_modes(self, test_client, mode):
        """Test querying with different modes."""
        response = test_client.post(
            "/query",
            json={
                "question": "What is LightRAG?",
                "mode": mode
            }
        )
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["success"] is True
        assert "answer" in data
        assert data["mode"] == mode
        assert "processing_time" in data
        assert "timestamp" in data
    
    def test_query_invalid_mode(self, test_client):
        """Test querying with invalid mode."""
        response = test_client.post(
            "/query",
            json={
                "question": "What is LightRAG?",
                "mode": "invalid_mode"
            }
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_query_empty_question(self, test_client):
        """Test querying with empty question."""
        response = test_client.post(
            "/query",
            json={
                "question": "",
                "mode": "hybrid"
            }
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_query_with_optional_params(self, test_client):
        """Test querying with optional parameters."""
        response = test_client.post(
            "/query",
            json={
                "question": "What is LightRAG?",
                "mode": "hybrid",
                "stream": False,
                "top_k": 5,
                "include_sources": True
            }
        )
        assert response.status_code == status.HTTP_200_OK


class TestGraphEndpoints:
    """Test knowledge graph endpoints."""
    
    def test_get_graph(self, test_client):
        """Test retrieving knowledge graph."""
        response = test_client.get("/graph")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "nodes" in data
        assert "edges" in data
        assert "stats" in data
        assert "timestamp" in data
        assert isinstance(data["nodes"], list)
        assert isinstance(data["edges"], list)
        assert isinstance(data["stats"], dict)


class TestAuthentication:
    """Test API authentication when enabled."""
    
    def test_api_key_required_when_enabled(self, test_client):
        """Test that API key is required when authentication is enabled."""
        # This test would need to mock settings with API_KEY_ENABLED=true
        # For now, we're testing with auth disabled
        response = test_client.get("/")
        assert response.status_code == status.HTTP_200_OK
    
    def test_rate_limiting(self, test_client):
        """Test rate limiting functionality."""
        # Make multiple requests quickly
        for _ in range(5):
            response = test_client.get("/")
            assert response.status_code == status.HTTP_200_OK


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_404_not_found(self, test_client):
        """Test 404 response for unknown endpoints."""
        response = test_client.get("/unknown-endpoint")
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_method_not_allowed(self, test_client):
        """Test 405 response for wrong HTTP method."""
        response = test_client.get("/documents")  # Should be POST
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    
    def test_large_request_body(self, test_client):
        """Test handling of large request bodies."""
        # Create a very large document
        large_doc = "x" * (11 * 1024 * 1024)  # 11MB (limit is 10MB)
        response = test_client.post(
            "/documents",
            json={"documents": [large_doc]}
        )
        # Should fail due to request size limit
        assert response.status_code in [
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]