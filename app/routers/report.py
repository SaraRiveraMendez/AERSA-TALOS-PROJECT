"""
app/routers/reports.py
Endpoints de la API relacionados con generación de reportes.

Rutas:
    POST /reports/generate          → Genera un reporte bajo demanda
    GET  /reports/{id}/status       → Consulta el estado de un reporte
    GET  /reports/{id}/download     → Descarga el PDF directamente
    GET  /reports/                  → Lista reportes recientes
"""

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.connection import get_db
from app.db.queries import (
    fetch_header,
    fetch_detalle,
    fetch_pendientes_validacion,
)
from app.models import GenerateReportRequest, ReportStatusResponse
from app.services.data_processor import DataProcessor
from app.config import get_settings

router = APIRouter(prefix="/reports", tags=["Reportes"])
settings = get_settings()


# ── Generación bajo demanda ───────────────────────────────────────────────────


@router.post("/generate", response_model=ReportStatusResponse)
async def generate_report(
    body: GenerateReportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Genera el reporte PDF de un inventario mensual.
    La generación se procesa en background para no bloquear la respuesta.
    """
    # Validar que el inventario existe
    try:
        header = await fetch_header(db, body.idinventariomes)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Encolar la generación en background
    background_tasks.add_task(
        _run_report_pipeline,
        idinventariomes=body.idinventariomes,
        notify_email=body.notify_email,
    )

    return ReportStatusResponse(
        idinventariomes=body.idinventariomes,
        status="processing",
        generated_at=datetime.utcnow(),
    )


# ── Consulta de estado ────────────────────────────────────────────────────────


@router.get("/{idinventariomes}/status", response_model=ReportStatusResponse)
async def get_report_status(idinventariomes: int):
    """Consulta si el reporte de un inventario ya está listo."""
    pdf_path = _get_pdf_path(idinventariomes)

    if pdf_path.exists():
        return ReportStatusResponse(
            idinventariomes=idinventariomes,
            status="ready",
            pdf_url=f"/reports/{idinventariomes}/download",
            generated_at=datetime.fromtimestamp(pdf_path.stat().st_mtime),
        )

    return ReportStatusResponse(
        idinventariomes=idinventariomes,
        status="pending",
    )


# ── Descarga del PDF ──────────────────────────────────────────────────────────


@router.get("/{idinventariomes}/download")
async def download_report(idinventariomes: int):
    """Descarga el PDF generado directamente."""
    pdf_path = _get_pdf_path(idinventariomes)

    if not pdf_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Reporte no generado aún. Usa POST /reports/generate primero.",
        )

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=f"reporte_inventario_{idinventariomes}.pdf",
    )


# ── Helpers privados ──────────────────────────────────────────────────────────


def _get_pdf_path(idinventariomes: int) -> Path:
    """Retorna la ruta esperada del PDF de un inventario."""
    base = Path(settings.storage_local_path)
    base.mkdir(parents=True, exist_ok=True)
    return base / f"reporte_{idinventariomes}.pdf"


async def _run_report_pipeline(
    idinventariomes: int,
    notify_email: str | None = None,
) -> None:
    """
    Pipeline completo de generación de un reporte.
    Se ejecuta en background.

    Pasos:
        1. Extrae datos de la BD
        2. Procesa KPIs y estadísticos (DataProcessor)
        3. Genera gráficas   (ChartGenerator)   ← próxima entrega
        4. Renderiza PDF     (PdfBuilder)        ← próxima entrega
        5. Guarda el archivo
        6. Notifica por email (opcional)         ← próxima entrega
    """
    from app.db.connection import get_db_context

    print(f"[Pipeline] Iniciando reporte para inventario {idinventariomes}...")

    try:
        async with get_db_context() as db:
            header = await fetch_header(db, idinventariomes)
            detalle = await fetch_detalle(db, idinventariomes)
            pendientes = await fetch_pendientes_validacion(db)

        # Paso 2: Procesar datos
        processor = DataProcessor(header, detalle, pendientes)
        context = processor.build_context()
        chart_data = processor.get_chart_data()

        print(
            f"[Pipeline] Datos procesados — {len(detalle)} productos, "
            f"{context.get('count_faltantes', 0)} faltantes."
        )

        # Pasos 3-6 se conectarán aquí en la siguiente fase
        # chart_images = await chart_generator.generate_all(chart_data)
        # pdf_bytes    = await pdf_builder.build(context, chart_images)
        # pdf_path     = _get_pdf_path(idinventariomes)
        # pdf_path.write_bytes(pdf_bytes)

        print(f"[Pipeline] ✓ Reporte {idinventariomes} completado.")

    except Exception as e:
        print(f"[Pipeline] ✗ Error en reporte {idinventariomes}: {e}")
        raise
