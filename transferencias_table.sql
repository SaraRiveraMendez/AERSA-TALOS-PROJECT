CREATE TABLE transferencia (
    -- ── Identificador ──────────────────────────────────────────────────────
    idtransferencia             INT             NOT NULL AUTO_INCREMENT,

    -- ── Contexto ───────────────────────────────────────────────────────────
    idempresa                   INT             NOT NULL,
    transferencia_fecha         DATE            NOT NULL,

    -- ── Origen ─────────────────────────────────────────────────────────────
    idsucursal_origen           INT             NOT NULL,
    idalmacen_origen            INT             NOT NULL,
    idinventariomes_origen      INT             NULL,      -- cierre de semana donde se detectó la salida

    -- ── Destino ────────────────────────────────────────────────────────────
    idsucursal_destino          INT             NOT NULL,
    idalmacen_destino           INT             NOT NULL,
    idinventariomes_destino     INT             NULL,      -- cierre de semana donde se detectó la entrada

    -- ── Producto ───────────────────────────────────────────────────────────
    idproducto                  INT             NOT NULL,
    transferencia_cantidad      DECIMAL(15,6)   NOT NULL,
    transferencia_costopromedio DECIMAL(15,2)   NULL,      -- costo al momento de la transferencia
    transferencia_importe       DECIMAL(15,2)   NULL,      -- cantidad × costo

    -- ── Clasificación ──────────────────────────────────────────────────────
    transferencia_tipo          ENUM(
                                    'interna',      -- misma sucursal, distinto almacén
                                    'entre_sucursales' -- distinta sucursal
                                )               NOT NULL DEFAULT 'interna',

    transferencia_origen        ENUM(
                                    'manual',       -- registrada por un usuario
                                    'detectada'     -- sugerida automáticamente por el sistema
                                )               NOT NULL DEFAULT 'manual',

    transferencia_estatus       ENUM(
                                    'pendiente',    -- detectada, sin confirmar
                                    'confirmada',   -- validada por el auditor
                                    'rechazada'     -- descartada (era pérdida real)
                                )               NOT NULL DEFAULT 'pendiente',

    -- ── Trazabilidad ───────────────────────────────────────────────────────
    idusuario_registra          INT             NULL,      -- usuario que la capturó
    idusuario_confirma          INT             NULL,      -- auditor que la validó
    transferencia_observaciones TEXT            NULL,
    transferencia_createdat     DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    transferencia_updatedat     DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
                                                ON UPDATE CURRENT_TIMESTAMP,

    -- ── Constraints ────────────────────────────────────────────────────────
    PRIMARY KEY (idtransferencia),

    CONSTRAINT fk_transf_almacen_origen
        FOREIGN KEY (idalmacen_origen)
        REFERENCES almacen(idalmacen),

    CONSTRAINT fk_transf_almacen_destino
        FOREIGN KEY (idalmacen_destino)
        REFERENCES almacen(idalmacen),

    CONSTRAINT fk_transf_producto
        FOREIGN KEY (idproducto)
        REFERENCES producto(idproducto),

    CONSTRAINT fk_transf_inventario_origen
        FOREIGN KEY (idinventariomes_origen)
        REFERENCES inventariomes(idinventariomes),

    CONSTRAINT fk_transf_inventario_destino
        FOREIGN KEY (idinventariomes_destino)
        REFERENCES inventariomes(idinventariomes),

    CONSTRAINT chk_almacenes_distintos
        CHECK (idalmacen_origen != idalmacen_destino),

    CONSTRAINT chk_cantidad_positiva
        CHECK (transferencia_cantidad > 0),

    -- ── Índices ────────────────────────────────────────────────────────────
    INDEX idx_transf_fecha          (transferencia_fecha),
    INDEX idx_transf_producto       (idproducto),
    INDEX idx_transf_origen         (idalmacen_origen),
    INDEX idx_transf_destino        (idalmacen_destino),
    INDEX idx_transf_estatus        (transferencia_estatus),
    INDEX idx_transf_inventario_org (idinventariomes_origen),
    INDEX idx_transf_inventario_dst (idinventariomes_destino)

) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Transferencias de productos entre almacenes — registradas manualmente o detectadas automáticamente por el sistema';

-- transferencia_origen distingue si la transferencia la capturó un humano o la detectó el sistema automáticamente — esto es clave para el flujo de trabajo: las detectadas quedan en pendiente hasta que el auditor las confirma o rechaza.
-- transferencia_estatus = 'rechazada' es igual de importante que 'confirmada' — cuando el auditor rechaza una sugerencia del sistema, eso confirma que sí era una pérdida real, y el reporte la trata como tal.
-- Los campos idinventariomes_origen e idinventariomes_destino permiten ligar cada transferencia directamente a los cierres de semana específicos donde se detectó el movimiento, lo que facilita el análisis retrospectivo.