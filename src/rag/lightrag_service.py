#!/usr/bin/env python3
"""LightRAG Service with native Ollama integration"""

import asyncio
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

from lightrag import LightRAG, QueryParam
from lightrag.llm.ollama import ollama_model_complete, ollama_embed
from lightrag.utils import EmbeddingFunc

logger = logging.getLogger(__name__)


class LightRAGService:
    """LightRAG service using Ollama for both LLM and embeddings"""
    
    def __init__(self, 
                 working_dir: str = "./rag_data",
                 llm_host: str = "http://localhost:12434",
                 llm_model: str = "qwen2.5:7b-instruct",
                 embedding_model: str = "nomic-embed-text",
                 embedding_dim: int = 768):
        
        self.working_dir = working_dir
        self.llm_host = llm_host
        self.llm_model = llm_model
        self.embedding_model = embedding_model
        self.embedding_dim = embedding_dim
        self.rag = None
        
        # Create working directory
        os.makedirs(self.working_dir, exist_ok=True)
        
    async def initialize(self):
        """Initialize LightRAG with Ollama"""
        logger.info("Initializing LightRAG service...")
        
        # Import shared storage module to initialize pipeline status
        from lightrag.kg.shared_storage import initialize_pipeline_status
        
        # Configure LightRAG
        self.rag = LightRAG(
            working_dir=self.working_dir,
            llm_model_func=ollama_model_complete,
            llm_model_name=self.llm_model,
            llm_model_max_token_size=32768,
            llm_model_kwargs={
                "host": self.llm_host,
                "options": {"num_ctx": 8192},
                "timeout": 300,
            },
            embedding_func=EmbeddingFunc(
                embedding_dim=self.embedding_dim,
                max_token_size=8192,
                func=lambda texts: ollama_embed(
                    texts,
                    embed_model=self.embedding_model,
                    host=self.llm_host,
                ),
            ),
        )
        
        # Initialize pipeline status before storages
        await initialize_pipeline_status()
        
        await self.rag.initialize_storages()
        logger.info("LightRAG initialized successfully")
        
    async def insert_documents(self, documents: List[str]):
        """Insert documents into LightRAG"""
        logger.info(f"Inserting {len(documents)} documents...")
        
        for i, doc in enumerate(documents):
            await self.rag.ainsert(doc)
            logger.info(f"Inserted document {i+1}/{len(documents)}")
    
    async def query(self, 
                   question: str, 
                   mode: str = "hybrid",
                   stream: bool = False) -> str:
        """Query LightRAG"""
        logger.info(f"Querying: {question} (mode: {mode})")
        
        param = QueryParam(mode=mode, stream=stream)
        response = await self.rag.aquery(question, param=param)
        
        if stream:
            # Handle streaming response
            full_response = ""
            async for chunk in response:
                full_response += chunk
            return full_response
        else:
            return response
    
    async def get_graph_data(self) -> Dict[str, Any]:
        """Get knowledge graph data"""
        if not self.rag:
            return {
                "nodes": [],
                "edges": [],
                "stats": {"node_count": 0, "edge_count": 0}
            }
        
        # This would need to be implemented based on LightRAG's actual API
        # For now, returning a placeholder structure
        return {
            "nodes": [],
            "edges": [],
            "stats": {"node_count": 0, "edge_count": 0}
        }
    
    async def close(self):
        """Cleanup resources"""
        if self.rag:
            await self.rag.llm_response_cache.index_done_callback()
            await self.rag.finalize_storages()


async def demo():
    """Simple demo of LightRAG service"""
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize service
    service = LightRAGService()
    await service.initialize()
    
    # Sample documents
    documents = [
        """Retrieval-Augmented Generation (RAG) is an AI framework that combines 
        information retrieval with text generation. RAG systems first retrieve relevant 
        documents from a knowledge base, then use these documents as context for 
        generating responses. This approach significantly reduces hallucinations and 
        improves factual accuracy.""",
        
        """Vector databases are essential for RAG systems. They store document embeddings 
        as high-dimensional vectors and enable fast similarity search. Popular vector 
        databases include Qdrant, Pinecone, and Weaviate. These databases use algorithms 
        like HNSW for efficient nearest neighbor search.""",
        
        """LightRAG is a simple and fast RAG framework that uses a graph-based approach 
        for knowledge representation. It creates entity and relationship graphs from 
        documents, enabling both local and global search strategies. This dual approach 
        allows for better context understanding and more accurate responses."""
    ]
    
    # Insert documents
    await service.insert_documents(documents)
    
    # Test queries
    queries = [
        ("What is RAG?", "naive"),
        ("How do vector databases work?", "local"),
        ("What makes LightRAG different?", "global"),
        ("Explain the complete RAG architecture", "hybrid")
    ]
    
    for question, mode in queries:
        print(f"\n{'='*70}")
        print(f"Question: {question}")
        print(f"Mode: {mode}")
        print(f"{'='*70}")
        
        response = await service.query(question, mode=mode)
        print(f"Response: {response}")
    
    # Cleanup
    await service.close()


if __name__ == "__main__":
    asyncio.run(demo())