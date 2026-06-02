"""
app/models.py
Modelos Pydantic para requests y responses de la API.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, model_validator

# ── Reportes ─────────────────────────────────────────────────────────────────


class GenerateReportRequest(BaseModel):
    idinventariomes: int = Field(
        ..., description="ID del inventario mensual a reportar"
    )
    notify_email: Optional[str] = None
    force: bool = False


class ReportStatusResponse(BaseModel):
    idinventariomes: int
    status: str
    pdf_url: Optional[str] = None
    generated_at: Optional[datetime] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    db_connected: bool
    timestamp: datetime
    version: str = "1.0.0"


# ── Transferencias ────────────────────────────────────────────────────────────


class TransferenciaCreate(BaseModel):
    """Body para POST /transferencias/ — registro manual."""

    idempresa: int
    transferencia_fecha: date

    idsucursal_origen: int
    idalmacen_origen: int
    idinventariomes_origen: Optional[int] = None

    idsucursal_destino: int
    idalmacen_destino: int
    idinventariomes_destino: Optional[int] = None

    idproducto: int
    transferencia_cantidad: Decimal = Field(..., gt=0)
    transferencia_costopromedio: Optional[Decimal] = None
    transferencia_observaciones: Optional[str] = None
    idusuario_registra: Optional[int] = None

    @model_validator(mode="after")
    def almacenes_distintos(self):
        if self.idalmacen_origen == self.idalmacen_destino:
            raise ValueError("El almacén origen y destino no pueden ser el mismo.")
        return self


class TransferenciaConfirm(BaseModel):
    """Body para PATCH /transferencias/{id}/confirmar."""

    idusuario_confirma: Optional[int] = None
    transferencia_observaciones: Optional[str] = None


class TransferenciaReject(BaseModel):
    """Body para PATCH /transferencias/{id}/rechazar."""

    idusuario_confirma: Optional[int] = None
    transferencia_observaciones: Optional[str] = None


class TransferenciaResponse(BaseModel):
    """Respuesta al consultar o crear una transferencia."""

    idtransferencia: int
    idempresa: int
    transferencia_fecha: date
    idsucursal_origen: int
    idalmacen_origen: int
    almacen_origen_nombre: Optional[str] = None
    idinventariomes_origen: Optional[int] = None
    idsucursal_destino: int
    idalmacen_destino: int
    almacen_destino_nombre: Optional[str] = None
    idinventariomes_destino: Optional[int] = None
    idproducto: int
    producto_nombre: Optional[str] = None
    transferencia_cantidad: Decimal
    transferencia_costopromedio: Optional[Decimal] = None
    transferencia_importe: Optional[Decimal] = None
    transferencia_tipo: str
    transferencia_origen: str
    transferencia_estatus: str
    transferencia_observaciones: Optional[str] = None
    idusuario_registra: Optional[int] = None
    idusuario_confirma: Optional[int] = None
    transferencia_createdat: datetime
    transferencia_updatedat: datetime

    class Config:
        from_attributes = True
