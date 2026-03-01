"""Data sources status API."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.models.models import DataSourceStatus

router = APIRouter()


@router.get("")
async def get_sources(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DataSourceStatus))
    sources = result.scalars().all()

    return [
        {
            "name": s.source_name,
            "last_success": s.last_success.isoformat() if s.last_success else None,
            "last_failure": s.last_failure.isoformat() if s.last_failure else None,
            "last_error": s.last_error,
            "records_last_fetch": s.records_last_fetch,
            "total_records": s.total_records,
            "is_healthy": s.is_healthy,
        }
        for s in sources
    ]
