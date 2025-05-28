"""Advanced integration tests for edge cases and real-world scenarios."""

import pytest
import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from fastapi import status
import io
import sys


class TestStreamingResponses:
    """Test streaming response functionality."""
    
    @pytest.mark.asyncio
    async def test_streaming_query_response(self, async_client):
        """Test streaming query responses."""
        response = await async_client.post(
            "/query",
            json={
                "question": "What is LightRAG?",
                "mode": "hybrid",
                "stream": True
            }
        )
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["success"] is True
        assert "answer" in data
        # In real implementation, this would test actual streaming
        
    @pytest.mark.asyncio
    async def test_streaming_timeout_handling(self, async_client):
        """Test streaming response timeout handling."""
        # Simulate a long-running query that might timeout
        response = await async_client.post(
            "/query",
            json={
                "question": "Very complex question that takes a long time",
                "mode": "global",
                "stream": True
            }
        )
        # Should handle gracefully even if it takes time
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_408_REQUEST_TIMEOUT]


class TestConcurrentRequests:
    """Test concurrent request handling and thread safety."""
    
    def test_concurrent_health_checks(self, test_client):
        """Test multiple concurrent health check requests."""
        def make_request():
            response = test_client.get("/health")
            return response.status_code
        
        # Create 10 concurrent requests
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [future.result() for future in futures]
        
        # All should succeed
        assert all(code == status.HTTP_200_OK for code in results)
    
    def test_concurrent_document_insertion(self, test_client):
        """Test concurrent document insertion requests."""
        def insert_documents(batch_id):
            response = test_client.post(
                "/documents",
                json={"documents": [f"Document from batch {batch_id}"]}
            )
            return response.status_code, batch_id
        
        # Create 5 concurrent document insertion requests
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(insert_documents, i) for i in range(5)]
            results = [future.result() for future in futures]
        
        # All should succeed
        for status_code, batch_id in results:
            assert status_code == status.HTTP_200_OK
    
    def test_concurrent_queries(self, test_client):
        """Test concurrent query requests."""
        questions = [
            "What is LightRAG?",
            "How does RAG work?",
            "What are the query modes?",
            "Explain knowledge graphs",
            "What is vector search?"
        ]
        
        def make_query(question):
            response = test_client.post(
                "/query",
                json={"question": question, "mode": "hybrid"}
            )
            return response.status_code, len(response.json().get("answer", ""))
        
        # Execute all queries concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_query, q) for q in questions]
            results = [future.result() for future in futures]
        
        # All should succeed and return responses
        for status_code, answer_length in results:
            assert status_code == status.HTTP_200_OK
            assert answer_length > 0


class TestDocumentProcessing:
    """Test document processing edge cases."""
    
    def test_large_document_processing(self, test_client):
        """Test processing of large documents."""
        # Create a large document (close to but under the limit)
        large_doc = "This is a test sentence. " * 10000  # ~250KB
        
        response = test_client.post(
            "/documents",
            json={"documents": [large_doc]}
        )
        assert response.status_code == status.HTTP_200_OK
    
    def test_many_small_documents(self, test_client):
        """Test processing many small documents at once."""
        # Create 50 small documents (under the 100 limit)
        small_docs = [f"Small document number {i}" for i in range(50)]
        
        response = test_client.post(
            "/documents",
            json={"documents": small_docs}
        )
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["documents_processed"] == 50
    
    def test_empty_document_handling(self, test_client):
        """Test handling of empty or whitespace-only documents."""
        docs_with_empties = [
            "Valid document",
            "",  # Empty
            "   ",  # Whitespace only
            "\n\t",  # Newlines and tabs
            "Another valid document"
        ]
        
        response = test_client.post(
            "/documents",
            json={"documents": docs_with_empties}
        )
        # Should handle gracefully
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_422_UNPROCESSABLE_ENTITY]
    
    def test_special_characters_in_documents(self, test_client):
        """Test documents with special characters and Unicode."""
        special_docs = [
            "Document with émojis 🚀 and ñoñ characters",
            "Chinese text: 你好世界",
            "Math symbols: ∑ ∫ ∂ ∇ ∞",
            "Special chars: @#$%^&*()_+-=[]{}|;:',.<>?",
            "Multiline\ndocument\nwith\nnewlines"
        ]
        
        response = test_client.post(
            "/documents",
            json={"documents": special_docs}
        )
        assert response.status_code == status.HTTP_200_OK


class TestSecurityAndValidation:
    """Test security vulnerabilities and input validation."""
    
    def test_sql_injection_attempts(self, test_client):
        """Test potential SQL injection in queries."""
        malicious_queries = [
            "'; DROP TABLE documents; --",
            "UNION SELECT * FROM users",
            "1' OR '1'='1",
            "<script>alert('xss')</script>",
            "../../etc/passwd"
        ]
        
        for malicious_query in malicious_queries:
            response = test_client.post(
                "/query",
                json={"question": malicious_query, "mode": "hybrid"}
            )
            # Should not crash or expose sensitive data
            assert response.status_code in [
                status.HTTP_200_OK, 
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ]
    
    def test_oversized_request_payload(self, test_client):
        """Test handling of oversized request payloads."""
        # Create a request that exceeds the 10MB limit
        huge_document = "x" * (11 * 1024 * 1024)  # 11MB
        
        response = test_client.post(
            "/documents",
            json={"documents": [huge_document]},
            timeout=30
        )
        
        # Should be rejected due to size limit
        assert response.status_code in [
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_400_BAD_REQUEST
        ]
    
    def test_malformed_json_handling(self, test_client):
        """Test handling of malformed JSON requests."""
        malformed_payloads = [
            '{"documents": [}',  # Missing closing bracket
            '{"documents": "not an array"}',  # Wrong type
            '{"wrong_field": ["doc"]}',  # Wrong field name
            '',  # Empty payload
            'not json at all'  # Not JSON
        ]
        
        for payload in malformed_payloads:
            response = test_client.post(
                "/documents",
                data=payload,
                headers={"Content-Type": "application/json"}
            )
            # Should return proper error codes
            assert response.status_code in [
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ]
    
    def test_header_injection_attempts(self, test_client):
        """Test potential header injection attacks."""
        malicious_headers = {
            "X-API-Key": "valid-key\r\nMalicious-Header: injected",
            "User-Agent": "Normal\r\nInjected: header",
            "Content-Type": "application/json\r\nX-Injected: true"
        }
        
        for header_name, header_value in malicious_headers.items():
            response = test_client.post(
                "/documents",
                json={"documents": ["test"]},
                headers={header_name: header_value}
            )
            # Should handle without crashing
            assert response.status_code in [
                status.HTTP_200_OK,
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ]


class TestMemoryAndPerformance:
    """Test memory usage and performance edge cases."""
    
    def test_memory_usage_with_large_responses(self, test_client):
        """Test memory usage when generating large responses."""
        # Query that might generate a large response
        response = test_client.post(
            "/query",
            json={
                "question": "Please provide a very detailed explanation of everything",
                "mode": "hybrid"
            }
        )
        assert response.status_code == status.HTTP_200_OK
        
        # Response should be reasonable size (not unlimited)
        data = response.json()
        answer_size = len(data.get("answer", ""))
        assert answer_size < 1024 * 1024  # Less than 1MB response
    
    def test_rapid_sequential_requests(self, test_client):
        """Test handling of rapid sequential requests."""
        start_time = time.time()
        
        # Make 20 rapid requests
        for i in range(20):
            response = test_client.get("/health")
            assert response.status_code == status.HTTP_200_OK
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should complete reasonably quickly (less than 10 seconds)
        assert total_time < 10.0
        # Average response time should be reasonable
        avg_response_time = total_time / 20
        assert avg_response_time < 0.5  # Less than 500ms per request


class TestErrorRecovery:
    """Test error recovery and graceful degradation."""
    
    def test_recovery_after_bad_requests(self, test_client):
        """Test that system recovers after receiving bad requests."""
        # Send several bad requests
        bad_requests = [
            {"invalid": "format"},
            {"documents": None},
            {"documents": []},
        ]
        
        for bad_request in bad_requests:
            response = test_client.post("/documents", json=bad_request)
            # Expect errors for bad requests
            assert response.status_code in [
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ]
        
        # System should still work normally after bad requests
        good_response = test_client.post(
            "/documents",
            json={"documents": ["Good document after errors"]}
        )
        assert good_response.status_code == status.HTTP_200_OK
    
    def test_health_check_consistency(self, test_client):
        """Test that health checks remain consistent under load."""
        # Check health before load
        initial_health = test_client.get("/health")
        assert initial_health.status_code == status.HTTP_200_OK
        
        # Generate some load
        for _ in range(10):
            test_client.post("/documents", json={"documents": ["Load test doc"]})
            test_client.post("/query", json={"question": "Load test", "mode": "hybrid"})
        
        # Check health after load
        final_health = test_client.get("/health")
        assert final_health.status_code == status.HTTP_200_OK
        
        # Health status should be consistent
        initial_data = initial_health.json()
        final_data = final_health.json()
        assert initial_data["status"] == final_data["status"]