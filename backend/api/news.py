"""News API."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import delete, func, select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.models.models import NewsArticle

router = APIRouter()


@router.get("")
async def get_news(
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(NewsArticle)
        .order_by(desc(NewsArticle.published_at))
        .limit(limit)
    )
    articles = result.scalars().all()

    return {
        "count": len(articles),
        "articles": [
            {
                "source": a.source,
                "title": a.title,
                "url": a.url,
                "domain": a.source_domain,
                "language": a.language,
                "published_at": (
                    a.published_at.isoformat()
                    if a.published_at else None
                ),
            }
            for a in articles
        ],
    }


@router.delete("/purge-gdelt")
async def purge_gdelt(
    db: AsyncSession = Depends(get_db),
):
    """Purge all GDELT articles so filtered ingester can repopulate."""
    count_q = await db.execute(
        select(func.count()).where(
            NewsArticle.source == "gdelt"
        )
    )
    count = count_q.scalar() or 0
    await db.execute(
        delete(NewsArticle).where(
            NewsArticle.source == "gdelt"
        )
    )
    await db.commit()
    return {"purged": count}
