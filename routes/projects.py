import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from database import get_db
from models import Project, Invoice
from schemas import ProjectCreate, ProjectUpdate, ProjectOut
from services.cloudinary_service import upload_image

router = APIRouter(prefix="/api/projects", tags=["projects"])


def project_to_out(project: Project) -> ProjectOut:
    return ProjectOut(
        id=project.id,
        name=project.name,
        description=project.description,
        dimensions=project.dimensions,
        client_name=project.client_name,
        status=project.status,
        photo_url=project.photo_url,
        created_at=project.created_at,
        total_spent=project.total_spent,
    )


@router.get("", response_model=List[ProjectOut])
async def list_projects(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Project).options(selectinload(Project.invoices)).order_by(Project.created_at.desc())
    )
    projects = result.scalars().all()
    return [project_to_out(p) for p in projects]


@router.post("", response_model=ProjectOut)
async def create_project(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    dimensions: Optional[str] = Form(None),
    client_name: Optional[str] = Form(None),
    status: Optional[str] = Form("active"),
    photo: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
):
    photo_url = None
    if photo and photo.filename:
        file_bytes = await photo.read()
        safe_name = photo.filename.replace(" ", "_")
        photo_url = await upload_image(file_bytes, f"projects/{safe_name}", folder="cubo-valoracion/projects")

    project = Project(
        name=name,
        description=description,
        dimensions=dimensions,
        client_name=client_name,
        status=status or "active",
        photo_url=photo_url,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)

    # Load invoices relationship
    result = await db.execute(
        select(Project).options(selectinload(Project.invoices)).where(Project.id == project.id)
    )
    project = result.scalar_one()
    return project_to_out(project)


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(project_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Project).options(selectinload(Project.invoices)).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return project_to_out(project)


@router.put("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: int,
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    dimensions: Optional[str] = Form(None),
    client_name: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Project).options(selectinload(Project.invoices)).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    if name is not None:
        project.name = name
    if description is not None:
        project.description = description
    if dimensions is not None:
        project.dimensions = dimensions
    if client_name is not None:
        project.client_name = client_name
    if status is not None:
        project.status = status

    if photo and photo.filename:
        file_bytes = await photo.read()
        safe_name = photo.filename.replace(" ", "_")
        project.photo_url = await upload_image(
            file_bytes, f"projects/{project_id}_{safe_name}", folder="cubo-valoracion/projects"
        )

    await db.commit()
    await db.refresh(project)

    result = await db.execute(
        select(Project).options(selectinload(Project.invoices)).where(Project.id == project_id)
    )
    project = result.scalar_one()
    return project_to_out(project)


@router.delete("/{project_id}")
async def delete_project(project_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    await db.delete(project)
    await db.commit()
    return {"message": "Proyecto eliminado"}
