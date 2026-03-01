"""Regions API -- admin1 level data."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.models.models import (
    ConflictEvent, Displacement, FoodSecurity, OperationalPresence,
)

router = APIRouter()


@router.get("")
async def list_regions(db: AsyncSession = Depends(get_db)):
    # Get unique admin1 regions with aggregated stats
    conflict_by_region = await db.execute(
        select(
            ConflictEvent.admin1_code,
            ConflictEvent.admin1_name,
            func.sum(ConflictEvent.events).label("events"),
            func.sum(ConflictEvent.fatalities).label("fatalities"),
        ).group_by(ConflictEvent.admin1_code, ConflictEvent.admin1_name)
    )

    regions = {}
    for r in conflict_by_region.all():
        if not r.admin1_code:
            continue
        regions[r.admin1_code] = {
            "code": r.admin1_code,
            "name": r.admin1_name,
            "conflict_events": r.events or 0,
            "fatalities": r.fatalities or 0,
            "idps": 0,
            "ipc_worst_phase": 0,
            "orgs_count": 0,
        }

    # Add IDP data (any source)
    idp_by_region = await db.execute(
        select(
            Displacement.admin1_code,
            func.sum(Displacement.population).label("pop"),
        ).where(
            Displacement.displacement_type == "idp",
        ).group_by(Displacement.admin1_code)
    )
    for r in idp_by_region.all():
        if r.admin1_code in regions:
            regions[r.admin1_code]["idps"] = r.pop or 0

    # Add IPC worst phase (only numeric phases 1-5)
    ipc_by_region = await db.execute(
        select(
            FoodSecurity.admin1_code,
            func.max(FoodSecurity.ipc_phase).label("worst"),
        ).where(
            FoodSecurity.ipc_phase.in_(["1", "2", "3", "4", "5"]),
        ).group_by(FoodSecurity.admin1_code)
    )
    for r in ipc_by_region.all():
        if r.admin1_code in regions:
            try:
                regions[r.admin1_code]["ipc_worst_phase"] = int(r.worst)
            except (ValueError, TypeError):
                pass

    # Add org counts
    org_by_region = await db.execute(
        select(
            OperationalPresence.admin1_code,
            func.count(func.distinct(OperationalPresence.org_acronym)).label("count"),
        ).group_by(OperationalPresence.admin1_code)
    )
    for r in org_by_region.all():
        if r.admin1_code in regions:
            regions[r.admin1_code]["orgs_count"] = r.count or 0

    # Compute severity score (0-100)
    for code, region in regions.items():
        conflict_score = min(region["fatalities"] / 500, 1.0) * 40
        ipc_score = (region["ipc_worst_phase"] / 5) * 30
        idp_score = min(region["idps"] / 1_000_000, 1.0) * 30
        region["severity"] = round(conflict_score + ipc_score + idp_score)

    return sorted(regions.values(), key=lambda x: x["severity"], reverse=True)


@router.get("/{admin1_code}")
async def get_region(admin1_code: str, db: AsyncSession = Depends(get_db)):
    # Conflict events for this region
    conflict_result = await db.execute(
        select(ConflictEvent).where(
            ConflictEvent.admin1_code == admin1_code
        ).order_by(ConflictEvent.reference_period_start)
    )
    conflicts = [
        {
            "event_type": c.event_type,
            "events": c.events,
            "fatalities": c.fatalities,
            "admin2": c.admin2_name,
            "date": c.reference_period_start.isoformat() if c.reference_period_start else None,
        }
        for c in conflict_result.scalars().all()
    ]

    # Displacement
    disp_result = await db.execute(
        select(Displacement).where(
            Displacement.admin1_code == admin1_code,
            Displacement.source == "hdx_hapi",
        ).order_by(Displacement.reference_period_start)
    )
    displacements = [
        {
            "type": d.displacement_type,
            "population": d.population,
            "admin2": d.admin2_name,
            "date": d.reference_period_start.isoformat() if d.reference_period_start else None,
        }
        for d in disp_result.scalars().all()
    ]

    # Food security
    fs_result = await db.execute(
        select(FoodSecurity).where(
            FoodSecurity.admin1_code == admin1_code
        ).order_by(FoodSecurity.reference_period_start)
    )
    food_security = [
        {
            "phase": f.ipc_phase,
            "type": f.ipc_type,
            "population": f.population_in_phase,
            "admin2": f.admin2_name,
            "date": f.reference_period_start.isoformat() if f.reference_period_start else None,
        }
        for f in fs_result.scalars().all()
    ]

    # Operational presence
    ops_result = await db.execute(
        select(OperationalPresence).where(
            OperationalPresence.admin1_code == admin1_code
        )
    )
    orgs = [
        {
            "acronym": o.org_acronym,
            "name": o.org_name,
            "type": o.org_type_description,
            "sector": o.sector_name,
            "admin2": o.admin2_name,
        }
        for o in ops_result.scalars().all()
    ]

    # Get admin1 name from conflict or food security data
    name_result = await db.execute(
        select(ConflictEvent.admin1_name).where(
            ConflictEvent.admin1_code == admin1_code,
            ConflictEvent.admin1_name.isnot(None),
        ).limit(1)
    )
    admin1_name = name_result.scalar() or admin1_code

    return {
        "admin1_code": admin1_code,
        "admin1_name": admin1_name,
        "conflict": conflicts,
        "displacement": displacements,
        "food_security": food_security,
        "operational_presence": orgs,
    }
