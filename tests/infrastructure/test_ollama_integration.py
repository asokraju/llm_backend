"""Infrastructure tests for Ollama LLM and embedding integration."""

import pytest
import asyncio
import json
import time
import numpy as np
from typing import List, Dict, Any
import requests
import aiohttp


class TestOllamaIntegration:
    """Test Ollama LLM and embedding functionality."""
    
    @pytest.fixture
    def ollama_url(self):
        """Ollama base URL."""
        return "http://localhost:11434"
    
    def test_ollama_connectivity(self, ollama_url):
        """Test basic Ollama connectivity."""
        # Test Ollama version endpoint
        response = requests.get(f"{ollama_url}/api/version", timeout=10)
        assert response.status_code == 200
        
        version_data = response.json()
        assert "version" in version_data
        
        print(f"✅ Ollama connected successfully.")
        print(f"   - Version: {version_data['version']}")
        
        # Test Ollama tags (models) endpoint
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        assert response.status_code == 200
        
        models_data = response.json()
        models = models_data.get("models", [])
        
        print(f"   - Available models: {len(models)}")
        for model in models:
            print(f"     - {model['name']} ({model['size'] // (1024*1024*1024):.1f}GB)")
    
    def test_required_models_available(self, ollama_url):
        """Test that required models are available."""
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        assert response.status_code == 200
        
        models_data = response.json()
        available_models = [model["name"] for model in models_data.get("models", [])]
        
        # Required models for our RAG system
        required_models = [
            "qwen2.5:7b-instruct",  # LLM model
            "nomic-embed-text:latest"  # Embedding model
        ]
        
        missing_models = []
        found_models = []
        
        for required in required_models:
            found = False
            for available in available_models:
                if required in available or available in required:
                    found_models.append(available)
                    found = True
                    break
            if not found:
                missing_models.append(required)
        
        print(f"✅ Required models check:")
        print(f"   - Required: {required_models}")
        print(f"   - Found: {found_models}")
        if missing_models:
            print(f"   - Missing: {missing_models}")
        
        assert len(missing_models) == 0, f"Missing required models: {missing_models}"
        assert len(found_models) >= 2, f"Not enough models found: {found_models}"
    
    def test_llm_text_generation(self, ollama_url):
        """Test LLM text generation functionality."""
        # Test data
        test_prompt = "Explain what artificial intelligence is in one sentence."
        
        request_data = {
            "model": "qwen2.5:7b-instruct",
            "prompt": test_prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "max_tokens": 100
            }
        }
        
        print(f"🔄 Testing LLM generation with prompt: '{test_prompt}'")
        
        start_time = time.time()
        response = requests.post(
            f"{ollama_url}/api/generate",
            json=request_data,
            timeout=30
        )
        generation_time = time.time() - start_time
        
        assert response.status_code == 200
        
        result = response.json()
        assert "response" in result
        assert len(result["response"].strip()) > 0
        
        generated_text = result["response"]
        prompt_eval_count = result.get("prompt_eval_count", 0)
        eval_count = result.get("eval_count", 0)
        total_duration = result.get("total_duration", 0) / 1e9  # Convert to seconds
        
        print(f"✅ LLM generation successful:")
        print(f"   - Generated text: {generated_text[:100]}{'...' if len(generated_text) > 100 else ''}")
        print(f"   - Prompt tokens: {prompt_eval_count}")
        print(f"   - Generated tokens: {eval_count}")
        print(f"   - Total time: {total_duration:.2f}s")
        print(f"   - Tokens/second: {eval_count/total_duration:.1f}" if total_duration > 0 else "")
        
        # Verify response quality
        assert len(generated_text.split()) >= 5, "Response too short"
        assert "artificial intelligence" in generated_text.lower() or "ai" in generated_text.lower()
    
    def test_streaming_llm_generation(self, ollama_url):
        """Test streaming LLM text generation."""
        request_data = {
            "model": "qwen2.5:7b-instruct",
            "prompt": "List three benefits of renewable energy:",
            "stream": True,
            "options": {
                "temperature": 0.5,
                "max_tokens": 150
            }
        }
        
        print(f"🔄 Testing streaming LLM generation...")
        
        response = requests.post(
            f"{ollama_url}/api/generate",
            json=request_data,
            stream=True,
            timeout=30
        )
        
        assert response.status_code == 200
        
        # Collect streaming chunks
        chunks = []
        full_response = ""
        
        for line in response.iter_lines():
            if line:
                try:
                    chunk_data = json.loads(line.decode())
                    if "response" in chunk_data:
                        chunk_text = chunk_data["response"]
                        chunks.append(chunk_text)
                        full_response += chunk_text
                        
                    if chunk_data.get("done", False):
                        break
                        
                except json.JSONDecodeError:
                    continue
        
        print(f"✅ Streaming generation successful:")
        print(f"   - Total chunks received: {len(chunks)}")
        print(f"   - Full response: {full_response[:150]}{'...' if len(full_response) > 150 else ''}")
        
        assert len(chunks) > 1, "Should receive multiple chunks"
        assert len(full_response.strip()) > 0, "Should generate non-empty response"
        assert "renewable" in full_response.lower() or "energy" in full_response.lower()
    
    def test_embedding_generation(self, ollama_url):
        """Test embedding generation functionality."""
        test_texts = [
            "Artificial intelligence is transforming technology.",
            "Machine learning enables computers to learn from data.",
            "Deep learning uses neural networks with multiple layers."
        ]
        
        embeddings_results = []
        
        for text in test_texts:
            request_data = {
                "model": "nomic-embed-text",
                "prompt": text
            }
            
            print(f"🔄 Generating embedding for: '{text[:50]}...'")
            
            start_time = time.time()
            response = requests.post(
                f"{ollama_url}/api/embeddings",
                json=request_data,
                timeout=15
            )
            embedding_time = time.time() - start_time
            
            assert response.status_code == 200
            
            result = response.json()
            assert "embedding" in result
            
            embedding = result["embedding"]
            assert isinstance(embedding, list), "Embedding should be a list"
            assert len(embedding) > 0, "Embedding should not be empty"
            
            embeddings_results.append({
                "text": text,
                "embedding": embedding,
                "time": embedding_time
            })
            
            print(f"   - Embedding dimensions: {len(embedding)}")
            print(f"   - Generation time: {embedding_time:.3f}s")
        
        # Verify embedding properties
        embedding_dims = [len(result["embedding"]) for result in embeddings_results]
        assert all(dim == embedding_dims[0] for dim in embedding_dims), "All embeddings should have same dimensions"
        
        # Test similarity calculation
        emb1 = np.array(embeddings_results[0]["embedding"])
        emb2 = np.array(embeddings_results[1]["embedding"])
        emb3 = np.array(embeddings_results[2]["embedding"])
        
        # Calculate cosine similarities
        sim_1_2 = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        sim_1_3 = np.dot(emb1, emb3) / (np.linalg.norm(emb1) * np.linalg.norm(emb3))
        sim_2_3 = np.dot(emb2, emb3) / (np.linalg.norm(emb2) * np.linalg.norm(emb3))
        
        print(f"✅ Embedding generation successful:")
        print(f"   - Embedding dimensions: {len(embeddings_results[0]['embedding'])}")
        print(f"   - Similarity AI-ML: {sim_1_2:.3f}")
        print(f"   - Similarity AI-DL: {sim_1_3:.3f}")
        print(f"   - Similarity ML-DL: {sim_2_3:.3f}")
        
        # All texts are related, so similarities should be positive
        assert sim_1_2 > 0.3, f"AI and ML texts should be similar: {sim_1_2}"
        assert sim_1_3 > 0.3, f"AI and DL texts should be similar: {sim_1_3}"
        assert sim_2_3 > 0.3, f"ML and DL texts should be similar: {sim_2_3}"
    
    def test_batch_embedding_performance(self, ollama_url):
        """Test embedding generation performance with multiple texts."""
        # Generate test texts
        test_texts = [
            f"This is test document number {i} about various topics in technology."
            for i in range(10)
        ]
        
        print(f"🔄 Testing batch embedding generation for {len(test_texts)} texts...")
        
        start_time = time.time()
        embeddings = []
        
        for i, text in enumerate(test_texts):
            request_data = {
                "model": "nomic-embed-text",
                "prompt": text
            }
            
            response = requests.post(
                f"{ollama_url}/api/embeddings",
                json=request_data,
                timeout=10
            )
            
            assert response.status_code == 200
            result = response.json()
            embeddings.append(result["embedding"])
            
            if (i + 1) % 5 == 0:
                print(f"   - Processed {i + 1}/{len(test_texts)} embeddings")
        
        total_time = time.time() - start_time
        avg_time_per_embedding = total_time / len(test_texts)
        
        print(f"✅ Batch embedding performance:")
        print(f"   - Total texts: {len(test_texts)}")
        print(f"   - Total time: {total_time:.2f}s")
        print(f"   - Average time per embedding: {avg_time_per_embedding:.3f}s")
        print(f"   - Throughput: {len(test_texts)/total_time:.1f} embeddings/sec")
        
        # Verify all embeddings generated
        assert len(embeddings) == len(test_texts)
        assert all(len(emb) > 0 for emb in embeddings)
        
        # Performance should be reasonable
        assert avg_time_per_embedding < 2.0, f"Embedding generation too slow: {avg_time_per_embedding:.3f}s"
    
    @pytest.mark.asyncio
    async def test_async_ollama_operations(self, ollama_url):
        """Test async Ollama operations."""
        async def generate_embedding_async(session, text):
            request_data = {
                "model": "nomic-embed-text",
                "prompt": text
            }
            
            async with session.post(
                f"{ollama_url}/api/embeddings",
                json=request_data,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                assert response.status == 200
                result = await response.json()
                return result["embedding"]
        
        async def generate_text_async(session, prompt):
            request_data = {
                "model": "qwen2.5:7b-instruct",
                "prompt": prompt,
                "stream": False,
                "options": {"max_tokens": 50}
            }
            
            async with session.post(
                f"{ollama_url}/api/generate",
                json=request_data,
                timeout=aiohttp.ClientTimeout(total=20)
            ) as response:
                assert response.status == 200
                result = await response.json()
                return result["response"]
        
        print(f"🔄 Testing async Ollama operations...")
        
        async with aiohttp.ClientSession() as session:
            # Test concurrent embedding generation
            texts = ["Text one", "Text two", "Text three"]
            
            start_time = time.time()
            embedding_tasks = [generate_embedding_async(session, text) for text in texts]
            embeddings = await asyncio.gather(*embedding_tasks)
            embedding_time = time.time() - start_time
            
            # Test concurrent text generation
            prompts = ["Say hello.", "Count to three.", "Name a color."]
            
            start_time = time.time()
            generation_tasks = [generate_text_async(session, prompt) for prompt in prompts]
            responses = await asyncio.gather(*generation_tasks)
            generation_time = time.time() - start_time
        
        print(f"✅ Async operations successful:")
        print(f"   - Concurrent embeddings: {len(embeddings)} in {embedding_time:.2f}s")
        print(f"   - Concurrent generations: {len(responses)} in {generation_time:.2f}s")
        
        # Verify results
        assert len(embeddings) == len(texts)
        assert len(responses) == len(prompts)
        assert all(len(emb) > 0 for emb in embeddings)
        assert all(len(resp.strip()) > 0 for resp in responses)
    
    def test_ollama_model_information(self, ollama_url):
        """Test getting detailed model information."""
        models_to_check = ["qwen2.5:7b-instruct", "nomic-embed-text"]
        
        for model_name in models_to_check:
            try:
                request_data = {"name": model_name}
                
                response = requests.post(
                    f"{ollama_url}/api/show",
                    json=request_data,
                    timeout=5
                )
                
                if response.status_code == 200:
                    model_info = response.json()
                    
                    print(f"✅ Model information for {model_name}:")
                    print(f"   - Modified: {model_info.get('modified_at', 'unknown')}")
                    print(f"   - Size: {model_info.get('size', 0) // (1024*1024):.1f} MB")
                    
                    if "details" in model_info:
                        details = model_info["details"]
                        print(f"   - Format: {details.get('format', 'unknown')}")
                        print(f"   - Family: {details.get('family', 'unknown')}")
                        print(f"   - Parameters: {details.get('parameter_size', 'unknown')}")
                        print(f"   - Quantization: {details.get('quantization_level', 'unknown')}")
                
            except Exception as e:
                print(f"⚠️  Could not get info for {model_name}: {e}")


class TestOllamaRAGIntegration:
    """Test Ollama integration with RAG system specifically."""
    
    def test_lightrag_ollama_configuration(self):
        """Test that LightRAG is configured to use Ollama correctly."""
        from src.rag.lightrag_service import LightRAGService
        
        # Create service instance to check configuration
        service = LightRAGService()
        
        print(f"✅ LightRAG Ollama configuration:")
        print(f"   - LLM host: {service.llm_host}")
        print(f"   - LLM model: {service.llm_model}")
        print(f"   - Embedding model: {service.embedding_model}")
        print(f"   - Embedding dimensions: {service.embedding_dim}")
        
        # Verify configuration matches available models
        assert "ollama" in service.llm_host.lower() or "11434" in service.llm_host
        assert service.llm_model in ["qwen2.5:7b-instruct", "qwen2.5:32b-instruct-q4_K_M"]
        assert service.embedding_model == "nomic-embed-text"
        assert service.embedding_dim == 768
    
    @pytest.mark.asyncio
    async def test_lightrag_with_real_ollama(self):
        """Test LightRAG service with real Ollama backend."""
        from src.rag.lightrag_service import LightRAGService
        
        # Create a temporary working directory
        import tempfile
        import shutil
        
        with tempfile.TemporaryDirectory() as temp_dir:
            service = LightRAGService(
                working_dir=temp_dir,
                llm_host="http://localhost:11434",
                llm_model="qwen2.5:7b-instruct",
                embedding_model="nomic-embed-text"
            )
            
            print(f"🔄 Testing LightRAG with real Ollama backend...")
            
            try:
                # Initialize the service
                await service.initialize()
                
                # Test document insertion
                test_documents = [
                    "LightRAG is a powerful framework for building RAG applications.",
                    "It integrates with Ollama for local LLM inference.",
                    "The system supports multiple query modes for different use cases."
                ]
                
                print(f"   - Inserting {len(test_documents)} test documents...")
                await service.insert_documents(test_documents)
                
                # Test querying
                test_query = "What is LightRAG?"
                
                print(f"   - Testing query: '{test_query}'")
                response = await service.query(test_query, mode="naive")
                
                print(f"✅ LightRAG + Ollama integration successful:")
                print(f"   - Documents inserted: {len(test_documents)}")
                print(f"   - Query response: {response[:100]}{'...' if len(response) > 100 else ''}")
                
                # Verify response quality
                assert len(response.strip()) > 10, "Response should not be empty"
                assert any(keyword in response.lower() for keyword in ["lightrag", "framework", "rag"])
                
                # Test different query modes
                modes = ["local", "global", "hybrid"]
                for mode in modes:
                    try:
                        mode_response = await service.query(test_query, mode=mode)
                        print(f"   - {mode} mode: {len(mode_response)} characters")
                        assert len(mode_response.strip()) > 0
                    except Exception as e:
                        print(f"   - {mode} mode failed: {e}")
                
            finally:
                await service.close()
    
    def test_ollama_health_for_monitoring(self, ollama_url="http://localhost:11434"):
        """Test Ollama health endpoints for monitoring integration."""
        # Test if Ollama provides health/metrics endpoints
        endpoints_to_check = [
            "/api/version",
            "/api/tags", 
            "/metrics",  # Might not exist
            "/health"    # Might not exist
        ]
        
        health_info = {}
        
        for endpoint in endpoints_to_check:
            try:
                response = requests.get(f"{ollama_url}{endpoint}", timeout=3)
                health_info[endpoint] = {
                    "status_code": response.status_code,
                    "available": response.status_code < 400,
                    "response_size": len(response.content)
                }
            except Exception as e:
                health_info[endpoint] = {
                    "status_code": None,
                    "available": False,
                    "error": str(e)
                }
        
        print(f"✅ Ollama health endpoints:")
        for endpoint, info in health_info.items():
            if info["available"]:
                print(f"   - {endpoint}: ✅ ({info['status_code']})")
            else:
                print(f"   - {endpoint}: ❌ (not available)")
        
        # At least version and tags should be available
        assert health_info["/api/version"]["available"], "Ollama version endpoint should be available"
        assert health_info["/api/tags"]["available"], "Ollama tags endpoint should be available"
        
        return health_info