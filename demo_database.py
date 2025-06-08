#!/usr/bin/env python3
"""
Quick demo of LightRAG database building with first 5 PDFs.
This creates a working demonstration of the knowledge graph functionality.
"""

import asyncio
import os
import logging
from pathlib import Path
from typing import List
import PyPDF2
import requests
from src.rag.lightrag_service import LightRAGService


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
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


def chunk_text(text: str, chunk_size: int = 6000) -> List[str]:
    """Split text into chunks."""
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        
        # Try to break at sentence boundary
        if end < len(text):
            last_period = chunk.rfind('.')
            if last_period > len(chunk) * 0.7:
                chunk = chunk[:last_period + 1]
                end = start + len(chunk)
        
        chunks.append(chunk.strip())
        start = end
        
        if start >= len(text):
            break
    
    return chunks


async def build_demo_database():
    """Build a demo database with first 5 PDFs."""
    
    logger.info("🚀 Starting Clinical Data Management Demo Database")
    
    # Check services
    try:
        response = requests.get("http://localhost:12434/api/version", timeout=5)
        logger.info(f"✅ Ollama ready: {response.json()['version']}")
    except Exception as e:
        logger.error(f"❌ Ollama not ready: {e}")
        return
    
    # Initialize LightRAG
    logger.info("Initializing LightRAG service...")
    service = LightRAGService(
        working_dir="./demo_clinical_rag",
        llm_model="qwen2.5:7b-instruct",
        embedding_model="nomic-embed-text"
    )
    
    try:
        await service.initialize()
        logger.info("✅ LightRAG initialized")
    except Exception as e:
        logger.error(f"❌ LightRAG initialization failed: {e}")
        return
    
    # Process first 5 PDFs
    data_dir = Path("data")
    pdf_files = sorted(list(data_dir.glob("*.pdf")))[:5]  # First 5 PDFs only
    
    logger.info(f"📚 Processing {len(pdf_files)} PDFs for demo:")
    for pdf in pdf_files:
        logger.info(f"  - {pdf.name}")
    
    documents = []
    
    for i, pdf_path in enumerate(pdf_files, 1):
        logger.info(f"📖 Processing {pdf_path.name} ({i}/{len(pdf_files)})")
        
        text = extract_text_from_pdf(str(pdf_path))
        if not text:
            continue
        
        # Create document with metadata
        document_content = f"""
# {pdf_path.stem.replace('_', ' ')}

**Source**: {pdf_path.name}  
**Document Type**: Clinical Data Management Guide  
**Chapter**: {i} of {len(pdf_files)}

{text}
        """.strip()
        
        # Chunk the document
        chunks = chunk_text(document_content)
        logger.info(f"  → Split into {len(chunks)} chunks")
        documents.extend(chunks)
    
    logger.info(f"📦 Total chunks to insert: {len(documents)}")
    
    # Insert documents
    logger.info("💾 Inserting documents into knowledge graph...")
    try:
        await service.insert_documents(documents)
        logger.info("✅ All documents inserted successfully!")
    except Exception as e:
        logger.error(f"❌ Document insertion failed: {e}")
        await service.close()
        return
    
    # Test with comprehensive queries
    logger.info("🔍 Testing knowledge graph with various queries...")
    
    test_queries = [
        ("What is clinical data management?", "naive"),
        ("What are the key principles of data privacy in clinical research?", "local"), 
        ("How should a data management plan be structured?", "global"),
        ("What are the best practices for clinical data management?", "hybrid"),
        ("What is the role of project management in clinical data?", "hybrid")
    ]
    
    results = []
    
    for question, mode in test_queries:
        logger.info(f"\n{'='*60}")
        logger.info(f"❓ Question: {question}")
        logger.info(f"🔧 Mode: {mode}")
        logger.info(f"{'='*60}")
        
        try:
            response = await service.query(question, mode=mode)
            logger.info(f"✅ Response generated ({len(response)} chars)")
            
            # Store result
            results.append({
                "question": question,
                "mode": mode,
                "response": response,
                "length": len(response)
            })
            
            # Print preview
            preview = response[:400] + "..." if len(response) > 400 else response
            print(f"\n🤖 **Answer**: {preview}\n")
            
        except Exception as e:
            logger.error(f"❌ Query failed: {e}")
    
    # Save results to file for review
    logger.info("💾 Saving demo results...")
    with open("demo_results.txt", "w", encoding="utf-8") as f:
        f.write("Clinical Data Management Knowledge Graph Demo Results\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Database built from {len(pdf_files)} PDF documents\n")
        f.write(f"Total chunks processed: {len(documents)}\n")
        f.write(f"Total queries tested: {len(results)}\n\n")
        
        for i, result in enumerate(results, 1):
            f.write(f"Query {i}: {result['question']}\n")
            f.write(f"Mode: {result['mode']}\n")
            f.write(f"Response Length: {result['length']} characters\n")
            f.write("-" * 40 + "\n")
            f.write(result['response'])
            f.write("\n\n" + "=" * 60 + "\n\n")
    
    await service.close()
    
    logger.info("🎉 Demo database build complete!")
    logger.info("📄 Results saved to: demo_results.txt")
    logger.info("📁 Knowledge graph data stored in: ./demo_clinical_rag/")
    
    print("\n" + "=" * 70)
    print("🎯 CLINICAL DATA MANAGEMENT KNOWLEDGE GRAPH DEMO COMPLETE!")
    print("=" * 70)
    print(f"📚 Processed: {len(pdf_files)} PDF documents")
    print(f"🧩 Created: {len(documents)} knowledge chunks")
    print(f"❓ Tested: {len(results)} different query modes")
    print(f"📄 Results: Saved to demo_results.txt")
    print("=" * 70)
    print("\n🔍 You can now query the knowledge graph using:")
    print("  • Different modes: naive, local, global, hybrid")
    print("  • Complex questions about clinical data management")
    print("  • The Python service directly or API endpoints")
    print("\n💡 To build the full database with all 33 PDFs, run:")
    print("     python build_database.py")


if __name__ == "__main__":
    asyncio.run(build_demo_database())