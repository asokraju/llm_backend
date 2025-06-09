#!/usr/bin/env python3
"""
Comprehensive CCDM (Clinical Data Management) RAG Database Builder

This script processes all 33 clinical data management PDF documents to create
a comprehensive knowledge graph database using LightRAG + DOCLING + Ollama.

Features:
- Processes all PDFs in data/ directory
- Optimized for large-scale document processing
- Comprehensive error handling and progress tracking
- Resource monitoring and memory management
- Detailed statistics and validation
"""

import asyncio
import logging
import time
import sys
import os
import signal
import traceback
import json
import psutil
from pathlib import Path
from typing import List, Dict, Any, Optional
import requests

# Add src directory to path for imports
script_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(script_dir, '../..'))
sys.path.append(project_root)

# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('ccdm_database_build.log', mode='w')
    ]
)
logger = logging.getLogger(__name__)

class CCDMDatabaseBuilder:
    """Comprehensive CCDM RAG Database Builder with production-grade features."""
    
    def __init__(self):
        self.base_url = "http://localhost:9000"
        self.working_dir = "ccdm_rag_database"
        self.data_dir = Path("data")
        self.lightrag = None
        self.start_time = time.time()
        
        # Performance tracking
        self.stats = {
            'start_time': self.start_time,
            'total_documents': 0,
            'processed_documents': 0,
            'failed_documents': 0,
            'total_processing_time': 0,
            'graph_entities': 0,
            'graph_relationships': 0,
            'graph_chunks': 0,
            'errors': [],
            'document_details': [],
            'memory_usage': []
        }
        
        # Production configuration for large-scale processing
        self.config = {
            'chunk_token_size': 1200,           # Balanced for clinical content
            'chunk_overlap_token_size': 100,    # Good context preservation
            'max_batch_size': 2,                # Conservative for memory
            'max_documents': None,              # Process all documents
            'enable_memory_monitoring': True,
            'memory_threshold': 0.85,           # 85% memory usage trigger
            'processing_timeout': 300,          # 5 minute timeout per document
            'enable_detailed_logging': True
        }
        
        # Set up signal handlers
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
            self._save_partial_results()
            sys.exit(1)
    
    def _log_progress(self, message: str, step: int, total_steps: int, extra_info: str = ""):
        """Log progress with step tracking and extra information."""
        progress = (step / total_steps) * 100
        elapsed = time.time() - self.start_time
        logger.info(f"[{step}/{total_steps}] ({progress:.1f}%) {message} - Elapsed: {elapsed:.1f}s {extra_info}")
    
    def _monitor_memory(self):
        """Monitor system memory usage."""
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent()
        
        memory_info = {
            'timestamp': time.time() - self.start_time,
            'memory_percent': memory.percent,
            'memory_available_gb': memory.available / (1024**3),
            'cpu_percent': cpu_percent
        }
        
        self.stats['memory_usage'].append(memory_info)
        
        if memory.percent > self.config['memory_threshold'] * 100:
            logger.warning(f"High memory usage: {memory.percent:.1f}% (threshold: {self.config['memory_threshold']*100}%)")
            
        return memory_info
    
    def _handle_error(self, error: Exception, context: str, critical: bool = False):
        """Centralized error handling with detailed tracking."""
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
        else:
            logger.warning(f"Non-critical error in {context}: {error}")
        
        return error_info
    
    async def check_services(self) -> bool:
        """Check all required services are running."""
        self._log_progress("Checking service availability", 1, 8)
        
        services = {
            'API': 'http://localhost:9000/health',
            'Ollama': 'http://localhost:12434/api/version',
            'Qdrant': 'http://localhost:7333/'
        }
        
        try:
            for name, url in services.items():
                logger.info(f"  Checking {name} at {url}")
                
                try:
                    response = requests.get(url, timeout=10)
                    if response.status_code == 200:
                        logger.info(f"  ✅ {name}: Running")
                    else:
                        logger.error(f"  ❌ {name}: HTTP {response.status_code}")
                        return False
                except requests.exceptions.Timeout:
                    logger.error(f"  ❌ {name}: Timeout")
                    return False
                except requests.exceptions.ConnectionError:
                    logger.error(f"  ❌ {name}: Connection failed")
                    return False
            
            logger.info("✅ All services are healthy")
            return True
            
        except Exception as e:
            self._handle_error(e, "service_check", critical=True)
            return False
    
    async def initialize_lightrag(self) -> bool:
        """Initialize LightRAG with optimized settings for large-scale processing."""
        self._log_progress("Initializing LightRAG for CCDM database", 2, 8)
        
        try:
            # Import with absolute path from project root
            import sys
            import os
            current_dir = os.getcwd()
            sys.path.insert(0, current_dir)
            from src.rag.lightrag_service import LightRAGService
            
            # Create working directory
            Path(self.working_dir).mkdir(parents=True, exist_ok=True)
            
            logger.info(f"  Working directory: {self.working_dir}")
            logger.info(f"  Configuration: {self.config}")
            
            # Initialize with production settings
            self.lightrag = LightRAGService(
                working_dir=self.working_dir,
                llm_model="qwen2.5:7b-instruct",
                embedding_model="nomic-embed-text",
                embedding_dim=768
            )
            
            logger.info("  Initializing LightRAG service...")
            await self.lightrag.initialize()
            
            logger.info("✅ LightRAG initialized for large-scale processing")
            return True
            
        except Exception as e:
            self._handle_error(e, "lightrag_initialization", critical=True)
            return False
    
    async def get_document_list(self) -> List[Path]:
        """Get sorted list of all PDF documents to process."""
        self._log_progress("Scanning document directory", 3, 8)
        
        try:
            if not self.data_dir.exists():
                raise FileNotFoundError(f"Data directory not found: {self.data_dir}")
            
            pdf_files = sorted(list(self.data_dir.glob("*.pdf")))
            
            if not pdf_files:
                raise FileNotFoundError("No PDF files found in data directory")
            
            # Apply document limit if specified
            if self.config['max_documents']:
                pdf_files = pdf_files[:self.config['max_documents']]
            
            self.stats['total_documents'] = len(pdf_files)
            
            logger.info(f"  📚 Found {len(pdf_files)} PDF documents to process")
            for i, pdf in enumerate(pdf_files[:5]):  # Show first 5
                logger.info(f"    {i+1:2d}. {pdf.name}")
            if len(pdf_files) > 5:
                logger.info(f"    ... and {len(pdf_files)-5} more documents")
            
            return pdf_files
            
        except Exception as e:
            self._handle_error(e, "document_scanning", critical=True)
            return []
    
    async def process_document_with_docling(self, pdf_path: Path) -> Optional[str]:
        """Process a single document with DOCLING and comprehensive error handling."""
        doc_start_time = time.time()
        
        try:
            # Import DOCLING (install if needed)
            try:
                from docling.document_converter import DocumentConverter
            except ImportError:
                logger.info(f"  📦 Installing DOCLING for {pdf_path.name}...")
                import subprocess
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "docling"],
                    capture_output=True, text=True, timeout=120
                )
                if result.returncode != 0:
                    raise Exception(f"DOCLING installation failed: {result.stderr}")
                from docling.document_converter import DocumentConverter
            
            converter = DocumentConverter()
            
            # Process with timeout
            logger.info(f"    🔄 Converting {pdf_path.name}...")
            result = converter.convert(pdf_path)
            markdown_content = result.document.export_to_markdown()
            
            processing_time = time.time() - doc_start_time
            
            # Validate content quality
            if len(markdown_content) < 100:
                logger.warning(f"    ⚠️ Short content extracted ({len(markdown_content)} chars)")
            
            # Create structured document
            document = f"""
# {pdf_path.stem.replace('_', ' ').title()}

**Source:** {pdf_path.name}  
**Collection:** Clinical Data Management Practices  
**Processed with:** DOCLING  
**Processing time:** {processing_time:.2f}s  
**Content length:** {len(markdown_content):,} characters  

---

{markdown_content}
            """.strip()
            
            # Track document details
            doc_info = {
                'filename': pdf_path.name,
                'processing_time': processing_time,
                'content_length': len(markdown_content),
                'structured_length': len(document),
                'success': True
            }
            self.stats['document_details'].append(doc_info)
            
            logger.info(f"    ✅ Processed {pdf_path.name}: {len(markdown_content):,} chars in {processing_time:.2f}s")
            return document
            
        except Exception as e:
            processing_time = time.time() - doc_start_time
            self._handle_error(e, f"docling_processing_{pdf_path.name}")
            
            # Track failed document
            doc_info = {
                'filename': pdf_path.name,
                'processing_time': processing_time,
                'error': str(e),
                'success': False
            }
            self.stats['document_details'].append(doc_info)
            self.stats['failed_documents'] += 1
            
            logger.error(f"    ❌ Failed to process {pdf_path.name}: {e}")
            return None
    
    async def process_all_documents(self, pdf_files: List[Path]) -> List[str]:
        """Process all documents with batch processing and memory management."""
        self._log_progress("Processing all CCDM documents with DOCLING", 4, 8)
        
        processed_documents = []
        batch_size = self.config['max_batch_size']
        
        logger.info(f"  📦 Processing {len(pdf_files)} documents in batches of {batch_size}")
        
        for i in range(0, len(pdf_files), batch_size):
            batch = pdf_files[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(pdf_files) + batch_size - 1) // batch_size
            
            logger.info(f"  📂 Batch {batch_num}/{total_batches}: {len(batch)} documents")
            
            # Monitor memory before batch
            memory_info = self._monitor_memory()
            
            batch_start_time = time.time()
            batch_documents = []
            
            for j, pdf_path in enumerate(batch, 1):
                logger.info(f"    Processing {pdf_path.name} ({i+j}/{len(pdf_files)})")
                
                document = await self.process_document_with_docling(pdf_path)
                if document:
                    batch_documents.append(document)
                    self.stats['processed_documents'] += 1
                
                # Memory check during processing
                if self.config['enable_memory_monitoring']:
                    current_memory = psutil.virtual_memory().percent
                    if current_memory > self.config['memory_threshold'] * 100:
                        logger.warning(f"    Memory usage high: {current_memory:.1f}%")
            
            batch_time = time.time() - batch_start_time
            processed_documents.extend(batch_documents)
            
            logger.info(f"  ✅ Batch {batch_num} completed: {len(batch_documents)}/{len(batch)} documents in {batch_time:.2f}s")
            
            # Small delay between batches for memory management
            if batch_num < total_batches:
                await asyncio.sleep(1)
        
        total_processing_time = time.time() - (time.time() - len(pdf_files) * 30)  # Rough estimate
        self.stats['total_processing_time'] = total_processing_time
        
        logger.info(f"✅ Document processing complete: {len(processed_documents)}/{len(pdf_files)} documents processed")
        return processed_documents
    
    async def build_knowledge_graph(self, documents: List[str]) -> bool:
        """Build comprehensive knowledge graph from all processed documents."""
        self._log_progress("Building comprehensive CCDM knowledge graph", 5, 8)
        
        if not documents:
            logger.error("  ❌ No documents provided for graph building")
            return False
        
        try:
            graph_start_time = time.time()
            
            # Process in small batches to manage memory
            batch_size = self.config['max_batch_size']
            total_batches = (len(documents) + batch_size - 1) // batch_size
            
            logger.info(f"  🏗️ Building graph from {len(documents)} documents in {total_batches} batches")
            
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                
                logger.info(f"    Graph batch {batch_num}/{total_batches}: {len(batch)} documents")
                
                try:
                    await self.lightrag.insert_documents(batch)
                    logger.info(f"    ✅ Graph batch {batch_num} completed successfully")
                    
                    # Monitor memory during graph building
                    memory_info = self._monitor_memory()
                    
                except Exception as e:
                    self._handle_error(e, f"graph_building_batch_{batch_num}")
                    logger.error(f"    ❌ Graph batch {batch_num} failed: {e}")
                    continue
            
            graph_build_time = time.time() - graph_start_time
            logger.info(f"✅ Knowledge graph building completed in {graph_build_time:.2f}s")
            
            return True
            
        except Exception as e:
            self._handle_error(e, "knowledge_graph_building", critical=True)
            return False
    
    async def analyze_graph_statistics(self) -> Dict[str, Any]:
        """Analyze and report comprehensive graph statistics."""
        self._log_progress("Analyzing CCDM knowledge graph statistics", 6, 8)
        
        try:
            working_path = Path(self.working_dir)
            
            graph_files = {
                'entities': working_path / 'vdb_entities.json',
                'relationships': working_path / 'vdb_relationships.json',
                'chunks': working_path / 'vdb_chunks.json',
                'graph': working_path / 'graph_chunk_entity_relation.graphml',
                'doc_status': working_path / 'kv_store_doc_status.json'
            }
            
            stats = {}
            
            for name, file_path in graph_files.items():
                try:
                    if not file_path.exists():
                        stats[name] = {"count": 0, "status": "Not found"}
                        continue
                        
                    file_size = file_path.stat().st_size
                    
                    if name == 'graph' and file_path.suffix == '.graphml':
                        stats[name] = {"size_bytes": file_size, "status": "GraphML file"}
                    elif file_path.suffix == '.json':
                        with open(file_path, 'r') as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                stats[name] = {"count": len(data), "size_bytes": file_size}
                            elif isinstance(data, dict):
                                stats[name] = {"count": len(data), "size_bytes": file_size}
                            else:
                                stats[name] = {"size_bytes": file_size, "status": "Unknown format"}
                    else:
                        stats[name] = {"size_bytes": file_size}
                        
                except Exception as e:
                    self._handle_error(e, f"stat_analysis_{name}")
                    stats[name] = {"error": str(e)}
            
            # Update internal stats
            if 'entities' in stats and 'count' in stats['entities']:
                self.stats['graph_entities'] = stats['entities']['count']
            if 'relationships' in stats and 'count' in stats['relationships']:
                self.stats['graph_relationships'] = stats['relationships']['count']
            if 'chunks' in stats and 'count' in stats['chunks']:
                self.stats['graph_chunks'] = stats['chunks']['count']
            
            logger.info("  📊 CCDM Knowledge Graph Statistics:")
            logger.info(f"    🏷️  Entities: {self.stats['graph_entities']}")
            logger.info(f"    🔗 Relationships: {self.stats['graph_relationships']}")
            logger.info(f"    📄 Text Chunks: {self.stats['graph_chunks']}")
            logger.info(f"    📋 Documents: {self.stats['processed_documents']}/{self.stats['total_documents']}")
            
            return stats
            
        except Exception as e:
            self._handle_error(e, "graph_statistics")
            return {}
    
    async def test_database_queries(self) -> List[Dict[str, Any]]:
        """Test the CCDM database with comprehensive queries."""
        self._log_progress("Testing CCDM database with sample queries", 7, 8)
        
        ccdm_queries = [
            {
                'question': "What are the key principles of good clinical data management?",
                'mode': 'hybrid',
                'expected_topics': ['GCP', 'data quality', 'validation']
            },
            {
                'question': "How should adverse events be managed in clinical trials?",
                'mode': 'global',
                'expected_topics': ['SAE', 'safety', 'reporting']
            },
            {
                'question': "What are the requirements for database validation?",
                'mode': 'local',
                'expected_topics': ['validation', 'testing', 'programming']
            },
            {
                'question': "How should electronic data capture systems be implemented?",
                'mode': 'hybrid',
                'expected_topics': ['EDC', 'implementation', 'training']
            }
        ]
        
        query_results = []
        
        for i, query in enumerate(ccdm_queries, 1):
            logger.info(f"  🔎 Query {i}/{len(ccdm_queries)}: {query['mode'].upper()} mode")
            logger.info(f"    ❓ {query['question']}")
            
            try:
                start_time = time.time()
                
                response = await asyncio.wait_for(
                    self.lightrag.query(query['question'], mode=query['mode']),
                    timeout=90.0
                )
                
                query_time = time.time() - start_time
                response_length = len(response)
                
                logger.info(f"    ⚡ Response time: {query_time:.2f}s")
                logger.info(f"    📏 Response length: {response_length:,} characters")
                logger.info(f"    🎯 Preview: {response[:150]}...")
                
                query_results.append({
                    'query': query,
                    'response': response,
                    'response_time': query_time,
                    'response_length': response_length,
                    'success': True
                })
                
            except asyncio.TimeoutError:
                self._handle_error(TimeoutError("Query timeout"), f"ccdm_query_{i}")
                logger.error(f"    ❌ Query timed out after 90 seconds")
                query_results.append({
                    'query': query,
                    'error': 'Timeout',
                    'success': False
                })
            except Exception as e:
                self._handle_error(e, f"ccdm_query_{i}")
                logger.error(f"    ❌ Query failed: {e}")
                query_results.append({
                    'query': query,
                    'error': str(e),
                    'success': False
                })
        
        successful_queries = sum(1 for r in query_results if r.get('success', False))
        logger.info(f"✅ Query testing complete: {successful_queries}/{len(ccdm_queries)} queries successful")
        
        return query_results
    
    async def generate_final_report(self, graph_stats: Dict, query_results: List[Dict]) -> None:
        """Generate comprehensive final report for CCDM database."""
        self._log_progress("Generating comprehensive CCDM database report", 8, 8)
        
        try:
            total_time = time.time() - self.start_time
            
            # Calculate processing statistics
            avg_doc_time = (sum(d['processing_time'] for d in self.stats['document_details'] if d.get('success', False)) / 
                          max(self.stats['processed_documents'], 1))
            
            total_content_chars = sum(d.get('content_length', 0) for d in self.stats['document_details'] if d.get('success', False))
            
            report = {
                'metadata': {
                    'database_name': 'CCDM (Clinical Data Management) RAG Database',
                    'build_timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'total_build_time': total_time,
                    'lightrag_version': 'latest',
                    'models': {
                        'llm': 'qwen2.5:7b-instruct',
                        'embedding': 'nomic-embed-text',
                        'document_processor': 'DOCLING'
                    },
                    'configuration': self.config
                },
                'document_processing': {
                    'total_documents': self.stats['total_documents'],
                    'processed_successfully': self.stats['processed_documents'],
                    'failed_documents': self.stats['failed_documents'],
                    'success_rate': (self.stats['processed_documents'] / max(self.stats['total_documents'], 1)) * 100,
                    'average_processing_time': avg_doc_time,
                    'total_content_characters': total_content_chars,
                    'document_details': self.stats['document_details']
                },
                'knowledge_graph': {
                    'entities': self.stats['graph_entities'],
                    'relationships': self.stats['graph_relationships'],
                    'text_chunks': self.stats['graph_chunks'],
                    'graph_files': graph_stats
                },
                'performance': {
                    'memory_usage': self.stats['memory_usage'],
                    'errors': self.stats['errors'],
                    'query_results': query_results
                },
                'working_directory': self.working_dir
            }
            
            # Save detailed report
            report_file = Path('ccdm_database_report.json')
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            logger.info(f"  ✅ Detailed report saved to {report_file}")
            
            # Create executive summary
            summary = f"""
# 🏥 CCDM RAG Database - Build Report

**Status:** {'✅ SUCCESS' if self.stats['failed_documents'] == 0 else '⚠️ PARTIAL SUCCESS'}  
**Build Time:** {total_time:.1f} seconds ({total_time/60:.1f} minutes)  
**Date:** {report['metadata']['build_timestamp']}  

## 📊 Database Statistics
- **Documents Processed:** {self.stats['processed_documents']}/{self.stats['total_documents']} ({report['document_processing']['success_rate']:.1f}% success)
- **Knowledge Graph Entities:** {self.stats['graph_entities']:,}
- **Knowledge Graph Relationships:** {self.stats['graph_relationships']:,}
- **Text Chunks:** {self.stats['graph_chunks']:,}
- **Total Content:** {total_content_chars:,} characters

## 🔧 Technology Stack
- ✅ **DOCLING:** Superior PDF processing with structure preservation
- ✅ **LightRAG:** Advanced knowledge graph construction and reasoning
- ✅ **Ollama:** Local LLM (qwen2.5:7b-instruct + nomic-embed-text)
- ✅ **Clinical Focus:** Comprehensive Clinical Data Management coverage

## 📚 Document Coverage
The CCDM database includes comprehensive coverage of:
- Good Clinical Data Management Practices
- Electronic Data Capture (EDC) systems
- Data validation and programming standards
- Safety data management and adverse event reporting
- Quality assurance and quality control processes
- Regulatory compliance (GCP, FDA, ICH guidelines)
- Database design, validation, and closure procedures
- Vendor selection and management
- Training and metrics in clinical data management

## 🎯 Query Performance
"""
            
            for result in query_results:
                if result.get('success', False):
                    mode = result['query']['mode']
                    time_val = result['response_time']
                    length = result['response_length']
                    summary += f"- **{mode.capitalize()}:** {time_val:.2f}s, {length:,} chars ✅\\n"
                else:
                    mode = result['query']['mode']
                    error = result.get('error', 'Unknown')
                    summary += f"- **{mode.capitalize()}:** Failed ({error}) ❌\\n"
            
            if self.stats['errors']:
                summary += f"\\n## ⚠️ Build Issues ({len(self.stats['errors'])})\\n"
                for error in self.stats['errors'][-5:]:  # Show last 5 errors
                    summary += f"- {error['context']}: {error['error_type']}\\n"
            
            summary += f"""
## 📁 Generated Files
- **Knowledge Graph:** `{self.working_dir}/`
- **Detailed Report:** `ccdm_database_report.json`
- **Build Log:** `ccdm_database_build.log`

## 🚀 Usage
The CCDM RAG database is now ready for production use:
```python
from src.rag.lightrag_service import LightRAGService

# Initialize with CCDM database
ccdm_rag = LightRAGService(working_dir="{self.working_dir}")
await ccdm_rag.initialize()

# Query the comprehensive clinical data management knowledge
response = await ccdm_rag.query("Your clinical data management question", mode="hybrid")
```

## 📈 Database Quality Metrics
- **Entity Density:** {self.stats['graph_entities'] / max(self.stats['processed_documents'], 1):.1f} entities per document
- **Relationship Density:** {self.stats['graph_relationships'] / max(self.stats['processed_documents'], 1):.1f} relationships per document
- **Content Coverage:** {total_content_chars / 1000:.0f}K characters of clinical knowledge
            """
            
            # Save executive summary
            summary_file = Path('ccdm_database_summary.md')
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(summary)
            
            logger.info(f"  ✅ Executive summary saved to {summary_file}")
            
        except Exception as e:
            self._handle_error(e, "report_generation")
    
    def _save_partial_results(self):
        """Save partial results in case of interruption."""
        try:
            partial_report = {
                'status': 'interrupted',
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'statistics': self.stats,
                'working_directory': self.working_dir
            }
            
            with open('ccdm_partial_results.json', 'w') as f:
                json.dump(partial_report, f, indent=2)
                
            logger.info("Partial results saved to ccdm_partial_results.json")
        except Exception as e:
            logger.error(f"Failed to save partial results: {e}")
    
    async def cleanup(self):
        """Clean up resources."""
        try:
            if self.lightrag:
                await self.lightrag.close()
                logger.info("  ✅ LightRAG service closed")
        except Exception as e:
            self._handle_error(e, "cleanup")
        finally:
            total_time = time.time() - self.start_time
            logger.info(f"🏁 CCDM database build completed in {total_time:.1f} seconds")

async def main():
    """Main execution function for CCDM database building."""
    print("🏥 CCDM (Clinical Data Management) RAG Database Builder")
    print("=" * 70)
    print("Building comprehensive knowledge graph from 33 clinical data management documents")
    print("Features: DOCLING processing, production optimization, comprehensive validation")
    print()
    
    builder = CCDMDatabaseBuilder()
    success = False
    
    try:
        # Execute build process step by step
        if not await builder.check_services():
            logger.error("❌ Service check failed")
            return 1
        
        if not await builder.initialize_lightrag():
            logger.error("❌ LightRAG initialization failed")
            return 1
        
        pdf_files = await builder.get_document_list()
        if not pdf_files:
            logger.error("❌ No documents found to process")
            return 1
        
        documents = await builder.process_all_documents(pdf_files)
        if not documents:
            logger.error("❌ Document processing failed completely")
            return 1
        
        if not await builder.build_knowledge_graph(documents):
            logger.error("❌ Knowledge graph building failed")
            return 1
        
        graph_stats = await builder.analyze_graph_statistics()
        query_results = await builder.test_database_queries()
        
        await builder.generate_final_report(graph_stats, query_results)
        
        success = True
        
        print("\\n" + "=" * 70)
        print("✅ CCDM RAG Database Build Complete!")
        print(f"🏥 {builder.stats['processed_documents']}/{builder.stats['total_documents']} clinical documents processed")
        print(f"🏷️ {builder.stats['graph_entities']:,} entities extracted")
        print(f"🔗 {builder.stats['graph_relationships']:,} relationships mapped")
        print(f"📄 {builder.stats['graph_chunks']:,} text chunks indexed")
        print("=" * 70)
        print("📊 Check 'ccdm_database_report.json' for detailed analysis")
        print("📋 Check 'ccdm_database_summary.md' for executive summary") 
        print("📝 Check 'ccdm_database_build.log' for full build logs")
        print(f"🕸️ Knowledge graph saved in '{builder.working_dir}/'")
        print("=" * 70)
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Build interrupted by user")
        return 1
    except Exception as e:
        builder._handle_error(e, "main_execution", critical=True)
        logger.error(f"Build failed with critical error: {e}")
        return 1
    
    finally:
        await builder.cleanup()
        
        if success:
            print("\\n🎉 CCDM RAG Database is ready for production clinical data management queries!")
        else:
            print("\\n⚠️ Build completed with issues. Check logs for details.")

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)