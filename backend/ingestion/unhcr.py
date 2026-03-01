"""UNHCR displacement data ingester."""

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ingestion.base import BaseIngester
from backend.models.models import Displacement

logger = logging.getLogger(__name__)

UNHCR_API = "https://api.unhcr.org/population/v1"


class UNHCRIngester(BaseIngester):
    source_name = "unhcr"
    update_interval_hours = 24

    async def fetch(self, db: AsyncSession) -> int:
        count = 0
        # UNHCR uses 'SUD' for Sudan (not SDN)
        # Refugees FROM Sudan (country of origin)
        count += await self._fetch_population(db, coo="SUD", disp_type="refugee")
        # IDPs IN Sudan (country of asylum = Sudan)
        count += await self._fetch_population(db, coa="SUD", disp_type="idp")
        return count

    async def _fetch_population(
        self, db: AsyncSession, disp_type: str,
        coo: str = None, coa: str = None,
    ) -> int:
        params = {"limit": 100, "yearFrom": 2010}
        if coo:
            params["coo"] = coo
        if coa:
            params["coa"] = coa

        url = f"{UNHCR_API}/population/"
        resp = await self.client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        count = 0

        for item in items:
            year = item.get("year")
            if not year:
                continue

            ref_start = datetime(year, 1, 1)
            ref_end = datetime(year, 12, 31)

            existing = await db.execute(
                select(Displacement).where(
                    Displacement.source == "unhcr",
                    Displacement.admin1_code == (coa or coo),
                    Displacement.displacement_type == disp_type,
                    Displacement.reference_period_start == ref_start,
                )
            )
            if existing.scalar_one_or_none():
                continue

            # Parse population -- UNHCR returns some fields as strings
            if disp_type == "refugee":
                pop = item.get("refugees", 0)
            else:
                pop = item.get("idps", 0)

            if isinstance(pop, str):
                pop = int(pop) if pop.isdigit() else 0

            if pop == 0:
                continue

            db.add(Displacement(
                source="unhcr",
                admin1_code=coa or coo,
                admin1_name=item.get("coo_name", "Sudan"),
                displacement_type=disp_type,
                population=pop,
                reference_period_start=ref_start,
                reference_period_end=ref_end,
            ))
            count += 1

        await db.commit()
        logger.info("UNHCR %s: %d records", disp_type, count)
        return count
