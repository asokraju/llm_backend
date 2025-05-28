"""Authentication and authorization for the RAG API."""

import time
from typing import Dict, Optional
from collections import defaultdict, deque

from fastapi import HTTPException, Security, Request
from fastapi.security import APIKeyHeader

from ..config.settings import settings
from .exceptions import AuthenticationError, RateLimitExceededError


api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self):
        self.requests: Dict[str, deque] = defaultdict(deque)
    
    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed for the given key."""
        now = time.time()
        window_start = now - settings.rate_limit_window
        
        # Clean old requests
        request_times = self.requests[key]
        while request_times and request_times[0] < window_start:
            request_times.popleft()
        
        # Check rate limit
        if len(request_times) >= settings.rate_limit_requests:
            return False
        
        # Add current request
        request_times.append(now)
        return True


# Global rate limiter instance
rate_limiter = RateLimiter()


async def verify_api_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    """Verify API key authentication."""
    if not settings.api_key_enabled:
        return "anonymous"
    
    if not api_key:
        raise AuthenticationError("API key is required")
    
    if api_key not in settings.api_keys:
        raise AuthenticationError("Invalid API key")
    
    return api_key


async def check_rate_limit(request: Request, api_key: str = Security(verify_api_key)):
    """Check rate limiting for the API key."""
    # Use API key for rate limiting, or IP address for anonymous users
    rate_limit_key = api_key if api_key != "anonymous" else request.client.host
    
    if not rate_limiter.is_allowed(rate_limit_key):
        raise RateLimitExceededError(
            f"Rate limit exceeded. Max {settings.rate_limit_requests} requests per {settings.rate_limit_window} seconds"
        )
    
    return api_key


def get_client_ip(request: Request) -> str:
    """Get client IP address from request."""
    # Check for forwarded headers first
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    return request.client.host


def get_user_agent(request: Request) -> str:
    """Get user agent from request."""
    return request.headers.get("User-Agent", "Unknown")


def get_request_id(request: Request) -> str:
    """Get or generate request ID."""
    return request.headers.get("X-Request-ID", None)