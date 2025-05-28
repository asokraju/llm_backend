#!/usr/bin/env python3
"""Production-ready LightRAG API server with comprehensive monitoring and security."""

import time
import uuid
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Response, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

from ..config.settings import settings
from ..rag.lightrag_service import LightRAGService
from .auth import check_rate_limit, get_client_ip, get_user_agent, get_request_id
from .exceptions import (
    RAGException, ServiceUnavailableError, InvalidRequestError,
    AuthenticationError, RateLimitExceededError
)
from .health import (
    get_all_service_statuses, get_uptime, is_system_healthy, is_system_ready
)
from .logging import (
    setup_logging, get_logger, correlation_context,
    log_request, log_response, log_document_processing, log_query_processing
)
from .models import (
    DocumentRequest, DocumentResponse, QueryRequest, QueryResponse,
    HealthCheck, ReadinessCheck, GraphResponse, ErrorResponse, ApiInfo
)

# Setup logging first
setup_logging()
logger = get_logger(__name__)

# Prometheus metrics
request_count = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status', 'api_key'])
request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration', ['method', 'endpoint'])
active_requests = Gauge('http_requests_active', 'Active HTTP requests')
document_count = Counter('documents_processed_total', 'Total documents processed')
query_count = Counter('queries_processed_total', 'Total queries processed', ['mode'])
rag_initialized = Gauge('rag_service_initialized', 'RAG service initialization status')
error_count = Counter('http_errors_total', 'Total HTTP errors', ['error_type', 'endpoint'])
auth_failures = Counter('auth_failures_total', 'Authentication failures', ['reason'])
rate_limit_hits = Counter('rate_limit_hits_total', 'Rate limit violations', ['api_key'])

# Global service instance
rag_service: Optional[LightRAGService] = None
app_start_time = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    # Startup
    global rag_service, app_start_time
    app_start_time = time.time()
    
    logger.info("Starting LightRAG API server...", 
                version=settings.api_version,
                environment="production" if settings.is_production() else "development")
    
    try:
        rag_service = LightRAGService(
            working_dir=settings.rag_working_dir,
            llm_host=settings.llm_host,
            llm_model=settings.llm_model,
            embedding_model=settings.embedding_model,
            embedding_dim=settings.embedding_dim
        )
        await rag_service.initialize()
        rag_initialized.set(1)
        logger.info("LightRAG service initialized successfully")
    except Exception as e:
        rag_initialized.set(0)
        logger.error("Failed to initialize LightRAG service", error=str(e))
        raise
    
    yield
    
    # Shutdown
    if rag_service:
        logger.info("Shutting down LightRAG service...")
        await rag_service.close()
        rag_initialized.set(0)
        logger.info("LightRAG service stopped")


# Create FastAPI app with enhanced configuration
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=settings.api_description,
    docs_url="/api/docs" if not settings.is_production() else None,
    redoc_url="/api/redoc" if not settings.is_production() else None,
    openapi_url="/api/openapi.json" if not settings.is_production() else None,
    lifespan=lifespan
)


# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

if settings.is_production():
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]  # Configure this properly in production
    )


@app.middleware("http")
async def add_prometheus_metrics(request: Request, call_next):
    """Enhanced middleware to track metrics and logging."""
    # Generate correlation ID
    correlation_id = get_request_id(request) or str(uuid.uuid4())
    
    # Get client info
    client_ip = get_client_ip(request)
    user_agent = get_user_agent(request)
    
    # Get API key from headers (for metrics)
    api_key = request.headers.get("X-API-Key", "anonymous")
    api_key_label = "authenticated" if api_key != "anonymous" else "anonymous"
    
    active_requests.inc()
    start_time = time.time()
    
    # Log request
    with correlation_context(correlation_id):
        log_request(
            method=request.method,
            url=str(request.url),
            headers=dict(request.headers),
            correlation_id=correlation_id
        )
        
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            # Record success metrics
            request_count.labels(
                method=request.method,
                endpoint=request.url.path,
                status=response.status_code,
                api_key=api_key_label
            ).inc()
            
            request_duration.labels(
                method=request.method,
                endpoint=request.url.path
            ).observe(duration)
            
            # Log response
            log_response(
                status_code=response.status_code,
                response_time=duration,
                correlation_id=correlation_id
            )
            
        except Exception as e:
            duration = time.time() - start_time
            
            # Record error metrics
            error_count.labels(
                error_type=type(e).__name__,
                endpoint=request.url.path
            ).inc()
            
            # Log error response
            log_response(
                status_code=500,
                response_time=duration,
                correlation_id=correlation_id,
                error=str(e)
            )
            
            raise
        
        finally:
            active_requests.dec()
    
    return response


# Exception handlers
@app.exception_handler(AuthenticationError)
async def auth_exception_handler(request: Request, exc: AuthenticationError):
    auth_failures.labels(reason="invalid_key").inc()
    error_response = ErrorResponse(
        error="AuthenticationError",
        message=exc.message,
        details=exc.details
    )
    return JSONResponse(
        status_code=401,
        content=error_response.model_dump(mode='json')
    )


@app.exception_handler(RateLimitExceededError)
async def rate_limit_exception_handler(request: Request, exc: RateLimitExceededError):
    api_key = request.headers.get("X-API-Key", "anonymous")
    rate_limit_hits.labels(api_key="authenticated" if api_key != "anonymous" else "anonymous").inc()
    error_response = ErrorResponse(
        error="RateLimitExceededError",
        message=exc.message,
        details=exc.details
    )
    return JSONResponse(
        status_code=429,
        content=error_response.model_dump(mode='json')
    )


@app.exception_handler(InvalidRequestError)
async def invalid_request_exception_handler(request: Request, exc: InvalidRequestError):
    error_response = ErrorResponse(
        error="InvalidRequestError",
        message=exc.message,
        details=exc.details
    )
    return JSONResponse(
        status_code=400,
        content=error_response.model_dump(mode='json')
    )


@app.exception_handler(ServiceUnavailableError)
async def service_unavailable_exception_handler(request: Request, exc: ServiceUnavailableError):
    error_response = ErrorResponse(
        error="ServiceUnavailableError",
        message=exc.message,
        details=exc.details
    )
    return JSONResponse(
        status_code=503,
        content=error_response.model_dump(mode='json')
    )


@app.exception_handler(RAGException)
async def rag_exception_handler(request: Request, exc: RAGException):
    error_response = ErrorResponse(
        error=type(exc).__name__,
        message=exc.message,
        details=exc.details
    )
    return JSONResponse(
        status_code=500,
        content=error_response.model_dump(mode='json')
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    error_response = ErrorResponse(
        error="HTTPException",
        message=exc.detail,
        details={"status_code": exc.status_code}
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(mode='json')
    )


@app.get("/", response_model=ApiInfo)
async def root():
    """API information endpoint."""
    return ApiInfo(
        title=settings.api_title,
        version=settings.api_version,
        description=settings.api_description,
        features=[
            "Document insertion with Docling support",
            "Multi-mode querying (naive, local, global, hybrid)",
            "Knowledge graph visualization",
            "Prometheus metrics",
            "Health checks",
            "Rate limiting",
            "API key authentication"
        ],
        limits={
            "max_documents_per_request": settings.max_documents_per_request,
            "max_document_size_bytes": settings.max_document_size,
            "max_request_size_bytes": settings.max_request_size,
            "rate_limit_per_minute": settings.rate_limit_requests,
            "llm_timeout_seconds": settings.llm_timeout
        }
    )


@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Basic health check endpoint."""
    is_healthy = await is_system_healthy() and rag_service is not None
    
    return HealthCheck(
        status="healthy" if is_healthy else "unhealthy",
        version=settings.api_version,
        uptime=get_uptime()
    )


@app.get("/health/ready", response_model=ReadinessCheck)
async def readiness_check():
    """Detailed readiness check for all services."""
    service_statuses = await get_all_service_statuses()
    is_ready = await is_system_ready() and rag_service is not None
    
    return ReadinessCheck(
        status="ready" if is_ready else "not ready",
        checks=service_statuses
    )


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post(
    "/documents",
    response_model=DocumentResponse,
    summary="Insert Documents",
    description="Insert multiple documents into the knowledge base with optional Docling parsing",
    responses={
        200: {"description": "Documents successfully inserted"},
        400: {"description": "Invalid request - check document size limits"},
        401: {"description": "Authentication required"},
        429: {"description": "Rate limit exceeded"},
        503: {"description": "Service unavailable"}
    }
)
async def insert_documents(
    request: DocumentRequest,
    api_key: str = Depends(check_rate_limit)
):
    """Insert documents into the knowledge base."""
    if not rag_service:
        raise ServiceUnavailableError("RAG service not initialized")
    
    start_time = time.time()
    
    try:
        await rag_service.insert_documents(request.documents)
        processing_time = time.time() - start_time
        
        # Update metrics
        document_count.inc(len(request.documents))
        
        # Log processing
        log_document_processing(
            doc_count=len(request.documents),
            processing_time=processing_time,
            success=True
        )
        
        return DocumentResponse(
            success=True,
            message=f"Successfully processed {len(request.documents)} documents",
            documents_processed=len(request.documents),
            processing_time=processing_time
        )
        
    except Exception as e:
        processing_time = time.time() - start_time
        
        # Log error
        log_document_processing(
            doc_count=len(request.documents),
            processing_time=processing_time,
            success=False,
            error=str(e)
        )
        
        logger.error("Error inserting documents", error=str(e), doc_count=len(request.documents))
        raise RAGException(f"Failed to insert documents: {str(e)}")


@app.post(
    "/query",
    response_model=QueryResponse,
    summary="Query Knowledge Base",
    description="Query the knowledge base using different modes: naive, local, global, or hybrid",
    responses={
        200: {"description": "Query processed successfully"},
        400: {"description": "Invalid query parameters"},
        401: {"description": "Authentication required"},
        429: {"description": "Rate limit exceeded"},
        503: {"description": "Service unavailable"}
    }
)
async def query(
    request: QueryRequest,
    api_key: str = Depends(check_rate_limit)
):
    """Query the knowledge base using various modes."""
    if not rag_service:
        raise ServiceUnavailableError("RAG service not initialized")
    
    start_time = time.time()
    
    try:
        answer = await rag_service.query(
            question=request.question,
            mode=request.mode,
            stream=request.stream
        )
        
        processing_time = time.time() - start_time
        
        # Update metrics
        query_count.labels(mode=request.mode).inc()
        
        # Log processing
        log_query_processing(
            question=request.question,
            mode=request.mode,
            processing_time=processing_time,
            success=True
        )
        
        return QueryResponse(
            success=True,
            answer=answer,
            mode=request.mode,
            processing_time=processing_time
        )
        
    except Exception as e:
        processing_time = time.time() - start_time
        
        # Log error
        log_query_processing(
            question=request.question,
            mode=request.mode,
            processing_time=processing_time,
            success=False,
            error=str(e)
        )
        
        logger.error("Error processing query", error=str(e), question_length=len(request.question), mode=request.mode)
        raise RAGException(f"Failed to process query: {str(e)}")


@app.get(
    "/graph",
    response_model=GraphResponse,
    summary="Get Knowledge Graph",
    description="Retrieve the current knowledge graph structure"
)
async def get_graph(api_key: str = Depends(check_rate_limit)):
    """Get the knowledge graph data."""
    if not rag_service:
        raise ServiceUnavailableError("RAG service not initialized")
    
    try:
        graph_data = await rag_service.get_graph_data()
        return GraphResponse(**graph_data)
    except Exception as e:
        logger.error("Error retrieving graph data", error=str(e))
        raise RAGException(f"Failed to retrieve graph data: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level=settings.log_level.lower()
    )