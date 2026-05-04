"""
app/routers/reports.py
Endpoints de la API relacionados con generación de reportes.

Rutas:
    POST /reports/generate          → Genera un reporte bajo demanda
    GET  /reports/{id}/status       → Consulta el estado de un reporte
    GET  /reports/{id}/download     → Descarga el PDF directamente
"""

from datetime import datetime
from pathlib import Path
import asyncio

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.connection import get_db
from app.db.queries import fetch_header, fetch_detalle
from app.db.transferencia_queries import fetch_transferencias_confirmadas
from app.models import GenerateReportRequest, ReportStatusResponse
from app.services.data_processor import DataProcessor
from app.services.chart_generator import generate_all_charts
from app.services.html_generator import render_report_html
from app.services.pdf_generator import run_pdf_sync
from app.config import get_settings

router = APIRouter(prefix="/reports", tags=["Reportes"])
settings = get_settings()


@router.post("/generate", response_model=ReportStatusResponse)
async def generate_report(
    body: GenerateReportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    try:
        await fetch_header(db, body.idinventariomes)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

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


@router.get("/{idinventariomes}/status", response_model=ReportStatusResponse)
async def get_report_status(idinventariomes: int):
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


@router.get("/{idinventariomes}/download")
async def download_report(idinventariomes: int):
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


def _get_pdf_path(idinventariomes: int) -> Path:
    base = Path(settings.storage_local_path)
    base.mkdir(parents=True, exist_ok=True)
    return base / f"reporte_{idinventariomes}.pdf"


async def _run_report_pipeline(
    idinventariomes: int,
    notify_email: str | None = None,
) -> None:
    from app.db.connection import get_db_context

    print(f"[Pipeline] Iniciando reporte {idinventariomes}...")

    try:
        # 1. Datos de la BD
        async with get_db_context() as db:
            header = await fetch_header(db, idinventariomes)
            detalle = await fetch_detalle(db, idinventariomes)
            transferencias = await fetch_transferencias_confirmadas(db, idinventariomes)

        print(
            f"[Pipeline] {len(detalle)} productos cargados, "
            f"{len(transferencias)} transferencias confirmadas."
        )

        # 2. Procesar KPIs y estadísticos
        processor = DataProcessor(header, detalle, transferencias=transferencias)
        context = processor.build_context()
        chart_data = processor.get_chart_data()

        print(
            f"[Pipeline] Datos procesados — {context.get('count_faltantes', 0)} faltantes, "
            f"{context.get('count_sobrantes', 0)} sobrantes."
        )

        # 3. Gráficas (matplotlib → base64)
        charts = generate_all_charts(chart_data)
        print("[Pipeline] Gráficas generadas.")

        # 4. HTML con Jinja2
        html_content = render_report_html(context, charts)

        # Debug: guardar HTML para inspección en el navegador
        html_path = (
            Path(settings.storage_local_path) / f"reporte_{idinventariomes}.html"
        )
        html_path.write_text(html_content, encoding="utf-8")
        print(f"[Pipeline] HTML guardado en {html_path}")

        # 5. PDF con Playwright en thread separado
        pdf_path = _get_pdf_path(idinventariomes)
        await asyncio.to_thread(run_pdf_sync, html_content, pdf_path)

        print(f"[Pipeline] ✓ Reporte {idinventariomes} listo → {pdf_path}")

    except Exception as e:
        print(f"[Pipeline] ✗ Error en reporte {idinventariomes}: {e}")
        raise
