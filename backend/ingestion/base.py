"""Abstract base class for data source ingesters."""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.models import DataSourceStatus

logger = logging.getLogger(__name__)


class BaseIngester(ABC):
    source_name: str = "unknown"
    update_interval_hours: int = 6

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=60.0)

    @abstractmethod
    async def fetch(self, db: AsyncSession) -> int:
        """Fetch data from source, upsert into DB. Returns record count."""
        ...

    async def _should_skip(self, db: AsyncSession) -> bool:
        """Skip fetch if last success was recent enough."""
        result = await db.execute(
            select(DataSourceStatus).where(
                DataSourceStatus.source_name
                == self.source_name
            )
        )
        status = result.scalar_one_or_none()
        if not status or not status.last_success:
            return False
        age = datetime.utcnow() - status.last_success
        # Skip if last success < 80% of interval
        threshold = timedelta(
            hours=self.update_interval_hours * 0.8
        )
        if age < threshold:
            logger.info(
                "%s: skipping, last success %s ago",
                self.source_name, age,
            )
            return True
        return False

    async def safe_fetch(self, db: AsyncSession) -> dict:
        try:
            if await self._should_skip(db):
                return {
                    "source": self.source_name,
                    "status": "skipped",
                    "reason": "recent data",
                }
            count = await self.fetch(db)
            await self._update_status(
                db, success=True, count=count,
            )
            return {
                "source": self.source_name,
                "status": "ok",
                "records": count,
            }
        except httpx.HTTPStatusError as e:
            error_msg = (
                f"HTTP {e.response.status_code}: "
                f"{e.response.text[:200]}"
            )
            logger.warning(
                "%s: %s", self.source_name, error_msg,
            )
            try:
                await db.rollback()
                await self._update_status(
                    db, success=False, error=error_msg,
                )
            except Exception:
                pass
            return {
                "source": self.source_name,
                "status": "error",
                "error": error_msg,
            }
        except Exception as e:
            error_msg = str(e)[:500]
            logger.error(
                "%s: %s", self.source_name, error_msg,
            )
            try:
                await db.rollback()
                await self._update_status(
                    db, success=False, error=error_msg,
                )
            except Exception:
                pass
            return {
                "source": self.source_name,
                "status": "error",
                "error": error_msg,
            }

    async def _update_status(
        self, db: AsyncSession, success: bool,
        count: int = 0, error: str = None,
    ):
        now = datetime.utcnow()
        result = await db.execute(
            select(DataSourceStatus).where(
                DataSourceStatus.source_name
                == self.source_name
            )
        )
        status = result.scalar_one_or_none()

        if not status:
            status = DataSourceStatus(source_name=self.source_name)
            db.add(status)

        if success:
            status.last_success = now
            status.records_last_fetch = count
            # Replace total, don't accumulate (avoids inflation
            # from duplicate ingestion runs)
            if count > 0:
                status.total_records = count
            status.is_healthy = True
            status.last_error = None
        else:
            status.last_failure = now
            status.last_error = error
            status.is_healthy = False

        await db.commit()

    async def close(self):
        await self.client.aclose()
