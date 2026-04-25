"""
app/main.py
Entry point de la API TALOS Report Service.

Incluye:
    - Startup / shutdown lifecycle
    - Health check
    - Scheduler semanal automático
    - Registro de routers
"""

from contextlib import asynccontextmanager
from datetime import datetime, date, timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings
from app.db.connection import check_db_connection, dispose_engine
from app.models import HealthResponse
from app.routers import reports

settings = get_settings()

# ── Scheduler ─────────────────────────────────────────────────────────────────

scheduler = AsyncIOScheduler(timezone=settings.scheduler_timezone)


async def _scheduled_weekly_reports() -> None:
    """
    Job que corre automáticamente cada fin de semana.
    Busca todos los inventarios cerrados en los últimos 7 días
    y genera su reporte.
    """
    from app.db.connection import get_db_context
    from app.db.queries import fetch_inventarios_del_periodo
    from app.routers.reports import _run_report_pipeline

    hoy = date.today()
    hace_7dias = hoy - timedelta(days=7)

    print(f"[Scheduler] Ejecutando reportes semanales — período: {hace_7dias} → {hoy}")

    async with get_db_context() as db:
        inventarios = await fetch_inventarios_del_periodo(
            db,
            fecha_inicio=hace_7dias.isoformat(),
            fecha_fin=hoy.isoformat(),
        )

    print(f"[Scheduler] {len(inventarios)} inventarios encontrados.")

    for inv in inventarios:
        await _run_report_pipeline(
            idinventariomes=inv["idinventariomes"],
            notify_email=None,  # configurable por sucursal en el futuro
        )


# ── Lifecycle ─────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup y shutdown de la aplicación."""
    # ── STARTUP ──
    print("=" * 50)
    print("  TALOS Report API — iniciando")
    print(f"  Entorno: {settings.app_env}")
    print(f"  BD:      {settings.database_url.split('@')[-1]}")  # Oculta credenciales
    print("=" * 50)

    db_ok = await check_db_connection()
    if not db_ok:
        print("[WARNING] No se pudo conectar a la BD — verifica DATABASE_URL en .env")

    # Registrar job semanal
    scheduler.add_job(
        _scheduled_weekly_reports,
        trigger=CronTrigger(
            day_of_week=settings.scheduler_day_of_week,
            hour=settings.scheduler_hour,
            minute=settings.scheduler_minute,
            timezone=settings.scheduler_timezone,
        ),
        id="weekly_reports",
        name="Reportes semanales TALOS",
        replace_existing=True,
        misfire_grace_time=3600,  # 1 hora de gracia si el servidor estaba caído
    )
    scheduler.start()
    print(
        f"[Scheduler] Job semanal registrado — "
        f"{settings.scheduler_day_of_week} {settings.scheduler_hour:02d}:{settings.scheduler_minute:02d} "
        f"({settings.scheduler_timezone})"
    )

    yield  # ← La app corre aquí

    # ── SHUTDOWN ──
    scheduler.shutdown(wait=False)
    await dispose_engine()
    print("[Shutdown] API detenida correctamente.")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="TALOS Report Service",
    description="API para generación automática de reportes de auditoría de inventario.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — ajustar origins en producción
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if not settings.is_production else ["https://tu-dashboard.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(reports.router)


# ── Endpoints base ────────────────────────────────────────────────────────────


@app.get("/", include_in_schema=False)
async def root():
    return {"message": "TALOS Report API", "docs": "/docs"}


@app.get("/health", response_model=HealthResponse, tags=["Sistema"])
async def health_check():
    """Verifica el estado de la API y la conexión a la BD."""
    db_ok = await check_db_connection()
    return HealthResponse(
        status="ok" if db_ok else "degraded",
        db_connected=db_ok,
        timestamp=datetime.utcnow(),
    )


# ── Entrypoint directo

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=not settings.is_production,
    )
