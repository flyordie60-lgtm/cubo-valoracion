from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
import unicodedata
import re

from database import get_db
from models import Project, Invoice, PriceHistory
from schemas import InvoiceCreate, InvoiceOut, ScanResult, PriceComparison
from services.cloudinary_service import upload_image
from services.ai_service import extract_invoice_data

router = APIRouter(tags=["invoices"])


def normalize_description(text: str) -> str:
    """Lowercase, remove accents, strip extra spaces for fuzzy matching."""
    if not text:
        return ""
    text = text.lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


async def get_price_comparisons(db: AsyncSession, items: list, supplier: str = None, area_m2: float = 0) -> List[PriceComparison]:
    comparisons = []
    for item in items:
        desc = item.get("description") or ""
        unit_price = item.get("unit_price")
        unit = item.get("unit")
        if not desc or unit_price is None:
            continue

        norm = normalize_description(desc)

        result = await db.execute(
            select(
                PriceHistory.supplier,
                func.avg(PriceHistory.unit_price).label("avg_price"),
                func.min(PriceHistory.unit_price).label("min_price"),
            )
            .where(PriceHistory.item_description_normalized == norm)
            .where(PriceHistory.unit_price.isnot(None))
            .group_by(PriceHistory.supplier)
            .order_by(func.min(PriceHistory.unit_price))
        )
        rows = result.all()

        if not rows:
            comparisons.append(PriceComparison(
                item_description=desc,
                unit=unit,
                current_unit_price=unit_price,
                avg_historical_price=None,
                min_historical_price=None,
                min_supplier=None,
                percent_diff=None,
                is_new=True,
            ))
            continue

        all_prices_result = await db.execute(
            select(
                func.avg(PriceHistory.unit_price),
                func.min(PriceHistory.unit_price),
                func.avg(PriceHistory.price_per_m2),
                func.min(PriceHistory.price_per_m2),
            )
            .where(PriceHistory.item_description_normalized == norm)
            .where(PriceHistory.unit_price.isnot(None))
        )
        avg_price, min_price, avg_price_m2, min_price_m2 = all_prices_result.one()
        min_supplier = rows[0].supplier if rows else None

        percent_diff = None
        if avg_price:
            percent_diff = round(((unit_price - avg_price) / avg_price) * 100, 1)

        # current price per m²
        item_total = item.get("total")
        current_price_m2_val = None
        if item_total and area_m2 and area_m2 > 0:
            current_price_m2_val = round(item_total / area_m2, 2)

        comparisons.append(PriceComparison(
            item_description=desc,
            unit=unit,
            current_unit_price=unit_price,
            avg_historical_price=round(avg_price, 2) if avg_price else None,
            min_historical_price=round(min_price, 2) if min_price else None,
            min_supplier=min_supplier,
            percent_diff=percent_diff,
            is_new=False,
            current_price_m2=current_price_m2_val,
            avg_historical_price_m2=round(avg_price_m2, 2) if avg_price_m2 else None,
            min_historical_price_m2=round(min_price_m2, 2) if min_price_m2 else None,
        ))

    return comparisons


@router.get("/api/projects/{project_id}/invoices", response_model=List[InvoiceOut])
async def list_invoices(project_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Invoice)
        .where(Invoice.project_id == project_id)
        .order_by(Invoice.created_at.desc())
    )
    return result.scalars().all()


@router.post("/api/projects/{project_id}/invoices/scan", response_model=ScanResult)
async def scan_invoice(
    project_id: int,
    photo: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload invoice photo, run Claude OCR, return extracted data with price comparisons."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    file_bytes = await photo.read()
    safe_name = photo.filename.replace(" ", "_") if photo.filename else "invoice.jpg"
    photo_url = await upload_image(
        file_bytes,
        f"invoices/scan_{project_id}_{safe_name}",
        folder="cubo-valoracion/invoices",
    )

    try:
        extracted = await extract_invoice_data(photo_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar la imagen: {str(e)}")

    items = extracted.get("items", []) or []
    comparisons = await get_price_comparisons(db, items, extracted.get("supplier"))

    return ScanResult(
        photo_url=photo_url,
        supplier=extracted.get("supplier"),
        invoice_number=extracted.get("invoice_number"),
        invoice_date=extracted.get("invoice_date"),
        total_amount=extracted.get("total_amount"),
        currency=extracted.get("currency", "COP"),
        items=items,
        notes=extracted.get("notes"),
        raw_text=extracted.get("raw_text"),
        comparisons=comparisons,
    )


@router.post("/api/projects/{project_id}/invoices", response_model=InvoiceOut)
async def save_invoice(
    project_id: int,
    invoice_data: InvoiceCreate,
    db: AsyncSession = Depends(get_db),
):
    """Save a confirmed invoice to the database and record price history."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    items_json = None
    if invoice_data.items:
        items_json = [item.model_dump() for item in invoice_data.items]

    invoice = Invoice(
        project_id=project_id,
        photo_url=invoice_data.photo_url,
        supplier=invoice_data.supplier,
        invoice_number=invoice_data.invoice_number,
        invoice_date=invoice_data.invoice_date,
        total_amount=invoice_data.total_amount,
        currency=invoice_data.currency or "COP",
        items=items_json,
        notes=invoice_data.notes,
        confirmed=invoice_data.confirmed if invoice_data.confirmed is not None else True,
        uploaded_by=invoice_data.uploaded_by,
        area_m2=invoice_data.area_m2,
    )
    db.add(invoice)
    await db.flush()  # get invoice.id before committing

    # Save price history for each item with a unit_price
    if invoice_data.items and invoice.confirmed:
        for item in invoice_data.items:
            if item.description and item.unit_price is not None:
                price_per_m2_val = None
                if item.total and invoice_data.area_m2 and invoice_data.area_m2 > 0:
                    price_per_m2_val = round(item.total / invoice_data.area_m2, 2)
                ph = PriceHistory(
                    invoice_id=invoice.id,
                    project_id=project_id,
                    supplier=invoice_data.supplier,
                    item_description=item.description,
                    item_description_normalized=normalize_description(item.description),
                    unit=item.unit,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    total=item.total,
                    area_m2=invoice_data.area_m2,
                    price_per_m2=price_per_m2_val,
                )
                db.add(ph)

    await db.commit()
    await db.refresh(invoice)
    return invoice


@router.put("/api/invoices/{invoice_id}", response_model=InvoiceOut)
async def update_invoice(invoice_id: int, invoice_data: InvoiceCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")

    for field in ['supplier', 'invoice_number', 'invoice_date', 'total_amount', 'currency', 'notes', 'photo_url', 'uploaded_by']:
        val = getattr(invoice_data, field, None)
        if val is not None:
            setattr(invoice, field, val)
    if invoice_data.items is not None:
        invoice.items = [item.model_dump() for item in invoice_data.items]
    if invoice_data.confirmed is not None:
        invoice.confirmed = invoice_data.confirmed

    await db.commit()
    await db.refresh(invoice)
    return invoice


@router.delete("/api/invoices/{invoice_id}")
async def delete_invoice(invoice_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    await db.delete(invoice)
    await db.commit()
    return {"message": "Factura eliminada"}
