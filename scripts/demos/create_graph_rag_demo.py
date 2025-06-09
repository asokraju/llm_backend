#!/usr/bin/env python3
"""
Comprehensive Graph RAG Demo using LightRAG + DOCLING + Ollama

This script demonstrates the complete pipeline:
1. DOCLING: Advanced PDF processing with structure preservation
2. LightRAG: Knowledge graph construction with entities and relationships
3. Ollama: Local LLM for text generation and embeddings
4. Graph-based querying with multiple modes

Features demonstrated:
- Superior PDF processing with DOCLING vs traditional methods
- Knowledge graph construction from clinical documents
- Entity and relationship extraction
- Multiple query modes (naive, local, global, hybrid)
- Graph visualization and statistics
"""

import asyncio
import logging
import time
import sys
import os
from pathlib import Path
from typing import List, Dict, Any
import json
import requests

# Add src directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('graph_rag_demo.log')
    ]
)
logger = logging.getLogger(__name__)

class GraphRAGDemo:
    """Comprehensive Graph RAG demonstration class."""
    
    def __init__(self):
        self.base_url = "http://localhost:9000"
        self.working_dir = "generated_data/graph_rag_demo"
        self.stats = {
            'documents_processed': 0,
            'processing_time': 0,
            'graph_entities': 0,
            'graph_relationships': 0,
            'queries_executed': 0
        }
        
    async def check_services(self) -> bool:
        """Verify all required services are running."""
        logger.info("🔍 Checking service availability...")
        
        services = {
            'API': 'http://localhost:9000/health',
            'Ollama': 'http://localhost:12434/api/version',
            'Qdrant': 'http://localhost:7333/'  # Qdrant uses root endpoint for health check
        }
        
        all_ok = True
        for name, url in services.items():
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    logger.info(f"  ✅ {name}: Running")
                else:
                    logger.error(f"  ❌ {name}: Error {response.status_code}")
                    all_ok = False
            except Exception as e:
                logger.error(f"  ❌ {name}: {str(e)}")
                all_ok = False
                
        return all_ok
    
    async def initialize_lightrag(self):
        """Initialize LightRAG service with DOCLING."""
        logger.info("🚀 Initializing LightRAG with DOCLING support...")
        
        from src.rag.lightrag_service import LightRAGService
        
        # Initialize with DOCLING-optimized settings
        self.lightrag = LightRAGService(
            working_dir=self.working_dir,
            llm_model="qwen2.5:7b-instruct",
            embedding_model="nomic-embed-text",
            embedding_dim=768
        )
        
        await self.lightrag.initialize()
        logger.info("  ✅ LightRAG initialized with DOCLING support")
        
    async def process_documents_with_docling(self, max_docs: int = 5) -> List[str]:
        """Process PDF documents using DOCLING for superior extraction."""
        logger.info(f"📄 Processing PDF documents with DOCLING (max: {max_docs})...")
        
        try:
            # Install docling if needed
            try:
                from docling.document_converter import DocumentConverter
            except ImportError:
                logger.info("📦 Installing DOCLING...")
                import subprocess
                subprocess.check_call([sys.executable, "-m", "pip", "install", "docling"])
                from docling.document_converter import DocumentConverter
            
            # Initialize DOCLING converter
            converter = DocumentConverter()
            
            # Find PDF files
            data_dir = Path("data")
            pdf_files = list(data_dir.glob("*.pdf"))[:max_docs]
            
            if not pdf_files:
                raise FileNotFoundError("No PDF files found in data/ directory")
                
            logger.info(f"  📚 Found {len(pdf_files)} PDF files to process")
            
            processed_documents = []
            start_time = time.time()
            
            for i, pdf_path in enumerate(pdf_files, 1):
                logger.info(f"  🔄 Processing {pdf_path.name} ({i}/{len(pdf_files)})")
                
                try:
                    # Use DOCLING for superior extraction
                    doc_start = time.time()
                    result = converter.convert(pdf_path)
                    markdown_content = result.document.export_to_markdown()
                    doc_time = time.time() - doc_start
                    
                    # Create structured document with metadata
                    document = f"""
# {pdf_path.stem.replace('_', ' ').title()}

**Source:** {pdf_path.name}  
**Type:** Clinical Data Management Guide  
**Processed with:** DOCLING  
**Processing time:** {doc_time:.2f}s  
**Content length:** {len(markdown_content):,} characters  

---

{markdown_content}
                    """.strip()
                    
                    processed_documents.append(document)
                    logger.info(f"    ✅ Extracted {len(markdown_content):,} characters in {doc_time:.2f}s")
                    
                except Exception as e:
                    logger.error(f"    ❌ Failed to process {pdf_path.name}: {e}")
                    continue
            
            processing_time = time.time() - start_time
            self.stats['documents_processed'] = len(processed_documents)
            self.stats['processing_time'] = processing_time
            
            logger.info(f"  ✅ Processed {len(processed_documents)} documents in {processing_time:.2f}s")
            return processed_documents
            
        except Exception as e:
            logger.error(f"  ❌ DOCLING processing failed: {e}")
            return []
    
    async def build_knowledge_graph(self, documents: List[str]):
        """Build knowledge graph using LightRAG."""
        logger.info("🕸️ Building knowledge graph with LightRAG...")
        
        if not documents:
            logger.error("  ❌ No documents to process")
            return
            
        try:
            start_time = time.time()
            
            # Insert documents in batches for better performance
            batch_size = 2
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                total_batches = (len(documents) + batch_size - 1) // batch_size
                
                logger.info(f"  📦 Processing batch {batch_num}/{total_batches} ({len(batch)} documents)")
                
                await self.lightrag.insert_documents(batch)
                logger.info(f"    ✅ Batch {batch_num} inserted successfully")
            
            build_time = time.time() - start_time
            logger.info(f"  ✅ Knowledge graph built in {build_time:.2f}s")
            
            # Get graph statistics
            await self.get_graph_statistics()
            
        except Exception as e:
            logger.error(f"  ❌ Knowledge graph construction failed: {e}")
    
    async def get_graph_statistics(self):
        """Retrieve and display knowledge graph statistics."""
        logger.info("📊 Analyzing knowledge graph structure...")
        
        try:
            # Check if graph files exist
            working_path = Path(self.working_dir)
            
            graph_files = {
                'entities': working_path / 'vdb_entities.json',
                'relationships': working_path / 'vdb_relationships.json',
                'chunks': working_path / 'vdb_chunks.json',
                'graph': working_path / 'graph_chunk_entity_relation.graphml'
            }
            
            stats = {}
            for name, file_path in graph_files.items():
                if file_path.exists():
                    if name == 'graph' and file_path.suffix == '.graphml':
                        # GraphML file - just check existence
                        stats[name] = f"GraphML file ({file_path.stat().st_size:,} bytes)"
                    elif file_path.suffix == '.json':
                        try:
                            with open(file_path, 'r') as f:
                                data = json.load(f)
                                if isinstance(data, list):
                                    stats[name] = len(data)
                                elif isinstance(data, dict):
                                    stats[name] = len(data)
                                else:
                                    stats[name] = "Unknown format"
                        except:
                            stats[name] = f"File exists ({file_path.stat().st_size:,} bytes)"
                else:
                    stats[name] = "Not found"
            
            logger.info("  📈 Graph Statistics:")
            logger.info(f"    🏷️  Entities: {stats.get('entities', 'N/A')}")
            logger.info(f"    🔗 Relationships: {stats.get('relationships', 'N/A')}")
            logger.info(f"    📄 Chunks: {stats.get('chunks', 'N/A')}")
            logger.info(f"    🕸️  Graph File: {stats.get('graph', 'N/A')}")
            
            # Update internal stats
            if isinstance(stats.get('entities'), int):
                self.stats['graph_entities'] = stats['entities']
            if isinstance(stats.get('relationships'), int):
                self.stats['graph_relationships'] = stats['relationships']
                
        except Exception as e:
            logger.error(f"  ❌ Failed to get graph statistics: {e}")
    
    async def demonstrate_query_modes(self):
        """Demonstrate different LightRAG query modes."""
        logger.info("🔍 Demonstrating graph-based query modes...")
        
        # Test queries for clinical data management
        test_queries = [
            {
                'question': "What is clinical data management?",
                'mode': 'naive',
                'description': 'Simple similarity search'
            },
            {
                'question': "What are the key principles of data quality in clinical research?",
                'mode': 'local', 
                'description': 'Entity-focused graph traversal'
            },
            {
                'question': "How do electronic data capture systems improve clinical trials?",
                'mode': 'global',
                'description': 'Community-focused graph analysis'
            },
            {
                'question': "Explain the complete workflow of clinical data management from collection to analysis",
                'mode': 'hybrid',
                'description': 'Combined local + global approach (recommended)'
            }
        ]
        
        results = []
        
        for i, query in enumerate(test_queries, 1):
            logger.info(f"  🔎 Query {i}/4: {query['mode'].upper()} mode")
            logger.info(f"    ❓ Question: {query['question']}")
            logger.info(f"    📝 Description: {query['description']}")
            
            try:
                start_time = time.time()
                response = await self.lightrag.query(
                    query['question'], 
                    mode=query['mode']
                )
                query_time = time.time() - start_time
                
                # Log response summary
                response_length = len(response)
                logger.info(f"    ⚡ Response time: {query_time:.2f}s")
                logger.info(f"    📏 Response length: {response_length:,} characters")
                logger.info(f"    🎯 Preview: {response[:150]}...")
                
                results.append({
                    'query': query,
                    'response': response,
                    'response_time': query_time,
                    'response_length': response_length
                })
                
                self.stats['queries_executed'] += 1
                
            except Exception as e:
                logger.error(f"    ❌ Query failed: {e}")
                results.append({
                    'query': query,
                    'error': str(e),
                    'response_time': 0,
                    'response_length': 0
                })
            
            # Add spacing between queries
            if i < len(test_queries):
                logger.info("")
        
        return results
    
    async def compare_with_traditional_rag(self):
        """Compare graph RAG performance with traditional approaches."""
        logger.info("⚖️ Comparing Graph RAG vs Traditional RAG...")
        
        comparison_query = "What are the relationships between data quality, validation, and regulatory compliance?"
        
        # Test with different modes to show graph advantage
        modes_to_test = ['naive', 'hybrid']
        
        for mode in modes_to_test:
            logger.info(f"  🔄 Testing {mode} mode...")
            try:
                start_time = time.time()
                response = await self.lightrag.query(comparison_query, mode=mode)
                query_time = time.time() - start_time
                
                logger.info(f"    ⚡ {mode.capitalize()} mode: {query_time:.2f}s, {len(response):,} chars")
                
                # Analyze response quality (basic heuristics)
                mentions_relationships = any(word in response.lower() for word in [
                    'relationship', 'connect', 'link', 'associate', 'relate', 'correlation'
                ])
                mentions_multiple_concepts = sum(word in response.lower() for word in [
                    'quality', 'validation', 'compliance', 'regulatory', 'data'
                ]) >= 3
                
                quality_score = sum([mentions_relationships, mentions_multiple_concepts])
                logger.info(f"    🎯 Quality indicators: {quality_score}/2 ({'✅' if quality_score >= 1 else '❌'})")
                
            except Exception as e:
                logger.error(f"    ❌ {mode} mode failed: {e}")
    
    async def save_demo_results(self, query_results: List[Dict]):
        """Save demo results for analysis."""
        logger.info("💾 Saving demo results...")
        
        try:
            results = {
                'metadata': {
                    'demo_timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'lightrag_version': 'latest',
                    'ollama_model': 'qwen2.5:7b-instruct',
                    'embedding_model': 'nomic-embed-text',
                    'docling_enabled': True
                },
                'statistics': self.stats,
                'query_results': query_results,
                'working_directory': self.working_dir
            }
            
            # Save results
            results_file = Path('graph_rag_demo_results.json')
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            logger.info(f"  ✅ Results saved to {results_file}")
            
            # Create summary report
            await self.create_summary_report(results)
            
        except Exception as e:
            logger.error(f"  ❌ Failed to save results: {e}")
    
    async def create_summary_report(self, results: Dict):
        """Create a human-readable summary report."""
        logger.info("📋 Creating summary report...")
        
        try:
            report = f"""
# Graph RAG Demo Results Summary

**Demo Date:** {results['metadata']['demo_timestamp']}  
**System:** LightRAG + DOCLING + Ollama  

## 📊 Performance Statistics

- **Documents Processed:** {self.stats['documents_processed']}
- **Processing Time:** {self.stats['processing_time']:.2f}s
- **Graph Entities:** {self.stats['graph_entities']}
- **Graph Relationships:** {self.stats['graph_relationships']}
- **Queries Executed:** {self.stats['queries_executed']}

## 🎯 Query Performance

| Mode | Query Time | Response Length | Quality |
|------|------------|-----------------|---------|
"""
            
            for result in results['query_results']:
                if 'error' not in result:
                    mode = result['query']['mode']
                    time_val = result['response_time']
                    length = result['response_length']
                    quality = "✅" if length > 500 else "⚠️"
                    report += f"| {mode.capitalize()} | {time_val:.2f}s | {length:,} chars | {quality} |\n"
            
            report += f"""
## 🔍 Technology Comparison

**DOCLING Advantages:**
- ✅ Superior PDF structure preservation
- ✅ Better table and figure handling
- ✅ Markdown output with formatting
- ✅ Metadata extraction

**Graph RAG Benefits:**
- ✅ Entity relationship understanding
- ✅ Multi-hop reasoning capabilities
- ✅ Context-aware responses
- ✅ Knowledge graph visualization

## 📁 Generated Files

- **Knowledge Graph:** `{self.working_dir}/graph_chunk_entity_relation.graphml`
- **Entities:** `{self.working_dir}/vdb_entities.json`
- **Relationships:** `{self.working_dir}/vdb_relationships.json`
- **Full Results:** `graph_rag_demo_results.json`

## 🚀 Next Steps

1. Visualize the knowledge graph using tools like Gephi or NetworkX
2. Experiment with different query strategies
3. Add more domain-specific documents
4. Fine-tune entity extraction prompts
"""
            
            # Save report
            report_file = Path('graph_rag_demo_report.md')
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            
            logger.info(f"  ✅ Summary report saved to {report_file}")
            
        except Exception as e:
            logger.error(f"  ❌ Failed to create summary report: {e}")
    
    async def cleanup(self):
        """Clean up resources."""
        if hasattr(self, 'lightrag'):
            await self.lightrag.close()
            logger.info("🧹 LightRAG service closed")

async def main():
    """Main demo execution."""
    print("🎯 LightRAG + DOCLING + Ollama Graph RAG Demo")
    print("=" * 60)
    print()
    
    demo = GraphRAGDemo()
    
    try:
        # Check services
        if not await demo.check_services():
            print("❌ Some required services are not running!")
            print("Please start services with: docker-compose up -d")
            return 1
        
        # Initialize LightRAG
        await demo.initialize_lightrag()
        
        # Process documents with DOCLING
        documents = await demo.process_documents_with_docling(max_docs=3)
        if not documents:
            print("❌ No documents were processed successfully!")
            return 1
        
        # Build knowledge graph
        await demo.build_knowledge_graph(documents)
        
        # Demonstrate query modes
        query_results = await demo.demonstrate_query_modes()
        
        # Compare approaches
        await demo.compare_with_traditional_rag()
        
        # Save results
        await demo.save_demo_results(query_results)
        
        print("\n" + "=" * 60)
        print("✅ Graph RAG Demo Complete!")
        print("📊 Check 'graph_rag_demo_results.json' for detailed results")
        print("📋 Check 'graph_rag_demo_report.md' for summary")
        print(f"🕸️ Knowledge graph saved in '{demo.working_dir}/'")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        return 1
    
    finally:
        await demo.cleanup()

if __name__ == "__main__":
    asyncio.run(main())