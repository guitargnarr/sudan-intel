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
        # IDPs IN Sudan (country of asylum = Sudan)
        count += await self._fetch_idps(db)
        # Refugees FROM Sudan by country of asylum
        count += await self._fetch_refugees_abroad(db)
        return count

    async def _fetch_idps(self, db: AsyncSession) -> int:
        params = {
            "limit": 100, "yearFrom": 2010,
            "coa": "SUD",
        }
        url = f"{UNHCR_API}/population/"
        resp = await self.client.get(url, params=params)
        resp.raise_for_status()
        items = resp.json().get("items", [])
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
                    Displacement.admin1_code == "SUD",
                    Displacement.displacement_type == "idp",
                    Displacement.reference_period_start
                    == ref_start,
                )
            )
            if existing.scalar_one_or_none():
                continue

            pop = self._parse_pop(item.get("idps", 0))
            if pop == 0:
                continue

            db.add(Displacement(
                source="unhcr",
                admin1_code="SUD",
                admin1_name="Sudan",
                displacement_type="idp",
                population=pop,
                reference_period_start=ref_start,
                reference_period_end=ref_end,
            ))
            count += 1

        await db.commit()
        logger.info("UNHCR IDPs: %d records", count)
        return count

    async def _fetch_refugees_abroad(
        self, db: AsyncSession,
    ) -> int:
        """Fetch refugees FROM Sudan by country of asylum.

        UNHCR API requires per-country queries to get
        breakdown by destination.
        """
        # Top asylum countries for Sudanese refugees
        # UNHCR uses its own country codes, NOT ISO-3166
        asylum_countries = {
            "CHD": "Chad",
            "ARE": "Egypt",
            "SSD": "South Sudan",
            "ETH": "Ethiopia",
            "CAR": "Central African Republic",
            "ISR": "Israel",
            "KEN": "Kenya",
            "UGA": "Uganda",
            "LBY": "Libya",
            "SAU": "Saudi Arabia",
        }
        count = 0
        url = f"{UNHCR_API}/population/"

        for coa_code, coa_name in asylum_countries.items():
            params = {
                "limit": 20, "yearFrom": 2020,
                "coo": "SUD", "coa": coa_code,
            }
            try:
                resp = await self.client.get(
                    url, params=params
                )
                resp.raise_for_status()
            except Exception as e:
                logger.warning(
                    "UNHCR %s fetch failed: %s",
                    coa_code, e,
                )
                continue

            items = resp.json().get("items", [])
            for item in items:
                year = item.get("year")
                if not year:
                    continue

                ref_start = datetime(year, 1, 1)
                ref_end = datetime(year, 12, 31)

                existing = await db.execute(
                    select(Displacement).where(
                        Displacement.source == "unhcr",
                        Displacement.admin1_code
                        == coa_code,
                        Displacement.displacement_type
                        == "refugee",
                        Displacement.reference_period_start
                        == ref_start,
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                pop = self._parse_pop(
                    item.get("refugees", 0)
                )
                if pop == 0:
                    continue

                db.add(Displacement(
                    source="unhcr",
                    admin1_code=coa_code,
                    admin1_name=coa_name,
                    displacement_type="refugee",
                    population=pop,
                    reference_period_start=ref_start,
                    reference_period_end=ref_end,
                ))
                count += 1

        await db.commit()
        logger.info("UNHCR refugees: %d records", count)
        return count

    @staticmethod
    def _parse_pop(val):
        if isinstance(val, str):
            return int(val) if val.isdigit() else 0
        return val or 0
