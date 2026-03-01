"""HDX HAPI ingester -- primary data source for Sudan humanitarian data."""

import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.ingestion.base import BaseIngester
from backend.models.models import (
    ConflictEvent, Displacement, FoodPrice, FoodSecurity,
    HumanitarianNeed, OperationalPresence,
)

logger = logging.getLogger(__name__)

BASE_URL = "https://hapi.humdata.org/api/v1"
LOCATION_CODE = "SDN"
# Only keep data from 2023 onwards
MIN_YEAR = 2023
# Max records per endpoint
MAX_RECORDS = 10000


def parse_dt(s):
    """Parse ISO datetime string to Python datetime."""
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00").replace("+00:00", ""))
    except (ValueError, AttributeError):
        return None


def is_recent(ref_start_str):
    """Check if a reference period is from MIN_YEAR onwards."""
    if not ref_start_str:
        return False
    try:
        return int(ref_start_str[:4]) >= MIN_YEAR
    except (ValueError, IndexError):
        return False


class HDXHAPIIngester(BaseIngester):
    source_name = "hdx_hapi"
    update_interval_hours = 6

    async def fetch(self, db: AsyncSession) -> int:
        total = 0
        headers = {"X-HDX-HAPI-APP-IDENTIFIER": settings.HDX_APP_IDENTIFIER}

        total += await self._fetch_conflict(db, headers)
        total += await self._fetch_idps(db, headers)
        total += await self._fetch_food_security(db, headers)
        total += await self._fetch_food_prices(db, headers)
        total += await self._fetch_humanitarian_needs(db, headers)
        total += await self._fetch_operational_presence(db, headers)

        return total

    async def _paginate(self, url: str, headers: dict, params: dict = None) -> list:
        """Paginate through HDX HAPI results with caps."""
        all_results = []
        offset = 0
        limit = 1000
        base_params = params or {}

        while len(all_results) < MAX_RECORDS:
            p = {**base_params, "offset": offset, "limit": limit, "location_code": LOCATION_CODE}
            resp = await self.client.get(url, headers=headers, params=p)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("data", [])
            if not results:
                break

            # Filter to recent data only
            recent = [r for r in results if is_recent(r.get("reference_period_start"))]
            all_results.extend(recent)

            # If we're past the recent data window, stop
            if recent and not is_recent(results[-1].get("reference_period_start", "")):
                # Data is sorted old-to-new, we haven't reached recent yet
                pass

            offset += limit
            if len(results) < limit:
                break

        logger.info("Fetched %d recent records from %s", len(all_results), url.split("/")[-1])
        return all_results

    async def _fetch_conflict(self, db: AsyncSession, headers: dict) -> int:
        url = f"{BASE_URL}/coordination-context/conflict-event"
        rows = await self._paginate(url, headers)
        count = 0

        for row in rows:
            ref_start = parse_dt(row.get("reference_period_start"))
            if not ref_start:
                continue

            db.add(ConflictEvent(
                source="hdx_hapi",
                admin1_code=row.get("admin1_code"),
                admin1_name=row.get("admin1_name"),
                admin2_code=row.get("admin2_code"),
                admin2_name=row.get("admin2_name"),
                event_type=row.get("event_type"),
                events=row.get("events", 0),
                fatalities=row.get("fatalities", 0),
                reference_period_start=ref_start,
                reference_period_end=parse_dt(row.get("reference_period_end")),
            ))
            count += 1

        try:
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.warning("Conflict batch insert failed: %s", str(e)[:200])

        logger.info("HDX HAPI conflict: %d records", count)
        return count

    async def _fetch_idps(self, db: AsyncSession, headers: dict) -> int:
        url = f"{BASE_URL}/affected-people/idps"
        rows = await self._paginate(url, headers)
        count = 0

        for row in rows:
            ref_start = parse_dt(row.get("reference_period_start"))
            if not ref_start:
                continue

            db.add(Displacement(
                source="hdx_hapi",
                admin1_code=row.get("admin1_code"),
                admin1_name=row.get("admin1_name"),
                admin2_code=row.get("admin2_code"),
                admin2_name=row.get("admin2_name"),
                displacement_type="idp",
                population=row.get("population", 0),
                reference_period_start=ref_start,
                reference_period_end=parse_dt(row.get("reference_period_end")),
            ))
            count += 1

        try:
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.warning("IDPs batch insert failed: %s", str(e)[:200])

        logger.info("HDX HAPI IDPs: %d records", count)
        return count

    async def _fetch_food_security(self, db: AsyncSession, headers: dict) -> int:
        url = f"{BASE_URL}/food/food-security"
        rows = await self._paginate(url, headers)
        count = 0

        for row in rows:
            ref_start = parse_dt(row.get("reference_period_start"))
            if not ref_start:
                continue

            db.add(FoodSecurity(
                admin1_code=row.get("admin1_code"),
                admin1_name=row.get("admin1_name"),
                admin2_code=row.get("admin2_code"),
                admin2_name=row.get("admin2_name"),
                ipc_phase=row.get("ipc_phase"),
                ipc_type=row.get("ipc_type"),
                population_in_phase=row.get("population_in_phase", 0),
                population_fraction_in_phase=row.get("population_fraction_in_phase"),
                reference_period_start=ref_start,
                reference_period_end=parse_dt(row.get("reference_period_end")),
            ))
            count += 1

        try:
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.warning("Food security batch insert failed: %s", str(e)[:200])

        logger.info("HDX HAPI food security: %d records", count)
        return count

    async def _fetch_food_prices(self, db: AsyncSession, headers: dict) -> int:
        url = f"{BASE_URL}/food/food-price"
        rows = await self._paginate(url, headers)
        count = 0

        for row in rows:
            ref_start = parse_dt(row.get("reference_period_start"))
            if not ref_start:
                continue

            db.add(FoodPrice(
                admin1_code=row.get("admin1_code"),
                admin1_name=row.get("admin1_name"),
                admin2_code=row.get("admin2_code"),
                admin2_name=row.get("admin2_name"),
                market_code=row.get("market_code"),
                market_name=row.get("market_name"),
                commodity_code=row.get("commodity_code"),
                commodity_name=row.get("commodity_name"),
                commodity_category=row.get("commodity_category"),
                currency_code=row.get("currency_code"),
                unit=row.get("unit"),
                price=row.get("price"),
                price_type=row.get("price_type"),
                lat=row.get("lat"),
                lon=row.get("lon"),
                reference_period_start=ref_start,
                reference_period_end=parse_dt(row.get("reference_period_end")),
            ))
            count += 1

        try:
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.warning("Food prices batch insert failed: %s", str(e)[:200])

        logger.info("HDX HAPI food prices: %d records", count)
        return count

    async def _fetch_humanitarian_needs(self, db: AsyncSession, headers: dict) -> int:
        url = f"{BASE_URL}/affected-people/humanitarian-needs"
        rows = await self._paginate(url, headers)
        count = 0

        for row in rows:
            ref_start = parse_dt(row.get("reference_period_start"))
            if not ref_start:
                continue

            db.add(HumanitarianNeed(
                admin1_code=row.get("admin1_code"),
                admin1_name=row.get("admin1_name"),
                admin2_code=row.get("admin2_code"),
                admin2_name=row.get("admin2_name"),
                sector_code=row.get("sector_code"),
                sector_name=row.get("sector_name"),
                population_status=row.get("population_status"),
                population=row.get("population", 0),
                reference_period_start=ref_start,
                reference_period_end=parse_dt(row.get("reference_period_end")),
            ))
            count += 1

        try:
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.warning("Humanitarian needs batch insert failed: %s", str(e)[:200])

        logger.info("HDX HAPI humanitarian needs: %d records", count)
        return count

    async def _fetch_operational_presence(self, db: AsyncSession, headers: dict) -> int:
        url = f"{BASE_URL}/coordination-context/operational-presence"
        rows = await self._paginate(url, headers)
        count = 0

        for row in rows:
            ref_start = parse_dt(row.get("reference_period_start"))
            if not ref_start:
                continue

            db.add(OperationalPresence(
                admin1_code=row.get("admin1_code"),
                admin1_name=row.get("admin1_name"),
                admin2_code=row.get("admin2_code"),
                admin2_name=row.get("admin2_name"),
                org_acronym=row.get("org_acronym"),
                org_name=row.get("org_name"),
                org_type_code=row.get("org_type_code"),
                org_type_description=row.get("org_type_description"),
                sector_code=row.get("sector_code"),
                sector_name=row.get("sector_name"),
                reference_period_start=ref_start,
                reference_period_end=parse_dt(row.get("reference_period_end")),
            ))
            count += 1

        try:
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.warning("Operational presence batch insert failed: %s", str(e)[:200])

        logger.info("HDX HAPI operational presence: %d records", count)
        return count
