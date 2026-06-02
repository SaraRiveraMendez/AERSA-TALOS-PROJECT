"""
app/db/queries.py
Queries usando vistas limpias + JOIN a tabla raw para fechas.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_settings

settings = get_settings()


QUERY_HEADER = text("""
    SELECT
        im.idinventariomes,
        im.idempresa,
        im.idsucursal,
        im.idalmacen,
        im.idauditor,
        im.inventariomes_fecha,
        im.inventariomes_version,
        im.inventariomes_estatus,
        im.inventariomes_totalimportefisico,
        im.inventariomes_finalalimentos,
        im.inventariomes_finalbebidas,
        im.inventariomes_finalmiscelaneos,
        im.inventariomes_faltantes,
        im.inventariomes_sobrantes,
        im.inventariomes_total,
        raw.inventariomes_createdat,
        raw.inventariomes_updatedat,
        raw.inventariomes_xls,
        raw.inventariomes_pdf,
        raw.inventariomes_xls_inicial,
        raw.inventariomes_pdf_inicial,
        raw.idusuario,
        a.almacen_nombre,
        a.almacen_encargado
    FROM vw_inventariomes_limpio im
    LEFT JOIN almacen      a   ON a.idalmacen       = im.idalmacen
    LEFT JOIN inventariomes raw ON raw.idinventariomes = im.idinventariomes
    WHERE im.idinventariomes = :idinventariomes
""")


QUERY_DETALLE = text("""
    SELECT
        imd.idinventariomesdetalle,
        imd.idinventariomes,
        imd.idproducto,
        p.producto_nombre,
        p.producto_baja,
        p.producto_rendimiento,
        p.producto_oculto,
        p.producto_tipo,
        c.categoria_nombre,
        c.idcategoria,
        c.idcategoriapadre,
        um.unidadmedida_nombre,
        imd.stockinicial                     AS inventariomesdetalle_stockinicial,
        imd.stockteorico_bd                  AS inventariomesdetalle_stockteorico,
        imd.stockfisico                      AS inventariomesdetalle_stockfisico,
        imd.diferencia_bd                    AS inventariomesdetalle_diferencia,
        imd.ingresocompra                    AS inventariomesdetalle_ingresocompra,
        imd.ingresorequisicion               AS inventariomesdetalle_ingresorequisicion,
        imd.egresorequisicion                AS inventariomesdetalle_egresorequisicion,
        imd.egresoventa                      AS inventariomesdetalle_egresoventa,
        imd.reajuste                         AS inventariomesdetalle_reajuste,
        imd.ingresoordentablajeria           AS inventariomesdetalle_ingresoordentablajeria,
        imd.egresoordentablajeria            AS inventariomesdetalle_egresoordentablajeria,
        imd.egresodevolucion                 AS inventariomesdetalle_egresodevolucion,
        imd.costopromedio                    AS inventariomesdetalle_costopromedio,
        imd.difimporte_bd                    AS inventariomesdetalle_difimporte,
        imd.importefisico_bd                 AS inventariomesdetalle_importefisico,
        raw.inventariomesdetalle_revisada,
        raw.inventariomesdetalle_aclaracion,
        raw.inventariomesdetalle_categoria_aclaracion,
        imd.flag_outlier,
        imd.flag_costopromedio_cero,
        imd.flag_stockteorico_no_cuadra,
        imd.flag_fisico_cero_teorico_positivo
    FROM vw_inventariomesdetalle_limpio imd
    INNER JOIN vw_producto_limpio  p  ON p.idproducto     = imd.idproducto
    INNER JOIN vw_categoria_limpia c  ON c.idcategoria    = p.idcategoria
    INNER JOIN unidadmedida        um ON um.idunidadmedida = p.idunidadmedida
    LEFT JOIN inventariomesdetalle raw ON raw.idinventariomesdetalle = imd.idinventariomesdetalle
    WHERE imd.idinventariomes = :idinventariomes
      AND imd.flag_outlier = 0
      AND imd.flag_costopromedio_cero = 0
    ORDER BY c.categoria_nombre, p.producto_nombre
""")


QUERY_INVENTARIOS_PERIODO = text("""
    SELECT
        im.idinventariomes,
        im.idsucursal,
        im.idauditor,
        im.inventariomes_fecha,
        im.inventariomes_estatus,
        a.almacen_nombre
    FROM vw_inventariomes_limpio im
    LEFT JOIN almacen a ON a.idalmacen = im.idalmacen
    WHERE DATE(im.inventariomes_fecha) BETWEEN :fecha_inicio AND :fecha_fin
    ORDER BY im.idsucursal, im.inventariomes_fecha
""")


QUERY_INVENTARIOS_RECIENTES = text("""
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
    FROM vw_inventariomes_limpio im
    JOIN almacen a ON a.idalmacen = im.idalmacen
    JOIN vw_inventariomesdetalle_limpio imd
        ON imd.idinventariomes = im.idinventariomes
        AND imd.flag_outlier = 0
    WHERE im.inventariomes_totalimportefisico > 1000
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
""")


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
