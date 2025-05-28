"""Request and response models for the RAG API."""

from typing import List, Optional, Dict, Any, Literal
from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator, ConfigDict

from ..config.settings import settings


def utc_now() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


class BaseModelWithConfig(BaseModel):
    """Base model with datetime JSON serialization."""
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


class HealthCheck(BaseModelWithConfig):
    """Health check response model."""
    status: Literal["healthy", "unhealthy", "degraded"] = Field(..., description="Service health status")
    timestamp: datetime = Field(default_factory=utc_now, description="Check timestamp")
    version: str = Field(..., description="API version")
    uptime: float = Field(..., description="Uptime in seconds")


class ServiceStatus(BaseModelWithConfig):
    """Individual service status."""
    name: str = Field(..., description="Service name")
    status: Literal["up", "down", "degraded"] = Field(..., description="Service status")
    response_time: Optional[float] = Field(None, description="Response time in milliseconds")
    error: Optional[str] = Field(None, description="Error message if down")


class ReadinessCheck(BaseModelWithConfig):
    """Readiness check response model."""
    status: Literal["ready", "not ready"] = Field(..., description="Readiness status")
    timestamp: datetime = Field(default_factory=utc_now, description="Check timestamp")
    checks: List[ServiceStatus] = Field(..., description="Individual service checks")


class DocumentRequest(BaseModelWithConfig):
    """Request model for document insertion."""
    documents: List[str] = Field(
        ..., 
        min_items=1, 
        max_items=100,
        description="List of document texts to insert"
    )
    
    @field_validator('documents')
    @classmethod
    def validate_documents(cls, v):
        """Validate documents size."""
        # Check individual document size
        for doc in v:
            if len(doc.encode('utf-8')) > settings.max_document_size:
                raise ValueError(f'Document too large. Max size: {settings.max_document_size} bytes')
        
        # Check total request size
        total_size = sum(len(doc.encode('utf-8')) for doc in v)
        if total_size > settings.max_request_size:
            raise ValueError(f'Total request too large. Max size: {settings.max_request_size} bytes')
        return v


class DocumentResponse(BaseModelWithConfig):
    """Response model for document insertion."""
    success: bool = Field(..., description="Whether insertion was successful")
    message: str = Field(..., description="Status message")
    documents_processed: int = Field(..., description="Number of documents processed")
    processing_time: float = Field(..., description="Processing time in seconds")
    timestamp: datetime = Field(default_factory=utc_now, description="Response timestamp")


class QueryRequest(BaseModelWithConfig):
    """Request model for querying the knowledge base."""
    question: str = Field(
        ..., 
        min_length=1, 
        max_length=1000,
        description="Question to ask the knowledge base"
    )
    mode: Literal["naive", "local", "global", "hybrid"] = Field(
        default="hybrid",
        description="Query mode: naive (simple), local (entity-focused), global (community-focused), or hybrid (combined)"
    )
    stream: bool = Field(
        default=False,
        description="Whether to stream the response"
    )
    top_k: Optional[int] = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of top results to consider"
    )
    include_sources: bool = Field(
        default=True,
        description="Whether to include source information in response"
    )


class QueryResponse(BaseModelWithConfig):
    """Response model for knowledge base queries."""
    success: bool = Field(..., description="Whether query was successful")
    answer: str = Field(..., description="Generated answer")
    mode: str = Field(..., description="Query mode used")
    sources: Optional[List[Dict[str, Any]]] = Field(None, description="Source documents/entities")
    processing_time: float = Field(..., description="Processing time in seconds")
    timestamp: datetime = Field(default_factory=utc_now, description="Response timestamp")


class GraphNode(BaseModelWithConfig):
    """Knowledge graph node model."""
    id: str = Field(..., description="Node ID")
    type: str = Field(..., description="Node type")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Node properties")


class GraphEdge(BaseModelWithConfig):
    """Knowledge graph edge model."""
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    type: str = Field(..., description="Edge type/relationship")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Edge properties")


class GraphResponse(BaseModelWithConfig):
    """Response model for knowledge graph data."""
    nodes: List[GraphNode] = Field(..., description="Graph nodes")
    edges: List[GraphEdge] = Field(..., description="Graph edges")
    stats: Dict[str, int] = Field(..., description="Graph statistics")
    timestamp: datetime = Field(default_factory=utc_now, description="Response timestamp")


class ErrorResponse(BaseModelWithConfig):
    """Error response model."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=utc_now, description="Error timestamp")
    correlation_id: Optional[str] = Field(None, description="Request correlation ID")


class ApiInfo(BaseModelWithConfig):
    """API information model."""
    title: str = Field(..., description="API title")
    version: str = Field(..., description="API version")
    description: str = Field(..., description="API description")
    features: List[str] = Field(..., description="Available features")
    limits: Dict[str, Any] = Field(..., description="API limits")
    timestamp: datetime = Field(default_factory=utc_now, description="Response timestamp")


class MetricsResponse(BaseModelWithConfig):
    """Metrics response model."""
    metrics: Dict[str, Any] = Field(..., description="Current metrics")
    timestamp: datetime = Field(default_factory=utc_now, description="Metrics timestamp")