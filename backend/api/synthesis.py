"""Synthesis API -- AI-generated briefings."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.models.models import SynthesisBrief

router = APIRouter()


@router.get("")
async def get_synthesis(
    scope: str = Query("national"),
    region: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(SynthesisBrief).where(SynthesisBrief.scope == scope)
    if region:
        query = query.where(SynthesisBrief.region_code == region)

    result = await db.execute(
        query.order_by(desc(SynthesisBrief.generated_at)).limit(1)
    )
    brief = result.scalar_one_or_none()

    if not brief:
        return {"content": None, "message": "No synthesis available yet. Ingestion may still be running."}

    return {
        "content": brief.content,
        "scope": brief.scope,
        "region_code": brief.region_code,
        "brief_type": brief.brief_type,
        "model_used": brief.model_used,
        "generated_at": brief.generated_at.isoformat() if brief.generated_at else None,
        "data_window": {
            "start": brief.data_window_start.isoformat() if brief.data_window_start else None,
            "end": brief.data_window_end.isoformat() if brief.data_window_end else None,
        },
    }


@router.post("/generate")
async def trigger_synthesis(db: AsyncSession = Depends(get_db)):
    """Manually trigger a synthesis generation."""
    from backend.synthesis.briefing import BriefingGenerator

    generator = BriefingGenerator()
    content = await generator.generate_national_brief(db)

    return {
        "status": "generated",
        "length": len(content) if content else 0,
    }
