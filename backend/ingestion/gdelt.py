"""GDELT news monitoring ingester."""

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ingestion.base import BaseIngester
from backend.models.models import NewsArticle

logger = logging.getLogger(__name__)

GDELT_DOC_API = "https://api.gdeltproject.org/api/v2/doc/doc"


class GDELTIngester(BaseIngester):
    source_name = "gdelt"
    update_interval_hours = 1

    @staticmethod
    def _parse_gdelt_date(s):
        if not s:
            return None
        try:
            return datetime.strptime(s, "%Y%m%dT%H%M%SZ")
        except (ValueError, TypeError):
            return None

    async def fetch(self, db: AsyncSession) -> int:
        params = {
            "query": "(Sudan OR Khartoum OR Darfur) (crisis OR conflict OR humanitarian OR war)",
            "mode": "artlist",
            "maxrecords": "75",
            "format": "json",
            "sort": "datedesc",
        }

        resp = await self.client.get(GDELT_DOC_API, params=params)
        resp.raise_for_status()
        text = resp.text.strip()
        if not text or text.startswith("<"):
            logger.warning("GDELT returned non-JSON response")
            return 0
        data = resp.json()
        articles = data.get("articles", [])
        count = 0

        for article in articles:
            url = article.get("url", "")
            if not url:
                continue

            existing = await db.execute(
                select(NewsArticle).where(NewsArticle.url == url)
            )
            if existing.scalar_one_or_none():
                continue

            db.add(NewsArticle(
                source="gdelt",
                title=article.get("title", "")[:500],
                url=url[:1000],
                source_domain=article.get("domain", ""),
                source_country=article.get("sourcecountry", ""),
                language=article.get("language", ""),
                published_at=self._parse_gdelt_date(article.get("seendate")),
            ))
            count += 1

        await db.commit()
        logger.info("GDELT: %d new articles", count)
        return count
