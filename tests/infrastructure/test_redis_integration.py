"""Infrastructure tests for Redis caching and queue integration."""

import pytest
import asyncio
import json
import time
from typing import List, Dict, Any
import redis
import redis.asyncio as aioredis


class TestRedisIntegration:
    """Test Redis caching and queue functionality."""
    
    @pytest.fixture
    def redis_client(self):
        """Create Redis client."""
        return redis.Redis(host="localhost", port=6379, decode_responses=True)
    
    @pytest.fixture
    async def async_redis_client(self):
        """Create async Redis client."""
        client = aioredis.from_url("redis://localhost:6379", decode_responses=True)
        yield client
        await client.aclose()
    
    def test_redis_connectivity(self, redis_client):
        """Test basic Redis connectivity."""
        # Test ping
        ping_result = redis_client.ping()
        assert ping_result is True
        
        # Test info
        info = redis_client.info()
        assert "redis_version" in info
        assert info["connected_clients"] >= 1
        
        print(f"✅ Redis connected successfully.")
        print(f"   - Version: {info['redis_version']}")
        print(f"   - Connected clients: {info['connected_clients']}")
        print(f"   - Used memory: {info['used_memory_human']}")
    
    def test_basic_caching_operations(self, redis_client):
        """Test basic caching operations."""
        test_key = "test:cache:basic"
        test_value = "Hello Redis!"
        
        # Set and get
        redis_client.set(test_key, test_value)
        retrieved_value = redis_client.get(test_key)
        assert retrieved_value == test_value
        
        # Test expiration
        redis_client.setex(f"{test_key}:expiring", 1, "temporary")
        assert redis_client.get(f"{test_key}:expiring") == "temporary"
        time.sleep(1.1)
        assert redis_client.get(f"{test_key}:expiring") is None
        
        # Test JSON data
        json_data = {"key": "value", "number": 42, "list": [1, 2, 3]}
        redis_client.set(f"{test_key}:json", json.dumps(json_data))
        retrieved_json = json.loads(redis_client.get(f"{test_key}:json"))
        assert retrieved_json == json_data
        
        # Clean up
        redis_client.delete(test_key, f"{test_key}:json")
        
        print(f"✅ Basic caching operations test passed.")
    
    def test_queue_operations(self, redis_client):
        """Test Redis as a queue system."""
        queue_name = "test:queue"
        
        # Clean up first
        redis_client.delete(queue_name)
        
        # Test FIFO queue (list operations)
        items = ["task1", "task2", "task3"]
        
        # Push items to queue
        for item in items:
            redis_client.lpush(queue_name, item)
        
        # Check queue length
        queue_length = redis_client.llen(queue_name)
        assert queue_length == len(items)
        
        # Pop items from queue (FIFO)
        popped_items = []
        while redis_client.llen(queue_name) > 0:
            item = redis_client.rpop(queue_name)
            popped_items.append(item)
        
        assert popped_items == items
        
        # Test blocking pop (with timeout)
        redis_client.lpush(queue_name, "blocking_test")
        result = redis_client.brpop(queue_name, timeout=1)
        assert result == (queue_name, "blocking_test")
        
        # Clean up
        redis_client.delete(queue_name)
        
        print(f"✅ Queue operations test passed.")
    
    def test_advanced_data_structures(self, redis_client):
        """Test Redis advanced data structures."""
        # Test Sets
        set_key = "test:set"
        redis_client.delete(set_key)
        
        members = ["member1", "member2", "member3"]
        for member in members:
            redis_client.sadd(set_key, member)
        
        assert redis_client.scard(set_key) == len(members)
        assert redis_client.sismember(set_key, "member1") == 1
        assert redis_client.sismember(set_key, "nonexistent") == 0
        
        # Test Hashes (for structured data)
        hash_key = "test:hash"
        redis_client.delete(hash_key)
        
        hash_data = {"field1": "value1", "field2": "value2", "counter": "100"}
        redis_client.hset(hash_key, mapping=hash_data)
        
        assert redis_client.hget(hash_key, "field1") == "value1"
        assert redis_client.hgetall(hash_key) == hash_data
        
        # Test atomic increment
        redis_client.hincrby(hash_key, "counter", 5)
        assert redis_client.hget(hash_key, "counter") == "105"
        
        # Test Sorted Sets (for rankings/scoring)
        zset_key = "test:zset"
        redis_client.delete(zset_key)
        
        redis_client.zadd(zset_key, {"item1": 1.0, "item2": 2.0, "item3": 3.0})
        
        # Get by rank
        top_items = redis_client.zrevrange(zset_key, 0, 1, withscores=True)
        assert top_items[0] == ("item3", 3.0)
        
        # Clean up
        redis_client.delete(set_key, hash_key, zset_key)
        
        print(f"✅ Advanced data structures test passed.")
    
    @pytest.mark.asyncio
    async def test_async_redis_operations(self, async_redis_client):
        """Test async Redis operations."""
        test_key = "test:async"
        
        # Async set and get
        await async_redis_client.set(test_key, "async_value")
        value = await async_redis_client.get(test_key)
        assert value == "async_value"
        
        # Async pipeline
        pipe = async_redis_client.pipeline()
        pipe.set(f"{test_key}:1", "value1")
        pipe.set(f"{test_key}:2", "value2")
        pipe.get(f"{test_key}:1")
        pipe.get(f"{test_key}:2")
        results = await pipe.execute()
        
        assert results[2] == "value1"  # First get result
        assert results[3] == "value2"  # Second get result
        
        # Clean up
        await async_redis_client.delete(test_key, f"{test_key}:1", f"{test_key}:2")
        
        print(f"✅ Async Redis operations test passed.")
    
    def test_redis_performance(self, redis_client):
        """Test Redis performance with batch operations."""
        # Performance test with pipeline
        num_operations = 1000
        pipeline = redis_client.pipeline()
        
        start_time = time.time()
        
        # Batch set operations
        for i in range(num_operations):
            pipeline.set(f"perf:test:{i}", f"value_{i}")
        
        pipeline.execute()
        set_time = time.time() - start_time
        
        # Batch get operations
        pipeline = redis_client.pipeline()
        start_time = time.time()
        
        for i in range(num_operations):
            pipeline.get(f"perf:test:{i}")
        
        results = pipeline.execute()
        get_time = time.time() - start_time
        
        # Verify results
        assert len(results) == num_operations
        assert results[0] == "value_0"
        assert results[-1] == f"value_{num_operations-1}"
        
        # Clean up
        pipeline = redis_client.pipeline()
        for i in range(num_operations):
            pipeline.delete(f"perf:test:{i}")
        pipeline.execute()
        
        print(f"✅ Performance test passed.")
        print(f"   - {num_operations} SET operations in {set_time:.3f}s ({num_operations/set_time:.0f} ops/sec)")
        print(f"   - {num_operations} GET operations in {get_time:.3f}s ({num_operations/get_time:.0f} ops/sec)")


class TestRedisRAGIntegration:
    """Test Redis integration with RAG system specifically."""
    
    @pytest.fixture
    def redis_client(self):
        """Create Redis client."""
        return redis.Redis(host="localhost", port=6379, decode_responses=True)
    
    def test_llm_cache_simulation(self, redis_client):
        """Test LLM response caching simulation."""
        cache_prefix = "llm:cache"
        
        # Simulate LLM response caching
        query = "What is artificial intelligence?"
        query_hash = str(hash(query))
        cache_key = f"{cache_prefix}:{query_hash}"
        
        # Simulate expensive LLM call result
        llm_response = {
            "answer": "Artificial intelligence is the simulation of human intelligence in machines...",
            "model": "qwen2.5:7b-instruct", 
            "tokens": 150,
            "timestamp": time.time()
        }
        
        # Cache the response with 1 hour TTL
        redis_client.setex(cache_key, 3600, json.dumps(llm_response))
        
        # Retrieve from cache
        cached_result = redis_client.get(cache_key)
        assert cached_result is not None
        
        parsed_result = json.loads(cached_result)
        assert parsed_result["answer"] == llm_response["answer"]
        assert parsed_result["model"] == llm_response["model"]
        
        # Test cache hit statistics
        stats_key = "llm:stats:cache_hits"
        redis_client.incr(stats_key)
        
        cache_hits = int(redis_client.get(stats_key) or 0)
        assert cache_hits >= 1
        
        # Clean up
        redis_client.delete(cache_key, stats_key)
        
        print(f"✅ LLM cache simulation test passed.")
    
    def test_document_processing_queue(self, redis_client):
        """Test document processing queue simulation."""
        queue_name = "documents:processing"
        status_prefix = "document:status"
        
        # Clean up
        redis_client.delete(queue_name)
        
        # Simulate document processing workflow
        documents = [
            {"id": "doc1", "content": "Document about AI", "priority": "high"},
            {"id": "doc2", "content": "Document about ML", "priority": "normal"},
            {"id": "doc3", "content": "Document about NLP", "priority": "low"}
        ]
        
        # Add documents to processing queue
        for doc in documents:
            redis_client.lpush(queue_name, json.dumps(doc))
            # Set initial status
            redis_client.hset(f"{status_prefix}:{doc['id']}", mapping={
                "status": "queued",
                "queued_at": time.time(),
                "priority": doc["priority"]
            })
        
        assert redis_client.llen(queue_name) == len(documents)
        
        # Simulate processing
        processed_docs = []
        while redis_client.llen(queue_name) > 0:
            # Get next document
            doc_json = redis_client.rpop(queue_name)
            doc = json.loads(doc_json)
            
            # Update status to processing
            redis_client.hset(f"{status_prefix}:{doc['id']}", mapping={
                "status": "processing",
                "started_at": time.time()
            })
            
            # Simulate processing time
            time.sleep(0.1)
            
            # Update status to completed
            redis_client.hset(f"{status_prefix}:{doc['id']}", mapping={
                "status": "completed",
                "completed_at": time.time(),
                "vector_count": 5  # Simulated vector count
            })
            
            processed_docs.append(doc)
        
        assert len(processed_docs) == len(documents)
        
        # Verify all documents are marked as completed
        for doc in documents:
            status = redis_client.hget(f"{status_prefix}:{doc['id']}", "status")
            assert status == "completed"
        
        # Clean up
        for doc in documents:
            redis_client.delete(f"{status_prefix}:{doc['id']}")
        
        print(f"✅ Document processing queue test passed.")
    
    def test_metrics_collection(self, redis_client):
        """Test metrics collection for monitoring."""
        metrics_prefix = "metrics"
        
        # Simulate various metrics
        metrics = {
            "queries:total": 100,
            "queries:successful": 95,
            "queries:failed": 5,
            "documents:indexed": 1000,
            "vectors:created": 5000,
            "cache:hits": 80,
            "cache:misses": 20
        }
        
        # Store metrics
        for metric_name, value in metrics.items():
            redis_client.set(f"{metrics_prefix}:{metric_name}", value)
        
        # Test atomic increments (for real-time metrics)
        redis_client.incr(f"{metrics_prefix}:queries:total")
        redis_client.incr(f"{metrics_prefix}:queries:successful")
        
        # Verify metrics
        total_queries = int(redis_client.get(f"{metrics_prefix}:queries:total"))
        successful_queries = int(redis_client.get(f"{metrics_prefix}:queries:successful"))
        
        assert total_queries == 101  # Incremented from 100
        assert successful_queries == 96  # Incremented from 95
        
        # Test time-series metrics (using sorted sets)
        timeseries_key = f"{metrics_prefix}:response_times"
        current_time = time.time()
        
        # Add response time measurements
        response_times = [0.1, 0.2, 0.15, 0.3, 0.12]
        for i, rt in enumerate(response_times):
            redis_client.zadd(timeseries_key, {f"req_{i}": current_time + i})
            redis_client.hset(f"response_time:req_{i}", mapping={
                "duration": rt,
                "timestamp": current_time + i
            })
        
        # Get recent response times
        recent_requests = redis_client.zrevrange(timeseries_key, 0, 4)
        assert len(recent_requests) == 5
        
        # Clean up
        for metric_name in metrics.keys():
            redis_client.delete(f"{metrics_prefix}:{metric_name}")
        redis_client.delete(timeseries_key)
        for i in range(len(response_times)):
            redis_client.delete(f"response_time:req_{i}")
        
        print(f"✅ Metrics collection test passed.")
        print(f"   - Tracked {len(metrics)} different metrics")
        print(f"   - Response time tracking working")
        
    def test_redis_monitoring_info(self, redis_client):
        """Test Redis monitoring and health information."""
        # Get comprehensive Redis info
        info = redis_client.info()
        
        # Check important health metrics
        important_metrics = [
            'connected_clients',
            'used_memory',
            'used_memory_peak',
            'keyspace_hits',
            'keyspace_misses',
            'instantaneous_ops_per_sec',
            'total_commands_processed'
        ]
        
        print(f"✅ Redis health metrics:")
        for metric in important_metrics:
            if metric in info:
                print(f"   - {metric}: {info[metric]}")
        
        # Test slow log (commands taking too long)
        slow_log = redis_client.slowlog_get(10)
        print(f"   - Slow log entries: {len(slow_log)}")
        
        # Test memory usage
        memory_info = redis_client.memory_usage("dummy_key_that_doesnt_exist")
        # This will return None for non-existent keys, which is expected
        
        print(f"✅ Redis monitoring info retrieved successfully.")