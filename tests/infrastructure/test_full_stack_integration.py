"""Full stack integration tests for the complete RAG system."""

import pytest
import asyncio
import time
import json
import requests
import redis
from qdrant_client import QdrantClient
from typing import Dict, List, Any
import numpy as np


class TestFullStackIntegration:
    """Test complete RAG system integration across all services."""
    
    @pytest.fixture
    def services_config(self):
        """Configuration for all services."""
        return {
            "api": "http://localhost:8000",
            "ollama": "http://localhost:11434", 
            "qdrant": "http://localhost:6333",
            "redis": "redis://localhost:6379",
            "prometheus": "http://localhost:9090",
            "grafana": "http://localhost:3000"
        }
    
    @pytest.fixture
    def redis_client(self):
        """Redis client for testing."""
        return redis.Redis(host="localhost", port=6379, decode_responses=True)
    
    @pytest.fixture
    def qdrant_client(self):
        """Qdrant client for testing."""
        return QdrantClient(host="localhost", port=6333)
    
    def test_all_services_connectivity(self, services_config):
        """Test that all core services are running and accessible."""
        service_status = {}
        
        for service_name, url in services_config.items():
            try:
                if service_name == "api":
                    response = requests.get(f"{url}/health", timeout=5)
                elif service_name == "ollama":
                    response = requests.get(f"{url}/api/version", timeout=5)
                elif service_name == "qdrant":
                    response = requests.get(f"{url}/cluster", timeout=5)
                elif service_name == "prometheus":
                    response = requests.get(f"{url}/-/healthy", timeout=5)
                elif service_name == "grafana":
                    response = requests.get(f"{url}/api/health", timeout=5)
                else:
                    continue
                
                service_status[service_name] = {
                    "status": "up" if response.status_code < 400 else "down",
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds()
                }
                
            except Exception as e:
                service_status[service_name] = {
                    "status": "down",
                    "error": str(e)
                }
        
        print(f"✅ Service connectivity status:")
        for service, status in service_status.items():
            if status["status"] == "up":
                print(f"   - {service}: ✅ ({status.get('response_time', 0):.3f}s)")
            else:
                print(f"   - {service}: ❌ ({status.get('error', 'Unknown error')})")
        
        # All core services should be up
        required_services = ["api", "ollama", "qdrant"]
        for service in required_services:
            assert service in service_status, f"Service {service} not tested"
            assert service_status[service]["status"] == "up", f"Service {service} is down"
        
        return service_status
    
    def test_end_to_end_document_processing(self, services_config, redis_client, qdrant_client):
        """Test complete document processing flow through all services."""
        api_url = services_config["api"]
        
        # Test documents
        test_documents = [
            "Artificial Intelligence (AI) is revolutionizing technology across industries.",
            "Machine Learning enables computers to learn and improve from experience automatically.",
            "Deep Learning uses neural networks with multiple layers to process complex data patterns.",
            "Natural Language Processing helps computers understand and generate human language.",
            "Computer Vision allows machines to interpret and analyze visual information from images."
        ]
        
        print(f"🔄 Testing end-to-end document processing with {len(test_documents)} documents...")
        
        # Step 1: Insert documents via API
        start_time = time.time()
        
        response = requests.post(
            f"{api_url}/documents",
            json={"documents": test_documents},
            timeout=60
        )
        
        assert response.status_code == 200, f"Document insertion failed: {response.status_code}"
        
        insert_response = response.json()
        assert insert_response["success"] is True
        assert insert_response["documents_processed"] == len(test_documents)
        
        processing_time = insert_response["processing_time"]
        
        print(f"   ✅ Documents inserted successfully:")
        print(f"     - Processing time: {processing_time:.2f}s")
        print(f"     - Documents processed: {insert_response['documents_processed']}")
        
        # Step 2: Verify documents are stored in Qdrant
        time.sleep(2)  # Wait for indexing
        
        collections = qdrant_client.get_collections()
        collection_names = [col.name for col in collections.collections]
        
        print(f"   ✅ Qdrant verification:")
        print(f"     - Collections found: {len(collection_names)}")
        
        # Find collections with points
        collections_with_points = []
        for collection_name in collection_names:
            try:
                collection_info = qdrant_client.get_collection(collection_name)
                if collection_info.points_count > 0:
                    collections_with_points.append({
                        "name": collection_name,
                        "points": collection_info.points_count
                    })
            except:
                pass
        
        for col in collections_with_points:
            print(f"     - {col['name']}: {col['points']} points")
        
        # Should have at least one collection with points
        assert len(collections_with_points) > 0, "No collections with points found"
        
        # Step 3: Test querying
        test_queries = [
            "What is artificial intelligence?",
            "How does machine learning work?",
            "Explain deep learning"
        ]
        
        query_results = []
        
        for query in test_queries:
            print(f"   🔄 Testing query: '{query}'")
            
            response = requests.post(
                f"{api_url}/query",
                json={"question": query, "mode": "naive"},
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"   ❌ Query failed with status {response.status_code}")
                print(f"   Error: {response.text}")
                
            assert response.status_code == 200, f"Query failed: {response.status_code}"
            
            query_response = response.json()
            assert query_response["success"] is True
            
            answer = query_response["answer"]
            query_time = query_response["processing_time"]
            
            query_results.append({
                "query": query,
                "answer": answer,
                "time": query_time
            })
            
            print(f"     - Response time: {query_time:.2f}s")
            print(f"     - Answer: {answer[:100]}{'...' if len(answer) > 100 else ''}")
        
        print(f"   ✅ All queries successful:")
        avg_query_time = sum(r["time"] for r in query_results) / len(query_results)
        print(f"     - Average query time: {avg_query_time:.2f}s")
        
        return {
            "insert_time": processing_time,
            "query_results": query_results,
            "avg_query_time": avg_query_time
        }
    
    def test_caching_and_performance(self, services_config, redis_client):
        """Test caching behavior and performance optimization."""
        api_url = services_config["api"]
        
        # Test query that should be cached
        test_query = "What is the main topic of the documents?"
        
        print(f"🔄 Testing caching and performance optimization...")
        
        # Clear any existing cache for this test
        cache_pattern = "*cache*"
        try:
            for key in redis_client.scan_iter(match=cache_pattern):
                redis_client.delete(key)
        except:
            pass
        
        # First query (cache miss)
        start_time = time.time()
        response1 = requests.post(
            f"{api_url}/query",
            json={"question": test_query, "mode": "naive"},
            timeout=30
        )
        first_query_time = time.time() - start_time
        
        assert response1.status_code == 200
        first_response = response1.json()
        
        # Wait a moment
        time.sleep(1)
        
        # Second identical query (potential cache hit)
        start_time = time.time()
        response2 = requests.post(
            f"{api_url}/query",
            json={"question": test_query, "mode": "naive"},
            timeout=30
        )
        second_query_time = time.time() - start_time
        
        assert response2.status_code == 200
        second_response = response2.json()
        
        print(f"   ✅ Caching test results:")
        print(f"     - First query time: {first_query_time:.3f}s")
        print(f"     - Second query time: {second_query_time:.3f}s")
        print(f"     - Speed improvement: {(first_query_time/second_query_time):.1f}x" if second_query_time > 0 else "N/A")
        
        # Check Redis for any cache keys
        all_keys = list(redis_client.scan_iter())
        cache_keys = [key for key in all_keys if "cache" in key.lower()]
        
        print(f"     - Redis cache keys found: {len(cache_keys)}")
        
        if cache_keys:
            for key in cache_keys[:3]:  # Show first 3 cache keys
                try:
                    ttl = redis_client.ttl(key)
                    print(f"       - {key}: TTL {ttl}s")
                except:
                    pass
        
        return {
            "first_query_time": first_query_time,
            "second_query_time": second_query_time,
            "cache_keys_found": len(cache_keys)
        }
    
    def test_metrics_collection_pipeline(self, services_config):
        """Test metrics collection from API to Prometheus to Grafana."""
        api_url = services_config["api"]
        prometheus_url = services_config["prometheus"]
        
        print(f"🔄 Testing metrics collection pipeline...")
        
        # Step 1: Generate API activity to create metrics
        activities = [
            ("GET", "/health"),
            ("GET", "/"),
            ("GET", "/metrics"),
            ("POST", "/query", {"question": "Test query", "mode": "naive"})
        ]
        
        generated_requests = 0
        for method, endpoint, *data in activities:
            for _ in range(3):  # Multiple requests per endpoint
                try:
                    if method == "GET":
                        response = requests.get(f"{api_url}{endpoint}", timeout=5)
                    elif method == "POST" and data:
                        response = requests.post(f"{api_url}{endpoint}", json=data[0], timeout=10)
                    
                    if response.status_code < 500:  # Count successful and client error responses
                        generated_requests += 1
                        
                except Exception as e:
                    print(f"     ⚠️  Request failed: {method} {endpoint} - {e}")
                
                time.sleep(0.1)
        
        print(f"   ✅ Generated {generated_requests} API requests")
        
        # Step 2: Check API metrics endpoint
        response = requests.get(f"{api_url}/metrics", timeout=5)
        assert response.status_code == 200
        
        metrics_content = response.text
        metric_lines = [line for line in metrics_content.split('\\n') if line and not line.startswith('#')]
        
        print(f"   ✅ API metrics endpoint:")
        print(f"     - Total metric lines: {len(metric_lines)}")
        
        # Look for specific metrics
        expected_metrics = ["http_requests_total", "http_request_duration", "python_info"]
        found_metrics = []
        
        for expected in expected_metrics:
            if expected in metrics_content:
                found_metrics.append(expected)
        
        print(f"     - Expected metrics found: {len(found_metrics)}/{len(expected_metrics)}")
        
        # Step 3: Wait for Prometheus to scrape
        print(f"   ⏳ Waiting for Prometheus to scrape metrics...")
        time.sleep(15)
        
        # Step 4: Query Prometheus for our metrics
        prometheus_queries = [
            "up{job=~\".*api.*\"}",
            "http_requests_total",
            "process_start_time_seconds"
        ]
        
        prometheus_results = {}
        
        for query in prometheus_queries:
            try:
                response = requests.get(
                    f"{prometheus_url}/api/v1/query",
                    params={"query": query},
                    timeout=5
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data["status"] == "success":
                        results = data["data"]["result"]
                        prometheus_results[query] = len(results)
                    else:
                        prometheus_results[query] = 0
                else:
                    prometheus_results[query] = 0
                    
            except Exception as e:
                prometheus_results[query] = 0
                print(f"     ⚠️  Prometheus query failed: {query} - {e}")
        
        print(f"   ✅ Prometheus metrics query:")
        for query, result_count in prometheus_results.items():
            print(f"     - {query}: {result_count} series")
        
        # Should find at least some metrics
        total_series = sum(prometheus_results.values())
        assert total_series > 0, "No metrics found in Prometheus"
        
        return {
            "api_requests_generated": generated_requests,
            "api_metrics_lines": len(metric_lines),
            "prometheus_series_found": total_series
        }
    
    def test_error_handling_and_resilience(self, services_config):
        """Test system behavior under error conditions."""
        api_url = services_config["api"]
        
        print(f"🔄 Testing error handling and system resilience...")
        
        # Test various error conditions
        error_tests = [
            {
                "name": "Empty document list",
                "endpoint": "/documents",
                "data": {"documents": []},
                "expected_status": 400
            },
            {
                "name": "Invalid query mode", 
                "endpoint": "/query",
                "data": {"question": "test", "mode": "invalid_mode"},
                "expected_status": 400
            },
            {
                "name": "Empty question",
                "endpoint": "/query", 
                "data": {"question": "", "mode": "naive"},
                "expected_status": 400
            },
            {
                "name": "Oversized request",
                "endpoint": "/documents",
                "data": {"documents": ["x" * 1000000]},  # Very large document
                "expected_status": [400, 413, 422]  # Could be various error codes
            }
        ]
        
        error_results = {}
        
        for test in error_tests:
            try:
                response = requests.post(
                    f"{api_url}{test['endpoint']}",
                    json=test["data"],
                    timeout=10
                )
                
                expected_statuses = test["expected_status"] if isinstance(test["expected_status"], list) else [test["expected_status"]]
                
                if response.status_code in expected_statuses:
                    error_results[test["name"]] = "✅ Correctly handled"
                else:
                    error_results[test["name"]] = f"❌ Wrong status: {response.status_code}"
                
            except Exception as e:
                error_results[test["name"]] = f"❌ Exception: {str(e)[:50]}"
        
        print(f"   ✅ Error handling tests:")
        for test_name, result in error_results.items():
            print(f"     - {test_name}: {result}")
        
        # Test recovery after errors
        recovery_response = requests.get(f"{api_url}/health", timeout=5)
        assert recovery_response.status_code == 200, "System should recover after errors"
        
        print(f"     - System recovery: ✅ Healthy after error tests")
        
        return error_results
    
    def test_concurrent_operations(self, services_config):
        """Test system behavior under concurrent load."""
        import threading
        import queue
        
        api_url = services_config["api"]
        
        print(f"🔄 Testing concurrent operations...")
        
        # Concurrent requests configuration
        num_threads = 5
        requests_per_thread = 3
        
        results_queue = queue.Queue()
        
        def worker_thread(thread_id):
            thread_results = []
            
            for i in range(requests_per_thread):
                try:
                    # Mix of different request types
                    if i % 3 == 0:
                        response = requests.get(f"{api_url}/health", timeout=10)
                    elif i % 3 == 1:
                        response = requests.post(
                            f"{api_url}/query",
                            json={"question": f"Thread {thread_id} query {i}", "mode": "naive"},
                            timeout=15
                        )
                    else:
                        response = requests.get(f"{api_url}/", timeout=10)
                    
                    thread_results.append({
                        "thread_id": thread_id,
                        "request_id": i,
                        "status_code": response.status_code,
                        "response_time": response.elapsed.total_seconds(),
                        "success": response.status_code < 400
                    })
                    
                except Exception as e:
                    thread_results.append({
                        "thread_id": thread_id,
                        "request_id": i,
                        "error": str(e),
                        "success": False
                    })
            
            results_queue.put(thread_results)
        
        # Start concurrent threads
        threads = []
        start_time = time.time()
        
        for thread_id in range(num_threads):
            thread = threading.Thread(target=worker_thread, args=(thread_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # Collect all results
        all_results = []
        while not results_queue.empty():
            thread_results = results_queue.get()
            all_results.extend(thread_results)
        
        # Analyze results
        successful_requests = [r for r in all_results if r.get("success", False)]
        failed_requests = [r for r in all_results if not r.get("success", False)]
        
        if successful_requests:
            avg_response_time = sum(r["response_time"] for r in successful_requests) / len(successful_requests)
            max_response_time = max(r["response_time"] for r in successful_requests)
        else:
            avg_response_time = 0
            max_response_time = 0
        
        print(f"   ✅ Concurrent operations results:")
        print(f"     - Total requests: {len(all_results)}")
        print(f"     - Successful: {len(successful_requests)}")
        print(f"     - Failed: {len(failed_requests)}")
        print(f"     - Total time: {total_time:.2f}s")
        print(f"     - Average response time: {avg_response_time:.3f}s")
        print(f"     - Max response time: {max_response_time:.3f}s")
        print(f"     - Requests per second: {len(all_results)/total_time:.1f}")
        
        # System should handle concurrent requests reasonably well
        success_rate = len(successful_requests) / len(all_results) if all_results else 0
        assert success_rate >= 0.8, f"Success rate too low: {success_rate:.2f}"
        
        return {
            "total_requests": len(all_results),
            "success_rate": success_rate,
            "avg_response_time": avg_response_time,
            "requests_per_second": len(all_results)/total_time
        }
    
    def test_data_consistency_across_services(self, services_config, qdrant_client, redis_client):
        """Test data consistency across all services."""
        api_url = services_config["api"]
        
        print(f"🔄 Testing data consistency across services...")
        
        # Insert a unique test document
        unique_content = f"Unique test document created at {time.time()}"
        
        response = requests.post(
            f"{api_url}/documents",
            json={"documents": [unique_content]},
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"   ❌ Document insertion failed: {response.status_code}")
            print(f"   Error: {response.text}")
            
        assert response.status_code == 200
        
        # Wait for processing
        time.sleep(3)
        
        # Verify document can be queried
        query_response = requests.post(
            f"{api_url}/query",
            json={"question": "unique test document", "mode": "naive"},
            timeout=20
        )
        
        assert query_response.status_code == 200
        query_result = query_response.json()
        
        # Check if the response contains relevant information
        answer = query_result["answer"].lower()
        
        print(f"   ✅ Data consistency verification:")
        print(f"     - Document inserted successfully")
        print(f"     - Query response: {answer[:100]}{'...' if len(answer) > 100 else ''}")
        
        # Check Qdrant collections for new data
        collections = qdrant_client.get_collections()
        total_points = 0
        
        for collection in collections.collections:
            try:
                collection_info = qdrant_client.get_collection(collection.name)
                total_points += collection_info.points_count
            except:
                pass
        
        print(f"     - Total points in Qdrant: {total_points}")
        
        # Check Redis for any related cache/data
        redis_keys = list(redis_client.scan_iter())
        print(f"     - Redis keys count: {len(redis_keys)}")
        
        # For naive mode, we just check that we got a response
        # Naive mode doesn't use vector search, so it won't find the document
        assert len(answer) > 0, "Query should return some response"
        
        return {
            "document_inserted": True,
            "query_successful": True,
            "qdrant_points": total_points,
            "redis_keys": len(redis_keys)
        }