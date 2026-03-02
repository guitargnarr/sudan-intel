"""APScheduler for data ingestion and synthesis cron jobs."""

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from backend.core.config import settings

logger = logging.getLogger(__name__)


class IngestScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler(
            job_defaults={"misfire_grace_time": 300, "max_instances": 3},
        )

    async def start(self):
        try:
            now = datetime.now(timezone.utc)

            self.scheduler.add_job(
                self._run_hdx_hapi,
                "interval",
                hours=settings.HDX_INTERVAL_HOURS,
                id="hdx_hapi",
                name="HDX HAPI Ingestion",
                replace_existing=True,
                next_run_time=now,
            )

            self.scheduler.add_job(
                self._run_gdelt,
                "interval",
                minutes=settings.GDELT_INTERVAL_MINUTES,
                id="gdelt",
                name="GDELT News Ingestion",
                replace_existing=True,
                next_run_time=now,
            )

            self.scheduler.add_job(
                self._run_unhcr,
                "interval",
                hours=settings.UNHCR_INTERVAL_HOURS,
                id="unhcr",
                name="UNHCR Displacement Ingestion",
                replace_existing=True,
                next_run_time=now,
            )

            self.scheduler.add_job(
                self._run_reliefweb,
                "interval",
                hours=1,
                id="reliefweb",
                name="ReliefWeb Reports Ingestion",
                replace_existing=True,
                next_run_time=now,
            )

            self.scheduler.add_job(
                self._run_synthesis,
                "interval",
                hours=settings.SYNTHESIS_INTERVAL_HOURS,
                id="synthesis",
                name="AI Synthesis Generation",
                replace_existing=True,
                misfire_grace_time=300,
            )

            self.scheduler.start()
            job_count = len(self.scheduler.get_jobs())
            logger.info(
                "Scheduler started with %d jobs", job_count
            )

        except Exception as e:
            logger.error("Failed to start scheduler: %s", e)

    def shutdown(self):
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")

    def get_status(self):
        if not self.scheduler.running:
            return {"running": False, "jobs": []}
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": (
                    job.next_run_time.isoformat()
                    if job.next_run_time else None
                ),
            })
        return {"running": True, "jobs": jobs}

    async def _run_hdx_hapi(self):
        logger.info("Running HDX HAPI ingestion...")
        try:
            from backend.core.database import AsyncSessionLocal
            from backend.ingestion.hdx_hapi import HDXHAPIIngester

            async with AsyncSessionLocal() as db:
                ingester = HDXHAPIIngester()
                result = await ingester.safe_fetch(db)
                logger.info("HDX HAPI: %s", result)
        except Exception as e:
            logger.error("HDX HAPI ingestion failed: %s", e)

    async def _run_gdelt(self):
        logger.info("Running GDELT ingestion...")
        try:
            from backend.core.database import AsyncSessionLocal
            from backend.ingestion.gdelt import GDELTIngester

            async with AsyncSessionLocal() as db:
                ingester = GDELTIngester()
                result = await ingester.safe_fetch(db)
                logger.info("GDELT: %s", result)
        except Exception as e:
            logger.error("GDELT ingestion failed: %s", e)

    async def _run_unhcr(self):
        logger.info("Running UNHCR ingestion...")
        try:
            from backend.core.database import AsyncSessionLocal
            from backend.ingestion.unhcr import UNHCRIngester

            async with AsyncSessionLocal() as db:
                ingester = UNHCRIngester()
                result = await ingester.safe_fetch(db)
                logger.info("UNHCR: %s", result)
        except Exception as e:
            logger.error("UNHCR ingestion failed: %s", e)

    async def _run_reliefweb(self):
        logger.info("Running ReliefWeb ingestion...")
        try:
            from backend.core.database import AsyncSessionLocal
            from backend.ingestion.reliefweb import ReliefWebIngester

            async with AsyncSessionLocal() as db:
                ingester = ReliefWebIngester()
                result = await ingester.safe_fetch(db)
                logger.info("ReliefWeb: %s", result)
        except Exception as e:
            logger.error("ReliefWeb ingestion failed: %s", e)

    async def _run_synthesis(self):
        logger.info("Running AI synthesis...")
        try:
            from backend.core.database import AsyncSessionLocal
            from backend.synthesis.briefing import BriefingGenerator

            async with AsyncSessionLocal() as db:
                generator = BriefingGenerator()
                result = await generator.generate_national_brief(db)
                chars = len(result) if result else 0
                logger.info("Synthesis complete: %d chars", chars)
        except Exception as e:
            logger.error("Synthesis failed: %s", e)


scheduler = IngestScheduler()


async def start_scheduler():
    await scheduler.start()
    return scheduler
