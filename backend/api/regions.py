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
    # Build region list from ALL data sources, not just conflict.
    # Many states have displacement/food security data but no
    # recorded conflict events.
    regions = {}

    # Seed from all sources that have admin1 codes.
    # Exclude country-level codes (SUD, SDN) -- only state-level (SD01-SD18).
    for Model in (ConflictEvent, Displacement, FoodSecurity):
        result = await db.execute(
            select(Model.admin1_code, Model.admin1_name).where(
                Model.admin1_code.isnot(None),
                Model.admin1_code.like("SD%"),
            ).distinct()
        )
        for r in result.all():
            if r.admin1_code and r.admin1_code not in regions:
                regions[r.admin1_code] = {
                    "code": r.admin1_code,
                    "name": r.admin1_name,
                    "conflict_events": 0,
                    "fatalities": 0,
                    "idps": 0,
                    "ipc_worst_phase": 0,
                    "orgs_count": 0,
                }

    # Add conflict stats
    conflict_by_region = await db.execute(
        select(
            ConflictEvent.admin1_code,
            func.sum(ConflictEvent.events).label("events"),
            func.sum(ConflictEvent.fatalities).label("fatalities"),
        ).group_by(ConflictEvent.admin1_code)
    )
    for r in conflict_by_region.all():
        if r.admin1_code in regions:
            regions[r.admin1_code]["conflict_events"] = r.events or 0
            regions[r.admin1_code]["fatalities"] = r.fatalities or 0

    # Add IDP data -- latest reference period only (stock, not flow)
    # First find the latest IDP period
    latest_idp_period = await db.execute(
        select(func.max(Displacement.reference_period_start)).where(
            Displacement.displacement_type == "idp",
            # Exclude country-level 'SUD' rows from UNHCR
            Displacement.admin1_code.notin_(["SUD", "SDN"]),
        )
    )
    latest_idp_date = latest_idp_period.scalar()

    if latest_idp_date:
        # Sum admin2-level records per admin1 -- exclude aggregate rows
        # (rows with admin2_name=NULL are state-level aggregates)
        idp_by_region = await db.execute(
            select(
                Displacement.admin1_code,
                func.sum(Displacement.population).label("pop"),
            ).where(
                Displacement.displacement_type == "idp",
                Displacement.reference_period_start == latest_idp_date,
                Displacement.admin1_code.isnot(None),
                Displacement.admin2_name.isnot(None),
            ).group_by(Displacement.admin1_code)
        )
        for r in idp_by_region.all():
            if r.admin1_code in regions:
                regions[r.admin1_code]["idps"] = r.pop or 0

    # Add IPC worst phase -- latest period only (stock, not flow)
    latest_ipc_period = await db.execute(
        select(func.max(FoodSecurity.reference_period_start)).where(
            FoodSecurity.ipc_phase.in_(["1", "2", "3", "4", "5"]),
        )
    )
    latest_ipc_date = latest_ipc_period.scalar()

    ipc_by_region = await db.execute(
        select(
            FoodSecurity.admin1_code,
            func.max(FoodSecurity.ipc_phase).label("worst"),
        ).where(
            FoodSecurity.ipc_phase.in_(["1", "2", "3", "4", "5"]),
            FoodSecurity.reference_period_start == latest_ipc_date
            if latest_ipc_date else True,
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

    # Compute severity index (0-100).
    # Normalized against the max value in each dimension across all
    # regions, so scores reflect relative severity.  Weights:
    #   Fatalities 40% | IPC worst phase 30% | IDPs 30%
    # This is an INDEX for map coloring, not a validated metric.
    max_fat = max((r["fatalities"] for r in regions.values()), default=1) or 1
    max_idps = max((r["idps"] for r in regions.values()), default=1) or 1

    for code, region in regions.items():
        conflict_score = (region["fatalities"] / max_fat) * 40
        ipc_score = (region["ipc_worst_phase"] / 5) * 30
        idp_score = (region["idps"] / max_idps) * 30
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

    # Displacement -- all sources, but exclude aggregate rows
    disp_result = await db.execute(
        select(Displacement).where(
            Displacement.admin1_code == admin1_code,
            Displacement.admin2_name.isnot(None),
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

    # Get admin1 name from any source
    name_result = await db.execute(
        select(ConflictEvent.admin1_name).where(
            ConflictEvent.admin1_code == admin1_code,
            ConflictEvent.admin1_name.isnot(None),
        ).limit(1)
    )
    admin1_name = name_result.scalar()
    if not admin1_name:
        # Try displacement table
        name_result2 = await db.execute(
            select(Displacement.admin1_name).where(
                Displacement.admin1_code == admin1_code,
                Displacement.admin1_name.isnot(None),
            ).limit(1)
        )
        admin1_name = name_result2.scalar() or admin1_code

    # Latest IDP figure for this region (stock, not cumulative)
    latest_idp_q = await db.execute(
        select(func.sum(Displacement.population)).where(
            Displacement.admin1_code == admin1_code,
            Displacement.displacement_type == "idp",
            Displacement.admin2_name.isnot(None),
            Displacement.reference_period_start == (
                select(
                    func.max(Displacement.reference_period_start)
                ).where(
                    Displacement.admin1_code == admin1_code,
                    Displacement.displacement_type == "idp",
                    Displacement.admin2_name.isnot(None),
                ).scalar_subquery()
            ),
        )
    )
    latest_idps = latest_idp_q.scalar() or 0

    # Latest IPC period for this region
    latest_ipc_q = await db.execute(
        select(func.max(FoodSecurity.reference_period_start)).where(
            FoodSecurity.admin1_code == admin1_code,
            FoodSecurity.ipc_phase.in_(["1", "2", "3", "4", "5"]),
        )
    )
    latest_ipc_period = latest_ipc_q.scalar()

    return {
        "admin1_code": admin1_code,
        "admin1_name": admin1_name,
        "latest_idps": latest_idps,
        "latest_ipc_period": latest_ipc_period.isoformat()
        if latest_ipc_period else None,
        "conflict": conflicts,
        "displacement": displacements,
        "food_security": food_security,
        "operational_presence": orgs,
    }
