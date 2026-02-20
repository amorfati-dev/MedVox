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
import uuid
from collections import defaultdict, deque
from urllib.parse import urlparse
from sqlalchemy import text

from app.core.config import settings
from app.core.security import get_password_hash

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
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

# Parse hostnames from configured allowed hosts for TrustedHost middleware
trusted_hosts = []
for host in settings.allowed_hosts_list:
    parsed = urlparse(host)
    if parsed.hostname:
        trusted_hosts.append(parsed.hostname)
trusted_hosts.extend(["localhost", "127.0.0.1"])

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if settings.is_development else sorted(set(trusted_hosts)),
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

# Lightweight in-memory rate limiting for critical endpoints
_rate_limit_buckets: dict[str, deque] = defaultdict(deque)
_rate_limit_window_seconds = 60


def _is_rate_limited(path: str, client_ip: str) -> bool:
    if path.endswith("/auth/login"):
        limit = settings.RATE_LIMIT_LOGIN_PER_MINUTE
    elif path.endswith("/documentation/process-audio"):
        limit = settings.RATE_LIMIT_AUDIO_PER_MINUTE
    else:
        return False

    key = f"{path}:{client_ip}"
    now = time.time()
    bucket = _rate_limit_buckets[key]

    while bucket and now - bucket[0] > _rate_limit_window_seconds:
        bucket.popleft()

    if len(bucket) >= limit:
        return True

    bucket.append(now)
    return False


@app.middleware("http")
async def rate_limit_requests(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    if _is_rate_limited(request.url.path, client_ip):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        return JSONResponse(
            status_code=429,
            content={
                "detail": "Too many requests",
                "request_id": request_id,
                "timestamp": time.time(),
            },
            headers={"X-Request-ID": request_id},
        )
    return await call_next(request)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with timing"""
    start_time = time.time()
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    
    # Log request
    logger.info(
        "Request started",
        request_id=request_id,
        method=request.method,
        url=str(request.url),
        client_ip=request.client.host if request.client else None,
    )
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    
    # Log response
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(round(process_time, 4))
    logger.info(
        "Request completed",
        request_id=request_id,
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


@app.on_event("startup")
def create_default_admin() -> None:
    """
    Create a default admin user on first startup if no users exist.
    Credentials are read from env vars ADMIN_EMAIL / ADMIN_PASSWORD.
    In production, no defaults are allowed.
    """
    import os
    import secrets
    from app.core.database import SessionLocal
    from app.models.user import User, UserRole

    admin_email = os.environ.get("ADMIN_EMAIL", "admin@medvox.local")
    admin_password = os.environ.get("ADMIN_PASSWORD")

    if settings.is_production and not admin_password:
        logger.error("ADMIN_PASSWORD is required in production - default admin will not be created")
        return

    if not admin_password:
        admin_password = secrets.token_urlsafe(12)
        logger.warning("Generated development admin password", email=admin_email)

    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            admin = User(
                email=admin_email,
                hashed_password=get_password_hash(admin_password),
                first_name="Admin",
                last_name="MedVox",
                role=UserRole.ADMIN,
                is_active=True,
                is_superuser=True,
            )
            db.add(admin)
            db.commit()
            logger.warning(
                "Default admin created – change the password!",
                email=admin_email,
            )
    finally:
        db.close()


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
    
    from app.core.database import SessionLocal

    db_status = "ok"
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"
    finally:
        try:
            db.close()
        except Exception:
            pass

    checks = {
        "database": db_status,
        "stt_provider": "ok" if (settings.STT_PROVIDER != "google" or settings.GOOGLE_CLOUD_API_KEY) else "misconfigured",
        "llm_provider": "ok" if (settings.LLM_PROVIDER != "google" or settings.GOOGLE_GEMINI_API_KEY) else "misconfigured",
        "evident": "ok" if settings.EVIDENT_API_URL else "not_configured"
    }
    
    all_healthy = all(status in {"ok", "not_configured"} for status in checks.values())
    
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
        request_id=getattr(request.state, "request_id", None),
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
        reload_excludes=["venv/*", ".venv/*", "__pycache__/*"] if settings.is_development else None,
        log_level=settings.LOG_LEVEL.lower(),
    ) 