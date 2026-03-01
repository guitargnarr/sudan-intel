"""Briefing generator for AI-generated intelligence briefs."""

import logging
from datetime import datetime

from sqlalchemy import func, select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.models.models import (
    ConflictEvent, Displacement, FoodSecurity, FoodPrice,
    NewsArticle, SynthesisBrief, DataSourceStatus,
)
from backend.models.models import OperationalPresence
from backend.synthesis.ollama_client import OllamaClient
from backend.synthesis.prompts import (
    NATIONAL_BRIEF_PROMPT, REGION_BRIEF_PROMPT,
)

logger = logging.getLogger(__name__)


class BriefingGenerator:
    def __init__(self):
        self.ollama = OllamaClient()

    async def generate_national_brief(self, db: AsyncSession) -> str:
        now = datetime.utcnow()

        # Check if Ollama is available
        if not await self.ollama.is_available():
            logger.warning("Ollama not available, skipping synthesis")
            return None

        # Aggregate data summaries
        conflict = await self._summarize_conflict(db)
        displacement = await self._summarize_displacement(db)
        food_security = await self._summarize_food_security(db)
        food_prices = await self._summarize_food_prices(db)
        news = await self._summarize_news(db)
        staleness = await self._summarize_staleness(db)

        prompt = NATIONAL_BRIEF_PROMPT.format(
            conflict=conflict,
            displacement=displacement,
            food_security=food_security,
            food_prices=food_prices,
            news=news,
            staleness=staleness,
            date=now.strftime("%Y-%m-%d"),
        )

        content = await self.ollama.generate(prompt)

        if content and not content.startswith("[Ollama"):
            # Cache the brief
            brief = SynthesisBrief(
                scope="national",
                brief_type="situation_overview",
                content=content,
                model_used=settings.OLLAMA_MODEL,
                data_window_start=now,
                data_window_end=now,
                generated_at=now,
            )
            db.add(brief)
            await db.commit()
            logger.info("National brief generated: %d chars", len(content))

        return content

    async def generate_region_brief(
        self, db: AsyncSession,
        admin1_code: str, admin1_name: str,
    ) -> str:
        now = datetime.utcnow()

        if not await self.ollama.is_available():
            return None

        conflict = await self._region_conflict(
            db, admin1_code
        )
        displacement = await self._region_displacement(
            db, admin1_code
        )
        food_sec = await self._region_food_security(
            db, admin1_code
        )
        ops = await self._region_ops(db, admin1_code)

        prompt = REGION_BRIEF_PROMPT.format(
            region_name=admin1_name,
            conflict=conflict,
            displacement=displacement,
            food_security=food_sec,
            ops_presence=ops,
            date=now.strftime("%Y-%m-%d"),
        )

        content = await self.ollama.generate(prompt)

        if content and not content.startswith("[Ollama"):
            brief = SynthesisBrief(
                scope="admin1",
                region_code=admin1_code,
                brief_type="situation_overview",
                content=content,
                model_used=settings.OLLAMA_MODEL,
                data_window_start=now,
                data_window_end=now,
                generated_at=now,
            )
            db.add(brief)
            await db.commit()
            logger.info(
                "Region brief %s: %d chars",
                admin1_code, len(content),
            )

        return content

    async def _region_conflict(
        self, db: AsyncSession, code: str,
    ) -> str:
        result = await db.execute(
            select(
                ConflictEvent.event_type,
                func.sum(ConflictEvent.events).label("ev"),
                func.sum(
                    ConflictEvent.fatalities
                ).label("fat"),
            ).where(
                ConflictEvent.admin1_code == code,
            ).group_by(ConflictEvent.event_type)
            .order_by(
                func.sum(ConflictEvent.fatalities).desc()
            )
        )
        rows = result.all()
        if not rows:
            return "No conflict data."
        total_ev = sum(r.ev or 0 for r in rows)
        total_fat = sum(r.fat or 0 for r in rows)
        lines = [f"Total: {total_ev} events, "
                 f"{total_fat} fatalities"]
        for r in rows[:5]:
            lines.append(
                f"- {r.event_type}: {r.ev} events, "
                f"{r.fat} fatalities"
            )
        return "\n".join(lines)

    async def _region_displacement(
        self, db: AsyncSession, code: str,
    ) -> str:
        result = await db.execute(
            select(
                Displacement.admin2_name,
                func.sum(
                    Displacement.population
                ).label("pop"),
            ).where(
                Displacement.admin1_code == code,
                Displacement.displacement_type == "idp",
                Displacement.admin2_name.isnot(None),
            ).group_by(Displacement.admin2_name)
            .order_by(
                func.sum(Displacement.population).desc()
            )
        )
        rows = result.all()
        if not rows:
            return "No displacement data."
        lines = []
        for r in rows[:10]:
            lines.append(
                f"- {r.admin2_name}: {r.pop:,} IDPs"
            )
        return "\n".join(lines)

    async def _region_food_security(
        self, db: AsyncSession, code: str,
    ) -> str:
        result = await db.execute(
            select(
                FoodSecurity.ipc_phase,
                func.sum(
                    FoodSecurity.population_in_phase
                ).label("pop"),
            ).where(
                FoodSecurity.admin1_code == code,
            ).group_by(FoodSecurity.ipc_phase)
            .order_by(FoodSecurity.ipc_phase)
        )
        rows = result.all()
        if not rows:
            return "No food security data."
        labels = {
            "1": "Minimal", "2": "Stressed",
            "3": "Crisis", "4": "Emergency",
            "5": "Famine",
        }
        lines = []
        for r in rows:
            label = labels.get(
                r.ipc_phase, f"Phase {r.ipc_phase}"
            )
            lines.append(
                f"- Phase {r.ipc_phase} ({label}): "
                f"{(r.pop or 0):,}"
            )
        return "\n".join(lines)

    async def _region_ops(
        self, db: AsyncSession, code: str,
    ) -> str:
        result = await db.execute(
            select(
                OperationalPresence.sector_name,
                func.count(func.distinct(
                    OperationalPresence.org_acronym
                )).label("orgs"),
            ).where(
                OperationalPresence.admin1_code == code,
            ).group_by(OperationalPresence.sector_name)
            .order_by(func.count(func.distinct(
                OperationalPresence.org_acronym
            )).desc())
        )
        rows = result.all()
        if not rows:
            return "No operational data."
        lines = []
        for r in rows[:10]:
            lines.append(
                f"- {r.sector_name}: {r.orgs} orgs"
            )
        return "\n".join(lines)

    async def _summarize_conflict(self, db: AsyncSession) -> str:
        result = await db.execute(
            select(
                ConflictEvent.admin1_name,
                func.sum(ConflictEvent.events).label("events"),
                func.sum(ConflictEvent.fatalities).label("fatalities"),
            ).group_by(ConflictEvent.admin1_name)
            .order_by(func.sum(ConflictEvent.fatalities).desc())
        )
        rows = result.all()
        if not rows:
            return "No conflict data available."

        total_events = sum(r.events or 0 for r in rows)
        total_fatalities = sum(r.fatalities or 0 for r in rows)

        lines = [
            f"Total: {total_events} events, "
            f"{total_fatalities} fatalities"
        ]
        for r in rows[:10]:
            lines.append(
                f"- {r.admin1_name}: {r.events} events, "
                f"{r.fatalities} fatalities"
            )

        return "\n".join(lines)

    async def _summarize_displacement(self, db: AsyncSession) -> str:
        # Use latest reference period only (stock figures)
        latest_period = await db.execute(
            select(
                func.max(Displacement.reference_period_start)
            ).where(
                Displacement.displacement_type == "idp",
                Displacement.source == "hdx_hapi",
            )
        )
        latest = latest_period.scalar()
        q = select(
            Displacement.admin1_name,
            Displacement.displacement_type,
            func.sum(Displacement.population).label("pop"),
        ).where(
            Displacement.admin2_name.isnot(None),
        ).group_by(
            Displacement.admin1_name,
            Displacement.displacement_type,
        ).order_by(func.sum(Displacement.population).desc())
        if latest:
            q = q.where(
                Displacement.reference_period_start == latest
            )
        result = await db.execute(q)
        rows = result.all()
        if not rows:
            return "No displacement data available."

        lines = []
        for r in rows[:15]:
            lines.append(
                f"- {r.admin1_name}: "
                f"{r.pop:,} {r.displacement_type}s"
            )

        return "\n".join(lines)

    async def _summarize_food_security(self, db: AsyncSession) -> str:
        # Use latest reference period only (stock figures)
        latest_period = await db.execute(
            select(func.max(FoodSecurity.reference_period_start))
        )
        latest = latest_period.scalar()
        q = select(
            FoodSecurity.ipc_phase,
            func.sum(FoodSecurity.population_in_phase).label("pop"),
        ).group_by(FoodSecurity.ipc_phase).order_by(
            FoodSecurity.ipc_phase
        )
        if latest:
            q = q.where(
                FoodSecurity.reference_period_start == latest
            )
        result = await db.execute(q)
        rows = result.all()
        if not rows:
            return "No food security data available."

        phase_labels = {
            "1": "Minimal", "2": "Stressed", "3": "Crisis",
            "4": "Emergency", "5": "Famine",
        }
        lines = []
        for r in rows:
            label = phase_labels.get(r.ipc_phase, f"Phase {r.ipc_phase}")
            pop = r.pop or 0
            lines.append(
                f"- IPC Phase {r.ipc_phase} ({label}): "
                f"{pop:,} people"
            )

        return "\n".join(lines)

    async def _summarize_food_prices(self, db: AsyncSession) -> str:
        result = await db.execute(
            select(
                FoodPrice.commodity_name,
                func.avg(FoodPrice.price).label("avg_price"),
                FoodPrice.currency_code,
                FoodPrice.unit,
            ).group_by(
                FoodPrice.commodity_name,
                FoodPrice.currency_code,
                FoodPrice.unit,
            )
            .order_by(FoodPrice.commodity_name)
            .limit(10)
        )
        rows = result.all()
        if not rows:
            return "No food price data available."

        lines = []
        for r in rows:
            lines.append(
                f"- {r.commodity_name}: avg "
                f"{r.avg_price:.1f} {r.currency_code}/{r.unit}"
            )

        return "\n".join(lines)

    async def _summarize_news(self, db: AsyncSession) -> str:
        result = await db.execute(
            select(NewsArticle)
            .order_by(desc(NewsArticle.published_at))
            .limit(10)
        )
        articles = result.scalars().all()
        if not articles:
            return "No recent news available."

        lines = []
        for a in articles:
            date_str = (a.published_at.strftime("%Y-%m-%d")
                        if a.published_at else "unknown")
            lines.append(f"- [{date_str}] {a.title}")

        return "\n".join(lines)

    async def _summarize_staleness(self, db: AsyncSession) -> str:
        result = await db.execute(select(DataSourceStatus))
        sources = result.scalars().all()
        if not sources:
            return "No data source status available."

        lines = []
        for s in sources:
            status = "OK" if s.is_healthy else "STALE/ERROR"
            last = (s.last_success.strftime("%Y-%m-%d %H:%M")
                    if s.last_success else "never")
            lines.append(
                f"- {s.source_name}: {status} "
                f"(last: {last}, {s.total_records} records)"
            )

        return "\n".join(lines)
