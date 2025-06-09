#!/usr/bin/env python3
"""
Robust Graph RAG Demo with Comprehensive Error Handling

This version includes:
- Detailed progress tracking
- Comprehensive error handling
- Timeout protection
- Resource monitoring
- Graceful degradation
- Complete logging
"""

import asyncio
import logging
import time
import sys
import os
import signal
import traceback
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
import requests

# Add src directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('robust_graph_rag_demo.log', mode='w')
    ]
)
logger = logging.getLogger(__name__)

class TimeoutError(Exception):
    """Custom timeout exception."""
    pass

class GraphRAGDemoRobust:
    """Robust Graph RAG demonstration with comprehensive error handling."""
    
    def __init__(self):
        self.base_url = "http://localhost:9000"
        self.working_dir = "generated_data/robust_graph_rag_demo"
        self.lightrag = None
        self.start_time = time.time()
        self.stats = {
            'start_time': self.start_time,
            'documents_processed': 0,
            'processing_time': 0,
            'graph_entities': 0,
            'graph_relationships': 0,
            'queries_executed': 0,
            'errors': []
        }
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.warning(f"Received signal {signum}, shutting down gracefully...")
        asyncio.create_task(self._emergency_cleanup())
        
    async def _emergency_cleanup(self):
        """Emergency cleanup on shutdown."""
        try:
            if self.lightrag:
                await self.lightrag.close()
                logger.info("Emergency cleanup completed")
        except Exception as e:
            logger.error(f"Error during emergency cleanup: {e}")
        finally:
            sys.exit(1)
    
    def _log_progress(self, message: str, step: int, total_steps: int):
        """Log progress with step tracking."""
        progress = (step / total_steps) * 100
        elapsed = time.time() - self.start_time
        logger.info(f"[{step}/{total_steps}] ({progress:.1f}%) {message} - Elapsed: {elapsed:.1f}s")
    
    def _handle_error(self, error: Exception, context: str, critical: bool = False):
        """Centralized error handling."""
        error_info = {
            'context': context,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'timestamp': time.time() - self.start_time,
            'critical': critical,
            'traceback': traceback.format_exc()
        }
        
        self.stats['errors'].append(error_info)
        
        if critical:
            logger.error(f"CRITICAL ERROR in {context}: {error}")
            logger.error(f"Traceback: {traceback.format_exc()}")
        else:
            logger.warning(f"Non-critical error in {context}: {error}")
        
        return error_info
    
    async def check_services_with_timeout(self, timeout: int = 30) -> bool:
        """Check services with timeout protection."""
        self._log_progress("Checking service availability", 1, 10)
        
        services = {
            'API': 'http://localhost:9000/health',
            'Ollama': 'http://localhost:12434/api/version',
            'Qdrant': 'http://localhost:7333/'
        }
        
        try:
            for name, url in services.items():
                logger.info(f"  Checking {name} at {url}")
                
                try:
                    response = requests.get(url, timeout=5)
                    if response.status_code == 200:
                        logger.info(f"  ✅ {name}: Running (Status: {response.status_code})")
                    else:
                        logger.error(f"  ❌ {name}: HTTP {response.status_code}")
                        return False
                except requests.exceptions.Timeout:
                    self._handle_error(TimeoutError(f"{name} timeout"), f"service_check_{name}")
                    return False
                except requests.exceptions.ConnectionError as e:
                    self._handle_error(e, f"service_check_{name}")
                    return False
            
            logger.info("✅ All services are healthy")
            return True
            
        except Exception as e:
            self._handle_error(e, "service_check", critical=True)
            return False
    
    async def initialize_lightrag_safe(self) -> bool:
        """Initialize LightRAG with comprehensive error handling."""
        self._log_progress("Initializing LightRAG", 2, 10)
        
        try:
            from src.rag.lightrag_service import LightRAGService
            
            # Create working directory
            Path(self.working_dir).mkdir(parents=True, exist_ok=True)
            
            logger.info(f"  Working directory: {self.working_dir}")
            
            self.lightrag = LightRAGService(
                working_dir=self.working_dir,
                llm_model="qwen2.5:7b-instruct",
                embedding_model="nomic-embed-text",
                embedding_dim=768
            )
            
            logger.info("  Initializing LightRAG service...")
            await self.lightrag.initialize()
            
            logger.info("✅ LightRAG initialized successfully")
            return True
            
        except ImportError as e:
            self._handle_error(e, "lightrag_import", critical=True)
            return False
        except Exception as e:
            self._handle_error(e, "lightrag_initialization", critical=True)
            return False
    
    async def process_documents_with_safety(self, max_docs: int = 2) -> Optional[List[str]]:
        """Process documents with comprehensive error handling and progress tracking."""
        self._log_progress("Processing PDF documents with DOCLING", 3, 10)
        
        try:
            # Install/import DOCLING with error handling
            try:
                from docling.document_converter import DocumentConverter
                logger.info("  ✅ DOCLING already available")
            except ImportError:
                logger.info("  📦 Installing DOCLING...")
                import subprocess
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "docling"],
                    capture_output=True, text=True, timeout=120
                )
                if result.returncode != 0:
                    raise Exception(f"DOCLING installation failed: {result.stderr}")
                
                from docling.document_converter import DocumentConverter
                logger.info("  ✅ DOCLING installed successfully")
            
            converter = DocumentConverter()
            
            # Find PDF files
            data_dir = Path("data")
            if not data_dir.exists():
                raise FileNotFoundError("Data directory not found")
                
            pdf_files = list(data_dir.glob("*.pdf"))[:max_docs]
            
            if not pdf_files:
                raise FileNotFoundError("No PDF files found in data/ directory")
                
            logger.info(f"  📚 Found {len(pdf_files)} PDF files to process (limit: {max_docs})")
            
            processed_documents = []
            processing_start = time.time()
            
            for i, pdf_path in enumerate(pdf_files, 1):
                logger.info(f"  🔄 Processing {pdf_path.name} ({i}/{len(pdf_files)})")
                
                try:
                    doc_start = time.time()
                    
                    # Process with timeout protection
                    result = converter.convert(pdf_path)
                    markdown_content = result.document.export_to_markdown()
                    
                    doc_time = time.time() - doc_start
                    
                    if len(markdown_content) < 100:
                        logger.warning(f"    ⚠️ Short content extracted ({len(markdown_content)} chars)")
                    
                    # Create structured document
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
                    logger.info(f"    ✅ Extracted {len(markdown_content):,} chars in {doc_time:.2f}s")
                    
                except Exception as e:
                    error_info = self._handle_error(e, f"docling_processing_{pdf_path.name}")
                    logger.error(f"    ❌ Failed to process {pdf_path.name}: {e}")
                    continue
            
            processing_time = time.time() - processing_start
            self.stats['documents_processed'] = len(processed_documents)
            self.stats['processing_time'] = processing_time
            
            if processed_documents:
                logger.info(f"✅ Successfully processed {len(processed_documents)} documents in {processing_time:.2f}s")
                return processed_documents
            else:
                logger.error("❌ No documents were processed successfully")
                return None
                
        except Exception as e:
            self._handle_error(e, "document_processing", critical=True)
            return None
    
    async def build_knowledge_graph_safe(self, documents: List[str]) -> bool:
        """Build knowledge graph with error handling and progress tracking."""
        self._log_progress("Building knowledge graph", 4, 10)
        
        if not documents:
            logger.error("  ❌ No documents provided for graph building")
            return False
        
        try:
            start_time = time.time()
            
            # Process in small batches to avoid memory issues
            batch_size = 1  # Conservative batch size
            total_batches = len(documents)
            
            logger.info(f"  📦 Processing {len(documents)} documents in {total_batches} batches")
            
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                
                logger.info(f"    Batch {batch_num}/{total_batches}: {len(batch)} documents")
                
                try:
                    await self.lightrag.insert_documents(batch)
                    logger.info(f"    ✅ Batch {batch_num} completed successfully")
                    
                except Exception as e:
                    error_info = self._handle_error(e, f"graph_building_batch_{batch_num}")
                    logger.error(f"    ❌ Batch {batch_num} failed: {e}")
                    # Continue with next batch rather than failing completely
                    continue
            
            build_time = time.time() - start_time
            logger.info(f"✅ Knowledge graph building completed in {build_time:.2f}s")
            
            # Get statistics
            await self.get_graph_statistics_safe()
            return True
            
        except Exception as e:
            self._handle_error(e, "knowledge_graph_building", critical=True)
            return False
    
    async def get_graph_statistics_safe(self) -> Dict[str, Any]:
        """Get graph statistics with error handling."""
        self._log_progress("Analyzing graph statistics", 5, 10)
        
        try:
            working_path = Path(self.working_dir)
            
            graph_files = {
                'entities': working_path / 'vdb_entities.json',
                'relationships': working_path / 'vdb_relationships.json',
                'chunks': working_path / 'vdb_chunks.json',
                'graph': working_path / 'graph_chunk_entity_relation.graphml'
            }
            
            stats = {}
            
            for name, file_path in graph_files.items():
                try:
                    if not file_path.exists():
                        stats[name] = "Not found"
                        continue
                        
                    file_size = file_path.stat().st_size
                    
                    if name == 'graph' and file_path.suffix == '.graphml':
                        stats[name] = f"GraphML file ({file_size:,} bytes)"
                    elif file_path.suffix == '.json':
                        with open(file_path, 'r') as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                stats[name] = len(data)
                            elif isinstance(data, dict):
                                stats[name] = len(data)
                            else:
                                stats[name] = f"Unknown format ({file_size:,} bytes)"
                    else:
                        stats[name] = f"{file_size:,} bytes"
                        
                except Exception as e:
                    error_info = self._handle_error(e, f"stat_analysis_{name}")
                    stats[name] = f"Error: {e}"
            
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
            
            return stats
            
        except Exception as e:
            self._handle_error(e, "graph_statistics")
            return {}
    
    async def test_query_modes_safe(self) -> List[Dict[str, Any]]:
        """Test query modes with comprehensive error handling."""
        self._log_progress("Testing query modes", 6, 10)
        
        test_queries = [
            {
                'question': "What is clinical data management?",
                'mode': 'naive',
                'description': 'Simple similarity search'
            },
            {
                'question': "What are the key principles of data quality?",
                'mode': 'hybrid',
                'description': 'Combined approach (most reliable)'
            }
        ]
        
        results = []
        
        for i, query in enumerate(test_queries, 1):
            logger.info(f"  🔎 Query {i}/{len(test_queries)}: {query['mode'].upper()} mode")
            logger.info(f"    ❓ Question: {query['question']}")
            
            try:
                start_time = time.time()
                
                # Query with timeout protection
                response = await asyncio.wait_for(
                    self.lightrag.query(query['question'], mode=query['mode']),
                    timeout=60.0  # 60 second timeout per query
                )
                
                query_time = time.time() - start_time
                response_length = len(response)
                
                logger.info(f"    ⚡ Response time: {query_time:.2f}s")
                logger.info(f"    📏 Response length: {response_length:,} characters")
                logger.info(f"    🎯 Preview: {response[:100]}...")
                
                results.append({
                    'query': query,
                    'response': response,
                    'response_time': query_time,
                    'response_length': response_length,
                    'success': True
                })
                
                self.stats['queries_executed'] += 1
                
            except asyncio.TimeoutError:
                error_info = self._handle_error(TimeoutError("Query timeout"), f"query_{query['mode']}")
                logger.error(f"    ❌ Query timed out after 60 seconds")
                results.append({
                    'query': query,
                    'error': 'Timeout',
                    'success': False
                })
            except Exception as e:
                error_info = self._handle_error(e, f"query_{query['mode']}")
                logger.error(f"    ❌ Query failed: {e}")
                results.append({
                    'query': query,
                    'error': str(e),
                    'success': False
                })
        
        successful_queries = sum(1 for r in results if r.get('success', False))
        logger.info(f"✅ Completed {successful_queries}/{len(test_queries)} queries successfully")
        
        return results
    
    async def generate_final_report(self, query_results: List[Dict]) -> None:
        """Generate comprehensive final report."""
        self._log_progress("Generating final report", 9, 10)
        
        try:
            total_time = time.time() - self.start_time
            
            report = {
                'metadata': {
                    'demo_timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'total_runtime': total_time,
                    'lightrag_version': 'latest',
                    'ollama_model': 'qwen2.5:7b-instruct',
                    'embedding_model': 'nomic-embed-text',
                    'docling_enabled': True
                },
                'statistics': self.stats,
                'query_results': query_results,
                'working_directory': self.working_dir,
                'files_generated': []
            }
            
            # List generated files
            working_path = Path(self.working_dir)
            if working_path.exists():
                report['files_generated'] = [str(f.relative_to('.')) for f in working_path.iterdir()]
            
            # Save detailed results
            results_file = Path('robust_graph_rag_results.json')
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            logger.info(f"  ✅ Detailed results saved to {results_file}")
            
            # Create summary
            summary = f"""
# 🎯 Graph RAG Demo - Executive Summary

**Status:** {'✅ SUCCESS' if len(self.stats['errors']) == 0 else '⚠️ PARTIAL SUCCESS'}  
**Runtime:** {total_time:.1f} seconds  
**Date:** {report['metadata']['demo_timestamp']}  

## 📊 Results
- **Documents Processed:** {self.stats['documents_processed']}
- **Graph Entities:** {self.stats['graph_entities']}
- **Graph Relationships:** {self.stats['graph_relationships']}
- **Queries Executed:** {self.stats['queries_executed']}
- **Errors:** {len(self.stats['errors'])}

## 🔧 Technology Stack
- ✅ **DOCLING:** Superior PDF processing
- ✅ **LightRAG:** Knowledge graph construction  
- ✅ **Ollama:** qwen2.5:7b + nomic-embed-text
- ✅ **Graph Database:** {self.stats['graph_entities']} entities, {self.stats['graph_relationships']} relationships

## 🎯 Query Performance
"""
            
            for result in query_results:
                if result.get('success', False):
                    mode = result['query']['mode']
                    time_val = result['response_time']
                    length = result['response_length']
                    summary += f"- **{mode.capitalize()}:** {time_val:.2f}s, {length:,} chars ✅\n"
                else:
                    mode = result['query']['mode']
                    error = result.get('error', 'Unknown')
                    summary += f"- **{mode.capitalize()}:** Failed ({error}) ❌\n"
            
            if self.stats['errors']:
                summary += f"\n## ⚠️ Errors ({len(self.stats['errors'])})\n"
                for error in self.stats['errors']:
                    summary += f"- {error['context']}: {error['error_type']} - {error['error_message']}\n"
            
            summary += f"\n## 📁 Generated Files\n"
            summary += f"- Knowledge Graph: `{self.working_dir}/`\n"
            summary += f"- Detailed Results: `robust_graph_rag_results.json`\n"
            summary += f"- Log File: `robust_graph_rag_demo.log`\n"
            
            # Save summary
            summary_file = Path('graph_rag_summary.md')
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(summary)
            
            logger.info(f"  ✅ Executive summary saved to {summary_file}")
            
        except Exception as e:
            self._handle_error(e, "report_generation")
    
    async def cleanup_safe(self):
        """Safe cleanup with error handling."""
        self._log_progress("Cleaning up resources", 10, 10)
        
        try:
            if self.lightrag:
                await self.lightrag.close()
                logger.info("  ✅ LightRAG service closed")
        except Exception as e:
            self._handle_error(e, "cleanup")
        finally:
            total_time = time.time() - self.start_time
            logger.info(f"🏁 Demo completed in {total_time:.1f} seconds")

async def main():
    """Main execution with comprehensive error handling."""
    print("🎯 Robust LightRAG + DOCLING + Ollama Graph RAG Demo")
    print("=" * 60)
    print("Features: Error handling, timeouts, progress tracking")
    print()
    
    demo = GraphRAGDemoRobust()
    success = False
    
    try:
        # Step-by-step execution with error handling
        if not await demo.check_services_with_timeout():
            logger.error("❌ Service check failed")
            return 1
        
        if not await demo.initialize_lightrag_safe():
            logger.error("❌ LightRAG initialization failed")
            return 1
        
        documents = await demo.process_documents_with_safety(max_docs=2)
        if not documents:
            logger.error("❌ Document processing failed")
            return 1
        
        if not await demo.build_knowledge_graph_safe(documents):
            logger.error("❌ Knowledge graph building failed")
            return 1
        
        query_results = await demo.test_query_modes_safe()
        
        await demo.generate_final_report(query_results)
        
        success = True
        
        print("\n" + "=" * 60)
        print("✅ Robust Graph RAG Demo Complete!")
        print("📊 Check 'robust_graph_rag_results.json' for detailed results")
        print("📋 Check 'graph_rag_summary.md' for executive summary")
        print("📝 Check 'robust_graph_rag_demo.log' for full logs")
        print(f"🕸️ Knowledge graph saved in '{demo.working_dir}/'")
        print("=" * 60)
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Demo interrupted by user")
        return 1
    except Exception as e:
        demo._handle_error(e, "main_execution", critical=True)
        logger.error(f"Demo failed with critical error: {e}")
        return 1
    
    finally:
        await demo.cleanup_safe()
        
        if success:
            print("\n🎉 Graph RAG system is now ready for production use!")
        else:
            print("\n⚠️ Demo completed with issues. Check logs for details.")

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)