from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database import get_db
from models import Project, Invoice
from schemas import InvoiceCreate, InvoiceOut, ScanResult
from services.cloudinary_service import upload_image
from services.ai_service import extract_invoice_data

router = APIRouter(tags=["invoices"])


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
    """Upload invoice photo, run Claude OCR, return extracted data — does NOT save to DB."""
    # Verify project exists
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

    return ScanResult(
        photo_url=photo_url,
        supplier=extracted.get("supplier"),
        invoice_number=extracted.get("invoice_number"),
        invoice_date=extracted.get("invoice_date"),
        total_amount=extracted.get("total_amount"),
        currency=extracted.get("currency", "COP"),
        items=extracted.get("items", []),
        notes=extracted.get("notes"),
        raw_text=extracted.get("raw_text"),
    )


@router.post("/api/projects/{project_id}/invoices", response_model=InvoiceOut)
async def save_invoice(
    project_id: int,
    invoice_data: InvoiceCreate,
    db: AsyncSession = Depends(get_db),
):
    """Save a confirmed invoice to the database."""
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
    )
    db.add(invoice)
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
