from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database import get_db
from models import Category, Material
from schemas import CategoryCreate, CategoryOut, CategoryWithMaterials, MaterialCreate, MaterialOut

router = APIRouter(tags=["catalog"])


@router.get("/api/catalog", response_model=List[CategoryWithMaterials])
async def list_catalog(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Category)
        .options(selectinload(Category.materials))
        .order_by(Category.name)
    )
    return result.scalars().all()


@router.post("/api/catalog/categories", response_model=CategoryOut)
async def create_category(data: CategoryCreate, db: AsyncSession = Depends(get_db)):
    cat = Category(name=data.name, description=data.description)
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return cat


@router.put("/api/catalog/categories/{cat_id}", response_model=CategoryOut)
async def update_category(cat_id: int, data: CategoryCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category).where(Category.id == cat_id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    cat.name = data.name
    if data.description is not None:
        cat.description = data.description
    await db.commit()
    await db.refresh(cat)
    return cat


@router.delete("/api/catalog/categories/{cat_id}")
async def delete_category(cat_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category).where(Category.id == cat_id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    await db.delete(cat)
    await db.commit()
    return {"message": "Categoría eliminada"}


@router.post("/api/catalog/materials", response_model=MaterialOut)
async def create_material(data: MaterialCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category).where(Category.id == data.category_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    mat = Material(
        category_id=data.category_id,
        name=data.name,
        description=data.description,
        default_unit=data.default_unit,
    )
    db.add(mat)
    await db.commit()
    await db.refresh(mat)
    # reload with category
    result2 = await db.execute(
        select(Material).options(selectinload(Material.category)).where(Material.id == mat.id)
    )
    return result2.scalar_one()


@router.put("/api/catalog/materials/{mat_id}", response_model=MaterialOut)
async def update_material(mat_id: int, data: MaterialCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Material).options(selectinload(Material.category)).where(Material.id == mat_id)
    )
    mat = result.scalar_one_or_none()
    if not mat:
        raise HTTPException(status_code=404, detail="Material no encontrado")
    mat.category_id = data.category_id
    mat.name = data.name
    if data.description is not None:
        mat.description = data.description
    if data.default_unit is not None:
        mat.default_unit = data.default_unit
    await db.commit()
    await db.refresh(mat)
    result2 = await db.execute(
        select(Material).options(selectinload(Material.category)).where(Material.id == mat.id)
    )
    return result2.scalar_one()


@router.delete("/api/catalog/materials/{mat_id}")
async def delete_material(mat_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Material).where(Material.id == mat_id))
    mat = result.scalar_one_or_none()
    if not mat:
        raise HTTPException(status_code=404, detail="Material no encontrado")
    await db.delete(mat)
    await db.commit()
    return {"message": "Material eliminado"}


@router.get("/api/catalog/search", response_model=List[MaterialOut])
async def search_materials(q: str = "", db: AsyncSession = Depends(get_db)):
    if not q or len(q) < 2:
        return []
    pattern = f"%{q}%"
    result = await db.execute(
        select(Material)
        .options(selectinload(Material.category))
        .where(Material.name.ilike(pattern))
        .order_by(Material.name)
        .limit(20)
    )
    return result.scalars().all()
