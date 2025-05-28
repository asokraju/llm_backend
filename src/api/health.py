"""Health check utilities for the RAG API."""

import time
import asyncio
import aiohttp
from typing import Dict, List

from ..config.settings import settings
from .exceptions import ServiceUnavailableError
from .models import ServiceStatus
from .logging import get_logger

logger = get_logger(__name__)

# Track application start time
APP_START_TIME = time.time()


async def check_service_health(url: str, service_name: str, timeout: float = None) -> ServiceStatus:
    """Check health of an external service."""
    if timeout is None:
        timeout = settings.health_check_timeout
    
    start_time = time.time()
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            async with session.get(url) as response:
                response_time = (time.time() - start_time) * 1000
                
                if response.status == 200:
                    return ServiceStatus(
                        name=service_name,
                        status="up",
                        response_time=response_time
                    )
                else:
                    return ServiceStatus(
                        name=service_name,
                        status="degraded",
                        response_time=response_time,
                        error=f"HTTP {response.status}"
                    )
    
    except asyncio.TimeoutError:
        return ServiceStatus(
            name=service_name,
            status="down",
            error="Timeout"
        )
    except Exception as e:
        return ServiceStatus(
            name=service_name,
            status="down",
            error=str(e)
        )


async def check_ollama_health() -> ServiceStatus:
    """Check Ollama service health."""
    url = f"{settings.llm_host.rstrip('/')}/api/tags"
    return await check_service_health(url, "ollama")


async def check_qdrant_health() -> ServiceStatus:
    """Check Qdrant service health."""
    url = f"{settings.qdrant_host.rstrip('/')}/health"
    return await check_service_health(url, "qdrant")


async def check_redis_health() -> ServiceStatus:
    """Check Redis service health."""
    try:
        import redis.asyncio as redis
        
        start_time = time.time()
        
        # Parse Redis URL
        redis_client = redis.from_url(settings.redis_host)
        
        # Simple ping
        await redis_client.ping()
        response_time = (time.time() - start_time) * 1000
        
        await redis_client.close()
        
        return ServiceStatus(
            name="redis",
            status="up",
            response_time=response_time
        )
    
    except Exception as e:
        return ServiceStatus(
            name="redis",
            status="down",
            error=str(e)
        )


async def check_prometheus_health() -> ServiceStatus:
    """Check Prometheus service health."""
    url = f"{settings.prometheus_host.rstrip('/')}/api/v1/status/config"
    return await check_service_health(url, "prometheus")


async def get_all_service_statuses() -> List[ServiceStatus]:
    """Get health status of all external services."""
    tasks = [
        check_ollama_health(),
        check_qdrant_health(),
        check_redis_health(),
        check_prometheus_health()
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    statuses = []
    for result in results:
        if isinstance(result, ServiceStatus):
            statuses.append(result)
        else:
            # Handle unexpected exceptions
            logger.error(f"Unexpected error in health check: {result}")
            statuses.append(ServiceStatus(
                name="unknown",
                status="down",
                error=str(result)
            ))
    
    return statuses


def get_uptime() -> float:
    """Get application uptime in seconds."""
    return time.time() - APP_START_TIME


async def is_system_healthy() -> bool:
    """Check if the entire system is healthy."""
    statuses = await get_all_service_statuses()
    
    # System is healthy if critical services are up
    critical_services = {"ollama", "qdrant"}
    
    for status in statuses:
        if status.name in critical_services and status.status == "down":
            return False
    
    return True


async def is_system_ready() -> bool:
    """Check if the system is ready to serve requests."""
    statuses = await get_all_service_statuses()
    
    # System is ready if all services are up or degraded (not down)
    for status in statuses:
        if status.status == "down":
            return False
    
    return True


def get_system_status() -> str:
    """Get overall system status."""
    # This is a simple implementation
    # In production, you might want more sophisticated logic
    return "healthy"