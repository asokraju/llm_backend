# LightRAG Architecture & Data Flow

## System Overview

```mermaid
graph TB
    subgraph "Input Sources"
        USER[Users/Apps]
        FILES[File Uploads<br/>PDF/DOCX/HTML/MD]
        APIS[External APIs]
    end

    subgraph "Gateway Layer"
        NGINX[NGINX<br/>Load Balancer<br/>Rate Limiting<br/>SSL Termination]
    end

    subgraph "Application Layer"
        API[FastAPI<br/>REST Endpoints<br/>Auth & Validation<br/>Request Queue]
        
        subgraph "LightRAG Core"
            LRAG[LightRAG Service<br/>Orchestrator]
            DOCPROC[Document Processor<br/>Docling Integration]
            CHUNK[Text Chunker<br/>1200 chars/100 overlap]
            EXTRACT[Entity Extractor<br/>NER + Relations]
            GRAPH[Graph Builder<br/>Knowledge Graph]
            QENGINE[Query Engine<br/>4 Modes]
        end
    end

    subgraph "AI/ML Layer"
        subgraph "Ollama Service"
            OLLAMA[Ollama Server<br/>Model Manager]
            QWEN[Qwen 2.5 7B<br/>Text Generation]
            NOMIC[Nomic-Embed<br/>768D Embeddings]
        end
    end

    subgraph "Storage Layer"
        subgraph "Vector Database"
            QDRANT[Qdrant<br/>Vector Search<br/>6333/6334]
            COLL1[entities<br/>collection]
            COLL2[chunks<br/>collection]
            COLL3[relations<br/>collection]
        end
        
        subgraph "Cache/Queue"
            REDIS[Redis<br/>LLM Cache<br/>Task Queue<br/>6379]
        end
        
        subgraph "File Storage"
            RAGDATA[./rag_data<br/>JSON Storage<br/>Graph Data]
        end
    end

    subgraph "Monitoring Layer"
        PROM[Prometheus<br/>Metrics Collector<br/>9090]
        GRAF[Grafana<br/>Dashboards<br/>3000]
        METRICS[Custom Metrics<br/>API Performance<br/>LLM Usage]
    end

    %% Input Flow
    USER --> NGINX
    FILES --> NGINX
    APIS --> NGINX
    
    %% Gateway to API
    NGINX --> API
    
    %% Document Processing Pipeline
    API -->|Insert| LRAG
    LRAG --> DOCPROC
    DOCPROC --> CHUNK
    CHUNK --> EXTRACT
    EXTRACT --> GRAPH
    
    %% Embedding Generation
    CHUNK -->|Text| OLLAMA
    OLLAMA --> NOMIC
    NOMIC -->|768D Vectors| QDRANT
    
    %% Entity/Relation Storage
    EXTRACT -->|Entities| COLL1
    CHUNK -->|Chunks| COLL2
    GRAPH -->|Relations| COLL3
    
    %% Query Processing
    API -->|Query| QENGINE
    QENGINE -->|Search| QDRANT
    QENGINE -->|Generate| QWEN
    
    %% Caching
    QWEN -->|Cache| REDIS
    API -->|Queue| REDIS
    
    %% Local Storage
    GRAPH -->|Persist| RAGDATA
    
    %% Monitoring
    API -->|Metrics| PROM
    OLLAMA -->|Metrics| PROM
    QDRANT -->|Metrics| PROM
    PROM -->|Display| GRAF
    
    %% Styling
    style API fill:#f9f,stroke:#333,stroke-width:4px
    style OLLAMA fill:#bbf,stroke:#333,stroke-width:2px
    style QDRANT fill:#bfb,stroke:#333,stroke-width:2px
    style REDIS fill:#fbb,stroke:#333,stroke-width:2px
```

## Detailed Component Interactions

### Document Processing Pipeline

```mermaid
sequenceDiagram
    participant User
    participant API
    participant LightRAG
    participant Docling
    participant Ollama
    participant Qdrant
    
    User->>API: POST /documents
    API->>LightRAG: insert_documents
    LightRAG->>Docling: Parse document
    Docling-->>LightRAG: Structured text
    LightRAG->>LightRAG: Chunk text
    
    loop For each chunk
        LightRAG->>Ollama: Generate embedding
        Ollama-->>LightRAG: 768D vector
        LightRAG->>Qdrant: Store vector
    end
    
    LightRAG->>Ollama: Extract entities/relations
    Ollama-->>LightRAG: Graph data
    LightRAG->>Qdrant: Store graph
    LightRAG-->>API: Success
    API-->>User: 200 OK
```

### Query Processing Pipeline

```mermaid
sequenceDiagram
    participant User
    participant API
    participant LightRAG
    participant Qdrant
    participant Ollama
    participant Redis
    
    User->>API: POST /query
    API->>Redis: Check cache
    
    alt Cache hit
        Redis-->>API: Cached response
        API-->>User: 200 OK + answer
    else Cache miss
        API->>LightRAG: process_query
        LightRAG->>Ollama: Embed query
        Ollama-->>LightRAG: Query vector
        
        par Vector search
            LightRAG->>Qdrant: Search chunks
            Qdrant-->>LightRAG: Relevant chunks
        and Graph search
            LightRAG->>Qdrant: Search entities
            Qdrant-->>LightRAG: Related entities
        end
        
        LightRAG->>Ollama: Generate answer
        Ollama-->>LightRAG: Response
        LightRAG-->>API: Answer
        API->>Redis: Cache response
        API-->>User: 200 OK + answer
    end
```

    subgraph "Query Modes"
        F -->|Naive Mode| L[Direct Search]
        F -->|Local Mode| M[Entity Search]
        F -->|Global Mode| N[Theme Search]
        F -->|Hybrid Mode| O[Combined Search]
    end

    subgraph "Monitoring"
        C -->|Metrics| P[Prometheus]
        P -->|Visualize| Q[Grafana]
    end

    style A fill:#e1f5fe
    style B fill:#fff3e0
    style C fill:#f3e5f5
    style D fill:#e8f5e9
    style G fill:#fff9c4
    style H fill:#fff9c4
    style P fill:#ffebee
    style Q fill:#ffebee
```

## Document Ingestion Flow

```mermaid
graph LR
    subgraph "Document Upload"
        A1[User] -->|POST /documents| A2[API Endpoint]
        A2 -->|Text Documents| A3[LightRAG Service]
    end

    subgraph "Text Processing"
        A3 -->|Split Text| B1[Chunking]
        B1 -->|Extract Entities| B2[Entity Recognition]
        B1 -->|Extract Relations| B3[Relationship Extraction]
    end

    subgraph "Embedding Generation"
        B1 -->|Text Chunks| C1[Nomic-Embed-Text]
        C1 -->|768-dim vectors| C2[Chunk Embeddings]
        B2 -->|Entity Names| C1
        B3 -->|Relation Text| C1
    end

    subgraph "Storage"
        C2 -->|Save| D1[KV Store]
        B2 -->|Save| D2[Entity Graph]
        B3 -->|Save| D3[Relationship Graph]
        D1 --> D4[File System]
        D2 --> D4
        D3 --> D4
    end

    style A1 fill:#e1f5fe
    style C1 fill:#fff9c4
    style D4 fill:#e8f5e9
```

## Document Chunking Details

```mermaid
graph TD
    subgraph "Chunking Process"
        T1[Input Text] -->|Tokenize| T2[Token Stream]
        T2 -->|Split by Size| T3[Token Windows]
        T3 -->|Decode| T4[Text Chunks]
    end

    subgraph "Chunk Parameters"
        P1[Chunk Size: 1200 tokens] --> T3
        P2[Overlap: 100 tokens] --> T3
        P3[Tokenizer: tiktoken gpt-4o-mini] --> T2
    end

    subgraph "Chunking Strategy"
        T1 -->|Check Split Character| S1{Has Delimiter?}
        S1 -->|Yes| S2[Split by Character First]
        S1 -->|No| S3[Split by Tokens Only]
        S2 -->|If chunk > 1200 tokens| S4[Re-split by Tokens]
        S2 -->|If chunk <= 1200 tokens| T4
        S3 --> T3
        S4 --> T3
    end

    style T1 fill:#e1f5fe
    style T4 fill:#e8f5e9
    style P1 fill:#fff3e0
    style P2 fill:#fff3e0
    style P3 fill:#fff3e0
```

### How Chunking Works

1. **Token-Based Chunking**
   - Uses tiktoken tokenizer (gpt-4o-mini model)
   - Default chunk size: 1200 tokens
   - Default overlap: 100 tokens
   - Configurable via environment variables:
     - `CHUNK_SIZE` (default: 1200)
     - `CHUNK_OVERLAP_SIZE` (default: 100)

2. **Chunking Algorithm**
   ```python
   # Simplified logic from chunking_by_token_size
   for start in range(0, total_tokens, chunk_size - overlap):
       chunk = tokens[start : start + chunk_size]
       yield decode(chunk)
   ```

3. **Smart Splitting Options**
   - **Character-based splitting**: Can split by sentence, paragraph, or custom delimiter
   - **Hybrid approach**: Split by character first, then by tokens if chunks are too large
   - **Overlap preservation**: Maintains context between chunks

4. **Why These Settings?**
   - **1200 tokens**: Balances context preservation with processing efficiency
   - **100 token overlap**: Ensures entities/relationships aren't cut off at boundaries
   - **tiktoken**: Industry-standard tokenizer, consistent with OpenAI models

## Query Processing Flow

```mermaid
graph LR
    subgraph "Query Input"
        Q1[User Query] -->|POST /query| Q2[API Endpoint]
        Q2 -->|Question + Mode| Q3[LightRAG Query]
    end

    subgraph "Query Embedding"
        Q3 -->|Query Text| E1[Nomic-Embed-Text]
        E1 -->|768-dim vector| E2[Query Embedding]
    end

    subgraph "Search Modes"
        E2 -->|Mode Selection| S1{Query Mode}
        S1 -->|naive| S2[Direct Text Search]
        S1 -->|local| S3[Entity-Based Search]
        S1 -->|global| S4[Theme-Based Search]
        S1 -->|hybrid| S5[Combined Search]
    end

    subgraph "Context Retrieval"
        S2 --> R1[Retrieve Chunks]
        S3 --> R2[Find Related Entities]
        S4 --> R3[Find Global Themes]
        S5 --> R4[Combine All Results]
        R1 --> R5[Build Context]
        R2 --> R5
        R3 --> R5
        R4 --> R5
    end

    subgraph "Answer Generation"
        R5 -->|Context + Query| L1[Qwen 2.5 32B]
        L1 -->|Generated Text| L2[Final Answer]
        L2 -->|JSON Response| L3[User]
    end

    style Q1 fill:#e1f5fe
    style E1 fill:#fff9c4
    style L1 fill:#fff9c4
    style L3 fill:#e1f5fe
```

## Model Locations & Roles

```mermaid
graph TB
    subgraph "Ollama Container"
        O1[Ollama Service]
        O1 -->|Hosts| M1[Qwen 2.5 32B Q4_K_M]
        O1 -->|Hosts| M2[Nomic-Embed-Text]
        M1 -->|Role| R1[Text Generation]
        M2 -->|Role| R2[Embedding Generation]
        R1 -->|Use Case| U1[Answer Questions]
        R2 -->|Use Case| U2[Semantic Search]
    end

    subgraph "Model Specs"
        M1 -->|Size| S1[19GB]
        M1 -->|VRAM| S2[22GB Usage]
        M2 -->|Size| S3[274MB]
        M2 -->|Dimensions| S4[768D Vectors]
    end

    style O1 fill:#fff3e0
    style M1 fill:#fff9c4
    style M2 fill:#fff9c4
```

## End User Journey

```mermaid
graph TD
    subgraph "Step 1: Upload Documents"
        U1[User] -->|Prepare Text| D1[Document Collection]
        D1 -->|HTTP POST| D2[/api/documents]
        D2 -->|Process| D3[Knowledge Graph Built]
    end

    subgraph "Step 2: Ask Questions"
        U1 -->|Write Question| Q1[Query]
        Q1 -->|Choose Mode| Q2[Select Query Type]
        Q2 -->|HTTP POST| Q3[/api/query]
    end

    subgraph "Step 3: Get Answers"
        Q3 -->|Process| A1[LightRAG Search]
        A1 -->|Generate| A2[Contextual Answer]
        A2 -->|Return| A3[JSON Response]
        A3 -->|Display| U1
    end

    style U1 fill:#e1f5fe
    style D3 fill:#e8f5e9
    style A3 fill:#e8f5e9
```

## API Usage Examples

### 1. Upload Documents
```bash
curl -X POST http://localhost/api/documents \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      "RAG combines retrieval with generation for accurate answers.",
      "LightRAG uses knowledge graphs to improve search quality."
    ]
  }'
```

### 2. Query with Different Modes
```bash
# Naive Mode - Simple text search
curl -X POST http://localhost/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is RAG?",
    "mode": "naive"
  }'

# Local Mode - Entity-focused search
curl -X POST http://localhost/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How does LightRAG work?",
    "mode": "local"
  }'

# Global Mode - Theme-based search
curl -X POST http://localhost/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the benefits of knowledge graphs?",
    "mode": "global"
  }'

# Hybrid Mode - Combined approach
curl -X POST http://localhost/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Explain the complete RAG architecture",
    "mode": "hybrid"
  }'
```

## Key Components Explained

### LightRAG Storage
- **Entity Graph**: Stores identified entities and their properties
- **Relationship Graph**: Stores connections between entities
- **Text Chunks**: Original document segments with metadata
- **KV Store**: Key-value storage for fast retrieval

### Query Modes
- **Naive**: Direct text similarity search without graph features
- **Local**: Focuses on specific entities and their immediate connections
- **Global**: Looks for overarching themes and concepts
- **Hybrid**: Combines all approaches for comprehensive results

### Why This Architecture?
1. **Graph-based**: Better context understanding than simple vector search
2. **Multi-modal search**: Different query modes for different needs
3. **Scalable**: Can handle large document collections
4. **Observable**: Full monitoring and metrics
5. **Flexible**: Easy to add new models or change configurations