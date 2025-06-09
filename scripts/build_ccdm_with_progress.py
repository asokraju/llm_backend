#!/usr/bin/env python3
"""
CCDM Database Builder with Progress Bar and Document-Specific Querying

Features:
- Real-time progress bar with ETA
- Document-by-document status tracking
- Resume capability from partial builds
- Document-specific query support
- Memory and performance monitoring
"""

import asyncio
import logging
import time
import sys
import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import requests
from tqdm import tqdm
import psutil

# Setup paths
script_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(script_dir, '../..'))
sys.path.append(project_root)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ccdm_progress.log', mode='w'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ProgressCCDMBuilder:
    """CCDM Database Builder with progress tracking and document-specific features."""
    
    def __init__(self):
        self.working_dir = "ccdm_rag_database"
        self.data_dir = Path("data")
        self.lightrag = None
        self.start_time = time.time()
        
        # Progress tracking
        self.progress_file = Path("ccdm_build_progress.json")
        self.stats = {
            'start_time': self.start_time,
            'documents': {},
            'current_phase': 'initialization',
            'total_entities': 0,
            'total_relationships': 0,
            'total_chunks': 0
        }
        
        # Load existing progress if available
        self.load_progress()
    
    def load_progress(self):
        """Load existing progress from file."""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r') as f:
                    saved_progress = json.load(f)
                    self.stats.update(saved_progress)
                logger.info(f"📂 Loaded existing progress: {len(self.stats['documents'])} documents tracked")
            except Exception as e:
                logger.warning(f"Could not load progress file: {e}")
    
    def save_progress(self):
        """Save current progress to file."""
        try:
            with open(self.progress_file, 'w') as f:
                json.dump(self.stats, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save progress: {e}")
    
    def update_document_status(self, filename: str, status: str, **kwargs):
        """Update status for a specific document."""
        if filename not in self.stats['documents']:
            self.stats['documents'][filename] = {}
        
        self.stats['documents'][filename]['status'] = status
        self.stats['documents'][filename]['timestamp'] = time.time()
        self.stats['documents'][filename].update(kwargs)
        self.save_progress()
    
    async def check_services(self) -> bool:
        """Check all required services."""
        print("🔍 Checking Services...")
        services = {
            'API': 'http://localhost:9000/health',
            'Ollama': 'http://localhost:12434/api/version', 
            'Qdrant': 'http://localhost:7333/'
        }
        
        for name, url in services.items():
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    print(f"  ✅ {name}: Running")
                else:
                    print(f"  ❌ {name}: HTTP {response.status_code}")
                    return False
            except Exception as e:
                print(f"  ❌ {name}: {e}")
                return False
        return True
    
    async def initialize_lightrag(self) -> bool:
        """Initialize LightRAG service."""
        print("🚀 Initializing LightRAG...")
        try:
            current_dir = os.getcwd()
            sys.path.insert(0, current_dir)
            from src.rag.lightrag_service import LightRAGService
            
            Path(self.working_dir).mkdir(parents=True, exist_ok=True)
            
            self.lightrag = LightRAGService(
                working_dir=self.working_dir,
                llm_model="qwen2.5:7b-instruct",
                embedding_model="nomic-embed-text",
                embedding_dim=768
            )
            
            await self.lightrag.initialize()
            print("✅ LightRAG initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize LightRAG: {e}")
            return False
    
    async def get_documents_to_process(self) -> List[Path]:
        """Get list of documents that need processing."""
        pdf_files = sorted(list(self.data_dir.glob("*.pdf")))
        
        # Filter out already processed documents
        unprocessed = []
        for pdf in pdf_files:
            status = self.stats['documents'].get(pdf.name, {}).get('status', 'pending')
            if status != 'completed':
                unprocessed.append(pdf)
        
        print(f"📚 Found {len(pdf_files)} total documents")
        print(f"📋 {len(unprocessed)} documents need processing")
        print(f"✅ {len(pdf_files) - len(unprocessed)} documents already completed")
        
        return unprocessed
    
    async def process_document_with_progress(self, pdf_path: Path, pbar: tqdm) -> bool:
        """Process a single document with progress updates."""
        filename = pdf_path.name
        
        try:
            self.update_document_status(filename, 'processing', 
                                      size_bytes=pdf_path.stat().st_size)
            
            pbar.set_description(f"Processing {filename[:30]}...")
            
            # Import DOCLING
            try:
                from docling.document_converter import DocumentConverter
            except ImportError:
                print(f"📦 Installing DOCLING...")
                import subprocess
                result = subprocess.run([sys.executable, "-m", "pip", "install", "docling"],
                                      capture_output=True, text=True, timeout=120)
                if result.returncode != 0:
                    raise Exception(f"DOCLING installation failed: {result.stderr}")
                from docling.document_converter import DocumentConverter
            
            converter = DocumentConverter()
            
            # Process document
            doc_start = time.time()
            result = converter.convert(pdf_path)
            markdown_content = result.document.export_to_markdown()
            processing_time = time.time() - doc_start
            
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
            
            # Insert into knowledge graph
            graph_start = time.time()
            await self.lightrag.insert_documents([document])
            graph_time = time.time() - graph_start
            
            # Update status
            self.update_document_status(filename, 'completed',
                                      processing_time=processing_time,
                                      graph_time=graph_time,
                                      content_length=len(markdown_content),
                                      structured_length=len(document))
            
            pbar.set_postfix({
                'Doc': f"{processing_time:.1f}s",
                'Graph': f"{graph_time:.1f}s", 
                'Chars': f"{len(markdown_content):,}"
            })
            pbar.update(1)
            
            return True
            
        except Exception as e:
            self.update_document_status(filename, 'failed', error=str(e))
            logger.error(f"Failed to process {filename}: {e}")
            pbar.update(1)
            return False
    
    async def build_database_with_progress(self):
        """Build database with progress bar."""
        print("🏗️ Building CCDM Knowledge Database...")
        
        documents = await self.get_documents_to_process()
        if not documents:
            print("✅ All documents already processed!")
            return True
        
        # Create progress bar
        pbar = tqdm(
            total=len(documents),
            desc="Processing Documents",
            unit="doc",
            bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}] {postfix}"
        )
        
        success_count = 0
        
        try:
            for pdf_path in documents:
                # Memory check
                memory = psutil.virtual_memory()
                if memory.percent > 90:
                    logger.warning(f"High memory usage: {memory.percent:.1f}%")
                    await asyncio.sleep(2)  # Brief pause
                
                success = await self.process_document_with_progress(pdf_path, pbar)
                if success:
                    success_count += 1
                
                # Small delay between documents
                await asyncio.sleep(0.5)
                
        finally:
            pbar.close()
        
        print(f"\n✅ Processing complete: {success_count}/{len(documents)} documents successful")
        return success_count > 0
    
    async def analyze_final_database(self):
        """Analyze final database statistics."""
        print("\n📊 Analyzing CCDM Database...")
        
        try:
            working_path = Path(self.working_dir)
            
            # Load statistics
            entities_file = working_path / 'vdb_entities.json'
            relationships_file = working_path / 'vdb_relationships.json'
            chunks_file = working_path / 'vdb_chunks.json'
            
            stats = {}
            
            if entities_file.exists():
                with open(entities_file, 'r') as f:
                    entities = json.load(f)
                    stats['entities'] = len(entities)
            
            if relationships_file.exists():
                with open(relationships_file, 'r') as f:
                    relationships = json.load(f)
                    stats['relationships'] = len(relationships)
            
            if chunks_file.exists():
                with open(chunks_file, 'r') as f:
                    chunks = json.load(f)
                    stats['chunks'] = len(chunks)
            
            # Update internal stats
            self.stats.update({
                'total_entities': stats.get('entities', 0),
                'total_relationships': stats.get('relationships', 0),
                'total_chunks': stats.get('chunks', 0),
                'completion_time': time.time()
            })
            
            print(f"🏷️  Entities: {stats.get('entities', 0):,}")
            print(f"🔗 Relationships: {stats.get('relationships', 0):,}")  
            print(f"📄 Text Chunks: {stats.get('chunks', 0):,}")
            
            # Document summary
            completed_docs = [doc for doc, info in self.stats['documents'].items() 
                            if info.get('status') == 'completed']
            failed_docs = [doc for doc, info in self.stats['documents'].items()
                         if info.get('status') == 'failed']
            
            print(f"📋 Documents: {len(completed_docs)} completed, {len(failed_docs)} failed")
            
            if failed_docs:
                print("❌ Failed documents:")
                for doc in failed_docs:
                    error = self.stats['documents'][doc].get('error', 'Unknown error')
                    print(f"   • {doc}: {error}")
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to analyze database: {e}")
            return {}
    
    async def test_document_specific_query(self):
        """Test document-specific querying capability."""
        print("\n🔎 Testing Document-Specific Queries...")
        
        try:
            # Test general query
            print("1. General query across all documents:")
            response = await self.lightrag.query(
                "What are the key principles of clinical data management?", 
                mode="hybrid"
            )
            print(f"   Response length: {len(response)} characters")
            print(f"   Preview: {response[:150]}...")
            
            # Test with document filter (if supported)
            print("\n2. Document-specific query capability:")
            print("   Note: LightRAG supports filtering by using specific terms")
            print("   Example: 'In the data management plan document, what are the key requirements?'")
            
            response2 = await self.lightrag.query(
                "In the data management plan document, what are the key requirements?",
                mode="local"
            )
            print(f"   Response length: {len(response2)} characters")
            print(f"   Preview: {response2[:150]}...")
            
        except Exception as e:
            logger.error(f"Query testing failed: {e}")
    
    async def cleanup(self):
        """Clean up resources."""
        if self.lightrag:
            await self.lightrag.close()
        self.save_progress()

async def main():
    """Main execution with progress tracking."""
    print("🏥 CCDM Database Builder with Progress Tracking")
    print("=" * 60)
    
    builder = ProgressCCDMBuilder()
    
    try:
        # Check services
        if not await builder.check_services():
            print("❌ Service check failed")
            return 1
        
        # Initialize LightRAG
        if not await builder.initialize_lightrag():
            print("❌ LightRAG initialization failed") 
            return 1
        
        # Build database with progress
        if not await builder.build_database_with_progress():
            print("❌ Database building failed")
            return 1
        
        # Analyze results
        stats = await builder.analyze_final_database()
        
        # Test querying
        await builder.test_document_specific_query()
        
        print("\n" + "=" * 60)
        print("✅ CCDM Database Build Complete!")
        print(f"🕒 Total time: {(time.time() - builder.start_time)/60:.1f} minutes")
        print(f"💾 Database location: {builder.working_dir}/")
        print(f"📊 Progress file: {builder.progress_file}")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        logger.error(f"Build failed: {e}")
        return 1
    
    finally:
        await builder.cleanup()

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️ Build interrupted by user")
        sys.exit(1)