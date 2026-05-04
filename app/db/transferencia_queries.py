"""
app/db/transferencia_queries.py
Queries para la tabla transferencia.
"""

from decimal import Decimal
from typing import Optional
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# ── INSERT ────────────────────────────────────────────────────────────────────

QUERY_INSERT_TRANSFERENCIA = text("""
    INSERT INTO transferencia (
        idempresa,
        transferencia_fecha,
        idsucursal_origen,
        idalmacen_origen,
        idinventariomes_origen,
        idsucursal_destino,
        idalmacen_destino,
        idinventariomes_destino,
        idproducto,
        transferencia_cantidad,
        transferencia_costopromedio,
        transferencia_importe,
        transferencia_tipo,
        transferencia_origen,
        transferencia_estatus,
        transferencia_observaciones,
        idusuario_registra
    ) VALUES (
        :idempresa,
        :transferencia_fecha,
        :idsucursal_origen,
        :idalmacen_origen,
        :idinventariomes_origen,
        :idsucursal_destino,
        :idalmacen_destino,
        :idinventariomes_destino,
        :idproducto,
        :transferencia_cantidad,
        :transferencia_costopromedio,
        :transferencia_importe,
        :transferencia_tipo,
        :transferencia_origen,
        :transferencia_estatus,
        :transferencia_observaciones,
        :idusuario_registra
    )
""")


# ── SELECT por ID ─────────────────────────────────────────────────────────────

QUERY_GET_TRANSFERENCIA = text("""
    SELECT
        t.*,
        p.producto_nombre,
        ao.almacen_nombre   AS almacen_origen_nombre,
        ad.almacen_nombre   AS almacen_destino_nombre
    FROM transferencia t
    LEFT JOIN producto  p  ON p.idproducto   = t.idproducto
    LEFT JOIN almacen   ao ON ao.idalmacen   = t.idalmacen_origen
    LEFT JOIN almacen   ad ON ad.idalmacen   = t.idalmacen_destino
    WHERE t.idtransferencia = :idtransferencia
""")


# ── LIST por inventario origen ────────────────────────────────────────────────

QUERY_LIST_POR_INVENTARIO = text("""
    SELECT
        t.*,
        p.producto_nombre,
        ao.almacen_nombre   AS almacen_origen_nombre,
        ad.almacen_nombre   AS almacen_destino_nombre
    FROM transferencia t
    LEFT JOIN producto  p  ON p.idproducto   = t.idproducto
    LEFT JOIN almacen   ao ON ao.idalmacen   = t.idalmacen_origen
    LEFT JOIN almacen   ad ON ad.idalmacen   = t.idalmacen_destino
    WHERE t.idinventariomes_origen = :idinventariomes
       OR t.idinventariomes_destino = :idinventariomes
    ORDER BY t.transferencia_fecha DESC, t.idtransferencia DESC
""")


# ── LIST por almacén y rango de fechas ────────────────────────────────────────

QUERY_LIST_POR_ALMACEN = text("""
    SELECT
        t.*,
        p.producto_nombre,
        ao.almacen_nombre   AS almacen_origen_nombre,
        ad.almacen_nombre   AS almacen_destino_nombre
    FROM transferencia t
    LEFT JOIN producto  p  ON p.idproducto   = t.idproducto
    LEFT JOIN almacen   ao ON ao.idalmacen   = t.idalmacen_origen
    LEFT JOIN almacen   ad ON ad.idalmacen   = t.idalmacen_destino
    WHERE (t.idalmacen_origen = :idalmacen OR t.idalmacen_destino = :idalmacen)
      AND t.transferencia_fecha BETWEEN :fecha_inicio AND :fecha_fin
      AND (:estatus IS NULL OR t.transferencia_estatus = :estatus)
    ORDER BY t.transferencia_fecha DESC, t.idtransferencia DESC
""")


# ── CONFIRMAR ─────────────────────────────────────────────────────────────────

QUERY_CONFIRMAR = text("""
    UPDATE transferencia
    SET transferencia_estatus       = 'confirmada',
        idusuario_confirma          = :idusuario_confirma,
        transferencia_observaciones = COALESCE(:observaciones, transferencia_observaciones)
    WHERE idtransferencia = :idtransferencia
      AND transferencia_estatus = 'pendiente'
""")


# ── RECHAZAR ──────────────────────────────────────────────────────────────────

QUERY_RECHAZAR = text("""
    UPDATE transferencia
    SET transferencia_estatus       = 'rechazada',
        idusuario_confirma          = :idusuario_confirma,
        transferencia_observaciones = COALESCE(:observaciones, transferencia_observaciones)
    WHERE idtransferencia = :idtransferencia
      AND transferencia_estatus = 'pendiente'
""")


# ── Helpers ───────────────────────────────────────────────────────────────────


async def insert_transferencia(db: AsyncSession, params: dict) -> int:
    """Inserta una transferencia y retorna el ID generado."""
    result = await db.execute(QUERY_INSERT_TRANSFERENCIA, params)
    await db.flush()
    return result.lastrowid


async def get_transferencia(db: AsyncSession, idtransferencia: int) -> Optional[dict]:
    result = await db.execute(
        QUERY_GET_TRANSFERENCIA, {"idtransferencia": idtransferencia}
    )
    row = result.mappings().one_or_none()
    return dict(row) if row else None


async def list_transferencias_por_inventario(
    db: AsyncSession,
    idinventariomes: int,
) -> list[dict]:
    result = await db.execute(
        QUERY_LIST_POR_INVENTARIO, {"idinventariomes": idinventariomes}
    )
    return [dict(r) for r in result.mappings().all()]


async def list_transferencias_por_almacen(
    db: AsyncSession,
    idalmacen: int,
    fecha_inicio: date,
    fecha_fin: date,
    estatus: Optional[str] = None,
) -> list[dict]:
    result = await db.execute(
        QUERY_LIST_POR_ALMACEN,
        {
            "idalmacen": idalmacen,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "estatus": estatus,
        },
    )
    return [dict(r) for r in result.mappings().all()]


async def confirmar_transferencia(
    db: AsyncSession,
    idtransferencia: int,
    idusuario_confirma: Optional[int],
    observaciones: Optional[str],
) -> bool:
    """Retorna True si se actualizó (estaba pendiente), False si no."""
    result = await db.execute(
        QUERY_CONFIRMAR,
        {
            "idtransferencia": idtransferencia,
            "idusuario_confirma": idusuario_confirma,
            "observaciones": observaciones,
        },
    )
    return result.rowcount > 0


async def rechazar_transferencia(
    db: AsyncSession,
    idtransferencia: int,
    idusuario_confirma: Optional[int],
    observaciones: Optional[str],
) -> bool:
    result = await db.execute(
        QUERY_RECHAZAR,
        {
            "idtransferencia": idtransferencia,
            "idusuario_confirma": idusuario_confirma,
            "observaciones": observaciones,
        },
    )
    return result.rowcount > 0


# ── Transferencias confirmadas para el reporte ────────────────────────────────

QUERY_TRANSFERENCIAS_REPORTE = text("""
    SELECT
        t.idtransferencia,
        t.idalmacen_origen,
        t.idalmacen_destino,
        t.idproducto,
        t.transferencia_cantidad,
        t.transferencia_costopromedio,
        t.transferencia_importe,
        t.transferencia_tipo,
        t.transferencia_origen,
        t.transferencia_observaciones,
        p.producto_nombre,
        c.categoria_nombre,
        ao.almacen_nombre   AS almacen_origen_nombre,
        ad.almacen_nombre   AS almacen_destino_nombre
    FROM transferencia t
    JOIN producto   p  ON p.idproducto  = t.idproducto
    JOIN categoria  c  ON c.idcategoria = p.idcategoria
    JOIN almacen    ao ON ao.idalmacen  = t.idalmacen_origen
    JOIN almacen    ad ON ad.idalmacen  = t.idalmacen_destino
    WHERE t.transferencia_estatus = 'confirmada'
      AND (
          t.idinventariomes_origen  = :idinventariomes
          OR t.idinventariomes_destino = :idinventariomes
      )
    ORDER BY t.transferencia_importe DESC
""")


async def fetch_transferencias_reporte(
    db: AsyncSession,
    idinventariomes: int,
) -> list[dict]:
    """Transferencias confirmadas asociadas a un inventario. Para el reporte."""
    result = await db.execute(
        QUERY_TRANSFERENCIAS_REPORTE, {"idinventariomes": idinventariomes}
    )
    return [dict(r) for r in result.mappings().all()]


# ── Transferencias confirmadas por inventario (para el reporte) ───────────────

QUERY_CONFIRMADAS_POR_INVENTARIO = text("""
    SELECT
        t.idtransferencia,
        t.idalmacen_origen,
        t.idalmacen_destino,
        ao.almacen_nombre           AS almacen_origen_nombre,
        ad.almacen_nombre           AS almacen_destino_nombre,
        t.idsucursal_origen,
        t.idsucursal_destino,
        t.idproducto,
        p.producto_nombre,
        c.categoria_nombre,
        t.transferencia_cantidad,
        t.transferencia_costopromedio,
        t.transferencia_importe,
        t.transferencia_tipo,
        t.transferencia_origen,
        t.transferencia_observaciones
    FROM transferencia t
    LEFT JOIN almacen  ao ON ao.idalmacen  = t.idalmacen_origen
    LEFT JOIN almacen  ad ON ad.idalmacen  = t.idalmacen_destino
    LEFT JOIN producto p  ON p.idproducto  = t.idproducto
    LEFT JOIN categoria c ON c.idcategoria = p.idcategoria
    WHERE t.transferencia_estatus = 'confirmada'
      AND (
          t.idinventariomes_origen  = :idinventariomes
          OR t.idinventariomes_destino = :idinventariomes
      )
    ORDER BY t.transferencia_importe DESC
""")


async def fetch_transferencias_confirmadas(
    db: AsyncSession,
    idinventariomes: int,
) -> list[dict]:
    """Transferencias confirmadas asociadas a un cierre. Usada por el reporte."""
    result = await db.execute(
        QUERY_CONFIRMADAS_POR_INVENTARIO, {"idinventariomes": idinventariomes}
    )
    return [dict(r) for r in result.mappings().all()]
