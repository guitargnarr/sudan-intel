"""Sudan Intel -- Humanitarian Intelligence Platform API."""

import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import dashboard, regions, conflict, displacement, food_security, news, synthesis, sources
from backend.core.config import settings
from backend.core.database import Base, engine

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Sudan Intel platform")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized")

    from backend.core.scheduler import start_scheduler
    sched = await start_scheduler()

    yield

    logger.info("Shutting down Sudan Intel platform")
    sched.shutdown()


app = FastAPI(
    title="Sudan Intel",
    description="AI-assisted humanitarian intelligence for the Sudan crisis",
    version=settings.VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)


@app.get("/health")
async def health_check():
    from backend.core.database import is_sqlite
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "db_engine": "sqlite" if is_sqlite else "postgresql",
    }


@app.get("/")
async def root():
    return {
        "name": "Sudan Intel",
        "description": "AI-assisted humanitarian intelligence for the Sudan crisis",
        "version": settings.VERSION,
        "data_sources": ["HDX HAPI", "GDELT", "UNHCR"],
    }


app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(regions.router, prefix="/api/regions", tags=["regions"])
app.include_router(conflict.router, prefix="/api/conflict", tags=["conflict"])
app.include_router(displacement.router, prefix="/api/displacement", tags=["displacement"])
app.include_router(food_security.router, prefix="/api/food-security", tags=["food-security"])
app.include_router(news.router, prefix="/api/news", tags=["news"])
app.include_router(synthesis.router, prefix="/api/synthesis", tags=["synthesis"])
app.include_router(sources.router, prefix="/api/sources", tags=["sources"])


if __name__ == "__main__":
    port = int(os.environ.get("PORT", settings.PORT))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=True)
