"""
app/models.py
Modelos Pydantic para requests y responses de la API.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class GenerateReportRequest(BaseModel):
    """Body del endpoint POST /reports/generate"""

    idinventariomes: int = Field(
        ..., description="ID del inventario mensual a reportar"
    )
    notify_email: Optional[str] = Field(
        None, description="Email al que enviar el reporte generado"
    )
    force: bool = Field(
        False, description="Si True, regenera aunque ya exista el reporte"
    )


class ReportStatusResponse(BaseModel):
    """Respuesta al consultar el estado de un reporte."""

    idinventariomes: int
    status: str  # pending | processing | ready | error
    pdf_url: Optional[str] = None
    generated_at: Optional[datetime] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Respuesta del endpoint /health"""

    status: str
    db_connected: bool
    timestamp: datetime
    version: str = "1.0.0"
