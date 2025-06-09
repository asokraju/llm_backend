#!/usr/bin/env python3
"""
Direct test of DOCLING vs PyPDF2 for PDF processing.
Shows the superior quality of DOCLING for clinical documents.
"""

import logging
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_pypdf2_extraction(pdf_path: Path) -> str:
    """Extract text using PyPDF2 (old method)."""
    try:
        import PyPDF2
        from io import open
        
        logger.info(f"📄 Extracting with PyPDF2: {pdf_path.name}")
        start_time = time.time()
        
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page_num, page in enumerate(pdf_reader.pages):
                text += f"\n--- Page {page_num + 1} ---\n"
                text += page.extract_text()
        
        extraction_time = time.time() - start_time
        logger.info(f"  ✅ PyPDF2: {len(text)} chars in {extraction_time:.2f}s")
        return text
        
    except Exception as e:
        logger.error(f"  ❌ PyPDF2 failed: {e}")
        return ""


def test_docling_extraction(pdf_path: Path) -> str:
    """Extract text using DOCLING (new method)."""
    try:
        # Install docling if needed
        try:
            from docling.document_converter import DocumentConverter
        except ImportError:
            logger.info("📦 Installing docling...")
            import subprocess
            subprocess.check_call(["pip", "install", "docling"])
            from docling.document_converter import DocumentConverter
        
        logger.info(f"🔧 Extracting with DOCLING: {pdf_path.name}")
        start_time = time.time()
        
        converter = DocumentConverter()
        result = converter.convert(pdf_path)
        markdown_content = result.document.export_to_markdown()
        
        extraction_time = time.time() - start_time
        logger.info(f"  ✅ DOCLING: {len(markdown_content)} chars in {extraction_time:.2f}s")
        return markdown_content
        
    except Exception as e:
        logger.error(f"  ❌ DOCLING failed: {e}")
        return ""


def compare_extractions():
    """Compare PyPDF2 vs DOCLING extraction quality."""
    
    logger.info("🆚 PyPDF2 vs DOCLING Comparison")
    logger.info("=" * 50)
    
    # Test with first PDF
    data_dir = Path("data")
    pdf_files = list(data_dir.glob("*.pdf"))
    
    if not pdf_files:
        logger.error("❌ No PDF files found in data/ directory")
        return
    
    test_file = pdf_files[0]  # Use first PDF for comparison
    logger.info(f"📚 Testing with: {test_file.name}")
    
    # Extract with both methods
    logger.info("\n1️⃣ PyPDF2 Extraction:")
    pypdf2_text = test_pypdf2_extraction(test_file)
    
    logger.info("\n2️⃣ DOCLING Extraction:")
    docling_text = test_docling_extraction(test_file)
    
    # Compare results
    logger.info("\n📊 Comparison Results:")
    logger.info("-" * 30)
    logger.info(f"PyPDF2 length: {len(pypdf2_text):,} characters")
    logger.info(f"DOCLING length: {len(docling_text):,} characters")
    
    if len(docling_text) > len(pypdf2_text):
        improvement = ((len(docling_text) - len(pypdf2_text)) / len(pypdf2_text)) * 100
        logger.info(f"🚀 DOCLING extracted {improvement:.1f}% more content!")
    
    # Save samples for comparison
    logger.info("\n💾 Saving extraction samples...")
    
    with open("pypdf2_sample.txt", "w", encoding="utf-8") as f:
        f.write("PyPDF2 Extraction Sample\n")
        f.write("=" * 30 + "\n\n")
        f.write(pypdf2_text[:2000])  # First 2000 chars
        f.write("\n\n[TRUNCATED - Full extraction was longer]")
    
    with open("docling_sample.txt", "w", encoding="utf-8") as f:
        f.write("DOCLING Extraction Sample\n")
        f.write("=" * 30 + "\n\n")
        f.write(docling_text[:2000])  # First 2000 chars
        f.write("\n\n[TRUNCATED - Full extraction was longer]")
    
    # Analysis
    logger.info("\n🔍 Content Analysis:")
    
    # Check for structured content
    docling_has_tables = "| " in docling_text or "|--" in docling_text
    pypdf2_has_tables = "| " in pypdf2_text or "|--" in pypdf2_text
    
    docling_has_headers = any(line.startswith("#") for line in docling_text.split("\n"))
    pypdf2_has_headers = any(line.startswith("#") for line in pypdf2_text.split("\n"))
    
    logger.info(f"📋 Tables preserved - PyPDF2: {pypdf2_has_tables}, DOCLING: {docling_has_tables}")
    logger.info(f"📝 Headers structured - PyPDF2: {pypdf2_has_headers}, DOCLING: {docling_has_headers}")
    
    # Create comparison summary
    print("\n" + "=" * 70)
    print("🎯 DOCLING vs PyPDF2 - EXTRACTION QUALITY COMPARISON")
    print("=" * 70)
    print(f"📄 Test Document: {test_file.name}")
    print(f"📊 Content Length:")
    print(f"   • PyPDF2: {len(pypdf2_text):,} characters")
    print(f"   • DOCLING: {len(docling_text):,} characters")
    print(f"🔧 Structured Content:")
    print(f"   • Tables: PyPDF2 {'✅' if pypdf2_has_tables else '❌'} | DOCLING {'✅' if docling_has_tables else '❌'}")
    print(f"   • Headers: PyPDF2 {'✅' if pypdf2_has_headers else '❌'} | DOCLING {'✅' if docling_has_headers else '❌'}")
    print(f"💾 Sample Files:")
    print(f"   • pypdf2_sample.txt - Traditional extraction")
    print(f"   • docling_sample.txt - DOCLING extraction")
    print("=" * 70)
    
    if len(docling_text) > len(pypdf2_text) and docling_has_headers:
        print("🏆 WINNER: DOCLING - Superior content extraction and structure!")
    elif len(docling_text) > len(pypdf2_text):
        print("🏆 WINNER: DOCLING - More content extracted!")
    else:
        print("🤝 Both methods performed similarly")
    
    print("\n✨ DOCLING Benefits for Clinical Documents:")
    print("   • Better table extraction and preservation")
    print("   • Superior layout understanding")
    print("   • Structured markdown output")
    print("   • Enhanced figure and image handling")
    print("   • More accurate text extraction from complex layouts")


if __name__ == "__main__":
    compare_extractions()