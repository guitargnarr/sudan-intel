"""ReliefWeb reports ingester -- verified humanitarian content for Sudan."""

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ingestion.base import BaseIngester
from backend.models.models import NewsArticle

logger = logging.getLogger(__name__)

RELIEFWEB_API = "https://api.reliefweb.int/v1/reports"


class ReliefWebIngester(BaseIngester):
    source_name = "reliefweb"
    update_interval_hours = 1

    @staticmethod
    def _parse_rw_date(s):
        if not s:
            return None
        try:
            clean = s.replace("Z", "+00:00")
            clean = clean.replace("+00:00", "")
            return datetime.fromisoformat(clean)
        except (ValueError, TypeError):
            return None

    async def fetch(self, db: AsyncSession) -> int:
        params = [
            ("appname", "mscott-sudan-intel-k7x99E0S2D8P3UddCKRjE"),
            ("filter[field]", "country"),
            ("filter[value]", "Sudan"),
            ("sort[]", "date:desc"),
            ("limit", "30"),
            ("fields[include][]", "title"),
            ("fields[include][]", "url_alias"),
            ("fields[include][]", "source"),
            ("fields[include][]", "date"),
            ("fields[include][]", "origin"),
        ]

        resp = await self.client.get(
            RELIEFWEB_API, params=params
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("data", [])
        count = 0

        for item in items:
            fields = item.get("fields", {})
            title = fields.get("title", "")
            node_id = item.get("id", "")
            url = (
                fields.get("url_alias")
                or f"https://reliefweb.int/node/{node_id}"
            )
            if not url:
                continue

            existing = await db.execute(
                select(NewsArticle).where(NewsArticle.url == url)
            )
            if existing.scalar_one_or_none():
                continue

            db.add(NewsArticle(
                source="reliefweb",
                title=title[:500],
                url=url[:1000],
                source_domain="reliefweb.int",
                source_country="Sudan",
                language="English",
                published_at=self._parse_rw_date(
                    fields.get("date", {}).get("original")
                ),
            ))
            count += 1

        await db.commit()
        logger.info("ReliefWeb: %d new reports", count)
        return count
