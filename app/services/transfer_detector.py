"""
app/services/transfer_detector.py
Detecta transferencias no registradas entre almacenes de una misma sucursal
(o entre sucursales) comparando cierres de inventario consecutivos.

Lógica:
    Para cada par de cierres consecutivos de la misma sucursal:
    1. Busca productos con diferencia negativa en almacén A
    2. Busca el mismo producto con diferencia positiva en almacén B
       en el mismo cierre semanal
    3. Si las cantidades coinciden dentro de un umbral de tolerancia,
       registra una transferencia detectada con estatus 'pendiente'

Sincronía confirmada: todos los almacenes de una sucursal cierran
el mismo día → comparamos directamente por fecha de cierre.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.transferencia_queries import insert_transferencia

# ── Configuración ─────────────────────────────────────────────────────────────

# Tolerancia para considerar que dos cantidades "coinciden"
# Ej: 0.15 = hasta 15% de diferencia entre lo que salió de A y entró a B
TOLERANCIA_CANTIDAD: float = 0.15

# Diferencia mínima en unidades para considerar que vale la pena alertar
# Evita ruido de microdifferencias decimales
DIFERENCIA_MINIMA: float = 0.01

# Importe mínimo de la transferencia detectada para incluirla
# Evita alertas de productos casi sin valor
IMPORTE_MINIMO: float = 5.0


# ── Queries ───────────────────────────────────────────────────────────────────

# Obtiene todos los cierres de una sucursal en una fecha específica
# con sus diferencias por producto
QUERY_DIFERENCIAS_POR_FECHA = text("""
    SELECT
        im.idinventariomes,
        im.idalmacen,
        a.almacen_nombre,
        imd.idproducto,
        p.producto_nombre,
        p.idcategoria,
        c.categoria_nombre,
        imd.inventariomesdetalle_diferencia     AS diferencia,
        imd.inventariomesdetalle_costopromedio  AS costopromedio,
        imd.inventariomesdetalle_difimporte     AS difimporte,
        imd.inventariomesdetalle_stockfisico    AS stockfisico
    FROM inventariomes im
    JOIN almacen              a   ON a.idalmacen    = im.idalmacen
    JOIN inventariomesdetalle imd ON imd.idinventariomes = im.idinventariomes
    JOIN producto             p   ON p.idproducto   = imd.idproducto
    JOIN categoria            c   ON c.idcategoria  = p.idcategoria
    WHERE im.idsucursal = :idsucursal
      AND DATE(im.inventariomes_fecha) = :fecha
      AND im.inventariomes_estatus = 'finalizado'
      AND ABS(imd.inventariomesdetalle_diferencia) > :diferencia_minima
    ORDER BY imd.idproducto, im.idalmacen
""")

# Obtiene las dos fechas de cierre más recientes de una sucursal
QUERY_CIERRES_RECIENTES = text("""
    SELECT DISTINCT DATE(inventariomes_fecha) AS fecha
    FROM inventariomes
    WHERE idsucursal = :idsucursal
      AND inventariomes_estatus = 'finalizado'
    ORDER BY fecha DESC
    LIMIT :n
""")

# Verifica si ya existe una transferencia detectada para ese par
QUERY_EXISTE_DETECCION = text("""
    SELECT COUNT(*) AS cnt
    FROM transferencia
    WHERE idproducto          = :idproducto
      AND idalmacen_origen    = :idalmacen_origen
      AND idalmacen_destino   = :idalmacen_destino
      AND idinventariomes_origen = :idinventariomes_origen
      AND transferencia_origen = 'detectada'
""")


# ── Dataclasses ───────────────────────────────────────────────────────────────


@dataclass
class DiferenciaProducto:
    idinventariomes: int
    idalmacen: int
    almacen_nombre: str
    idproducto: int
    producto_nombre: str
    categoria_nombre: str
    diferencia: float  # negativo = faltante, positivo = sobrante
    costopromedio: float
    difimporte: float


@dataclass
class TransferenciaDetectada:
    idproducto: int
    producto_nombre: str
    categoria_nombre: str
    idalmacen_origen: int
    almacen_origen_nombre: str
    idinventariomes_origen: int
    idalmacen_destino: int
    almacen_destino_nombre: str
    idinventariomes_destino: int
    cantidad: float
    costopromedio: float
    importe: float
    confianza: float  # 0.0–1.0: qué tan bien coinciden las cantidades


# ── Detector principal ────────────────────────────────────────────────────────


class TransferDetector:
    """
    Analiza los cierres de una sucursal y detecta transferencias
    no registradas entre sus almacenes.

    Uso:
        detector = TransferDetector(db)
        detectadas = await detector.analizar_sucursal(idsucursal, idempresa)
        guardadas  = await detector.guardar_detecciones(detectadas, idsucursal, idempresa)
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def analizar_sucursal(
        self,
        idsucursal: int,
        idempresa: int,
        fecha_cierre: Optional[str] = None,
    ) -> list[TransferenciaDetectada]:
        """
        Analiza el cierre más reciente de la sucursal (o la fecha indicada).
        Retorna la lista de transferencias detectadas, sin guardarlas aún.
        """
        # Obtener la fecha a analizar
        if fecha_cierre:
            fecha = fecha_cierre
        else:
            fecha = await self._ultima_fecha_cierre(idsucursal)
            if not fecha:
                return []

        # Cargar todas las diferencias de esa fecha
        diferencias = await self._cargar_diferencias(idsucursal, str(fecha))
        if not diferencias:
            return []

        # Separar faltantes y sobrantes
        faltantes: dict[int, list[DiferenciaProducto]] = {}
        sobrantes: dict[int, list[DiferenciaProducto]] = {}

        for d in diferencias:
            if d.diferencia < -DIFERENCIA_MINIMA:
                faltantes.setdefault(d.idproducto, []).append(d)
            elif d.diferencia > DIFERENCIA_MINIMA:
                sobrantes.setdefault(d.idproducto, []).append(d)

        # Cruzar: mismo producto con faltante en A y sobrante en B
        detectadas: list[TransferenciaDetectada] = []

        for idproducto, lista_faltantes in faltantes.items():
            if idproducto not in sobrantes:
                continue  # No hay contrapartida — pérdida real

            lista_sobrantes = sobrantes[idproducto]

            for f in lista_faltantes:
                for s in lista_sobrantes:
                    if f.idalmacen == s.idalmacen:
                        continue  # Mismo almacén — no aplica

                    cantidad_faltante = abs(f.diferencia)
                    cantidad_sobrante = s.diferencia

                    # Calcular qué tan bien coinciden las cantidades
                    confianza = self._calcular_confianza(
                        cantidad_faltante, cantidad_sobrante
                    )
                    if confianza < (1 - TOLERANCIA_CANTIDAD):
                        continue  # Diferencia demasiado grande — no es transferencia

                    # Importe mínimo para reducir ruido
                    importe = cantidad_faltante * f.costopromedio
                    if importe < IMPORTE_MINIMO:
                        continue

                    detectadas.append(
                        TransferenciaDetectada(
                            idproducto=idproducto,
                            producto_nombre=f.producto_nombre,
                            categoria_nombre=f.categoria_nombre,
                            idalmacen_origen=f.idalmacen,
                            almacen_origen_nombre=f.almacen_nombre,
                            idinventariomes_origen=f.idinventariomes,
                            idalmacen_destino=s.idalmacen,
                            almacen_destino_nombre=s.almacen_nombre,
                            idinventariomes_destino=s.idinventariomes,
                            cantidad=cantidad_faltante,
                            costopromedio=f.costopromedio,
                            importe=importe,
                            confianza=confianza,
                        )
                    )

        # Ordenar por importe descendente (las más importantes primero)
        detectadas.sort(key=lambda x: x.importe, reverse=True)
        return detectadas

    async def guardar_detecciones(
        self,
        detectadas: list[TransferenciaDetectada],
        idsucursal: int,
        idempresa: int,
        fecha_cierre: Optional[str] = None,
    ) -> int:
        """
        Guarda las transferencias detectadas en la BD como 'pendiente'.
        Omite las que ya existen para evitar duplicados.
        Retorna el número de transferencias nuevas guardadas.
        """
        if not detectadas:
            return 0

        fecha = fecha_cierre or await self._ultima_fecha_cierre(idsucursal)
        guardadas = 0

        for t in detectadas:
            # Verificar si ya existe esta detección
            existe = await self._existe_deteccion(
                t.idproducto,
                t.idalmacen_origen,
                t.idalmacen_destino,
                t.idinventariomes_origen,
            )
            if existe:
                continue

            # Determinar tipo
            # Para detectadas siempre empieza como 'interna' —
            # si el auditor la edita y cambia sucursal, se actualiza
            tipo = "interna"

            params = {
                "idempresa": idempresa,
                "transferencia_fecha": fecha,
                "idsucursal_origen": idsucursal,
                "idalmacen_origen": t.idalmacen_origen,
                "idinventariomes_origen": t.idinventariomes_origen,
                "idsucursal_destino": idsucursal,
                "idalmacen_destino": t.idalmacen_destino,
                "idinventariomes_destino": t.idinventariomes_destino,
                "idproducto": t.idproducto,
                "transferencia_cantidad": Decimal(str(round(t.cantidad, 6))),
                "transferencia_costopromedio": Decimal(str(round(t.costopromedio, 2))),
                "transferencia_importe": Decimal(str(round(t.importe, 2))),
                "transferencia_tipo": tipo,
                "transferencia_origen": "detectada",
                "transferencia_estatus": "pendiente",
                "transferencia_observaciones": (
                    f"Detección automática — confianza {t.confianza:.0%}. "
                    f"Faltante en {t.almacen_origen_nombre}, "
                    f"sobrante en {t.almacen_destino_nombre}."
                ),
                "idusuario_registra": None,
            }

            await insert_transferencia(self.db, params)
            guardadas += 1

        return guardadas

    # ── Helpers privados ──────────────────────────────────────────────────────

    async def _ultima_fecha_cierre(self, idsucursal: int) -> Optional[str]:
        result = await self.db.execute(
            QUERY_CIERRES_RECIENTES, {"idsucursal": idsucursal, "n": 1}
        )
        row = result.mappings().one_or_none()
        return str(row["fecha"]) if row else None

    async def _cargar_diferencias(
        self,
        idsucursal: int,
        fecha: str,
    ) -> list[DiferenciaProducto]:
        result = await self.db.execute(
            QUERY_DIFERENCIAS_POR_FECHA,
            {
                "idsucursal": idsucursal,
                "fecha": fecha,
                "diferencia_minima": DIFERENCIA_MINIMA,
            },
        )
        rows = result.mappings().all()
        return [
            DiferenciaProducto(
                idinventariomes=row["idinventariomes"],
                idalmacen=row["idalmacen"],
                almacen_nombre=row["almacen_nombre"],
                idproducto=row["idproducto"],
                producto_nombre=row["producto_nombre"],
                categoria_nombre=row["categoria_nombre"],
                diferencia=float(row["diferencia"] or 0),
                costopromedio=float(row["costopromedio"] or 0),
                difimporte=float(row["difimporte"] or 0),
            )
            for row in rows
        ]

    async def _existe_deteccion(
        self,
        idproducto: int,
        idalmacen_origen: int,
        idalmacen_destino: int,
        idinventariomes_origen: int,
    ) -> bool:
        result = await self.db.execute(
            QUERY_EXISTE_DETECCION,
            {
                "idproducto": idproducto,
                "idalmacen_origen": idalmacen_origen,
                "idalmacen_destino": idalmacen_destino,
                "idinventariomes_origen": idinventariomes_origen,
            },
        )
        row = result.mappings().one()
        return row["cnt"] > 0

    @staticmethod
    def _calcular_confianza(cantidad_a: float, cantidad_b: float) -> float:
        """
        Calcula qué tan bien coinciden dos cantidades.
        1.0 = coincidencia perfecta, 0.0 = no coinciden.
        Usa la proporción del menor sobre el mayor.
        """
        if cantidad_a <= 0 or cantidad_b <= 0:
            return 0.0
        menor = min(cantidad_a, cantidad_b)
        mayor = max(cantidad_a, cantidad_b)
        return menor / mayor
