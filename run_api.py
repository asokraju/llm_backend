#!/usr/bin/env python3
"""Run the API server."""

import os

# Disable pipmaster auto-install for faster startup
os.environ['PIPMASTER_DISABLE'] = '1'

if __name__ == "__main__":
    import uvicorn
    from src.config.settings import settings
    
    print("Starting LightRAG API server...")
    print(f"Host: {settings.api_host}:{settings.api_port}")
    print(f"API Key Auth: {'Enabled' if settings.api_key_enabled else 'Disabled'}")
    print(f"LLM Model: {settings.llm_model}")
    print(f"Working Directory: {settings.rag_working_dir}")
    print("\nNote: Ensure Ollama is running at http://localhost:11434")
    print("\nPress Ctrl+C to stop the server\n")
    
    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level=settings.log_level.lower()
    )