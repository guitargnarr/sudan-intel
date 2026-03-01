"""GDELT news monitoring ingester -- filtered for Sudan-relevant content."""

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ingestion.base import BaseIngester
from backend.models.models import NewsArticle

logger = logging.getLogger(__name__)

GDELT_DOC_API = "https://api.gdeltproject.org/api/v2/doc/doc"

# Trusted domains for Sudan humanitarian coverage
TRUSTED_DOMAINS = {
    "reliefweb.int",
    "dabangasudan.org",
    "sudantribune.com",
    "unocha.org",
    "unhcr.org",
    "unicef.org",
    "msf.org",
    "icrc.org",
    "aljazeera.com",
    "reuters.com",
    "bbc.com",
    "bbc.co.uk",
    "theguardian.com",
    "apnews.com",
    "middleeasteye.net",
    "theafricareport.com",
    "africanews.com",
    "france24.com",
}

# Reject articles from domains that frequently produce false positives
BLOCKED_DOMAINS = {
    "gulftoday.ae",
    "siasat.com",
    "timesnownews.com",
}

# Title must contain at least one of these to be relevant
RELEVANCE_KEYWORDS = {
    "sudan", "khartoum", "darfur", "kordofan", "omdurman",
    "rsf", "rapid support", "janjaweed", "hemeti", "burhan",
    "idp", "displaced", "refugee", "humanitarian",
    "ceasefire", "peace talks", "famine", "cholera",
    "سودان", "خرطوم", "دارفور",
}


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

    @staticmethod
    def _is_relevant(article):
        """Check if article is actually about Sudan, not just mentioning it."""
        domain = article.get("domain", "").lower()

        # Block known false-positive domains
        if domain in BLOCKED_DOMAINS:
            return False

        # Trusted domains always pass
        if domain in TRUSTED_DOMAINS:
            return True

        # For other domains, title must contain a Sudan-specific keyword
        title = (article.get("title") or "").lower()
        return any(kw in title for kw in RELEVANCE_KEYWORDS)

    async def fetch(self, db: AsyncSession) -> int:
        params = {
            "query": (
                "(Sudan OR Darfur OR Khartoum)"
                " (humanitarian OR conflict OR war"
                " OR displaced OR famine OR ceasefire)"
                " sourcelang:english"
            ),
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
        filtered = 0

        for article in articles:
            url = article.get("url", "")
            if not url:
                continue

            if not self._is_relevant(article):
                filtered += 1
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
        logger.info(
            "GDELT: %d relevant articles (%d filtered)",
            count, filtered,
        )
        return count
