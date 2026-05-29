from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel


# ── Client schemas ───────────────────────────────────────────────

class ClientCreate(BaseModel):
    name: str
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    notes: Optional[str] = None


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    notes: Optional[str] = None


class ClientOut(BaseModel):
    id: int
    name: str
    contact_person: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    company: Optional[str]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Project schemas ──────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    dimensions: Optional[str] = None
    client_name: Optional[str] = None
    client_id: Optional[int] = None
    status: Optional[str] = "active"


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    dimensions: Optional[str] = None
    client_name: Optional[str] = None
    client_id: Optional[int] = None
    status: Optional[str] = None
    photo_url: Optional[str] = None


class ProjectOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    dimensions: Optional[str]
    client_name: Optional[str]
    client_id: Optional[int]
    status: str
    photo_url: Optional[str]
    created_at: datetime
    total_spent: float
    client: Optional[ClientOut] = None

    class Config:
        from_attributes = True


# ── Invoice schemas ──────────────────────────────────────────────

class InvoiceItem(BaseModel):
    description: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    total: Optional[float] = None


class InvoiceCreate(BaseModel):
    supplier: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    total_amount: Optional[float] = None
    currency: Optional[str] = "COP"
    items: Optional[List[InvoiceItem]] = None
    notes: Optional[str] = None
    photo_url: Optional[str] = None
    confirmed: Optional[bool] = True


class InvoiceOut(BaseModel):
    id: int
    project_id: int
    photo_url: Optional[str]
    supplier: Optional[str]
    invoice_number: Optional[str]
    invoice_date: Optional[str]
    total_amount: Optional[float]
    currency: str
    items: Optional[Any]
    notes: Optional[str]
    created_at: datetime
    confirmed: bool

    class Config:
        from_attributes = True


# ── Scan result (not saved) ──────────────────────────────────────

class ScanResult(BaseModel):
    photo_url: str
    supplier: Optional[str]
    invoice_number: Optional[str]
    invoice_date: Optional[str]
    total_amount: Optional[float]
    currency: Optional[str]
    items: Optional[List[InvoiceItem]]
    notes: Optional[str]
    raw_text: Optional[str] = None


# ── Dashboard ────────────────────────────────────────────────────

class DashboardOut(BaseModel):
    total_projects: int
    active_projects: int
    total_spent: float
    recent_invoices: List[InvoiceOut]
