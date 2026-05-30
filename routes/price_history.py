from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database import get_db
from models import PriceHistory
from schemas import RankingOut, SupplierRankingItem, PriceHistoryOut

router = APIRouter(tags=["price_history"])


@router.get("/api/price-history/rankings", response_model=RankingOut)
async def get_rankings(
    item: Optional[str] = Query(None, description="Filter by item description substring"),
    db: AsyncSession = Depends(get_db),
):
    """Return supplier rankings sorted by average unit price per item."""
    query = (
        select(
            PriceHistory.item_description,
            PriceHistory.unit,
            PriceHistory.supplier,
            PriceHistory.brand,
            func.avg(PriceHistory.unit_price).label("avg_price"),
            func.min(PriceHistory.unit_price).label("min_price"),
            func.avg(PriceHistory.price_per_m2).label("avg_price_m2"),
            func.min(PriceHistory.price_per_m2).label("min_price_m2"),
            func.count(PriceHistory.id).label("times_bought"),
            func.max(PriceHistory.recorded_at).label("last_date"),
        )
        .where(PriceHistory.unit_price.isnot(None))
        .where(PriceHistory.supplier.isnot(None))
        .group_by(PriceHistory.item_description, PriceHistory.unit, PriceHistory.supplier, PriceHistory.brand)
        .order_by(PriceHistory.item_description, func.avg(PriceHistory.unit_price))
    )

    if item:
        query = query.where(PriceHistory.item_description_normalized.contains(item.lower()))

    result = await db.execute(query)
    rows = result.all()

    rankings = [
        SupplierRankingItem(
            item_description=row.item_description,
            unit=row.unit,
            supplier=row.supplier,
            brand=row.brand,
            avg_price=round(row.avg_price, 2),
            min_price=round(row.min_price, 2),
            avg_price_m2=round(row.avg_price_m2, 2) if row.avg_price_m2 else None,
            min_price_m2=round(row.min_price_m2, 2) if row.min_price_m2 else None,
            times_bought=row.times_bought,
            last_date=row.last_date,
        )
        for row in rows
    ]

    return RankingOut(rankings=rankings)


@router.get("/api/price-history", response_model=List[PriceHistoryOut])
async def list_price_history(
    item: Optional[str] = Query(None),
    supplier: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(PriceHistory).order_by(PriceHistory.recorded_at.desc()).limit(200)
    if item:
        query = query.where(PriceHistory.item_description_normalized.contains(item.lower()))
    if supplier:
        query = query.where(PriceHistory.supplier.ilike(f"%{supplier}%"))
    result = await db.execute(query)
    return result.scalars().all()
