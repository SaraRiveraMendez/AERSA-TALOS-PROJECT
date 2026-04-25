"""
app/db/queries.py
Todas las queries para extraer datos del inventario mensual.

Escritas en SQL estándar ANSI para ser compatibles con MySQL y Oracle.
Evitamos deliberadamente: LIMIT/OFFSET (usar FETCH FIRST en Oracle),
    GROUP BY sin agregados, y funciones propietarias.

Compatibilidad:
    MySQL:  usa LIMIT n
    Oracle: usa FETCH FIRST n ROWS ONLY
El helper _limit() elige automáticamente según el engine configurado.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_settings

settings = get_settings()


def _limit(n: int) -> str:
    """Devuelve la cláusula LIMIT correcta según el motor."""
    if settings.is_oracle:
        return f"FETCH FIRST {n} ROWS ONLY"
    return f"LIMIT {n}"


# ── Encabezado del inventario ────────────────────────────────────────────────

QUERY_HEADER = text(
    """
    SELECT
        im.idempresa,
        im.idsucursal,
        im.idauditor,
        im.fecha                    AS inventariomes_fecha,
        im.version                  AS inventariomes_version,
        im.estatus                  AS inventariomes_estatus,
        im.created_at               AS inventariomes_createdat,
        im.updated_at               AS inventariomes_updatedat,
        im.total_importe_fisico     AS inventariomes_totalimportefisico,
        im.final_alimentos          AS inventariomes_finalalimentos,
        im.final_bebidas            AS inventariomes_finalbebidas,
        im.final_miscelaneos        AS inventariomes_finalmiscelaneos,
        im.faltantes                AS inventariomes_faltantes,
        im.sobrantes                AS inventariomes_sobrantes,
        im.total                    AS inventariomes_total,
        im.xls                      AS inventariomes_xls,
        im.pdf                      AS inventariomes_pdf,
        im.xls_inicial              AS inventariomes_xls_inicial,
        im.pdf_inicial              AS inventariomes_pdf_inicial,
        a.nombre                    AS almacen_nombre,
        a.encargado                 AS almacen_encargado
    FROM inventariomes im
    LEFT JOIN almacen a ON a.idalmacen = im.idalmacen
    WHERE im.idinventariomes = :idinventariomes
"""
)


# ── Detalle de productos ─────────────────────────────────────────────────────

QUERY_DETALLE = text(
    """
    SELECT
        imd.idinventariomesdetalle,
        imd.idinventariomes,
        p.nombre                        AS producto_nombre,
        p.baja                          AS producto_baja,
        p.rendimiento                   AS producto_rendimiento,
        p.visible                       AS producto_visible,
        c.nombre                        AS categoria_nombre,
        c.idcategoria,
        sc.idsubcategoria,
        um.nombre                       AS unidadmedida_nombre,
        imd.stock_inicial               AS inventariomesdetalle_stockinicial,
        imd.stock_teorico               AS inventariomesdetalle_stockteorico,
        imd.stock_fisico                AS inventariomesdetalle_stockfisico,
        imd.diferencia                  AS inventariomesdetalle_diferencia,
        imd.costo_promedio              AS inventariomesdetalle_costopromedio,
        imd.importe_fisico              AS inventariomesdetalle_importefisico,
        imd.dif_importe                 AS inventariomesdetalle_difimporte,
        imd.ingreso_compra              AS inventariomesdetalle_ingresocompra,
        imd.ingreso_requisicion         AS inventariomesdetalle_ingresorequisicion,
        imd.egreso_requisicion          AS inventariomesdetalle_egresorequisicion,
        imd.egreso_venta                AS inventariomesdetalle_egresoventa,
        imd.ingreso_orden_tablajeria    AS inventariomesdetalle_ingresoordentablajeria,
        imd.egreso_orden_tablajeria     AS inventariomesdetalle_egresoordentablajeria,
        imd.egreso_devolucion           AS inventariomesdetalle_egresodevolucion,
        imd.reajuste                    AS inventariomesdetalle_reajuste,
        imd.revisada                    AS inventariomesdetalle_revisada,
        imd.aclaracion                  AS inventariomesdetalle_aclaracion,
        imd.categoria_aclaracion        AS inventariomesdetalle_categoriaaclaracion
    FROM inventariomesdetalle imd
    INNER JOIN producto p         ON p.idproducto     = imd.idproducto
    INNER JOIN categoria c        ON c.idcategoria    = p.idcategoria
    LEFT  JOIN subcategoria sc    ON sc.idsubcategoria = p.idsubcategoria
    INNER JOIN unidadmedida um    ON um.idunidadmedida = p.idunidadmedida
    WHERE imd.idinventariomes = :idinventariomes
    ORDER BY c.nombre, p.nombre
"""
)


# ── Productos pendientes de validación en catálogo TALOS ─────────────────────

QUERY_PENDIENTES_VALIDACION = text(
    """
    SELECT
        pt.nombre       AS producto_nombre,
        pt.idcategoria,
        pt.idsubcategoria,
        um.nombre       AS unidadmedida_nombre,
        pt.visible      AS producto_visible
    FROM productotalos pt
    LEFT JOIN unidadmedida um ON um.idunidadmedida = pt.idunidadmedida
    WHERE pt.validado = 0
       OR pt.idproducto IS NULL
    ORDER BY pt.nombre
"""
)


# ── Helpers de consulta ──────────────────────────────────────────────────────


async def fetch_header(db: AsyncSession, idinventariomes: int) -> dict:
    """Retorna el encabezado del inventario como diccionario."""
    result = await db.execute(QUERY_HEADER, {"idinventariomes": idinventariomes})
    row = result.mappings().one_or_none()
    if row is None:
        raise ValueError(f"Inventario {idinventariomes} no encontrado.")
    return dict(row)


async def fetch_detalle(db: AsyncSession, idinventariomes: int) -> list[dict]:
    """Retorna todos los renglones de detalle como lista de diccionarios."""
    result = await db.execute(QUERY_DETALLE, {"idinventariomes": idinventariomes})
    return [dict(row) for row in result.mappings().all()]


async def fetch_pendientes_validacion(db: AsyncSession) -> list[dict]:
    """Retorna productos del catálogo TALOS sin validar."""
    result = await db.execute(QUERY_PENDIENTES_VALIDACION)
    return [dict(row) for row in result.mappings().all()]


async def fetch_inventarios_del_periodo(
    db: AsyncSession,
    fecha_inicio: str,
    fecha_fin: str,
) -> list[dict]:
    """
    Retorna todos los inventarios cerrados en un rango de fechas.
    Usado por el scheduler para generar reportes del fin de semana.
    """
    query = text(
        """
        SELECT
            im.idinventariomes,
            im.idsucursal,
            im.idauditor,
            im.fecha,
            im.estatus
        FROM inventariomes im
        WHERE im.estatus = 'cerrado'
          AND im.fecha BETWEEN :fecha_inicio AND :fecha_fin
        ORDER BY im.idsucursal, im.fecha
    """
    )
    result = await db.execute(
        query,
        {"fecha_inicio": fecha_inicio, "fecha_fin": fecha_fin},
    )
    return [dict(row) for row in result.mappings().all()]
