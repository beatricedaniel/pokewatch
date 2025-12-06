"""
Security and Logging Middleware

Provides request/response logging, security headers, request ID tracking,
and other middleware functionality for the API.
"""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

import logging

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Adds unique request ID to each request for tracing.

    Adds X-Request-ID header to both request and response.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check if request already has ID (from load balancer, etc.)
        request_id = request.headers.get("X-Request-ID")

        if not request_id:
            request_id = str(uuid.uuid4())

        # Store in request state for access in endpoints
        request.state.request_id = request_id

        # Process request
        response = await call_next(request)

        # Add to response headers
        response.headers["X-Request-ID"] = request_id

        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs all HTTP requests and responses with timing information.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        # Get request ID if available
        request_id = getattr(request.state, "request_id", "N/A")

        # Get API key if available (masked)
        api_key = getattr(request.state, "api_key", "anonymous")
        if api_key != "anonymous" and len(api_key) > 8:
            api_key = f"{api_key[:4]}***{api_key[-4:]}"

        # Log request
        logger.info(
            f"Request started | ID: {request_id} | "
            f"Method: {request.method} | Path: {request.url.path} | "
            f"API Key: {api_key} | Client: {request.client.host if request.client else 'unknown'}"
        )

        # Process request
        try:
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Log response
            logger.info(
                f"Request completed | ID: {request_id} | "
                f"Status: {response.status_code} | Duration: {duration:.3f}s"
            )

            # Add timing header
            response.headers["X-Response-Time"] = f"{duration:.3f}s"

            return response

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"Request failed | ID: {request_id} | "
                f"Error: {str(e)} | Duration: {duration:.3f}s",
                exc_info=True,
            )
            raise


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds security headers to all responses.

    Implements OWASP recommended security headers.
    """

    def __init__(self, app: ASGIApp, enable_csp: bool = False):
        super().__init__(app)
        self.enable_csp = enable_csp

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Enable XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions policy (formerly Feature-Policy)
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), payment=()"
        )

        # Content Security Policy (optional, can break some tools)
        if self.enable_csp:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; "
                "font-src 'self'; "
                "connect-src 'self';"
            )

        # HSTS (HTTP Strict Transport Security) - only for HTTPS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response


class RateLimitHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds rate limit headers to responses.

    Works in conjunction with RateLimiter dependency.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Add rate limit headers if available from rate limiter
        rate_limit_headers = getattr(request.state, "rate_limit_headers", {})
        for key, value in rate_limit_headers.items():
            response.headers[key] = value

        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Limits the size of incoming requests to prevent abuse.
    """

    def __init__(self, app: ASGIApp, max_size: int = 10 * 1024 * 1024):  # 10MB default
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check Content-Length header
        content_length = request.headers.get("Content-Length")

        if content_length and int(content_length) > self.max_size:
            logger.warning(
                f"Request rejected - size too large: {content_length} bytes "
                f"(max: {self.max_size} bytes)"
            )
            return Response(
                content="Request entity too large",
                status_code=413,
                headers={"Content-Type": "text/plain"},
            )

        return await call_next(request)


class CORSHeadersMiddleware(BaseHTTPMiddleware):
    """
    Custom CORS middleware (if not using FastAPI's built-in CORS).

    Note: Prefer using fastapi.middleware.cors.CORSMiddleware in production.
    This is provided as an alternative/example.
    """

    def __init__(
        self,
        app: ASGIApp,
        allow_origins: list[str] = None,
        allow_methods: list[str] = None,
        allow_headers: list[str] = None,
        allow_credentials: bool = False,
    ):
        super().__init__(app)
        self.allow_origins = allow_origins or ["*"]
        self.allow_methods = allow_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.allow_headers = allow_headers or ["*"]
        self.allow_credentials = allow_credentials

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Handle preflight requests
        if request.method == "OPTIONS":
            response = Response(status_code=200)
        else:
            response = await call_next(request)

        # Add CORS headers
        origin = request.headers.get("origin")

        if origin in self.allow_origins or "*" in self.allow_origins:
            response.headers["Access-Control-Allow-Origin"] = origin or "*"
            response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allow_methods)
            response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allow_headers)

            if self.allow_credentials:
                response.headers["Access-Control-Allow-Credentials"] = "true"

        return response


# Middleware composition helper
def setup_middleware(app, config: dict = None):
    """
    Setup all middleware in the correct order.

    Order matters! Middleware wraps the application in reverse order of addition.

    Args:
        app: FastAPI application
        config: Configuration dictionary

    Example:
        >>> from fastapi import FastAPI
        >>> app = FastAPI()
        >>> setup_middleware(app, {"max_request_size": 5 * 1024 * 1024})
    """
    config = config or {}

    # 1. Request size limit (first check, before processing)
    max_size = config.get("max_request_size", 10 * 1024 * 1024)
    app.add_middleware(RequestSizeLimitMiddleware, max_size=max_size)

    # 2. Request ID (early, so it's available to all other middleware)
    app.add_middleware(RequestIDMiddleware)

    # 3. Security headers
    enable_csp = config.get("enable_csp", False)
    app.add_middleware(SecurityHeadersMiddleware, enable_csp=enable_csp)

    # 4. Rate limit headers (after rate limiting dependency runs)
    app.add_middleware(RateLimitHeadersMiddleware)

    # 5. Logging (near the end, so it logs the full request/response)
    app.add_middleware(LoggingMiddleware)

    logger.info("Middleware configured successfully")
