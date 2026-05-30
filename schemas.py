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
    unit: Optional[str] = None
    unit_price: Optional[float] = None
    total: Optional[float] = None


class PriceComparison(BaseModel):
    item_description: str
    unit: Optional[str]
    current_unit_price: Optional[float]
    avg_historical_price: Optional[float]
    min_historical_price: Optional[float]
    min_supplier: Optional[str]
    percent_diff: Optional[float]
    is_new: bool
    current_price_m2: Optional[float] = None
    avg_historical_price_m2: Optional[float] = None
    min_historical_price_m2: Optional[float] = None


class PriceHistoryOut(BaseModel):
    id: int
    supplier: Optional[str]
    item_description: str
    unit: Optional[str]
    unit_price: Optional[float]
    quantity: Optional[float]
    total: Optional[float]
    recorded_at: datetime
    area_m2: Optional[float] = None
    price_per_m2: Optional[float] = None

    class Config:
        from_attributes = True


class SupplierRankingItem(BaseModel):
    item_description: str
    unit: Optional[str]
    supplier: str
    avg_price: float
    min_price: float
    times_bought: int
    last_date: datetime
    avg_price_m2: Optional[float] = None
    min_price_m2: Optional[float] = None


class RankingOut(BaseModel):
    rankings: List[SupplierRankingItem]


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
    uploaded_by: Optional[str] = None
    area_m2: Optional[float] = None


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
    uploaded_by: Optional[str] = None

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
    comparisons: Optional[List[PriceComparison]] = None


# ── Dashboard ────────────────────────────────────────────────────

class DashboardOut(BaseModel):
    total_projects: int
    active_projects: int
    total_spent: float
    recent_invoices: List[InvoiceOut]


# ── Auth schemas ─────────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str
    display_name: Optional[str] = None
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    display_name: Optional[str]
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    token: str
    username: str
    display_name: Optional[str]
    role: str
