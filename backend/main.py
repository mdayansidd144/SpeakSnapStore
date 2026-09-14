from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from routes import voice, vision, parse, inventory

import os
import time
import logging
from typing import Dict, Any
from contextlib import asynccontextmanager


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format=(
        "%(asctime)s - %(name)s - "
        "%(levelname)s - %(message)s"
    ),
)

logger = logging.getLogger(__name__)


# ============================================================
# REQUEST METRICS
# ============================================================

class RequestMetrics:
    """Track basic request metrics for monitoring."""

    def __init__(self):
        self.request_count = 0
        self.error_count = 0
        self.response_times = []
        self.endpoint_stats = {}

    def record_request(
        self,
        endpoint: str,
        duration: float,
        status_code: int,
    ):
        """Record one HTTP request."""

        self.request_count += 1

        if status_code >= 400:
            self.error_count += 1

        self.response_times.append(duration)

        if endpoint not in self.endpoint_stats:
            self.endpoint_stats[endpoint] = {
                "count": 0,
                "total_time": 0.0,
            }

        self.endpoint_stats[endpoint]["count"] += 1
        self.endpoint_stats[endpoint]["total_time"] += duration

        # Keep memory usage bounded.
        if len(self.response_times) > 1000:
            self.response_times.pop(0)

    def get_stats(self) -> Dict[str, Any]:
        """Return current request statistics."""

        average_response_time = (
            sum(self.response_times)
            / len(self.response_times)
            if self.response_times
            else 0.0
        )

        return {
            "total_requests": self.request_count,
            "error_count": self.error_count,
            "error_rate": (
                round(
                    (
                        self.error_count
                        / self.request_count
                        * 100
                    ),
                    2,
                )
                if self.request_count > 0
                else 0.0
            ),
            "avg_response_time_ms": round(
                average_response_time * 1000,
                2,
            ),
            "endpoints": self.endpoint_stats,
        }


metrics = RequestMetrics()


# ============================================================
# REQUEST METRICS MIDDLEWARE
# ============================================================

class MetricsMiddleware:
    """Middleware that records basic HTTP metrics."""

    def __init__(self, app):
        self.app = app

    async def __call__(
        self,
        scope,
        receive,
        send,
    ):
        if scope["type"] != "http":
            return await self.app(
                scope,
                receive,
                send,
            )

        start_time = time.perf_counter()

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                duration = (
                    time.perf_counter()
                    - start_time
                )

                endpoint = scope.get(
                    "path",
                    "unknown",
                )

                status_code = message.get(
                    "status",
                    500,
                )

                metrics.record_request(
                    endpoint,
                    duration,
                    status_code,
                )

            await send(message)

        await self.app(
            scope,
            receive,
            send_wrapper,
        )


# ============================================================
# APPLICATION LIFESPAN
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup and shutdown lifecycle.
    """

    logger.info(
        "Starting Speak Snap Store API"
    )

    logger.info(
        "Environment: %s",
        os.getenv(
            "ENVIRONMENT",
            "development",
        ),
    )

    # --------------------------------------------------------
    # STARTUP
    # --------------------------------------------------------

    try:
        from database import (
            pool,
            cache,
        )

        # Access the objects so their initialization/import
        # is completed before accepting requests.
        if pool is not None:
            logger.info(
                "Database system initialized"
            )

        if cache is not None:
            logger.info(
                "Cache system initialized"
            )

    except Exception as exc:
        logger.exception(
            "Database initialization failed: %s",
            exc,
        )

        # Do not prevent application startup here.
        # /health will report the actual problem.

    yield

    # --------------------------------------------------------
    # SHUTDOWN
    # --------------------------------------------------------

    logger.info(
        "Shutting down Speak Snap Store API"
    )

    try:
        from database import pool

        # Use the public cleanup method provided by the
        # database module rather than accessing private
        # connection-pool internals.
        if pool is not None and hasattr(
            pool,
            "close_all",
        ):
            pool.close_all()

        logger.info(
            "Database connections closed"
        )

    except Exception as exc:
        logger.warning(
            "Database cleanup warning: %s",
            exc,
        )


# ============================================================
# CREATE APPLICATION
# ============================================================

app = FastAPI(
    title="Speak Snap Store API",
    description=(
        "AI-Powered Inventory Management System"
    ),
    version="3.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)


# ============================================================
# MIDDLEWARE
# ============================================================

app.add_middleware(
    MetricsMiddleware
)

app.add_middleware(
    GZipMiddleware,
    minimum_size=1000,
)


# ============================================================
# CORS
# ============================================================

frontend_url = os.getenv(
    "FRONTEND_URL",
    "",
).strip().rstrip("/")

# Explicit local origins plus the configured production frontend.
cors_origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
]

if frontend_url:
    # Avoid accidentally adding the same origin twice.
    if frontend_url not in cors_origins:
        cors_origins.append(
            frontend_url
        )

# Vercel creates different deployment URLs for production,
# previews, and branch deployments. Allow only HTTPS origins
# ending in vercel.app instead of allowing every website.
cors_origin_regex = r"https://([a-zA-Z0-9-]+\.)*vercel\.app$"

logger.info(
    "Configured CORS origins: %s",
    cors_origins,
)
logger.info(
    "Configured CORS origin regex: %s",
    cors_origin_regex,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=cors_origin_regex,
    allow_credentials=True,
    allow_methods=[
        "GET",
        "POST",
        "PUT",
        "DELETE",
        "OPTIONS",
    ],
    allow_headers=["*"],
    expose_headers=[
        "X-Response-Time",
        "X-Request-ID",
    ],
    max_age=3600,
)


# ============================================================
# TRUSTED HOST
# ============================================================

allowed_hosts = [
    "localhost",
    "127.0.0.1",
    "*.onrender.com",
]

custom_allowed_host = os.getenv(
    "ALLOWED_HOST",
    "",
).strip()

if custom_allowed_host:
    if custom_allowed_host not in allowed_hosts:
        allowed_hosts.append(
            custom_allowed_host
        )

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=allowed_hosts,
)


# ============================================================
# API ROUTES
# ============================================================

app.include_router(
    voice.router,
    prefix="/api/voice",
    tags=["Voice"],
)

app.include_router(
    vision.router,
    prefix="/api/vision",
    tags=["Vision"],
)

app.include_router(
    parse.router,
    prefix="/api/parse",
    tags=["Parse"],
)

app.include_router(
    inventory.router,
    prefix="/api/inventory",
    tags=["Inventory"],
)


# ============================================================
# ROOT ENDPOINT
# ============================================================

@app.get("/")
async def root():
    """Basic API information."""

    return {
        "message": "Speak Snap Store API",
        "status": "active",
        "version": "3.0.0",
        "environment": os.getenv(
            "ENVIRONMENT",
            "development",
        ),
        "docs_url": "/api/docs",
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
async def health_check():
    """
    Health check endpoint used by Render and
    other monitoring systems.
    """

    try:
        from database import (
            get_db_health
        )

        db_health = get_db_health()

        # ----------------------------------------------------
        # Validate database health.
        # ----------------------------------------------------
        if isinstance(
            db_health,
            dict,
        ):
            db_status = db_health.get(
                "status",
                "unknown",
            )

            if db_status not in {
                "ok",
                "healthy",
                "connected",
            }:
                return JSONResponse(
                    status_code=503,
                    content={
                        "status": "unhealthy",
                        "database": db_health,
                        "timestamp": time.time(),
                    },
                )

        return {
            "status": "healthy",
            "timestamp": time.time(),
            "database": db_health,
            "metrics": metrics.get_stats(),
        }

    except Exception as exc:
        logger.exception(
            "Health check failed: %s",
            exc,
        )

        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": time.time(),
                "database": {
                    "status": "error",
                },
                "error": str(exc),
            },
        )


# ============================================================
# METRICS
# ============================================================

@app.get("/metrics")
async def get_metrics():
    """
    Return basic API request metrics.
    """

    return metrics.get_stats()


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.exception_handler(404)
async def not_found_handler(
    request: Request,
    exc,
):
    """Handle unknown routes."""

    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "path": request.url.path,
            "message": (
                "The requested endpoint "
                "does not exist"
            ),
        },
    )


@app.exception_handler(500)
async def internal_error_handler(
    request: Request,
    exc,
):
    """Handle unexpected server errors."""

    logger.exception(
        "Internal server error: %s",
        exc,
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": (
                "An unexpected error occurred. "
                "Please try again later."
            ),
        },
    )


# ============================================================
# LOCAL SERVER
# ============================================================

if __name__ == "__main__":
    import uvicorn

    # Render provides PORT automatically.
    port = int(
        os.getenv(
            "PORT",
            "8000",
        )
    )

    host = os.getenv(
        "HOST",
        "0.0.0.0",
    )

    debug = (
        os.getenv(
            "DEBUG",
            "False",
        ).lower()
        == "true"
    )

    workers = int(
        os.getenv(
            "WORKERS",
            "1",
        )
    )

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug,
        workers=workers,
        log_level=os.getenv(
            "LOG_LEVEL",
            "info",
        ).lower(),
        access_log=True,
        timeout_keep_alive=65,
        loop="asyncio",
    )