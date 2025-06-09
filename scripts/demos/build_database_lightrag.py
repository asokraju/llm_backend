#!/usr/bin/env python3
"""
Build LightRAG database using LightRAG's native document processing with DOCLING.
No more PyPDF2 - uses LightRAG's built-in document processing pipeline.
"""

import asyncio
import os
import sys
import logging
from pathlib import Path
from typing import List
import requests

# Add src directory to Python path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from src.rag.lightrag_service import LightRAGService


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def build_database_with_lightrag():
    """Build database using LightRAG's native document processing."""
    
    logger.info("🚀 Starting LightRAG Database Build (using DOCLING)")
    
    # Check services
    try:
        response = requests.get("http://localhost:12434/api/version", timeout=5)
        logger.info(f"✅ Ollama ready: {response.json()['version']}")
    except Exception as e:
        logger.error(f"❌ Ollama not ready: {e}")
        return
    
    # Initialize LightRAG service
    logger.info("Initializing LightRAG service...")
    service = LightRAGService(
        working_dir="./clinical_data_lightrag",
        llm_model="qwen2.5:7b-instruct",
        embedding_model="nomic-embed-text"
    )
    
    try:
        await service.initialize()
        logger.info("✅ LightRAG initialized")
    except Exception as e:
        logger.error(f"❌ LightRAG initialization failed: {e}")
        return
    
    # Get all PDF files
    data_dir = Path("data")
    pdf_files = sorted(list(data_dir.glob("*.pdf")))
    
    logger.info(f"📚 Found {len(pdf_files)} PDF files to process")
    for pdf in pdf_files:
        logger.info(f"  - {pdf.name}")
    
    # Use LightRAG's native document processing
    # This will automatically use DOCLING if DOCUMENT_LOADING_ENGINE=DOCLING
    documents_for_lightrag = []
    
    for i, pdf_path in enumerate(pdf_files, 1):
        logger.info(f"📖 Preparing {pdf_path.name} ({i}/{len(pdf_files)})")
        
        # Read PDF as binary (LightRAG will handle conversion with docling)
        try:
            with open(pdf_path, 'rb') as f:
                pdf_content = f.read()
            
            # Create a document entry that LightRAG can process
            # LightRAG will automatically detect .pdf extension and use docling
            document_info = {
                'content': pdf_content,
                'filename': pdf_path.name,
                'path': str(pdf_path),
                'source': f"Clinical Data Management - {pdf_path.stem.replace('_', ' ')}"
            }
            
            documents_for_lightrag.append(document_info)
            logger.info(f"  → Prepared {pdf_path.name}")
            
        except Exception as e:
            logger.error(f"❌ Error reading {pdf_path.name}: {e}")
            continue
    
    logger.info(f"📦 Total documents prepared: {len(documents_for_lightrag)}")
    
    # Process documents using LightRAG's pipeline
    logger.info("💾 Processing documents with LightRAG + DOCLING...")
    
    # For LightRAG's native processing, we need to save files and let it process them
    # Or we can use the text insertion if we extract content first
    
    # Let's use a hybrid approach - copy PDFs to LightRAG's input directory
    # and let it process them with its native pipeline
    
    lightrag_input_dir = Path(service.working_dir) / "inputs"
    lightrag_input_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy PDF files to LightRAG input directory
    for i, pdf_path in enumerate(pdf_files, 1):
        dest_path = lightrag_input_dir / pdf_path.name
        if not dest_path.exists():
            logger.info(f"📋 Copying {pdf_path.name} to LightRAG input directory")
            import shutil
            shutil.copy2(pdf_path, dest_path)
    
    # Now let LightRAG process all files with its native pipeline
    # We'll simulate what the LightRAG API does
    try:
        from lightrag.api.routers.document_routes import pipeline_index_files
        
        # Get list of PDF files in the input directory
        pdf_files_in_input = list(lightrag_input_dir.glob("*.pdf"))
        logger.info(f"🔄 Processing {len(pdf_files_in_input)} files with LightRAG pipeline...")
        
        # Use LightRAG's native file processing pipeline
        await pipeline_index_files(service.rag, pdf_files_in_input)
        
        logger.info("✅ All documents processed successfully with DOCLING!")
        
    except Exception as e:
        logger.error(f"❌ LightRAG pipeline processing failed: {e}")
        logger.info("📝 Falling back to manual text insertion...")
        
        # Fallback: extract text manually and insert
        # Install docling if needed
        try:
            import docling
        except ImportError:
            logger.info("📦 Installing docling...")
            import subprocess
            subprocess.check_call(["pip", "install", "docling"])
            import docling
        
        from docling.document_converter import DocumentConverter
        
        converter = DocumentConverter()
        texts_to_insert = []
        
        for i, pdf_path in enumerate(pdf_files, 1):
            logger.info(f"📑 Extracting text from {pdf_path.name} with docling ({i}/{len(pdf_files)})")
            try:
                result = converter.convert(pdf_path)
                markdown_content = result.document.export_to_markdown()
                
                # Add metadata
                document_text = f"""# {pdf_path.stem.replace('_', ' ')}

**Source**: {pdf_path.name}  
**Document Type**: Clinical Data Management Guide  
**Processed with**: Docling  
**Chapter**: {i} of {len(pdf_files)}

{markdown_content}
"""
                texts_to_insert.append(document_text)
                logger.info(f"  ✅ Extracted {len(markdown_content)} characters")
                
            except Exception as e:
                logger.error(f"❌ Error processing {pdf_path.name}: {e}")
                continue
        
        # Insert extracted texts
        if texts_to_insert:
            logger.info(f"💾 Inserting {len(texts_to_insert)} processed documents...")
            await service.insert_documents(texts_to_insert)
            logger.info("✅ All documents inserted successfully!")
    
    # Test the database with sample queries
    logger.info("🔍 Testing database with sample queries...")
    
    test_queries = [
        ("What is clinical data management?", "naive"),
        ("What are the key principles of data privacy in clinical research?", "local"), 
        ("How should electronic data capture systems be implemented?", "global"),
        ("What are the best practices for ensuring data quality?", "hybrid"),
        ("Explain the role of a clinical data manager", "hybrid")
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
    
    # Save results
    logger.info("💾 Saving results...")
    with open("lightrag_docling_results.txt", "w", encoding="utf-8") as f:
        f.write("LightRAG + DOCLING Clinical Data Management Results\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Database built from {len(pdf_files)} PDF documents using DOCLING\n")
        f.write(f"Total queries tested: {len(results)}\n\n")
        
        for i, result in enumerate(results, 1):
            f.write(f"Query {i}: {result['question']}\n")
            f.write(f"Mode: {result['mode']}\n")
            f.write(f"Response Length: {result['length']} characters\n")
            f.write("-" * 40 + "\n")
            f.write(result['response'])
            f.write("\n\n" + "=" * 60 + "\n\n")
    
    await service.close()
    
    logger.info("🎉 LightRAG + DOCLING database build complete!")
    logger.info("📄 Results saved to: lightrag_docling_results.txt")
    logger.info("📁 Database stored in: ./clinical_data_lightrag/")
    
    print("\n" + "=" * 70)
    print("🎯 LIGHTRAG + DOCLING DATABASE BUILD COMPLETE!")
    print("=" * 70)
    print(f"📚 Processed: {len(pdf_files)} PDF documents with DOCLING")
    print(f"❓ Tested: {len(results)} different query modes")
    print(f"📄 Results: Saved to lightrag_docling_results.txt")
    print("=" * 70)
    print("\n🔍 Advanced document processing with:")
    print("  • DOCLING: Superior PDF layout understanding")
    print("  • Table extraction and preservation")
    print("  • Figure and image handling")
    print("  • Structured markdown output")
    print("  • LightRAG knowledge graph construction")


if __name__ == "__main__":
    asyncio.run(build_database_with_lightrag())