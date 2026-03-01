"""Displacement API."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.models.models import Displacement

router = APIRouter()


@router.get("")
async def get_displacement(
    admin1_code: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(Displacement).order_by(Displacement.reference_period_start)
    if admin1_code:
        query = query.where(Displacement.admin1_code == admin1_code)

    result = await db.execute(query)
    records = result.scalars().all()

    by_type = {}
    for r in records:
        t = r.displacement_type or "unknown"
        if t not in by_type:
            by_type[t] = 0
        by_type[t] = max(by_type[t], r.population or 0)

    return {
        "summary": by_type,
        "records": [
            {
                "source": r.source,
                "admin1": r.admin1_name,
                "admin2": r.admin2_name,
                "type": r.displacement_type,
                "population": r.population,
                "date": r.reference_period_start.isoformat() if r.reference_period_start else None,
            }
            for r in records
        ],
    }
