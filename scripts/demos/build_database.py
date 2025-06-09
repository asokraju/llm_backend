#!/usr/bin/env python3
"""
Build LightRAG database from clinical data management PDFs.

This script processes all PDF files in the data/ directory and creates
a comprehensive knowledge graph database.
"""

import asyncio
import os
import logging
from pathlib import Path
from typing import List
import sys

# Add the parent directory to the path so we can import from src
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

import PyPDF2
import requests
from src.rag.lightrag_service import LightRAGService


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from a PDF file."""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    text += f"\n--- Page {page_num + 1} ---\n"
                    text += page_text
                except Exception as e:
                    logger.warning(f"Error extracting page {page_num + 1} from {pdf_path}: {e}")
                    continue
            
            return text.strip()
    except Exception as e:
        logger.error(f"Error reading PDF {pdf_path}: {e}")
        return ""


def chunk_text(text: str, chunk_size: int = 8000, overlap: int = 500) -> List[str]:
    """Split text into overlapping chunks."""
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # If not the first chunk, move back to include overlap
        if start > 0:
            start = start - overlap
        
        chunk = text[start:end]
        
        # Try to break at sentence boundary
        if end < len(text):
            last_period = chunk.rfind('.')
            last_newline = chunk.rfind('\n')
            break_point = max(last_period, last_newline)
            
            if break_point > len(chunk) * 0.7:  # If break point is reasonable
                chunk = chunk[:break_point + 1]
                end = start + len(chunk)
        
        chunks.append(chunk.strip())
        start = end
        
        if start >= len(text):
            break
    
    return chunks


async def process_pdfs_and_build_database():
    """Process all PDFs and build the knowledge graph database."""
    
    # Check if services are ready
    logger.info("Checking if services are ready...")
    
    # Wait for Ollama to be ready
    ollama_ready = False
    for attempt in range(30):  # 30 seconds timeout
        try:
            response = requests.get("http://localhost:12434/api/version", timeout=5)
            if response.status_code == 200:
                ollama_ready = True
                logger.info("Ollama service is ready")
                break
        except Exception:
            pass
        
        logger.info(f"Waiting for Ollama... (attempt {attempt + 1}/30)")
        await asyncio.sleep(1)
    
    if not ollama_ready:
        logger.error("Ollama service not available. Please ensure services are running.")
        return
    
    # Wait for API to be ready
    api_ready = False
    for attempt in range(30):  # 30 seconds timeout
        try:
            response = requests.get("http://localhost:9000/health", timeout=5)
            if response.status_code == 200:
                api_ready = True
                logger.info("API service is ready")
                break
        except Exception:
            pass
        
        logger.info(f"Waiting for API... (attempt {attempt + 1}/30)")
        await asyncio.sleep(1)
    
    if not api_ready:
        logger.error("API service not available. Please ensure services are running.")
        return
    
    # Initialize LightRAG service
    logger.info("Initializing LightRAG service...")
    service = LightRAGService(
        working_dir="./clinical_data_rag",
        llm_model="qwen2.5:7b-instruct",
        embedding_model="nomic-embed-text"
    )
    
    try:
        await service.initialize()
        logger.info("LightRAG service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize LightRAG service: {e}")
        return
    
    # Process PDF files
    data_dir = Path("data")
    pdf_files = list(data_dir.glob("*.pdf"))
    pdf_files.sort()  # Process in order
    
    logger.info(f"Found {len(pdf_files)} PDF files to process")
    
    all_documents = []
    
    for i, pdf_path in enumerate(pdf_files, 1):
        logger.info(f"Processing {pdf_path.name} ({i}/{len(pdf_files)})")
        
        # Extract text
        text = extract_text_from_pdf(str(pdf_path))
        if not text:
            logger.warning(f"No text extracted from {pdf_path.name}")
            continue
        
        # Create document with metadata
        document_content = f"""
# {pdf_path.stem.replace('_', ' ')}

Source: {pdf_path.name}
Document Type: Clinical Data Management Guide
Processed: {i}/{len(pdf_files)}

{text}
        """.strip()
        
        # Chunk the document
        chunks = chunk_text(document_content, chunk_size=6000, overlap=300)
        logger.info(f"Split {pdf_path.name} into {len(chunks)} chunks")
        
        all_documents.extend(chunks)
    
    logger.info(f"Total documents to insert: {len(all_documents)}")
    
    # Insert documents in batches
    batch_size = 5  # Process 5 documents at a time
    total_batches = (len(all_documents) + batch_size - 1) // batch_size
    
    for batch_num in range(total_batches):
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, len(all_documents))
        batch_docs = all_documents[start_idx:end_idx]
        
        logger.info(f"Inserting batch {batch_num + 1}/{total_batches} ({len(batch_docs)} documents)")
        
        try:
            await service.insert_documents(batch_docs)
            logger.info(f"Successfully inserted batch {batch_num + 1}")
        except Exception as e:
            logger.error(f"Error inserting batch {batch_num + 1}: {e}")
            continue
    
    logger.info("Database building complete!")
    
    # Test the database with sample queries
    logger.info("Testing database with sample queries...")
    
    test_queries = [
        ("What is clinical data management?", "naive"),
        ("What are the key principles of data privacy?", "local"),
        ("How do you ensure data quality in clinical research?", "global"),
        ("What is the role of a clinical data manager?", "hybrid")
    ]
    
    for question, mode in test_queries:
        logger.info(f"Testing query: '{question}' (mode: {mode})")
        try:
            response = await service.query(question, mode=mode)
            logger.info(f"Response length: {len(response)} characters")
            logger.info(f"Response preview: {response[:200]}...")
        except Exception as e:
            logger.error(f"Error testing query: {e}")
    
    # Cleanup
    await service.close()
    logger.info("LightRAG service closed")


def main():
    """Main function to run the database building process."""
    print("=" * 70)
    print("Clinical Data Management Knowledge Graph Builder")
    print("=" * 70)
    print()
    
    # Check if data directory exists
    if not os.path.exists("data"):
        print("❌ Error: 'data' directory not found")
        print("Please ensure PDF files are in the 'data' directory")
        return
    
    # Check if PDFs exist
    pdf_files = list(Path("data").glob("*.pdf"))
    if not pdf_files:
        print("❌ Error: No PDF files found in 'data' directory")
        return
    
    print(f"✅ Found {len(pdf_files)} PDF files")
    print("📊 This will create a comprehensive knowledge graph from clinical data management documents")
    print()
    
    # Check if required packages are available
    try:
        import PyPDF2
        import requests
    except ImportError as e:
        print(f"❌ Error: Missing required package: {e}")
        print("Please install: pip install PyPDF2 requests")
        return
    
    print("🚀 Starting database building process...")
    print("⏱️  This may take 10-30 minutes depending on document size")
    print()
    
    asyncio.run(process_pdfs_and_build_database())
    
    print()
    print("=" * 70)
    print("✅ Database building complete!")
    print("🔍 You can now query the knowledge graph using:")
    print("   - curl http://localhost:8000/query")
    print("   - python examples/connect_to_services.py api")
    print("   - The tutorial examples in TUTORIAL.md")
    print("=" * 70)


if __name__ == "__main__":
    main()