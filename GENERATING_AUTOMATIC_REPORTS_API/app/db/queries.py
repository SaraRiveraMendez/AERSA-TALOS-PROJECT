"""
app/db/queries.py
Queries ajustadas a los nombres REALES de columnas de talos_tecmty.

Columnas confirmadas vía SHOW COLUMNS / SELECT real:
  - producto.producto_nombre       (no 'nombre')
  - producto.producto_baja
  - producto.producto_rendimiento
  - categoria.categoria_nombre     (no 'nombre')
  - unidadmedida.unidadmedida_nombre
  - inventariomesdetalle usa nombres completos con prefijo
  - inventariomesdetalle_aclaracion
  - inventariomesdetalle_categoria_aclaracion  (con guión bajo, confirmado)
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from GENERATING_AUTOMATIC_REPORTS_API.app.config import get_settings

settings = get_settings()


def _limit(n: int) -> str:
    """Cláusula LIMIT compatible con MySQL y Oracle."""
    if settings.is_oracle:
        return f"FETCH FIRST {n} ROWS ONLY"
    return f"LIMIT {n}"


# ── Encabezado del inventario ────────────────────────────────────────────────

QUERY_HEADER = text(
    """
    SELECT
        im.idinventariomes,
        im.idempresa,
        im.idsucursal,
        im.idalmacen,
        im.idusuario,
        im.idauditor,
        im.inventariomes_fecha,
        im.inventariomes_version,
        im.inventariomes_estatus,
        im.inventariomes_createdat,
        im.inventariomes_updatedat,
        im.inventariomes_totalimportefisico,
        im.inventariomes_finalalimentos,
        im.inventariomes_finalbebidas,
        im.inventariomes_finalmiscelaneos,
        im.inventariomes_faltantes,
        im.inventariomes_sobrantes,
        im.inventariomes_total,
        im.inventariomes_xls,
        im.inventariomes_pdf,
        im.inventariomes_xls_inicial,
        im.inventariomes_pdf_inicial,
        a.almacen_nombre,
        a.almacen_encargado
    FROM inventariomes im
    LEFT JOIN almacen a ON a.idalmacen = im.idalmacen
    WHERE im.idinventariomes = :idinventariomes
"""
)


# ── Detalle de productos ─────────────────────────────────────────────────────
# Nombres confirmados con SHOW COLUMNS y SELECT real sobre inventario 118889.

QUERY_DETALLE = text(
    """
    SELECT
        imd.idinventariomesdetalle,
        imd.idinventariomes,
        imd.idproducto,

        p.producto_nombre,
        p.producto_baja,
        p.producto_rendimiento,
        p.producto_visible,

        c.categoria_nombre,
        c.idcategoria,
        c.idcategoriapadre,

        um.unidadmedida_nombre,

        imd.inventariomesdetalle_stockinicial,
        imd.inventariomesdetalle_stockteorico,
        imd.inventariomesdetalle_explosion,
        imd.inventariomesdetalle_stockfisico,
        imd.inventariomesdetalle_totalfisico,
        imd.inventariomesdetalle_diferencia,

        imd.inventariomesdetalle_ingresocompra,
        imd.inventariomesdetalle_ingresorequisicion,
        imd.inventariomesdetalle_egresorequisicion,
        imd.inventariomesdetalle_egresoventa,
        imd.inventariomesdetalle_reajuste,
        imd.inventariomesdetalle_ingresoordentablajeria,
        imd.inventariomesdetalle_egresoordentablajeria,
        imd.inventariomesdetalle_egresodevolucion,

        imd.inventariomesdetalle_costopromedio,
        imd.inventariomesdetalle_difimporte,
        imd.inventariomesdetalle_importefisico,

        imd.inventariomesdetalle_revisada,
        imd.inventariomesdetalle_aclaracion,
        imd.inventariomesdetalle_categoria_aclaracion

    FROM inventariomesdetalle imd
    INNER JOIN producto     p  ON p.idproducto     = imd.idproducto
    INNER JOIN categoria    c  ON c.idcategoria    = p.idcategoria
    INNER JOIN unidadmedida um ON um.idunidadmedida = p.idunidadmedida
    WHERE imd.idinventariomes = :idinventariomes
    ORDER BY c.categoria_nombre, p.producto_nombre
"""
)


# ── Inventarios del período (scheduler semanal) ──────────────────────────────

QUERY_INVENTARIOS_PERIODO = text(
    """
    SELECT
        im.idinventariomes,
        im.idsucursal,
        im.idauditor,
        im.inventariomes_fecha,
        im.inventariomes_estatus,
        a.almacen_nombre
    FROM inventariomes im
    LEFT JOIN almacen a ON a.idalmacen = im.idalmacen
    WHERE im.inventariomes_estatus = 'finalizado'
      AND DATE(im.inventariomes_fecha) BETWEEN :fecha_inicio AND :fecha_fin
    ORDER BY im.idsucursal, im.inventariomes_fecha
"""
)


# ── Inventarios recientes con movimientos reales (dashboard) ─────────────────

QUERY_INVENTARIOS_RECIENTES = text(
    """
    SELECT
        im.idinventariomes,
        im.inventariomes_fecha,
        im.idsucursal,
        a.almacen_nombre,
        im.inventariomes_totalimportefisico,
        im.inventariomes_faltantes,
        im.inventariomes_sobrantes,
        im.inventariomes_estatus,
        COUNT(imd.idinventariomesdetalle) AS total_productos
    FROM inventariomes im
    JOIN almacen a ON a.idalmacen = im.idalmacen
    JOIN inventariomesdetalle imd ON imd.idinventariomes = im.idinventariomes
    WHERE im.inventariomes_totalimportefisico > 1000
      AND imd.inventariomesdetalle_stockteorico > 0
    GROUP BY
        im.idinventariomes,
        im.inventariomes_fecha,
        im.idsucursal,
        a.almacen_nombre,
        im.inventariomes_totalimportefisico,
        im.inventariomes_faltantes,
        im.inventariomes_sobrantes,
        im.inventariomes_estatus
    ORDER BY im.inventariomes_fecha DESC
"""
)


# ── Helpers ──────────────────────────────────────────────────────────────────


async def fetch_header(db: AsyncSession, idinventariomes: int) -> dict:
    result = await db.execute(QUERY_HEADER, {"idinventariomes": idinventariomes})
    row = result.mappings().one_or_none()
    if row is None:
        raise ValueError(f"Inventario {idinventariomes} no encontrado.")
    return dict(row)


async def fetch_detalle(db: AsyncSession, idinventariomes: int) -> list[dict]:
    result = await db.execute(QUERY_DETALLE, {"idinventariomes": idinventariomes})
    return [dict(row) for row in result.mappings().all()]


async def fetch_inventarios_del_periodo(
    db: AsyncSession,
    fecha_inicio: str,
    fecha_fin: str,
) -> list[dict]:
    result = await db.execute(
        QUERY_INVENTARIOS_PERIODO,
        {"fecha_inicio": fecha_inicio, "fecha_fin": fecha_fin},
    )
    return [dict(row) for row in result.mappings().all()]


async def fetch_inventarios_recientes(db: AsyncSession) -> list[dict]:
    result = await db.execute(QUERY_INVENTARIOS_RECIENTES)
    return [dict(row) for row in result.mappings().all()]
