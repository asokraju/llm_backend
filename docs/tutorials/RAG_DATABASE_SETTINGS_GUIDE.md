# RAG Database Configuration Guide

A comprehensive guide to configuring LightRAG database building settings and their impact on performance, quality, and resource usage.

## Table of Contents

1. [Core Database Settings](#core-database-settings)
2. [Document Processing Settings](#document-processing-settings)
3. [LLM and Embedding Settings](#llm-and-embedding-settings)
4. [Vector Database Settings](#vector-database-settings)
5. [Knowledge Graph Settings](#knowledge-graph-settings)
6. [Performance and Resource Settings](#performance-and-resource-settings)
7. [Quality vs Performance Trade-offs](#quality-vs-performance-trade-offs)
8. [Environment-Specific Configurations](#environment-specific-configurations)

## Core Database Settings

### Working Directory
```python
working_dir = "./my_rag_database"
```
**Significance:**
- **Data Persistence**: Where all RAG data is stored (vectors, graphs, cache)
- **Multi-Database Support**: Different directories = different databases
- **Backup/Recovery**: Easy to backup entire RAG system
- **Disk Space**: Ensure sufficient space (can grow to GBs)

**Best Practices:**
- Use absolute paths for production
- Include database name/version in path
- Monitor disk usage regularly

### Database Type Selection
```python
# Vector Database Options
vector_db_type = "qdrant"  # qdrant, chroma, faiss, milvus
graph_db_type = "networkx"  # networkx, neo4j, age
kv_store_type = "json"     # json, redis, mongodb
```
**Significance:**
- **Scalability**: Different DBs handle different data sizes
- **Performance**: Query speed varies significantly
- **Features**: Advanced filtering, clustering capabilities
- **Resource Usage**: Memory vs disk trade-offs

## Document Processing Settings

### Text Chunking Parameters
```python
chunk_token_size = 1200        # Size of each text chunk
chunk_overlap_token_size = 100 # Overlap between chunks
tiktoken_model_name = "gpt-4"  # Tokenizer model
```
**Significance:**
- **Context Quality**: Larger chunks = more context, but may exceed LLM limits
- **Retrieval Precision**: Smaller chunks = more precise retrieval
- **Overlap**: Prevents context loss at chunk boundaries
- **Token Counting**: Accurate for cost estimation and LLM limits

**Recommendations:**
```python
# For technical documents (clinical, legal)
chunk_token_size = 800
chunk_overlap_token_size = 100

# For general knowledge documents  
chunk_token_size = 1200
chunk_overlap_token_size = 150

# For code documentation
chunk_token_size = 600
chunk_overlap_token_size = 50
```

### Document Loading Engine
```python
document_loading_engine = "DOCLING"  # DOCLING, pypdf2, unstructured
```
**Significance:**
- **DOCLING**: Superior structure preservation, tables, metadata
- **PyPDF2**: Fast, simple, but loses formatting
- **Unstructured**: Good for mixed document types

**Quality Comparison:**
| Engine | Structure | Tables | Speed | Memory |
|--------|-----------|--------|-------|--------|
| DOCLING | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| PyPDF2 | ⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Unstructured | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |

## LLM and Embedding Settings

### Model Selection
```python
# LLM Models (Text Generation)
llm_model = "qwen2.5:7b-instruct"     # Fast, good quality
llm_model = "qwen2.5:32b-instruct"    # Better quality, slower
llm_model = "llama3.3:70b-instruct"   # Best quality, requires powerful hardware

# Embedding Models (Vector Generation)
embedding_model = "nomic-embed-text"   # 768 dimensions, fast
embedding_model = "mxbai-embed-large"  # 1024 dimensions, better quality
```

**Model Comparison:**
| Model | VRAM | Speed | Quality | Use Case |
|-------|------|-------|---------|----------|
| qwen2.5:7b | 8GB | Fast | Good | Development, high throughput |
| qwen2.5:32b | 20GB | Medium | Better | Production, balanced |
| llama3.3:70b | 48GB+ | Slow | Best | Research, highest quality |

### LLM Parameters
```python
llm_max_tokens = 32768        # Maximum context length
llm_max_async = 16           # Concurrent LLM requests
llm_max_token_size = 8192    # Maximum response length
```
**Significance:**
- **Context Length**: Longer context = better understanding, more memory
- **Concurrency**: Higher = faster processing, more resource usage
- **Response Length**: Controls detail level of generated content

### Embedding Dimensions
```python
embedding_dim = 768    # Standard
embedding_dim = 1024   # Higher quality
embedding_dim = 1536   # Premium quality
```
**Trade-offs:**
- **Higher Dimensions**: Better semantic understanding, more storage
- **Lower Dimensions**: Faster similarity search, less memory
- **Standard**: 768 (good balance), 1024 (better quality)

## Vector Database Settings

### Qdrant Configuration
```python
qdrant_config = {
    "collection_name": "documents",
    "vector_size": 768,
    "distance": "Cosine",        # Cosine, Dot, Euclidean
    "storage_type": "InMemory",  # InMemory, Disk
    "replication_factor": 1,
    "shard_number": 1
}
```

### Distance Metrics
```python
distance_metric = "cosine"    # Most common for text
distance_metric = "dot"       # Faster, normalized vectors
distance_metric = "euclidean" # Geometric distance
```
**When to Use:**
- **Cosine**: Text similarity, angle-based (recommended)
- **Dot Product**: When vectors are normalized, fastest
- **Euclidean**: Magnitude matters, geometric data

### Search Parameters
```python
search_top_k = 20            # Number of candidates retrieved
rerank_top_k = 10           # Final results after reranking
similarity_threshold = 0.7   # Minimum similarity score
```

## Knowledge Graph Settings

### Entity Extraction
```python
entity_extract_max_gleaning = 1  # Rounds of entity refinement
entity_summary_to_max_tokens = 500  # Max tokens per entity summary
```
**Significance:**
- **Gleaning Rounds**: More rounds = better entities, slower processing
- **Entity Summary Length**: Longer = more detailed, more storage

### Relationship Extraction
```python
relation_max_gleaning = 1           # Relationship refinement rounds
relationship_summary_to_max_tokens = 500  # Max tokens per relationship
```

### Graph Construction
```python
max_graph_cluster_size = 10      # Community detection parameter
community_report_max_tokens = 1500  # Community summary length
```
**Impact:**
- **Cluster Size**: Smaller = more granular communities
- **Report Length**: Longer summaries = better global understanding

## Performance and Resource Settings

### Concurrency Settings
```python
max_async_concurrency = 16    # Concurrent operations
batch_size_for_insert = 10    # Documents per batch
max_retries = 3              # Retry failed operations
```

### Caching Configuration
```python
enable_llm_cache = True       # Cache LLM responses
cache_max_size = 1000        # Maximum cached responses
cache_ttl = 3600             # Cache time-to-live (seconds)
```
**Benefits:**
- **LLM Cache**: Dramatically speeds up repeated operations
- **Size Limits**: Prevents unbounded memory growth
- **TTL**: Ensures fresh responses for time-sensitive data

### Memory Management
```python
max_memory_usage = "8GB"      # Memory limit
disk_cache_size = "10GB"     # Disk cache limit
cleanup_threshold = 0.8      # Cleanup when 80% full
```

## Quality vs Performance Trade-offs

### High Quality Configuration (Slow)
```python
config_high_quality = {
    "chunk_token_size": 800,
    "chunk_overlap_token_size": 150,
    "llm_model": "qwen2.5:32b-instruct",
    "embedding_model": "mxbai-embed-large",
    "embedding_dim": 1024,
    "entity_extract_max_gleaning": 2,
    "relation_max_gleaning": 2,
    "search_top_k": 30,
    "rerank_top_k": 15
}
```

### Balanced Configuration (Recommended)
```python
config_balanced = {
    "chunk_token_size": 1200,
    "chunk_overlap_token_size": 100,
    "llm_model": "qwen2.5:7b-instruct",
    "embedding_model": "nomic-embed-text",
    "embedding_dim": 768,
    "entity_extract_max_gleaning": 1,
    "relation_max_gleaning": 1,
    "search_top_k": 20,
    "rerank_top_k": 10
}
```

### High Performance Configuration (Fast)
```python
config_high_performance = {
    "chunk_token_size": 1500,
    "chunk_overlap_token_size": 50,
    "llm_model": "qwen2.5:7b-instruct",
    "embedding_model": "nomic-embed-text",
    "embedding_dim": 768,
    "entity_extract_max_gleaning": 0,
    "relation_max_gleaning": 0,
    "search_top_k": 10,
    "rerank_top_k": 5,
    "max_async_concurrency": 32
}
```

## Environment-Specific Configurations

### Development Environment
```python
dev_config = {
    "working_dir": "./dev_rag_db",
    "llm_model": "qwen2.5:7b-instruct",
    "chunk_token_size": 1000,
    "max_async_concurrency": 4,
    "enable_logging": True,
    "log_level": "DEBUG"
}
```

### Production Environment
```python
prod_config = {
    "working_dir": "/data/production_rag_db",
    "llm_model": "qwen2.5:32b-instruct",
    "chunk_token_size": 1200,
    "max_async_concurrency": 16,
    "enable_llm_cache": True,
    "backup_interval": 3600,
    "health_check_interval": 300
}
```

### Resource-Constrained Environment
```python
lightweight_config = {
    "llm_model": "qwen2.5:7b-instruct",
    "embedding_dim": 384,  # Smaller dimensions
    "chunk_token_size": 800,
    "max_async_concurrency": 2,
    "vector_db_type": "faiss",  # Memory efficient
    "enable_disk_cache": True
}
```

## Advanced Configuration Examples

### Clinical Documents RAG
```python
clinical_config = {
    "document_loading_engine": "DOCLING",  # Preserve medical tables
    "chunk_token_size": 800,              # Smaller for precision
    "chunk_overlap_token_size": 150,      # High overlap for context
    "entity_types": ["MEDICATION", "PROCEDURE", "DIAGNOSIS"],
    "custom_prompts": {
        "entity_extraction": "Extract medical entities...",
        "relationship_extraction": "Find clinical relationships..."
    }
}
```

### Legal Documents RAG
```python
legal_config = {
    "chunk_token_size": 1500,    # Longer for legal context
    "citation_extraction": True,
    "section_aware_chunking": True,
    "entity_types": ["CASE", "STATUTE", "REGULATION"],
    "relationship_types": ["CITES", "OVERRULES", "DISTINGUISHES"]
}
```

### Code Documentation RAG
```python
code_config = {
    "chunk_token_size": 600,     # Shorter for code blocks
    "preserve_code_structure": True,
    "entity_types": ["FUNCTION", "CLASS", "MODULE"],
    "relationship_types": ["IMPORTS", "INHERITS", "CALLS"],
    "syntax_highlighting": True
}
```

## Monitoring and Optimization

### Performance Metrics to Track
```python
metrics_config = {
    "track_processing_time": True,
    "track_memory_usage": True,
    "track_query_latency": True,
    "track_cache_hit_rate": True,
    "export_to_prometheus": True
}
```

### Auto-Optimization Settings
```python
auto_optimize = {
    "enable_auto_tuning": True,
    "optimize_for": "speed",  # speed, quality, memory
    "learning_rate": 0.1,
    "optimization_interval": 1000  # Every 1000 operations
}
```

## Configuration Best Practices

### 1. Start Conservative
```python
# Begin with smaller, faster settings
initial_config = {
    "chunk_token_size": 1000,
    "max_async_concurrency": 4,
    "llm_model": "qwen2.5:7b-instruct"
}
```

### 2. Profile and Optimize
```python
# Monitor performance and gradually increase
def profile_and_adjust(config, metrics):
    if metrics.memory_usage < 0.7:
        config.max_async_concurrency += 2
    if metrics.query_latency > 5.0:
        config.search_top_k -= 5
    return config
```

### 3. Environment-Specific Tuning
```python
# Adjust based on hardware capabilities
import psutil

def auto_configure():
    ram_gb = psutil.virtual_memory().total / (1024**3)
    cpu_cores = psutil.cpu_count()
    
    if ram_gb > 32:
        return high_quality_config
    elif ram_gb > 16:
        return balanced_config
    else:
        return lightweight_config
```

## Configuration File Templates

### YAML Configuration
```yaml
# config.yaml
rag_database:
  working_dir: "./production_rag"
  
  document_processing:
    engine: "DOCLING"
    chunk_size: 1200
    overlap: 100
    
  models:
    llm: "qwen2.5:7b-instruct"
    embedding: "nomic-embed-text"
    
  performance:
    max_concurrency: 16
    batch_size: 10
    enable_cache: true
    
  quality:
    entity_gleaning: 1
    relation_gleaning: 1
    top_k: 20
```

### Environment Variables
```bash
# .env
RAG_WORKING_DIR=/data/rag_database
RAG_LLM_MODEL=qwen2.5:7b-instruct
RAG_EMBEDDING_MODEL=nomic-embed-text
RAG_CHUNK_SIZE=1200
RAG_MAX_CONCURRENCY=16
RAG_ENABLE_CACHE=true
```

## Summary

The key to successful RAG database configuration is understanding the trade-offs:

**For Development:**
- Prioritize speed and resource efficiency
- Use smaller models and conservative settings
- Enable detailed logging

**For Production:**
- Balance quality and performance
- Use larger models if resources allow
- Enable caching and monitoring

**For Specialized Domains:**
- Customize chunking strategies
- Use domain-specific entity types
- Adjust processing for document types

**Remember:** Start with conservative settings and incrementally optimize based on actual performance metrics and quality requirements.