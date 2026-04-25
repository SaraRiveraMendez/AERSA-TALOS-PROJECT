"""
connection.py
Conexión async a la base de datos con SQLAlchemy.
Compatible con MySQL (ahora) y Oracle Autonomous DB (al migrar).

Para migrar: solo cambia DATABASE_URL en .env.
No necesitas tocar este archivo.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy import text, event

from app.config import get_settings

settings = get_settings()

# ── Motor de base de datos ──────────────────────────────────────────────────


def _build_engine() -> AsyncEngine:
    """
    Construye el engine según el backend configurado.
    MySQL:  mysql+aiomysql://...
    Oracle: oracle+oracledb://...  (solo cambia el URL en .env)
    """
    kwargs: dict = {
        "echo": not settings.is_production,  # Loguea SQL en desarrollo
        "pool_pre_ping": True,  # Detecta conexiones muertas
        "pool_recycle": 3600,  # Recicla conexiones cada hora
    }

    if settings.is_oracle:
        # Oracle Autonomous DB necesita pool más conservador
        kwargs.update(
            {
                "pool_size": 5,
                "max_overflow": 10,
            }
        )
    else:
        # MySQL local — pool generoso para desarrollo
        kwargs.update(
            {
                "pool_size": 10,
                "max_overflow": 20,
            }
        )

    return create_async_engine(settings.database_url, **kwargs)


engine: AsyncEngine = _build_engine()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ── Dependency para FastAPI ─────────────────────────────────────────────────


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency injection para rutas de FastAPI.
    Uso:
        @router.get("/")
        async def mi_ruta(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager para usar fuera de rutas FastAPI.
    Uso (en servicios, scheduler, scripts):
        async with get_db_context() as db:
            result = await db.execute(...)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── Health check ────────────────────────────────────────────────────────────


async def check_db_connection() -> bool:
    """Verifica que la BD esté accesible. Usado en el startup de FastAPI."""
    try:
        async with get_db_context() as db:
            await db.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"[DB] Error de conexión: {e}")
        return False


async def dispose_engine() -> None:
    """Cierra el pool de conexiones. Llamar en el shutdown de FastAPI."""
    await engine.dispose()
