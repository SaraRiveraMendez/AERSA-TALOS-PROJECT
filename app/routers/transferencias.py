"""
app/routers/transferencias.py
Endpoints para gestión de transferencias entre almacenes.

Rutas:
    POST   /transferencias/                         → Registrar transferencia manual
    GET    /transferencias/{id}                     → Consultar una transferencia
    GET    /transferencias/inventario/{id}          → Listar por inventario
    GET    /transferencias/almacen/{id}             → Listar por almacén y fechas
    PATCH  /transferencias/{id}/confirmar           → Auditor confirma transferencia
    PATCH  /transferencias/{id}/rechazar            → Auditor rechaza (era pérdida real)
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.connection import get_db
from app.db.transferencia_queries import (
    insert_transferencia,
    get_transferencia,
    list_transferencias_por_inventario,
    list_transferencias_por_almacen,
    confirmar_transferencia,
    rechazar_transferencia,
)
from app.models import (
    TransferenciaCreate,
    TransferenciaConfirm,
    TransferenciaReject,
    TransferenciaResponse,
)

router = APIRouter(prefix="/transferencias", tags=["Transferencias"])


# ── POST /transferencias/ ─────────────────────────────────────────────────────


@router.post("/", response_model=TransferenciaResponse, status_code=201)
async def crear_transferencia(
    body: TransferenciaCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Registra una transferencia de producto entre almacenes.
    El tipo (interna / entre_sucursales) se infiere automáticamente
    comparando idsucursal_origen vs idsucursal_destino.
    """
    # Calcular tipo e importe
    tipo = (
        "entre_sucursales"
        if body.idsucursal_origen != body.idsucursal_destino
        else "interna"
    )
    importe = (
        body.transferencia_cantidad * body.transferencia_costopromedio
        if body.transferencia_costopromedio is not None
        else None
    )

    params = {
        "idempresa": body.idempresa,
        "transferencia_fecha": body.transferencia_fecha,
        "idsucursal_origen": body.idsucursal_origen,
        "idalmacen_origen": body.idalmacen_origen,
        "idinventariomes_origen": body.idinventariomes_origen,
        "idsucursal_destino": body.idsucursal_destino,
        "idalmacen_destino": body.idalmacen_destino,
        "idinventariomes_destino": body.idinventariomes_destino,
        "idproducto": body.idproducto,
        "transferencia_cantidad": body.transferencia_cantidad,
        "transferencia_costopromedio": body.transferencia_costopromedio,
        "transferencia_importe": importe,
        "transferencia_tipo": tipo,
        "transferencia_origen": "manual",
        "transferencia_estatus": "confirmada",  # manual = ya confirmada
        "transferencia_observaciones": body.transferencia_observaciones,
        "idusuario_registra": body.idusuario_registra,
    }

    idtransferencia = await insert_transferencia(db, params)
    row = await get_transferencia(db, idtransferencia)

    if not row:
        raise HTTPException(
            status_code=500, detail="Error al recuperar la transferencia creada."
        )

    return _to_response(row)


# ── GET /transferencias/{id} ──────────────────────────────────────────────────


@router.get("/{idtransferencia}", response_model=TransferenciaResponse)
async def obtener_transferencia(
    idtransferencia: int,
    db: AsyncSession = Depends(get_db),
):
    row = await get_transferencia(db, idtransferencia)
    if not row:
        raise HTTPException(
            status_code=404, detail=f"Transferencia {idtransferencia} no encontrada."
        )
    return _to_response(row)


# ── GET /transferencias/inventario/{idinventariomes} ──────────────────────────


@router.get("/inventario/{idinventariomes}", response_model=list[TransferenciaResponse])
async def listar_por_inventario(
    idinventariomes: int,
    db: AsyncSession = Depends(get_db),
):
    """Todas las transferencias asociadas a un cierre de inventario."""
    rows = await list_transferencias_por_inventario(db, idinventariomes)
    return [_to_response(r) for r in rows]


# ── GET /transferencias/almacen/{idalmacen} ───────────────────────────────────


@router.get("/almacen/{idalmacen}", response_model=list[TransferenciaResponse])
async def listar_por_almacen(
    idalmacen: int,
    fecha_inicio: date = Query(default=None),
    fecha_fin: date = Query(default=None),
    estatus: Optional[str] = Query(
        default=None, description="pendiente | confirmada | rechazada"
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Transferencias de un almacén en un rango de fechas.
    Si no se especifican fechas, usa los últimos 30 días.
    """
    hoy = date.today()
    fecha_fin = fecha_fin or hoy
    fecha_inicio = fecha_inicio or (hoy - timedelta(days=30))

    rows = await list_transferencias_por_almacen(
        db, idalmacen, fecha_inicio, fecha_fin, estatus
    )
    return [_to_response(r) for r in rows]


# ── PATCH /transferencias/{id}/confirmar ─────────────────────────────────────


@router.patch("/{idtransferencia}/confirmar", response_model=TransferenciaResponse)
async def confirmar(
    idtransferencia: int,
    body: TransferenciaConfirm,
    db: AsyncSession = Depends(get_db),
):
    """
    El auditor confirma que el movimiento fue una transferencia real,
    no una pérdida. Se descuenta del faltante en el reporte.
    """
    actualizado = await confirmar_transferencia(
        db,
        idtransferencia,
        body.idusuario_confirma,
        body.transferencia_observaciones,
    )
    if not actualizado:
        raise HTTPException(
            status_code=409,
            detail="La transferencia no existe o ya fue procesada (no está pendiente).",
        )

    row = await get_transferencia(db, idtransferencia)
    return _to_response(row)


# ── PATCH /transferencias/{id}/rechazar ──────────────────────────────────────


@router.patch("/{idtransferencia}/rechazar", response_model=TransferenciaResponse)
async def rechazar(
    idtransferencia: int,
    body: TransferenciaReject,
    db: AsyncSession = Depends(get_db),
):
    """
    El auditor rechaza la transferencia: era una pérdida real.
    El faltante se mantiene en el reporte sin ajuste.
    """
    actualizado = await rechazar_transferencia(
        db,
        idtransferencia,
        body.idusuario_confirma,
        body.transferencia_observaciones,
    )
    if not actualizado:
        raise HTTPException(
            status_code=409,
            detail="La transferencia no existe o ya fue procesada (no está pendiente).",
        )

    row = await get_transferencia(db, idtransferencia)
    return _to_response(row)


# ── Helper interno ────────────────────────────────────────────────────────────


def _to_response(row: dict) -> TransferenciaResponse:
    """Convierte un dict de BD al modelo de respuesta."""
    return TransferenciaResponse(
        idtransferencia=row["idtransferencia"],
        idempresa=row["idempresa"],
        transferencia_fecha=row["transferencia_fecha"],
        idsucursal_origen=row["idsucursal_origen"],
        idalmacen_origen=row["idalmacen_origen"],
        almacen_origen_nombre=row.get("almacen_origen_nombre"),
        idinventariomes_origen=row.get("idinventariomes_origen"),
        idsucursal_destino=row["idsucursal_destino"],
        idalmacen_destino=row["idalmacen_destino"],
        almacen_destino_nombre=row.get("almacen_destino_nombre"),
        idinventariomes_destino=row.get("idinventariomes_destino"),
        idproducto=row["idproducto"],
        producto_nombre=row.get("producto_nombre"),
        transferencia_cantidad=row["transferencia_cantidad"],
        transferencia_costopromedio=row.get("transferencia_costopromedio"),
        transferencia_importe=row.get("transferencia_importe"),
        transferencia_tipo=row["transferencia_tipo"],
        transferencia_origen=row["transferencia_origen"],
        transferencia_estatus=row["transferencia_estatus"],
        transferencia_observaciones=row.get("transferencia_observaciones"),
        idusuario_registra=row.get("idusuario_registra"),
        idusuario_confirma=row.get("idusuario_confirma"),
        transferencia_createdat=row["transferencia_createdat"],
        transferencia_updatedat=row["transferencia_updatedat"],
    )


# ── POST /transferencias/detectar/{idsucursal} ───────────────────────────────


@router.post("/detectar/{idsucursal}", status_code=200)
async def detectar_transferencias(
    idsucursal: int,
    idempresa: int = Query(..., description="ID de la empresa"),
    fecha_cierre: Optional[date] = Query(
        None, description="Fecha del cierre a analizar. Default: último cierre."
    ),
    guardar: bool = Query(
        True, description="Si True, guarda las detecciones en BD como pendientes."
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Analiza el cierre más reciente de la sucursal y detecta posibles
    transferencias no registradas entre sus almacenes.

    Compara diferencias negativas (faltantes) y positivas (sobrantes)
    del mismo producto en distintos almacenes del mismo cierre.
    Si las cantidades coinciden dentro de un umbral de tolerancia (15%),
    registra una transferencia detectada con estatus 'pendiente'.
    El auditor luego confirma o rechaza cada una.
    """
    from app.services.transfer_detector import TransferDetector

    fecha_str = str(fecha_cierre) if fecha_cierre else None
    detector = TransferDetector(db)

    detectadas = await detector.analizar_sucursal(idsucursal, idempresa, fecha_str)

    guardadas = 0
    if guardar and detectadas:
        guardadas = await detector.guardar_detecciones(
            detectadas, idsucursal, idempresa, fecha_str
        )

    return {
        "idsucursal": idsucursal,
        "fecha_analizada": fecha_str or "último cierre disponible",
        "total_detectadas": len(detectadas),
        "nuevas_guardadas": guardadas,
        "transferencias": [
            {
                "producto": t.producto_nombre,
                "categoria": t.categoria_nombre,
                "almacen_origen": t.almacen_origen_nombre,
                "almacen_destino": t.almacen_destino_nombre,
                "cantidad": round(t.cantidad, 3),
                "importe": round(t.importe, 2),
                "confianza": f"{t.confianza:.0%}",
            }
            for t in detectadas
        ],
    }
