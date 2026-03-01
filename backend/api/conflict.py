"""Conflict API."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.models.models import ConflictEvent

router = APIRouter()


@router.get("")
async def get_conflict(
    admin1_code: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(ConflictEvent).order_by(ConflictEvent.reference_period_start)
    if admin1_code:
        query = query.where(ConflictEvent.admin1_code == admin1_code)

    result = await db.execute(query)
    events = result.scalars().all()

    # Summary stats
    total_events = sum(e.events or 0 for e in events)
    total_fatalities = sum(e.fatalities or 0 for e in events)

    # By event type
    type_breakdown = {}
    for e in events:
        t = e.event_type or "unknown"
        if t not in type_breakdown:
            type_breakdown[t] = {"events": 0, "fatalities": 0}
        type_breakdown[t]["events"] += e.events or 0
        type_breakdown[t]["fatalities"] += e.fatalities or 0

    return {
        "total_events": total_events,
        "total_fatalities": total_fatalities,
        "event_types": type_breakdown,
        "records": [
            {
                "admin1": e.admin1_name,
                "admin2": e.admin2_name,
                "event_type": e.event_type,
                "events": e.events,
                "fatalities": e.fatalities,
                "date": e.reference_period_start.isoformat() if e.reference_period_start else None,
            }
            for e in events
        ],
    }
