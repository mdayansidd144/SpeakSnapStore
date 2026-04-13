from fastapi import FastAPI, Request, status
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

logger = logging.getLogger(__name__)

# ==================== REQUEST METRICS ====================
class RequestMetrics:
    """Track request metrics for monitoring"""
    def __init__(self):
        self.request_count = 0
        self.error_count = 0
        self.response_times = []
        self.endpoint_stats = {}
    
    def record_request(self, endpoint: str, duration: float, status_code: int):
        self.request_count += 1
        if status_code >= 400:
            self.error_count += 1
        self.response_times.append(duration)
        if endpoint not in self.endpoint_stats:
            self.endpoint_stats[endpoint] = {'count': 0, 'total_time': 0}
        self.endpoint_stats[endpoint]['count'] += 1
        self.endpoint_stats[endpoint]['total_time'] += duration
        
        if len(self.response_times) > 1000:
            self.response_times.pop(0)
    
    def get_stats(self) -> Dict[str, Any]:
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        return {
            'total_requests': self.request_count,
            'error_count': self.error_count,
            'error_rate': round((self.error_count / self.request_count * 100), 2) if self.request_count > 0 else 0,
            'avg_response_time_ms': round(avg_response_time * 1000, 2),
            'endpoints': self.endpoint_stats
        }

metrics = RequestMetrics()

# ==================== MIDDLEWARE CLASSES ====================
class MetricsMiddleware:
    """Middleware to track request metrics"""
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        
        start_time = time.time()
        
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                duration = time.time() - start_time
                endpoint = scope.get("path", "unknown")
                status_code = message.get("status", 500)
                metrics.record_request(endpoint, duration, status_code)
            await send(message)
        
        await self.app(scope, receive, send_wrapper)

# ==================== LIFESPAN MANAGEMENT ====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    logger.info("🚀 Starting Speak Snap Store API...")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    
    try:
        from database import pool, cache
        logger.info("✅ Database connection pool ready")
        logger.info(f"✅ Cache system active")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
    
    yield
    
    logger.info("🛑 Shutting down Speak Snap Store API...")
    
    try:
        from database import pool
        if hasattr(pool, '_pool'):
            with pool._lock:
                for conn in pool._pool:
                    conn.close()
                pool._pool.clear()
        logger.info("✅ Database connections closed")
    except Exception as e:
        logger.error(f"❌ Cleanup error: {e}")

# ==================== CREATE APP ====================
app = FastAPI(
    title="Speak Snap Store API",
    description="AI-Powered Inventory Management System",
    version="3.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# ==================== MIDDLEWARES ====================
# 1. Metrics tracking (add first)
app.add_middleware(MetricsMiddleware)

# 2. GZip compression for responses
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 3. CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "https://*.vercel.app",
        "https://*.onrender.com",
        os.getenv("FRONTEND_URL", "")
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Response-Time", "X-Request-ID"],
    max_age=3600,
)

# 4. Trusted hosts (security)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=[
        "localhost",
        "127.0.0.1",
        "*.onrender.com",
        "*.vercel.app",
        os.getenv("ALLOWED_HOST", "")
    ]
)

# ==================== REGISTER ROUTERS ====================
app.include_router(voice.router, prefix="/api/voice", tags=["Voice"])
app.include_router(vision.router, prefix="/api/vision", tags=["Vision"])
app.include_router(parse.router, prefix="/api/parse", tags=["Parse"])
app.include_router(inventory.router, prefix="/api/inventory", tags=["Inventory"])

# ==================== HEALTH & METRICS ENDPOINTS ====================
@app.get("/")
async def root():
    return {
        "message": "Speak Snap Store API",
        "status": "active",
        "version": "3.0.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "docs_url": "/api/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    try:
        from database import get_db_health
        db_health = get_db_health() if 'get_db_health' in dir() else {"status": "ok"}
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "database": db_health,
            "metrics": metrics.get_stats()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )

@app.get("/metrics")
async def get_metrics():
    """Get request metrics for monitoring"""
    return metrics.get_stats()

# ==================== ERROR HANDLERS ====================
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "path": request.url.path,
            "message": "The requested endpoint does not exist"
        }
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred. Please try again later."
        }
    )

# ==================== RUN SERVER ====================
if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    debug = os.getenv("DEBUG", "False").lower() == "true"
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug,
        workers=int(os.getenv("WORKERS", 1)),
        log_level="info",
        access_log=True,
        timeout_keep_alive=65,
        loop="asyncio"
    )