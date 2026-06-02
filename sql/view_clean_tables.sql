CREATE OR REPLACE VIEW vw_producto_limpio AS
SELECT
    idproducto,
    idempresa,
    idunidadmedida,
    idcategoria,
    idsubcategoria,
    idproductotalos,
    producto_nombre,
    producto_tipo,
    producto_rendimiento,
    producto_ultimocosto,
    producto_costo,
    producto_iva,
    producto_ieps,
    producto_precio,
    producto_oculto,
    producto_baja
FROM producto
WHERE producto_baja = 0
  AND producto_oculto = 0;

CREATE OR REPLACE VIEW vw_inventariomes_limpio AS
SELECT
    im.idinventariomes,
    im.idempresa,
    im.idsucursal,
    im.idalmacen,
    im.idauditor,
    im.inventariomes_fecha,
    im.inventariomes_estatus,
    im.inventariomes_revisada,
    im.inventariomes_finalalimentos,
    im.inventariomes_finalbebidas,
    im.inventariomes_finalmiscelaneos,
    im.inventariomes_faltantes,
    im.inventariomes_sobrantes,
    im.inventariomes_total,
    im.inventariomes_totalimportefisico,
    im.inventariomes_version
FROM inventariomes im
JOIN almacen a ON a.idalmacen = im.idalmacen
WHERE im.inventariomes_estatus IN ('finalizado', 'aplicado', 'terminado')
  AND a.almacen_estatus = 1;

CREATE OR REPLACE VIEW vw_inventariomesdetalle_limpio AS
SELECT
    idinventariomesdetalle,
    idinventariomes,
    idproducto,

    -- Stocks
    IFNULL(inventariomesdetalle_stockinicial, 0)           AS stockinicial,
    IFNULL(inventariomesdetalle_stockteorico, 0)           AS stockteorico_bd,
    IFNULL(inventariomesdetalle_explosion, 0)              AS explosion,
    IFNULL(inventariomesdetalle_stockfisico, 0)            AS stockfisico,
    IFNULL(inventariomesdetalle_totalfisico, 0)            AS totalfisico_bd,
    IFNULL(inventariomesdetalle_diferencia, 0)             AS diferencia_bd,

    -- Movimientos
    IFNULL(inventariomesdetalle_ingresocompra, 0)          AS ingresocompra,
    IFNULL(inventariomesdetalle_ingresorequisicion, 0)     AS ingresorequisicion,
    IFNULL(inventariomesdetalle_egresorequisicion, 0)      AS egresorequisicion,
    IFNULL(inventariomesdetalle_egresoventa, 0)            AS egresoventa,
    IFNULL(inventariomesdetalle_reajuste, 0)               AS reajuste,
    IFNULL(inventariomesdetalle_ingresoordentablajeria, 0) AS ingresoordentablajeria,
    IFNULL(inventariomesdetalle_egresoordentablajeria, 0)  AS egresoordentablajeria,
    IFNULL(inventariomesdetalle_egresodevolucion, 0)       AS egresodevolucion,

    -- Importes
    IFNULL(inventariomesdetalle_costopromedio, 0)          AS costopromedio,
    IFNULL(inventariomesdetalle_difimporte, 0)             AS difimporte_bd,
    IFNULL(inventariomesdetalle_importefisico, 0)          AS importefisico_bd,

    -- Flags
    CASE
        WHEN ABS(
            IFNULL(inventariomesdetalle_stockteorico, 0) - (
                  IFNULL(inventariomesdetalle_stockinicial, 0)
                + IFNULL(inventariomesdetalle_ingresocompra, 0)
                + IFNULL(inventariomesdetalle_ingresorequisicion, 0)
                + IFNULL(inventariomesdetalle_ingresoordentablajeria, 0)
                - IFNULL(inventariomesdetalle_egresoventa, 0)
                - IFNULL(inventariomesdetalle_egresorequisicion, 0)
                - IFNULL(inventariomesdetalle_egresoordentablajeria, 0)
                - IFNULL(inventariomesdetalle_egresodevolucion, 0)
                + IFNULL(inventariomesdetalle_reajuste, 0)
            )
        ) > 0.01 THEN 1 ELSE 0
    END AS flag_stockteorico_no_cuadra,

    CASE
        WHEN ABS(IFNULL(inventariomesdetalle_stockteorico, 0)) > 10000
          OR ABS(IFNULL(inventariomesdetalle_diferencia, 0)) > 10000
          OR ABS(IFNULL(inventariomesdetalle_reajuste, 0)) > 10000
        THEN 1 ELSE 0
    END AS flag_outlier,

    CASE
        WHEN IFNULL(inventariomesdetalle_costopromedio, 0) = 0
        THEN 1 ELSE 0
    END AS flag_costopromedio_cero,

    CASE
        WHEN IFNULL(inventariomesdetalle_stockfisico, 0) = 0
         AND IFNULL(inventariomesdetalle_stockteorico, 0) > 0
        THEN 1 ELSE 0
    END AS flag_fisico_cero_teorico_positivo

FROM inventariomesdetalle
WHERE idinventariomes IN (
    SELECT im.idinventariomes
    FROM inventariomes im
    JOIN almacen a ON a.idalmacen = im.idalmacen
    WHERE im.inventariomes_estatus IN ('finalizado', 'aplicado', 'terminado')
      AND a.almacen_estatus = 1
);

CREATE OR REPLACE VIEW vw_categoria_limpia AS
SELECT
    idcategoria,
    categoria_nombre,
    idcategoriapadre,
    categoria_almacenable,
    categoria_visiblecierre,
    idcategoriagrupo
FROM categoria;