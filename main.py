import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from dotenv import load_dotenv

load_dotenv()

from database import init_db, get_db
from models import Project, Invoice
from schemas import DashboardOut, InvoiceOut
from routes.projects import router as projects_router
from routes.invoices import router as invoices_router
from routes.clients import router as clients_router
from routes.price_history import router as price_history_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await init_db()
    except Exception as e:
        print(f"[WARNING] Could not connect to database on startup: {e}")
        print("[WARNING] The app will start but DB-dependent endpoints will fail until a database is available.")
    yield


app = FastAPI(
    title="Cubo Digital - Valorización de Proyectos",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects_router)
app.include_router(invoices_router)
app.include_router(clients_router)
app.include_router(price_history_router)


@app.get("/api/dashboard", response_model=DashboardOut)
async def dashboard():
    from database import AsyncSessionLocal
    from sqlalchemy.orm import selectinload

    async with AsyncSessionLocal() as db:
        # Total projects
        total_result = await db.execute(select(func.count(Project.id)))
        total_projects = total_result.scalar() or 0

        # Active projects
        active_result = await db.execute(
            select(func.count(Project.id)).where(Project.status == "active")
        )
        active_projects = active_result.scalar() or 0

        # Total spent (sum of confirmed invoices)
        spent_result = await db.execute(
            select(func.sum(Invoice.total_amount)).where(Invoice.confirmed == True)
        )
        total_spent = spent_result.scalar() or 0.0

        # Recent invoices (last 10)
        recent_result = await db.execute(
            select(Invoice)
            .where(Invoice.confirmed == True)
            .order_by(Invoice.created_at.desc())
            .limit(10)
        )
        recent_invoices = recent_result.scalars().all()

    return DashboardOut(
        total_projects=total_projects,
        active_projects=active_projects,
        total_spent=float(total_spent),
        recent_invoices=[InvoiceOut.model_validate(inv) for inv in recent_invoices],
    )


@app.get("/")
async def serve_frontend():
    return FileResponse(os.path.join(os.path.dirname(__file__), "static", "index.html"))
