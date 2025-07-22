"""
MedVox FastAPI Application
Main entry point for the MedVox backend API
"""

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import time

from app.core.config import settings

# Configure structlog for JSON logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI-powered voice documentation tool for dental practices",
    version="0.1.0",
    openapi_url="/api/v1/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware with restricted origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_hosts_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if settings.is_development else ["localhost", "127.0.0.1"],
)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses"""
    response = await call_next(request)
    
    # Security headers
    response.headers["X-Frame-Options"] = settings.X_FRAME_OPTIONS
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    # HSTS header (only in production)
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = f"max-age={settings.HSTS_MAX_AGE}; includeSubDomains"
    
    return response

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with timing"""
    start_time = time.time()
    
    # Log request
    logger.info(
        "Request started",
        method=request.method,
        url=str(request.url),
        client_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.info(
        "Request completed",
        method=request.method,
        url=str(request.url),
        status_code=response.status_code,
        process_time=round(process_time, 4),
    )
    
    return response

# Import API router after middleware setup
from app.api.v1.api import api_router

# Include API router
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint"""
    logger.info("Root endpoint accessed")
    return {
        "message": f"Welcome to {settings.PROJECT_NAME} API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
        "ready": "/ready",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    logger.info("Health check requested")
    return {
        "status": "healthy", 
        "service": "medvox-api",
        "version": "0.1.0",
        "timestamp": time.time()
    }


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint for Docker/K8s"""
    logger.info("Readiness check requested")
    
    # TODO: Add actual health checks for:
    # - Database connectivity
    # - OpenAI API connectivity
    # - Whisper model availability
    # - Evident API connectivity (if configured)
    
    checks = {
        "database": "ok",  # TODO: implement actual check
        "openai": "ok",    # TODO: implement actual check
        "whisper": "ok",   # TODO: implement actual check
        "evident": "ok" if settings.EVIDENT_API_URL else "not_configured"
    }
    
    all_healthy = all(status == "ok" for status in checks.values())
    
    return {
        "status": "ready" if all_healthy else "not_ready",
        "checks": checks,
        "timestamp": time.time()
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with structured logging"""
    logger.error(
        "Unhandled exception",
        method=request.method,
        url=str(request.url),
        exception_type=type(exc).__name__,
        exception_message=str(exc),
        exc_info=True,
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "timestamp": time.time()
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting MedVox API server", 
                debug=settings.is_development,
                allowed_hosts=settings.allowed_hosts_list)
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.is_development,
        log_level=settings.LOG_LEVEL.lower(),
    ) 