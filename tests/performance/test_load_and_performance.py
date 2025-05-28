"""Load testing and performance validation tests."""

import pytest
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics
import psutil
import os
from fastapi import status


class TestLoadTesting:
    """Load testing for API endpoints."""
    
    def test_sustained_load_health_endpoint(self, test_client):
        """Test sustained load on health endpoint."""
        def make_health_request():
            start_time = time.time()
            response = test_client.get("/health")
            end_time = time.time()
            return {
                "status_code": response.status_code,
                "response_time": end_time - start_time,
                "success": response.status_code == 200
            }
        
        # Run 50 requests with 10 concurrent workers
        results = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_health_request) for _ in range(50)]
            results = [future.result() for future in as_completed(futures)]
        
        # Analyze results
        success_rate = sum(1 for r in results if r["success"]) / len(results)
        response_times = [r["response_time"] for r in results]
        avg_response_time = statistics.mean(response_times)
        p95_response_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
        
        # Performance assertions
        assert success_rate >= 0.95  # 95% success rate
        assert avg_response_time < 1.0  # Average under 1 second
        assert p95_response_time < 2.0  # 95% under 2 seconds
        
        print(f"Load test results: {success_rate:.2%} success, "
              f"avg: {avg_response_time:.3f}s, p95: {p95_response_time:.3f}s")
    
    def test_burst_load_handling(self, test_client):
        """Test handling of sudden burst load."""
        def burst_request():
            return test_client.get("/")
        
        # Create a sudden burst of 20 requests
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(burst_request) for _ in range(20)]
            responses = [future.result() for future in as_completed(futures)]
        end_time = time.time()
        
        # All requests should complete successfully
        success_count = sum(1 for r in responses if r.status_code == 200)
        assert success_count >= 18  # At least 90% success
        
        # Burst should complete reasonably quickly
        total_time = end_time - start_time
        assert total_time < 10.0  # Complete within 10 seconds
    
    def test_mixed_endpoint_load(self, test_client):
        """Test load across different endpoints simultaneously."""
        def make_mixed_requests():
            endpoints = ["/", "/health", "/metrics"]
            results = []
            
            for endpoint in endpoints:
                start_time = time.time()
                response = test_client.get(endpoint)
                end_time = time.time()
                results.append({
                    "endpoint": endpoint,
                    "status_code": response.status_code,
                    "response_time": end_time - start_time
                })
            return results
        
        # Run mixed load with 5 workers
        all_results = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_mixed_requests) for _ in range(10)]
            for future in as_completed(futures):
                all_results.extend(future.result())
        
        # Group results by endpoint
        by_endpoint = {}
        for result in all_results:
            endpoint = result["endpoint"]
            if endpoint not in by_endpoint:
                by_endpoint[endpoint] = []
            by_endpoint[endpoint].append(result)
        
        # Check each endpoint performed well
        for endpoint, results in by_endpoint.items():
            success_rate = sum(1 for r in results if r["status_code"] == 200) / len(results)
            avg_time = statistics.mean([r["response_time"] for r in results])
            
            assert success_rate >= 0.9  # 90% success rate per endpoint
            assert avg_time < 2.0  # Average under 2 seconds
            
            print(f"{endpoint}: {success_rate:.2%} success, avg: {avg_time:.3f}s")


class TestPerformanceBenchmarks:
    """Performance benchmark tests."""
    
    def test_response_time_benchmarks(self, test_client):
        """Test response time benchmarks for different endpoints."""
        benchmarks = {
            "/": 0.5,  # API info should be under 500ms
            "/health": 0.3,  # Health check under 300ms  
            "/metrics": 1.0,  # Metrics under 1 second
        }
        
        for endpoint, max_time in benchmarks.items():
            times = []
            
            # Test each endpoint 10 times
            for _ in range(10):
                start_time = time.time()
                response = test_client.get(endpoint)
                end_time = time.time()
                
                assert response.status_code == 200
                times.append(end_time - start_time)
            
            avg_time = statistics.mean(times)
            max_observed = max(times)
            
            assert avg_time < max_time, f"{endpoint} avg time {avg_time:.3f}s > {max_time}s"
            assert max_observed < max_time * 2, f"{endpoint} max time {max_observed:.3f}s too high"
            
            print(f"{endpoint}: avg={avg_time:.3f}s, max={max_observed:.3f}s")
    
    def test_throughput_benchmarks(self, test_client):
        """Test throughput benchmarks."""
        def make_request():
            return test_client.get("/health")
        
        # Measure requests per second
        start_time = time.time()
        request_count = 30
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(request_count)]
            responses = [future.result() for future in as_completed(futures)]
        
        end_time = time.time()
        duration = end_time - start_time
        throughput = request_count / duration
        
        # Should handle at least 10 requests per second
        assert throughput >= 10.0, f"Throughput {throughput:.1f} req/s too low"
        
        # All requests should succeed
        success_count = sum(1 for r in responses if r.status_code == 200)
        assert success_count == request_count
        
        print(f"Throughput: {throughput:.1f} requests/second")
    
    def test_memory_usage_under_load(self, test_client):
        """Test memory usage under load."""
        import gc
        
        # Get initial memory usage
        gc.collect()  # Force garbage collection
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Generate load
        def make_requests():
            for _ in range(20):
                test_client.get("/health")
                test_client.post("/query", json={"question": "Test", "mode": "hybrid"})
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(make_requests) for _ in range(3)]
            for future in as_completed(futures):
                future.result()
        
        # Check memory after load
        gc.collect()
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        memory_increase_mb = memory_increase / (1024 * 1024)
        
        # Memory increase should be reasonable (under 100MB for this load)
        assert memory_increase_mb < 100, f"Memory increased by {memory_increase_mb:.1f}MB"
        
        print(f"Memory increase: {memory_increase_mb:.1f}MB")


class TestScalabilityLimits:
    """Test scalability limits and breaking points."""
    
    def test_maximum_concurrent_connections(self, test_client):
        """Test behavior at maximum concurrent connections."""
        def long_running_request():
            # Simulate a request that takes some time
            response = test_client.post(
                "/query",
                json={"question": "Long running query", "mode": "hybrid"}
            )
            return response.status_code
        
        # Test with increasing concurrency
        max_workers = 20
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(long_running_request) for _ in range(max_workers)]
            results = [future.result() for future in as_completed(futures)]
        
        # Most requests should succeed
        success_count = sum(1 for status in results if status == 200)
        success_rate = success_count / len(results)
        
        assert success_rate >= 0.8  # At least 80% should succeed
        print(f"Concurrent connections test: {success_rate:.2%} success rate")
    
    def test_large_payload_handling(self, test_client):
        """Test handling of large payloads."""
        # Test with increasingly large document sizes
        sizes = [1000, 10000, 100000, 500000]  # Characters
        
        for size in sizes:
            large_doc = "x" * size
            
            start_time = time.time()
            response = test_client.post(
                "/documents",
                json={"documents": [large_doc]}
            )
            end_time = time.time()
            
            processing_time = end_time - start_time
            
            if size <= 100000:  # Under 100KB should definitely work
                assert response.status_code == 200
                assert processing_time < 10.0  # Should complete in 10 seconds
            elif size <= 500000:  # 500KB might work depending on limits
                assert response.status_code in [200, 413, 422]
            
            print(f"Size {size}: status={response.status_code}, time={processing_time:.2f}s")
    
    def test_many_small_requests_performance(self, test_client):
        """Test performance with many small requests."""
        start_time = time.time()
        
        # Make 100 small requests sequentially
        for i in range(100):
            response = test_client.get("/health")
            assert response.status_code == 200
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time_per_request = total_time / 100
        
        # Should complete in reasonable time
        assert total_time < 30.0  # Under 30 seconds total
        assert avg_time_per_request < 0.3  # Under 300ms per request
        
        print(f"100 sequential requests: {total_time:.2f}s total, "
              f"{avg_time_per_request:.3f}s average")


class TestResourceUtilization:
    """Test resource utilization patterns."""
    
    def test_cpu_usage_under_load(self, test_client):
        """Test CPU usage under sustained load."""
        import time
        import psutil
        
        # Measure CPU before load
        cpu_percent_before = psutil.cpu_percent(interval=1)
        
        def cpu_intensive_requests():
            for _ in range(10):
                # Make requests that might be CPU intensive
                test_client.post("/query", json={"question": "Complex query", "mode": "hybrid"})
                test_client.post("/documents", json={"documents": ["Doc"] * 10})
        
        # Generate CPU load
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(cpu_intensive_requests) for _ in range(4)]
            for future in as_completed(futures):
                future.result()
        end_time = time.time()
        
        # Measure CPU after load
        time.sleep(1)  # Let CPU settle
        cpu_percent_after = psutil.cpu_percent(interval=1)
        
        load_duration = end_time - start_time
        
        print(f"CPU usage: before={cpu_percent_before:.1f}%, "
              f"after={cpu_percent_after:.1f}%, duration={load_duration:.1f}s")
        
        # Test completed successfully (CPU measurements are informational)
        assert load_duration < 60.0  # Should complete within a minute
    
    def test_file_descriptor_usage(self, test_client):
        """Test file descriptor usage doesn't leak."""
        import psutil
        
        process = psutil.Process(os.getpid())
        initial_fds = process.num_fds() if hasattr(process, 'num_fds') else 0
        
        # Make many requests that could potentially leak file descriptors
        for _ in range(50):
            test_client.get("/health")
            test_client.get("/metrics")
        
        final_fds = process.num_fds() if hasattr(process, 'num_fds') else 0
        fd_increase = final_fds - initial_fds
        
        # File descriptor usage shouldn't increase significantly
        assert fd_increase < 10, f"File descriptors increased by {fd_increase}"
        
        print(f"File descriptors: initial={initial_fds}, final={final_fds}")


class TestDegradationPatterns:
    """Test graceful degradation under stress."""
    
    def test_response_time_degradation(self, test_client):
        """Test how response times degrade under increasing load."""
        load_levels = [1, 5, 10, 15]  # Concurrent requests
        results = {}
        
        for load_level in load_levels:
            def make_request():
                start = time.time()
                response = test_client.get("/health") 
                end = time.time()
                return end - start, response.status_code
            
            # Test at this load level
            with ThreadPoolExecutor(max_workers=load_level) as executor:
                futures = [executor.submit(make_request) for _ in range(load_level)]
                times_and_codes = [future.result() for future in as_completed(futures)]
            
            times = [t for t, c in times_and_codes if c == 200]
            success_rate = len(times) / len(times_and_codes)
            avg_time = statistics.mean(times) if times else float('inf')
            
            results[load_level] = {
                "avg_time": avg_time,
                "success_rate": success_rate
            }
            
            print(f"Load {load_level}: avg_time={avg_time:.3f}s, "
                  f"success_rate={success_rate:.2%}")
        
        # Response times shouldn't degrade too dramatically
        baseline_time = results[1]["avg_time"]
        high_load_time = results[15]["avg_time"]
        
        # High load shouldn't be more than 5x slower than baseline
        if baseline_time > 0:
            degradation_factor = high_load_time / baseline_time
            assert degradation_factor < 5.0, f"Response time degraded {degradation_factor:.1f}x"
        
        # Success rate should remain high even under load
        assert results[15]["success_rate"] >= 0.8  # 80% success even at high load