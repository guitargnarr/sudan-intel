"""Food Security API."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.models.models import FoodSecurity, FoodPrice

router = APIRouter()


@router.get("")
async def get_food_security(
    admin1_code: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    # IPC classifications
    ipc_query = select(FoodSecurity).order_by(FoodSecurity.reference_period_start)
    if admin1_code:
        ipc_query = ipc_query.where(FoodSecurity.admin1_code == admin1_code)

    result = await db.execute(ipc_query)
    ipc_records = result.scalars().all()

    # Phase distribution
    phase_dist = {}
    for r in ipc_records:
        p = r.ipc_phase or "unknown"
        if p not in phase_dist:
            phase_dist[p] = 0
        phase_dist[p] += r.population_in_phase or 0

    # Food prices
    price_query = select(FoodPrice).order_by(FoodPrice.reference_period_start.desc()).limit(500)
    if admin1_code:
        price_query = price_query.where(FoodPrice.admin1_code == admin1_code)

    price_result = await db.execute(price_query)
    prices = price_result.scalars().all()

    return {
        "ipc_phase_distribution": phase_dist,
        "ipc_records": [
            {
                "admin1": r.admin1_name,
                "admin2": r.admin2_name,
                "phase": r.ipc_phase,
                "type": r.ipc_type,
                "population": r.population_in_phase,
                "date": r.reference_period_start.isoformat() if r.reference_period_start else None,
            }
            for r in ipc_records
        ],
        "food_prices": [
            {
                "market": p.market_name,
                "commodity": p.commodity_name,
                "price": p.price,
                "currency": p.currency_code,
                "unit": p.unit,
                "lat": p.lat,
                "lon": p.lon,
                "date": p.reference_period_start.isoformat() if p.reference_period_start else None,
            }
            for p in prices
        ],
    }
