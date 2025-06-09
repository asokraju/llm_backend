#!/usr/bin/env python3
"""
Test basic functionality with a small sample before building the full database.
"""

import asyncio
import logging
import requests
import sys
import os

# Add the parent directory to the path so we can import from src
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from src.rag.lightrag_service import LightRAGService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_basic_functionality():
    """Test basic LightRAG functionality with sample data."""
    
    # Check if services are ready
    logger.info("Checking if services are ready...")
    
    try:
        # Check Ollama
        response = requests.get("http://localhost:12434/api/version", timeout=5)
        logger.info(f"Ollama version: {response.json()}")
        
        # Check API
        response = requests.get("http://localhost:9000/health", timeout=5)
        logger.info(f"API health: {response.json()}")
        
    except Exception as e:
        logger.error(f"Services not ready: {e}")
        logger.info("Please ensure all services are running with: docker-compose up -d")
        return
    
    # Initialize LightRAG service
    logger.info("Initializing LightRAG service...")
    service = LightRAGService(
        working_dir="./test_basic_rag",
        llm_model="qwen2.5:7b-instruct",
        embedding_model="nomic-embed-text"
    )
    
    try:
        await service.initialize()
        logger.info("✅ LightRAG service initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize LightRAG service: {e}")
        return
    
    # Test with sample clinical data management content
    sample_documents = [
        """
        Clinical Data Management (CDM) is a critical process in clinical research that involves the collection, integration, and management of data generated during clinical trials. The primary goal of CDM is to ensure that the clinical trial data is accurate, complete, reliable, and submitted in a timely manner.
        
        Key responsibilities of clinical data management include:
        1. Database design and development
        2. Data entry and validation
        3. Query management and resolution
        4. Database lock and finalization
        
        Good Clinical Data Management Practices (GCDMP) provide guidelines for maintaining data quality throughout the clinical trial process.
        """,
        
        """
        Data Quality in clinical research encompasses several dimensions:
        
        Accuracy: Data values should be correct and free from errors
        Completeness: All required data fields should be populated
        Consistency: Data should be uniform across the entire dataset
        Timeliness: Data should be available when needed for analysis
        
        Quality assurance measures include:
        - Edit checks and validation rules
        - Double data entry for critical fields
        - Regular data review and monitoring
        - Source data verification
        
        These practices ensure regulatory compliance and support reliable clinical trial outcomes.
        """,
        
        """
        Electronic Data Capture (EDC) systems have revolutionized clinical data management by:
        
        1. Improving data quality through real-time validation
        2. Reducing data entry errors
        3. Enabling faster query resolution
        4. Providing audit trails for regulatory compliance
        5. Supporting remote monitoring capabilities
        
        Popular EDC systems include Oracle Clinical, Medidata Rave, and OpenClinica. The selection of an appropriate EDC system depends on study complexity, budget, and regulatory requirements.
        """
    ]
    
    # Insert sample documents
    logger.info("Inserting sample documents...")
    try:
        await service.insert_documents(sample_documents)
        logger.info("✅ Successfully inserted sample documents")
    except Exception as e:
        logger.error(f"❌ Failed to insert documents: {e}")
        await service.close()
        return
    
    # Test different query modes
    test_queries = [
        ("What is clinical data management?", "naive"),
        ("What are the key aspects of data quality?", "local"),
        ("How do EDC systems improve clinical trials?", "global"),
        ("Explain the complete clinical data management process", "hybrid")
    ]
    
    logger.info("Testing different query modes...")
    
    for question, mode in test_queries:
        logger.info(f"\n{'='*60}")
        logger.info(f"Question: {question}")
        logger.info(f"Mode: {mode}")
        logger.info(f"{'='*60}")
        
        try:
            response = await service.query(question, mode=mode)
            logger.info(f"✅ Query successful (length: {len(response)} chars)")
            print(f"Response: {response[:300]}{'...' if len(response) > 300 else ''}")
        except Exception as e:
            logger.error(f"❌ Query failed: {e}")
    
    # Test API endpoints
    logger.info("\nTesting API endpoints...")
    
    try:
        # Test document insertion via API
        api_response = requests.post(
            "http://localhost:9000/documents",
            json={"documents": ["API test: This is a test document about clinical research protocols."]},
            timeout=30
        )
        logger.info(f"✅ API document insertion: {api_response.status_code}")
        
        # Test query via API
        query_response = requests.post(
            "http://localhost:9000/query",
            json={"question": "What did we learn about clinical research?", "mode": "hybrid"},
            timeout=30
        )
        if query_response.status_code == 200:
            logger.info(f"✅ API query successful")
            api_answer = query_response.json().get('answer', '')
            print(f"API Response: {api_answer[:200]}{'...' if len(api_answer) > 200 else ''}")
        else:
            logger.error(f"❌ API query failed: {query_response.status_code}")
        
    except Exception as e:
        logger.error(f"❌ API test failed: {e}")
    
    # Cleanup
    await service.close()
    logger.info("✅ Test completed successfully!")


if __name__ == "__main__":
    print("🧪 Testing Basic LightRAG Functionality")
    print("=" * 50)
    asyncio.run(test_basic_functionality())
    print("\n🎉 Basic functionality test complete!")
    print("If successful, you can now run: python build_database.py")