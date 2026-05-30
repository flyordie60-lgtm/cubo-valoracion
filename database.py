import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost/cubo_valoracion")

# Render provides postgresql:// but asyncpg needs postgresql+asyncpg://
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    from models import Project, Invoice, Client, PriceHistory, User, Category, Material  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Add client_id column to projects if it doesn't exist yet
        try:
            await conn.execute(
                __import__('sqlalchemy').text(
                    "ALTER TABLE projects ADD COLUMN IF NOT EXISTS client_id INTEGER REFERENCES clients(id) ON DELETE SET NULL"
                )
            )
        except Exception:
            pass
        # Add uploaded_by column to invoices if it doesn't exist yet
        try:
            await conn.execute(
                __import__('sqlalchemy').text(
                    "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS uploaded_by VARCHAR(100)"
                )
            )
        except Exception:
            pass
        # Add area_m2 / price_per_m2 columns
        try:
            await conn.execute(__import__('sqlalchemy').text("ALTER TABLE price_history ADD COLUMN IF NOT EXISTS area_m2 FLOAT"))
            await conn.execute(__import__('sqlalchemy').text("ALTER TABLE price_history ADD COLUMN IF NOT EXISTS price_per_m2 FLOAT"))
            await conn.execute(__import__('sqlalchemy').text("ALTER TABLE invoices ADD COLUMN IF NOT EXISTS area_m2 FLOAT"))
        except Exception:
            pass
        # Add material_id to price_history
        try:
            await conn.execute(__import__('sqlalchemy').text(
                "ALTER TABLE price_history ADD COLUMN IF NOT EXISTS material_id INTEGER REFERENCES materials(id) ON DELETE SET NULL"
            ))
        except Exception:
            pass
        # Seed example categories/materials if none exist
        from sqlalchemy import text as _text
        result = await conn.execute(_text("SELECT COUNT(*) FROM categories"))
        count = result.scalar()
        if count == 0:
            await conn.execute(_text("""
                INSERT INTO categories (name, description, created_at) VALUES
                ('Pinturas', 'Pinturas, esmaltes y recubrimientos', NOW()),
                ('Cementos y Morteros', 'Cementos, morteros y adhesivos', NOW()),
                ('Ferretería', 'Tornillos, tuercas, anclajes y elementos metálicos', NOW())
            """))
            await conn.execute(_text("""
                INSERT INTO materials (category_id, name, description, default_unit, created_at)
                SELECT c.id, m.name, m.description, m.default_unit, NOW()
                FROM (VALUES
                    ('Pinturas', 'Pintura vinilo blanca', 'Pintura vinílica interior color blanco', 'lt'),
                    ('Pinturas', 'Pintura esmalte negro', 'Esmalte brillante color negro', 'lt'),
                    ('Pinturas', 'Pintura exterior texturizada', 'Pintura para fachadas texturizada', 'lt'),
                    ('Cementos y Morteros', 'Cemento gris 50kg', 'Cemento Portland tipo I', 'saco'),
                    ('Cementos y Morteros', 'Mortero adhesivo', 'Adhesivo cementicio para pisos y muros', 'saco'),
                    ('Ferretería', 'Tornillo galvanizado 2"', 'Tornillo autorroscante galvanizado 2 pulgadas', 'unidad'),
                    ('Ferretería', 'Varilla corrugada 1/2"', 'Varilla de acero corrugado 6m', 'unidad')
                ) AS m(cat_name, name, description, default_unit)
                JOIN categories c ON c.name = m.cat_name
            """))
