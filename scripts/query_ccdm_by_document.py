#!/usr/bin/env python3
"""
Document-Specific CCDM Query Tool

This tool allows you to query specific documents within the CCDM database
or filter results to focus on particular document types.

Features:
- List all documents in the database
- Query specific documents by name
- Filter queries by document type/topic
- Compare responses across documents
"""

import asyncio
import sys
import os
import json
from pathlib import Path
from typing import List, Dict, Optional

# Setup paths
script_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(script_dir, '../..'))
sys.path.append(project_root)

class CCDMDocumentQuerier:
    """Tool for document-specific querying of CCDM database."""
    
    def __init__(self, working_dir: str = "ccdm_rag_database"):
        self.working_dir = working_dir
        self.lightrag = None
        self.documents_info = {}
    
    async def initialize(self):
        """Initialize the querier with CCDM database."""
        try:
            # Ensure proper import path
            current_dir = os.getcwd()
            sys.path.insert(0, current_dir)
            from src.rag.lightrag_service import LightRAGService
            
            self.lightrag = LightRAGService(
                working_dir=self.working_dir,
                llm_model="qwen2.5:7b-instruct",
                embedding_model="nomic-embed-text"
            )
            
            await self.lightrag.initialize()
            await self.load_document_info()
            print("✅ CCDM Database loaded successfully")
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize: {e}")
            return False
    
    async def load_document_info(self):
        """Load information about documents in the database."""
        try:
            doc_status_file = Path(self.working_dir) / 'kv_store_doc_status.json'
            if doc_status_file.exists():
                with open(doc_status_file, 'r') as f:
                    doc_status = json.load(f)
                
                for doc_id, info in doc_status.items():
                    if 'content' in info:
                        # Extract document name from content
                        content = info['content']
                        lines = content.split('\n')  # Fix: was using \\n instead of \n
                        source_line = next((line for line in lines if line.startswith('**Source:**')), None)
                        if source_line:
                            filename = source_line.replace('**Source:** ', '').strip()
                            self.documents_info[filename] = {
                                'doc_id': doc_id,
                                'status': info.get('status', 'unknown'),
                                'chunks_count': info.get('chunks_count', 0),
                                'content_length': info.get('content_length', 0)
                            }
        except Exception as e:
            print(f"⚠️ Could not load document info: {e}")
    
    def list_documents(self):
        """List all documents in the database."""
        print("\n📚 Documents in CCDM Database:")
        print("=" * 60)
        
        if not self.documents_info:
            print("No document information available")
            return
        
        for i, (filename, info) in enumerate(self.documents_info.items(), 1):
            status_emoji = "✅" if info['status'] == 'processed' else "⚠️"
            print(f"{i:2d}. {status_emoji} {filename}")
            print(f"     Chunks: {info['chunks_count']}, Size: {info['content_length']:,} chars")
        
        print("=" * 60)
        print(f"Total: {len(self.documents_info)} documents")
    
    def categorize_documents(self) -> Dict[str, List[str]]:
        """Categorize documents by topic/type."""
        categories = {
            'Data Management Planning': [],
            'Electronic Data Capture (EDC)': [],
            'Data Quality & Validation': [],
            'Safety & Adverse Events': [],
            'Regulatory & Compliance': [],
            'Training & Documentation': [],
            'Technical Implementation': [],
            'Other': []
        }
        
        for filename in self.documents_info.keys():
            name_lower = filename.lower()
            
            if any(term in name_lower for term in ['data_management_plan', 'planning']):
                categories['Data Management Planning'].append(filename)
            elif any(term in name_lower for term in ['electronic_data_capture', 'edc']):
                categories['Electronic Data Capture (EDC)'].append(filename)
            elif any(term in name_lower for term in ['validation', 'quality', 'programming']):
                categories['Data Quality & Validation'].append(filename)
            elif any(term in name_lower for term in ['safety', 'adverse', 'sae']):
                categories['Safety & Adverse Events'].append(filename)
            elif any(term in name_lower for term in ['compliance', 'practices', 'standards']):
                categories['Regulatory & Compliance'].append(filename)
            elif any(term in name_lower for term in ['training', 'documentation', 'archiving']):
                categories['Training & Documentation'].append(filename)
            elif any(term in name_lower for term in ['database', 'technical', 'vendor']):
                categories['Technical Implementation'].append(filename)
            else:
                categories['Other'].append(filename)
        
        return categories
    
    def show_categories(self):
        """Show documents organized by categories."""
        print("\n🗂️ Documents by Category:")
        print("=" * 60)
        
        categories = self.categorize_documents()
        
        for category, docs in categories.items():
            if docs:
                print(f"\n📁 {category} ({len(docs)} documents):")
                for doc in docs:
                    print(f"   • {doc}")
    
    async def query_all_documents(self, question: str, mode: str = "hybrid") -> str:
        """Query across all documents (standard behavior)."""
        try:
            response = await self.lightrag.query(question, mode=mode)
            return response
        except Exception as e:
            return f"Error: {e}"
    
    
    async def query_with_document_focus(self, question: str, document_keywords: List[str], mode: str = "local") -> str:
        """Query with focus on specific documents by including document names in the query."""
        # Construct a focused query that mentions the specific documents
        focused_question = f"Based on documents about {', '.join(document_keywords)}, {question}"
        
        try:
            response = await self.lightrag.query(focused_question, mode=mode)
            return response
        except Exception as e:
            return f"Error: {e}"
    
    async def query_by_category(self, question: str, category: str, mode: str = "local") -> str:
        """Query focusing on a specific category of documents."""
        categories = self.categorize_documents()
        
        if category not in categories or not categories[category]:
            return f"Category '{category}' not found or empty"
        
        # Create a focused query mentioning the category
        category_docs = categories[category]
        doc_terms = [doc.replace('.pdf', '').replace('_', ' ') for doc in category_docs]
        
        focused_question = f"Based on {category.lower()} documents covering {', '.join(doc_terms[:3])}, {question}"
        
        try:
            response = await self.lightrag.query(focused_question, mode=mode)
            return response
        except Exception as e:
            return f"Error: {e}"
    
    async def compare_responses(self, question: str):
        """Compare responses across different query approaches."""
        print(f"\n🔍 Comparing Responses for: '{question}'")
        print("=" * 80)
        
        # General query
        print("\n1️⃣ General Query (All Documents):")
        general_response = await self.query_all_documents(question, mode="hybrid")
        print(f"Response ({len(general_response)} chars): {general_response[:300]}...")
        
        # Category-focused queries
        categories = self.categorize_documents()
        relevant_categories = ['Data Quality & Validation', 'Regulatory & Compliance']
        
        for i, category in enumerate(relevant_categories, 2):
            if categories[category]:
                print(f"\n{i}️⃣ {category} Focus:")
                category_response = await self.query_by_category(question, category, mode="local")
                print(f"Response ({len(category_response)} chars): {category_response[:300]}...")
    
    async def interactive_mode(self):
        """Interactive mode for document-specific querying."""
        print("\n🎯 Interactive Document Query Mode")
        print("Commands:")
        print("  'list' - Show all documents")
        print("  'categories' - Show documents by category") 
        print("  'query <question>' - General query")
        print("  'focus <keywords> <question>' - Focus on specific documents")
        print("  'category <category> <question>' - Query specific category")
        print("  'compare <question>' - Compare different query approaches")
        print("  'quit' - Exit")
        print("=" * 60)
        
        while True:
            try:
                user_input = input("\n🔎 Enter command: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    break
                elif user_input.lower() == 'list':
                    self.list_documents()
                elif user_input.lower() == 'categories':
                    self.show_categories()
                elif user_input.startswith('query '):
                    question = user_input[6:].strip()
                    if question:
                        response = await self.query_all_documents(question)
                        print(f"\n📝 Response: {response}")
                elif user_input.startswith('focus '):
                    parts = user_input[6:].split(' ', 1)
                    if len(parts) == 2:
                        keywords = parts[0].split(',')
                        question = parts[1].strip()
                        response = await self.query_with_document_focus(question, keywords)
                        print(f"\n📝 Focused Response: {response}")
                    else:
                        print("Usage: focus <keyword1,keyword2> <question>")
                elif user_input.startswith('category '):
                    parts = user_input[9:].split(' ', 1)
                    if len(parts) == 2:
                        category = parts[0].replace('_', ' ').title()
                        question = parts[1].strip()
                        response = await self.query_by_category(question, category)
                        print(f"\n📝 Category Response: {response}")
                    else:
                        print("Usage: category <category_name> <question>")
                elif user_input.startswith('compare '):
                    question = user_input[8:].strip()
                    if question:
                        await self.compare_responses(question)
                else:
                    print("Unknown command. Type 'quit' to exit.")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
    
    async def cleanup(self):
        """Clean up resources."""
        if self.lightrag:
            await self.lightrag.close()

async def main():
    """Main execution."""
    print("🔍 CCDM Document-Specific Query Tool")
    print("=" * 50)
    
    querier = CCDMDocumentQuerier()
    
    try:
        if not await querier.initialize():
            return 1
        
        # Show available documents
        querier.list_documents()
        querier.show_categories()
        
        # Example queries
        print("\n💡 Example Queries:")
        
        # Test general query
        print("\n1. General query:")
        response = await querier.query_all_documents("What are the key components of a data management plan?")
        print(f"Response: {response[:200]}...")
        
        # Test category-specific query
        print("\n2. Category-specific query:")
        response = await querier.query_by_category("What are the validation requirements?", "Data Quality & Validation")
        print(f"Response: {response[:200]}...")
        
        # Enter interactive mode
        await querier.interactive_mode()
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    finally:
        await querier.cleanup()

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)