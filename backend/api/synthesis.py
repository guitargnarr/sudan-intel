"""Synthesis API -- AI-generated briefings."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.models.models import SynthesisBrief

router = APIRouter()


class BriefPush(BaseModel):
    content: str
    scope: str = "national"
    region_code: str | None = None
    brief_type: str = "situation_overview"
    model_used: str = "sudan-intel-analyst"


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
        return {
            "content": None,
            "message": "No synthesis available yet.",
        }

    return {
        "content": brief.content,
        "scope": brief.scope,
        "region_code": brief.region_code,
        "brief_type": brief.brief_type,
        "model_used": brief.model_used,
        "generated_at": (
            brief.generated_at.isoformat()
            if brief.generated_at else None
        ),
        "data_window": {
            "start": (
                brief.data_window_start.isoformat()
                if brief.data_window_start else None
            ),
            "end": (
                brief.data_window_end.isoformat()
                if brief.data_window_end else None
            ),
        },
    }


@router.post("/generate")
async def trigger_synthesis(
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger a synthesis generation."""
    from backend.synthesis.briefing import BriefingGenerator

    generator = BriefingGenerator()
    content = await generator.generate_national_brief(db)

    return {
        "status": "generated",
        "length": len(content) if content else 0,
    }


@router.post("/push")
async def push_brief(
    brief: BriefPush,
    db: AsyncSession = Depends(get_db),
):
    """Accept a pre-generated brief from local Ollama."""
    now = datetime.utcnow()
    record = SynthesisBrief(
        scope=brief.scope,
        region_code=brief.region_code,
        brief_type=brief.brief_type,
        content=brief.content,
        model_used=brief.model_used,
        data_window_start=now,
        data_window_end=now,
        generated_at=now,
    )
    db.add(record)
    await db.commit()
    return {
        "status": "stored",
        "length": len(brief.content),
        "scope": brief.scope,
    }
