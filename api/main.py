"""
KeyPick FastAPI Application
Main entry point for the API server
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.middleware.error_handler import ErrorHandlerMiddleware
from api.middleware.logging import LoggingMiddleware
from api.routers import crawler, processor, tools, cookies

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle events
    """
    # Startup
    logger.info("Starting KeyPick API server...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")

    yield

    # Shutdown
    logger.info("Shutting down KeyPick API server...")


# Create FastAPI application
app = FastAPI(
    title="KeyPick API",
    description="Multi-agent platform for social media content crawling and insight analysis",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# Add middlewares
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(LoggingMiddleware)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(crawler.router, prefix="/api/crawl", tags=["Crawler"])
app.include_router(processor.router, prefix="/api/process", tags=["Processor"])
app.include_router(tools.router, prefix="/api/tools", tags=["Tools"])
app.include_router(cookies.router)  # Cookie management endpoints


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "KeyPick API",
        "version": "0.1.0",
        "status": "running",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "keypick-api", "version": "0.1.0"}


@app.get("/api")
async def api_info():
    """API information endpoint"""
    return {
        "name": "KeyPick API",
        "version": "0.1.0",
        "endpoints": {
            "crawler": "/api/crawl",
            "processor": "/api/process",
            "tools": "/api/tools",
            "docs": "/docs",
            "health": "/health",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if settings.DEBUG else "warning",
    )
