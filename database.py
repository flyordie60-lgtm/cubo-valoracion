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
                ('Pinturas', 'Pinturas, esmaltes y recubrimientos líquidos', NOW()),
                ('Rígidos', 'Acrílicos, plásticos rígidos, foam board y materiales duros', NOW()),
                ('Flexibles', 'Vinilos, laminados, telas y materiales flexibles', NOW()),
                ('Ferretería', 'Tornillos, tuercas, anclajes y elementos metálicos', NOW()),
                ('Servicios', 'Servicios tercerizados: instalación, diseño, transporte, etc.', NOW())
            """))
            await conn.execute(_text("""
                INSERT INTO materials (category_id, name, description, default_unit, created_at)
                SELECT c.id, m.name, m.description, m.default_unit, NOW()
                FROM (VALUES
                    ('Pinturas', 'Pintura vinilo blanca', 'Pintura vinílica interior color blanco', 'lt'),
                    ('Pinturas', 'Pintura esmalte', 'Esmalte brillante', 'lt'),
                    ('Pinturas', 'Pintura exterior texturizada', 'Pintura para fachadas texturizada', 'lt'),
                    ('Pinturas', 'Sellador', 'Sellador para superficies', 'lt'),
                    ('Rígidos', 'Acrílico transparente', 'Lámina de acrílico transparente', 'm²'),
                    ('Rígidos', 'Acrílico color', 'Lámina de acrílico de color', 'm²'),
                    ('Rígidos', 'Foam board', 'Foam board para montajes', 'm²'),
                    ('Rígidos', 'PVC espumado', 'Lámina de PVC espumado', 'm²'),
                    ('Rígidos', 'Dibond', 'Panel compuesto de aluminio', 'm²'),
                    ('Flexibles', 'Vinilo adhesivo', 'Vinilo adhesivo para corte o impresión', 'm²'),
                    ('Flexibles', 'Vinilo microperforado', 'Vinilo microperforado para ventanas', 'm²'),
                    ('Flexibles', 'Lona', 'Lona para impresión', 'm²'),
                    ('Flexibles', 'Laminado brillante', 'Laminado brillante de protección', 'm²'),
                    ('Flexibles', 'Laminado mate', 'Laminado mate de protección', 'm²'),
                    ('Ferretería', 'Tornillo autorroscante', 'Tornillo autorroscante galvanizado', 'unidad'),
                    ('Ferretería', 'Remache', 'Remache de aluminio', 'unidad'),
                    ('Ferretería', 'Perfil de aluminio', 'Perfil de aluminio para marcos', 'm'),
                    ('Servicios', 'Instalación', 'Servicio de instalación en sitio', 'unidad'),
                    ('Servicios', 'Diseño gráfico', 'Servicio de diseño gráfico', 'unidad'),
                    ('Servicios', 'Transporte', 'Servicio de transporte y entrega', 'unidad'),
                    ('Servicios', 'Impresión digital', 'Servicio de impresión digital', 'm²')
                ) AS m(cat_name, name, description, default_unit)
                JOIN categories c ON c.name = m.cat_name
            """))
