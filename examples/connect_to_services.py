#!/usr/bin/env python3
"""
Example script showing how to connect to all services in the LightRAG Backend.

This demonstrates basic connectivity and operations for each service.
"""

import requests
import redis
import json
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import numpy as np
from datetime import datetime


def test_api_service():
    """Test main API service."""
    print("\n=== Testing API Service ===")
    base_url = "http://localhost:8000"
    
    # Health check
    response = requests.get(f"{base_url}/health")
    print(f"Health check: {response.json()}")
    
    # Insert a document
    doc_response = requests.post(
        f"{base_url}/documents",
        json={"documents": ["Artificial Intelligence is transforming the world."]}
    )
    print(f"Document insertion: {doc_response.json()}")
    
    # Query
    query_response = requests.post(
        f"{base_url}/query",
        json={"question": "What is AI transforming?", "mode": "naive"}
    )
    print(f"Query response: {query_response.json()['answer'][:100]}...")


def test_ollama_service():
    """Test Ollama LLM service."""
    print("\n=== Testing Ollama Service ===")
    base_url = "http://localhost:11434"
    
    # Check version
    version = requests.get(f"{base_url}/api/version")
    print(f"Ollama version: {version.json()}")
    
    # List models
    models = requests.get(f"{base_url}/api/tags")
    print(f"Available models: {[m['name'] for m in models.json()['models']]}")
    
    # Generate text
    generation = requests.post(
        f"{base_url}/api/generate",
        json={
            "model": "qwen2.5:7b-instruct",
            "prompt": "What is RAG in AI? Answer in one sentence.",
            "stream": False
        }
    )
    if generation.status_code == 200:
        print(f"Generated text: {generation.json()['response']}")
    
    # Generate embeddings
    embedding = requests.post(
        f"{base_url}/api/embeddings",
        json={
            "model": "nomic-embed-text",
            "prompt": "Artificial Intelligence"
        }
    )
    if embedding.status_code == 200:
        emb_vector = embedding.json()['embedding']
        print(f"Embedding dimensions: {len(emb_vector)}")


def test_qdrant_service():
    """Test Qdrant vector database."""
    print("\n=== Testing Qdrant Service ===")
    
    # Connect to Qdrant
    client = QdrantClient(host="localhost", port=6333)
    
    # Get collections
    collections = client.get_collections()
    print(f"Collections: {[col.name for col in collections.collections]}")
    
    # Create a test collection (if doesn't exist)
    test_collection = "test_examples"
    existing_collections = [col.name for col in collections.collections]
    
    if test_collection not in existing_collections:
        client.create_collection(
            collection_name=test_collection,
            vectors_config=VectorParams(size=768, distance=Distance.COSINE)
        )
        print(f"Created collection: {test_collection}")
    
    # Insert a test vector
    test_vector = np.random.rand(768).tolist()
    client.upsert(
        collection_name=test_collection,
        points=[
            PointStruct(
                id=1,
                vector=test_vector,
                payload={"text": "Example document", "timestamp": datetime.now().isoformat()}
            )
        ]
    )
    print("Inserted test vector")
    
    # Search similar vectors
    search_results = client.search(
        collection_name=test_collection,
        query_vector=test_vector,
        limit=3
    )
    print(f"Search results: {len(search_results)} similar vectors found")


def test_redis_service():
    """Test Redis cache/queue service."""
    print("\n=== Testing Redis Service ===")
    
    # Connect to Redis
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    
    # Test connection
    pong = r.ping()
    print(f"Redis ping: {'PONG' if pong else 'Failed'}")
    
    # Set and get a value
    r.set('test:example', 'Hello from Redis!', ex=60)  # Expires in 60 seconds
    value = r.get('test:example')
    print(f"Cached value: {value}")
    
    # Test queue operations
    queue_name = 'test:queue'
    r.lpush(queue_name, 'task1', 'task2', 'task3')
    print(f"Queue length: {r.llen(queue_name)}")
    
    # Pop from queue
    task = r.rpop(queue_name)
    print(f"Popped task: {task}")
    
    # Cleanup
    r.delete('test:example', queue_name)


def test_prometheus_service():
    """Test Prometheus metrics service."""
    print("\n=== Testing Prometheus Service ===")
    base_url = "http://localhost:9090"
    
    # Check health
    health = requests.get(f"{base_url}/-/healthy")
    print(f"Prometheus health: {health.text}")
    
    # Get targets
    targets = requests.get(f"{base_url}/api/v1/targets")
    active_targets = [t for t in targets.json()['data']['activeTargets'] if t['health'] == 'up']
    print(f"Active targets: {len(active_targets)}")
    
    # Query a metric
    query = requests.get(
        f"{base_url}/api/v1/query",
        params={"query": "up"}
    )
    if query.status_code == 200:
        results = query.json()['data']['result']
        print(f"Services up: {len(results)}")


def test_grafana_service():
    """Test Grafana visualization service."""
    print("\n=== Testing Grafana Service ===")
    base_url = "http://localhost:3000"
    
    # Check health
    health = requests.get(f"{base_url}/api/health")
    print(f"Grafana health: {health.json()}")
    
    # Get datasources (requires auth)
    # Default credentials: admin/admin
    datasources = requests.get(
        f"{base_url}/api/datasources",
        auth=('admin', 'admin')
    )
    if datasources.status_code == 200:
        ds_names = [ds['name'] for ds in datasources.json()]
        print(f"Datasources: {ds_names}")
    else:
        print("Note: Update admin password if changed from default")


def test_all_services():
    """Test all services connectivity."""
    print("=== LightRAG Backend Services Connection Test ===")
    print(f"Testing at: {datetime.now()}")
    
    services = [
        ("API", test_api_service),
        ("Ollama", test_ollama_service),
        ("Qdrant", test_qdrant_service),
        ("Redis", test_redis_service),
        ("Prometheus", test_prometheus_service),
        ("Grafana", test_grafana_service)
    ]
    
    for name, test_func in services:
        try:
            test_func()
        except Exception as e:
            print(f"\n❌ {name} test failed: {str(e)}")
    
    print("\n=== Test Complete ===")


if __name__ == "__main__":
    # Test individual services or all
    import sys
    
    if len(sys.argv) > 1:
        service = sys.argv[1].lower()
        if service == "api":
            test_api_service()
        elif service == "ollama":
            test_ollama_service()
        elif service == "qdrant":
            test_qdrant_service()
        elif service == "redis":
            test_redis_service()
        elif service == "prometheus":
            test_prometheus_service()
        elif service == "grafana":
            test_grafana_service()
        else:
            print(f"Unknown service: {service}")
            print("Available: api, ollama, qdrant, redis, prometheus, grafana")
    else:
        test_all_services()
        print("\nUsage: python connect_to_services.py [service_name]")
        print("Example: python connect_to_services.py ollama")