"""Dashboard API -- aggregated overview endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.models.models import (
    ConflictEvent, Displacement, FoodSecurity, OperationalPresence,
    SynthesisBrief, DataSourceStatus,
)

router = APIRouter()


@router.get("")
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    # KPI: Total IDPs (latest year per source)
    idp_result = await db.execute(
        select(func.sum(Displacement.population)).where(
            Displacement.displacement_type == "idp",
        )
    )
    total_idps = idp_result.scalar() or 0

    # KPI: Conflict events (all time from DB)
    conflict_result = await db.execute(
        select(func.sum(ConflictEvent.events))
    )
    total_conflict_events = conflict_result.scalar() or 0

    # KPI: Fatalities
    fatality_result = await db.execute(
        select(func.sum(ConflictEvent.fatalities))
    )
    total_fatalities = fatality_result.scalar() or 0

    # KPI: IPC Phase 4-5 population
    ipc_result = await db.execute(
        select(func.sum(FoodSecurity.population_in_phase)).where(
            FoodSecurity.ipc_phase.in_(["4", "5"]),
        )
    )
    ipc_emergency_pop = ipc_result.scalar() or 0

    # KPI: Active organizations
    org_result = await db.execute(
        select(func.count(func.distinct(OperationalPresence.org_acronym)))
    )
    active_orgs = org_result.scalar() or 0

    # Conflict timeline by admin1
    conflict_timeline = await db.execute(
        select(
            ConflictEvent.admin1_name,
            ConflictEvent.reference_period_start,
            func.sum(ConflictEvent.events).label("events"),
            func.sum(ConflictEvent.fatalities).label("fatalities"),
        ).group_by(
            ConflictEvent.admin1_name,
            ConflictEvent.reference_period_start,
        ).order_by(ConflictEvent.reference_period_start)
    )
    timeline = [
        {
            "region": r.admin1_name,
            "date": r.reference_period_start.isoformat() if r.reference_period_start else None,
            "events": r.events,
            "fatalities": r.fatalities,
        }
        for r in conflict_timeline.all()
    ]

    # Latest synthesis brief
    brief_result = await db.execute(
        select(SynthesisBrief).where(
            SynthesisBrief.scope == "national"
        ).order_by(desc(SynthesisBrief.generated_at)).limit(1)
    )
    brief = brief_result.scalar_one_or_none()
    latest_brief = {
        "content": brief.content if brief else None,
        "generated_at": brief.generated_at.isoformat() if brief else None,
        "model": brief.model_used if brief else None,
    }

    # Data freshness
    sources_result = await db.execute(select(DataSourceStatus))
    freshness = [
        {
            "source": s.source_name,
            "last_success": s.last_success.isoformat() if s.last_success else None,
            "is_healthy": s.is_healthy,
            "records": s.total_records,
        }
        for s in sources_result.scalars().all()
    ]

    return {
        "kpis": {
            "total_idps": total_idps,
            "total_conflict_events": total_conflict_events,
            "total_fatalities": total_fatalities,
            "ipc_emergency_population": ipc_emergency_pop,
            "active_organizations": active_orgs,
        },
        "conflict_timeline": timeline,
        "latest_brief": latest_brief,
        "data_freshness": freshness,
    }
