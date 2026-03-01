"""Dashboard API -- aggregated overview endpoint.

IMPORTANT: Every KPI must show the LATEST snapshot, not a sum across
all time periods.  Displacement and IPC data are stock figures (point-
in-time counts), not flows.  Summing them across periods is wrong.
"""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.models.models import (
    ConflictEvent, Displacement, FoodSecurity, FoodPrice,
    OperationalPresence, SynthesisBrief, DataSourceStatus,
)

router = APIRouter()


@router.get("")
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    # KPI: Total IDPs -- sum across admin regions for LATEST period only.
    # IDP figures are stock numbers; summing across time periods is wrong.
    # But within a single period, each admin2 row is a distinct population.
    #
    # Prefer HDX HAPI (sub-national) over UNHCR (national-only).
    latest_idp_period = await db.execute(
        select(func.max(Displacement.reference_period_start)).where(
            Displacement.displacement_type == "idp",
            Displacement.source == "hdx_hapi",
        )
    )
    idp_period = latest_idp_period.scalar()

    if idp_period:
        # Use admin2-level records only to avoid triple-counting
        # (national, state, and admin2 rows all contain the same total)
        idp_result = await db.execute(
            select(func.sum(Displacement.population)).where(
                Displacement.displacement_type == "idp",
                Displacement.source == "hdx_hapi",
                Displacement.reference_period_start == idp_period,
                Displacement.admin2_name.isnot(None),
            )
        )
        total_idps = idp_result.scalar() or 0

        # If no admin2 data, fall back to national aggregate
        if total_idps == 0:
            idp_result = await db.execute(
                select(func.sum(Displacement.population)).where(
                    Displacement.displacement_type == "idp",
                    Displacement.source == "hdx_hapi",
                    Displacement.reference_period_start == idp_period,
                )
            )
            total_idps = idp_result.scalar() or 0

        idp_source = "IOM DTM"
    else:
        # Fall back to latest UNHCR national figure
        idp_result = await db.execute(
            select(Displacement.population).where(
                Displacement.displacement_type == "idp",
            ).order_by(
                Displacement.reference_period_start.desc()
            ).limit(1)
        )
        total_idps = idp_result.scalar() or 0
        idp_period = None
        idp_source = "UNHCR"

    # KPI: Conflict events -- rolling 12 months, not all time
    # Step 1: find the latest data point
    latest_conflict = await db.execute(
        select(func.max(ConflictEvent.reference_period_start))
    )
    latest_conflict_date = latest_conflict.scalar()

    if latest_conflict_date:
        # Step 2: compute 12-month window from latest
        from datetime import timedelta
        window_start = latest_conflict_date - timedelta(days=365)
        conflict_result = await db.execute(
            select(
                func.sum(ConflictEvent.events),
                func.sum(ConflictEvent.fatalities),
            ).where(
                ConflictEvent.reference_period_start >= window_start
            )
        )
        crow = conflict_result.one()
        total_conflict_events = crow[0] or 0
        total_fatalities = crow[1] or 0
        conflict_window_start = window_start.isoformat()
        conflict_window_end = latest_conflict_date.isoformat()
    else:
        total_conflict_events = 0
        total_fatalities = 0
        conflict_window_start = None
        conflict_window_end = None

    # KPI: IPC Phase 4-5 population -- latest reference period ONLY
    # IPC figures are stock: population in each phase at a point in time.
    # Summing across periods double-counts the same people.
    latest_ipc_period = await db.execute(
        select(func.max(FoodSecurity.reference_period_start)).where(
            FoodSecurity.ipc_phase.in_(["4", "5"]),
        )
    )
    latest_ipc_start = latest_ipc_period.scalar()

    if latest_ipc_start:
        ipc_result = await db.execute(
            select(func.sum(FoodSecurity.population_in_phase)).where(
                FoodSecurity.ipc_phase.in_(["4", "5"]),
                FoodSecurity.reference_period_start == latest_ipc_start,
            )
        )
        ipc_emergency_pop = ipc_result.scalar() or 0
    else:
        ipc_emergency_pop = 0

    # IDP change: compare latest period to previous period
    idp_change = None
    idp_change_pct = None
    if idp_period:
        prev_period_q = await db.execute(
            select(
                func.max(Displacement.reference_period_start)
            ).where(
                Displacement.displacement_type == "idp",
                Displacement.source == "hdx_hapi",
                Displacement.reference_period_start < idp_period,
            )
        )
        prev_period = prev_period_q.scalar()
        if prev_period:
            prev_idp_q = await db.execute(
                select(
                    func.sum(Displacement.population)
                ).where(
                    Displacement.displacement_type == "idp",
                    Displacement.source == "hdx_hapi",
                    Displacement.reference_period_start == prev_period,
                    Displacement.admin2_name.isnot(None),
                )
            )
            prev_idps = prev_idp_q.scalar() or 0
            if prev_idps > 0:
                idp_change = total_idps - prev_idps
                idp_change_pct = round(
                    (idp_change / prev_idps) * 100, 1
                )

    # Food prices: top commodities by latest period
    latest_price_q = await db.execute(
        select(func.max(FoodPrice.reference_period_start))
    )
    latest_price_date = latest_price_q.scalar()

    food_prices = []
    if latest_price_date:
        price_q = await db.execute(
            select(
                FoodPrice.commodity_name,
                func.avg(FoodPrice.price).label("avg_price"),
                FoodPrice.currency_code,
                FoodPrice.unit,
            ).where(
                FoodPrice.reference_period_start == latest_price_date,
            ).group_by(
                FoodPrice.commodity_name,
                FoodPrice.currency_code,
                FoodPrice.unit,
            ).order_by(FoodPrice.commodity_name).limit(10)
        )
        for r in price_q.all():
            food_prices.append({
                "commodity": r.commodity_name,
                "price": round(r.avg_price, 1),
                "currency": r.currency_code,
                "unit": r.unit,
            })

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
            "date": (
                r.reference_period_start.isoformat()
                if r.reference_period_start else None
            ),
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
            "last_success": (
                s.last_success.isoformat()
                if s.last_success else None
            ),
            "last_failure": (
                s.last_failure.isoformat()
                if s.last_failure else None
            ),
            "last_error": s.last_error,
            "is_healthy": s.is_healthy,
            "records": s.total_records,
            "records_last_fetch": s.records_last_fetch,
        }
        for s in sources_result.scalars().all()
    ]

    return {
        "server_time": datetime.utcnow().isoformat(),
        "kpis": {
            "total_idps": total_idps,
            "total_conflict_events": total_conflict_events,
            "total_fatalities": total_fatalities,
            "ipc_emergency_population": ipc_emergency_pop,
            "active_organizations": active_orgs,
            "idp_source": idp_source,
            "idp_change": idp_change,
            "idp_change_pct": idp_change_pct,
            "idp_period": idp_period.isoformat()
            if idp_period else None,
            "conflict_window": {
                "start": conflict_window_start,
                "end": conflict_window_end,
                "label": "12 months",
            },
            "ipc_period": latest_ipc_start.isoformat()
            if latest_ipc_start else None,
        },
        "conflict_timeline": timeline,
        "latest_brief": latest_brief,
        "data_freshness": freshness,
        "food_prices": food_prices,
        "refugees_abroad": await _get_refugees_abroad(db),
    }


async def _get_refugees_abroad(db: AsyncSession):
    """Get latest refugee counts by country of asylum."""
    latest_q = await db.execute(
        select(
            func.max(Displacement.reference_period_start)
        ).where(
            Displacement.source == "unhcr",
            Displacement.displacement_type == "refugee",
            Displacement.admin1_code.notin_(
                ["SUD", "-", ""]
            ),
        )
    )
    latest = latest_q.scalar()
    if not latest:
        return []

    result = await db.execute(
        select(
            Displacement.admin1_code,
            Displacement.admin1_name,
            Displacement.population,
        ).where(
            Displacement.source == "unhcr",
            Displacement.displacement_type == "refugee",
            Displacement.reference_period_start == latest,
            Displacement.admin1_code.notin_(
                ["SUD", "-", ""]
            ),
        ).order_by(Displacement.population.desc()).limit(10)
    )
    return [
        {
            "country_code": r.admin1_code,
            "country": r.admin1_name,
            "refugees": r.population,
        }
        for r in result.all()
    ]
