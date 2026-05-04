"""
app/services/data_processor.py
Corazón analítico del reporte.

Recibe los datos crudos de la BD y produce el contexto completo
que Jinja2 necesita para renderizar el template del reporte.

Calcula:
    - KPIs e indicadores del encabezado
    - Estadísticos descriptivos (media, mediana, desv. std, IQR)
    - Outliers por z-score
    - Desglose por categoría (alimentos / bebidas / misceláneos)
    - Análisis de movimientos y reajustes
    - Rankings top-10
    - Alertas clasificadas por prioridad
    - Porcentajes y tasas de revisión/aclaración
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

# ── Constantes ────────────────────────────────────────────────────────────────

UMBRAL_ALTO_PCT: float = 150.0  # % sobre la media para alertas de prioridad alta
ZSCORE_UMBRAL: float = 2.0  # Desviaciones estándar para detectar outliers
CAT_ALIMENTOS: str = "Alimentos"
CAT_BEBIDAS: str = "Bebidas"
CAT_MISC: str = "Misceláneos"

TIPOS_MOVIMIENTO = [
    ("ingresocompra", "inventariomesdetalle_ingresocompra"),
    ("ingresorequisicion", "inventariomesdetalle_ingresorequisicion"),
    ("egresorequisicion", "inventariomesdetalle_egresorequisicion"),
    ("egresoventa", "inventariomesdetalle_egresoventa"),
    ("ingresoordentablajeria", "inventariomesdetalle_ingresoordentablajeria"),
    ("egresoordentablajeria", "inventariomesdetalle_egresoordentablajeria"),
    ("egresodevolucion", "inventariomesdetalle_egresodevolucion"),
    ("reajuste", "inventariomesdetalle_reajuste"),
]


# ── Helpers ───────────────────────────────────────────────────────────────────


def _fmt(value: Any, decimals: int = 2) -> str:
    """Formatea un número para mostrar en el reporte."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "0.00"
    return f"{float(value):,.{decimals}f}"


def _pct(numerator: float, denominator: float, decimals: int = 2) -> str:
    """Calcula un porcentaje de forma segura (evita división entre cero)."""
    if not denominator:
        return "0.00"
    return f"{(numerator / denominator) * 100:.{decimals}f}"


def _safe_stat(series: pd.Series, stat: str) -> float:
    """Extrae un estadístico de una serie, retornando 0 si está vacía."""
    if series.empty:
        return 0.0
    ops = {
        "mean": series.mean,
        "median": series.median,
        "std": lambda: series.std(ddof=1),
        "min": series.min,
        "max": series.max,
        "sum": series.sum,
        "iqr": lambda: series.quantile(0.75) - series.quantile(0.25),
    }
    try:
        result = ops[stat]()
        return float(result) if not pd.isna(result) else 0.0
    except Exception:
        return 0.0


# ── Procesador principal ──────────────────────────────────────────────────────


class DataProcessor:
    """
    Transforma datos crudos de la BD en el contexto completo del reporte.

    Uso:
        processor = DataProcessor(header, detalle, pendientes_validacion)
        contexto  = processor.build_context()
        # → dict con todos los {{placeholders}} del template resueltos
    """

    def __init__(
        self,
        header: dict,
        detalle: list[dict],
        transferencias: list[dict] | None = None,
        pendientes_validacion: list[dict] | None = None,
    ) -> None:
        self.header = header
        self.transferencias = transferencias or []
        self.pendientes = pendientes_validacion or []

        self.df = self._build_dataframe(detalle)

    # ── Constructor del DataFrame ─────────────────────────────────────────────

    def _build_dataframe(self, detalle: list[dict]) -> pd.DataFrame:
        """Construye y tipifica el DataFrame de detalle."""
        if not detalle:
            return pd.DataFrame()

        df = pd.DataFrame(detalle)

        numeric_cols = [
            "inventariomesdetalle_stockinicial",
            "inventariomesdetalle_stockteorico",
            "inventariomesdetalle_stockfisico",
            "inventariomesdetalle_diferencia",
            "inventariomesdetalle_costopromedio",
            "inventariomesdetalle_importefisico",
            "inventariomesdetalle_difimporte",
            "inventariomesdetalle_ingresocompra",
            "inventariomesdetalle_ingresorequisicion",
            "inventariomesdetalle_egresorequisicion",
            "inventariomesdetalle_egresoventa",
            "inventariomesdetalle_ingresoordentablajeria",
            "inventariomesdetalle_egresoordentablajeria",
            "inventariomesdetalle_egresodevolucion",
            "inventariomesdetalle_reajuste",
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

        # Columna auxiliar para clasificar diferencias
        df["_tiene_faltante"] = df["inventariomesdetalle_diferencia"] < 0
        df["_tiene_sobrante"] = df["inventariomesdetalle_diferencia"] > 0
        df["_exacto"] = df["inventariomesdetalle_diferencia"] == 0

        return df

    # ── Build context (entry point) ───────────────────────────────────────────

    def build_context(self) -> dict:
        """
        Punto de entrada principal.
        Retorna el diccionario completo de contexto para Jinja2.
        """
        if self.df.empty:
            return {**self.header, "_error": "Sin registros de detalle."}

        ctx: dict = {}
        ctx.update(self._ctx_header())
        ctx.update(self._ctx_kpis())
        ctx.update(self._ctx_stats_diferencias())
        ctx.update(self._ctx_stats_por_categoria())
        ctx.update(self._ctx_outliers())
        ctx.update(self._ctx_alertas())
        ctx.update(self._ctx_movimientos())
        ctx.update(self._ctx_reajustes())
        ctx.update(self._ctx_rankings())
        ctx.update(self._ctx_transferencias())
        ctx.update(self._ctx_aclaraciones())
        ctx.update(self._ctx_validacion_catalogo())
        ctx.update(self._ctx_conclusiones(ctx))

        # DataFrame de detalle por categoría (para las tablas del reporte)
        ctx["detalle_alimentos"] = self._detalle_categoria(CAT_ALIMENTOS)
        ctx["detalle_bebidas"] = self._detalle_categoria(CAT_BEBIDAS)
        ctx["detalle_miscelaneos"] = self._detalle_categoria(CAT_MISC)

        return ctx

    # ── Secciones del contexto ────────────────────────────────────────────────

    def _ctx_header(self) -> dict:
        """Datos del encabezado directamente del inventario."""
        h = self.header
        return {
            "idempresa": h.get("idempresa", ""),
            "idsucursal": h.get("idsucursal", ""),
            "idauditor": h.get("idauditor", ""),
            "almacen_nombre": h.get("almacen_nombre", ""),
            "almacen_encargado": h.get("almacen_encargado", ""),
            "inventariomes_fecha": str(h.get("inventariomes_fecha", "")),
            "inventariomes_version": h.get("inventariomes_version", ""),
            "inventariomes_estatus": h.get("inventariomes_estatus", ""),
            "inventariomes_createdat": str(h.get("inventariomes_createdat", "")),
            "inventariomes_updatedat": str(h.get("inventariomes_updatedat", "")),
            "inventariomes_totalimportefisico": _fmt(
                h.get("inventariomes_totalimportefisico", 0)
            ),
            "inventariomes_finalalimentos": _fmt(
                h.get("inventariomes_finalalimentos", 0)
            ),
            "inventariomes_finalbebidas": _fmt(h.get("inventariomes_finalbebidas", 0)),
            "inventariomes_finalmiscelaneos": _fmt(
                h.get("inventariomes_finalmiscelaneos", 0)
            ),
            "inventariomes_faltantes": _fmt(h.get("inventariomes_faltantes", 0)),
            "inventariomes_sobrantes": _fmt(h.get("inventariomes_sobrantes", 0)),
            "inventariomes_total": _fmt(h.get("inventariomes_total", 0)),
            "inventariomes_xls": h.get("inventariomes_xls", ""),
            "inventariomes_pdf": h.get("inventariomes_pdf", ""),
            "inventariomes_xls_inicial": h.get("inventariomes_xls_inicial", ""),
            "inventariomes_pdf_inicial": h.get("inventariomes_pdf_inicial", ""),
        }

    def _ctx_kpis(self) -> dict:
        """KPIs calculados a partir del detalle."""
        df = self.df
        total_fisico = float(
            self.header.get("inventariomes_totalimportefisico", 0) or 0
        )
        faltantes = float(self.header.get("inventariomes_faltantes", 0) or 0)
        sobrantes = float(self.header.get("inventariomes_sobrantes", 0) or 0)

        total_productos = len(df)
        revisados = int(
            df.get("inventariomesdetalle_revisada", pd.Series(dtype=int)).sum()
        )

        return {
            "faltantes_pct": _pct(faltantes, total_fisico),
            "sobrantes_pct": _pct(sobrantes, total_fisico),
            "count_faltantes": int(df["_tiene_faltante"].sum()),
            "count_sobrantes": int(df["_tiene_sobrante"].sum()),
            "count_exactos": int(df["_exacto"].sum()),
            "count_sin_revisar": total_productos - revisados,
            "tasa_revision": _pct(revisados, total_productos),
            "umbral_alto": _fmt(UMBRAL_ALTO_PCT, 0),
        }

    def _ctx_stats_diferencias(self) -> dict:
        """Estadísticos descriptivos de diferencias en unidades e importe."""
        df = self.df
        diff_u = df["inventariomesdetalle_diferencia"]
        diff_imp = df["inventariomesdetalle_difimporte"]

        return {
            # Unidades
            "diff_media": _fmt(_safe_stat(diff_u, "mean")),
            "diff_mediana": _fmt(_safe_stat(diff_u, "median")),
            "diff_desviacion": _fmt(_safe_stat(diff_u, "std")),
            "diff_min": _fmt(_safe_stat(diff_u, "min")),
            "diff_max": _fmt(_safe_stat(diff_u, "max")),
            "diff_iqr": _fmt(_safe_stat(diff_u, "iqr")),
            # Importe
            "difimporte_media": _fmt(_safe_stat(diff_imp, "mean")),
            "difimporte_mediana": _fmt(_safe_stat(diff_imp, "median")),
            "difimporte_desviacion": _fmt(_safe_stat(diff_imp, "std")),
            "difimporte_min": _fmt(_safe_stat(diff_imp, "min")),
            "difimporte_max": _fmt(_safe_stat(diff_imp, "max")),
            "difimporte_suma_abs": _fmt(_safe_stat(diff_imp.abs(), "sum")),
        }

    def _ctx_transferencias(self) -> dict:
        if not self.transferencias:
            return {
                "count_transferencias": 0,
                "importe_transferencias": "0.00",
                "faltante_bruto": "0.00",
                "pct_faltante_explicado": "0.00",
                "perdida_real": "0.00",
                "transferencias_internas": [],
                "transferencias_entre_suc": [],
            }

        df = self.df

        # Faltante original
        faltante_bruto = float(self.header.get("inventariomes_faltantes", 0) or 0)

        # Total transferencias
        importe_transferencias = sum(
            float(t.get("transferencia_importe") or 0) for t in self.transferencias
        )

        # Clasificación
        internas = []
        entre_suc = []

        for t in self.transferencias:
            if t.get("transferencia_tipo") == "interna":
                internas.append(t)
            else:
                entre_suc.append(t)

        # KPIs
        perdida_real = faltante_bruto - importe_transferencias
        pct_explicado = (
            (importe_transferencias / abs(faltante_bruto)) * 100
            if faltante_bruto
            else 0
        )

        return {
            "count_transferencias": len(self.transferencias),
            "importe_transferencias": _fmt(importe_transferencias),
            "faltante_bruto": _fmt(faltante_bruto),
            "pct_faltante_explicado": _fmt(pct_explicado),
            "perdida_real": _fmt(perdida_real),
            "transferencias_internas": internas,
            "transferencias_entre_suc": entre_suc,
        }

    def _ctx_stats_por_categoria(self) -> dict:
        """Estadísticos descriptivos agrupados por categoría."""
        df = self.df
        ctx = {}
        categorias = {
            "ali": CAT_ALIMENTOS,
            "beb": CAT_BEBIDAS,
            "misc": CAT_MISC,
        }
        for prefix, cat_nombre in categorias.items():
            sub = df[df["categoria_nombre"] == cat_nombre]
            diff = (
                sub["inventariomesdetalle_diferencia"]
                if not sub.empty
                else pd.Series(dtype=float)
            )
            imp = (
                sub["inventariomesdetalle_difimporte"]
                if not sub.empty
                else pd.Series(dtype=float)
            )
            ctx.update(
                {
                    f"{prefix}_n": len(sub),
                    f"{prefix}_media_diff": _fmt(_safe_stat(diff, "mean")),
                    f"{prefix}_desv": _fmt(_safe_stat(diff, "std")),
                    f"{prefix}_total_diff": _fmt(_safe_stat(imp, "sum")),
                }
            )
        return ctx

    def _ctx_outliers(self) -> dict:
        """Detecta outliers por z-score sobre dif_importe."""
        df = self.df.copy()
        imp = df["inventariomesdetalle_difimporte"]
        mean, std = imp.mean(), imp.std(ddof=1)

        if std == 0 or pd.isna(std):
            df["_zscore"] = 0.0
        else:
            df["_zscore"] = ((imp - mean) / std).abs()

        outliers = (
            df[df["_zscore"] >= ZSCORE_UMBRAL]
            .sort_values("_zscore", ascending=False)
            .copy()
        )
        outliers["_zscore_fmt"] = outliers["_zscore"].apply(lambda z: f"{z:.2f}")

        return {
            "outliers": outliers.to_dict("records"),  # lista para Jinja2
        }

    def _ctx_alertas(self) -> dict:
        """
        Clasifica alertas en tres niveles:
            alta:  faltantes cuyo importe supera UMBRAL_ALTO_PCT % sobre la media
            media: sobrantes significativos
            baja:  registros sin revisar
            baja_baja: productos dados de baja con movimientos activos
        """
        df = self.df
        imp = df["inventariomesdetalle_difimporte"]
        mean_imp = imp.mean()
        umbral_valor = mean_imp * (UMBRAL_ALTO_PCT / 100)

        # Prioridad alta: faltantes con importe < -umbral_valor
        alta = df[
            (df["inventariomesdetalle_diferencia"] < 0)
            & (df["inventariomesdetalle_difimporte"] < -abs(umbral_valor))
        ].sort_values("inventariomesdetalle_difimporte")

        # Prioridad media: sobrantes (diferencia > 0)
        media = df[df["inventariomesdetalle_diferencia"] > 0].sort_values(
            "inventariomesdetalle_difimporte", ascending=False
        )

        # Prioridad baja: sin revisar
        baja = df[
            df.get("inventariomesdetalle_revisada", pd.Series(0, index=df.index)) == 0
        ]

        # Productos dados de baja con movimientos
        cols_movimiento = [
            "inventariomesdetalle_ingresocompra",
            "inventariomesdetalle_egresoventa",
            "inventariomesdetalle_reajuste",
        ]
        if "producto_baja" in df.columns:
            baja_con_mov = df[
                (df["producto_baja"] == 1) & (df[cols_movimiento].abs().sum(axis=1) > 0)
            ]
        else:
            baja_con_mov = pd.DataFrame()

        return {
            "alertas_alta": alta.to_dict("records"),
            "alertas_media": media.to_dict("records"),
            "alertas_baja": baja.to_dict("records"),
            "alertas_baja_con_mov": baja_con_mov.to_dict("records"),
        }

    def _ctx_movimientos(self) -> dict:
        """Consolida totales de movimientos por tipo."""
        df = self.df
        ctx = {}
        for tipo, col in TIPOS_MOVIMIENTO:
            serie = df[col] if col in df.columns else pd.Series(dtype=float)
            ctx[f"total_{tipo}_u"] = _fmt(_safe_stat(serie.abs(), "sum"), 0)
            ctx[f"total_{tipo}_imp"] = _fmt(
                _safe_stat(
                    serie.abs()
                    * df.get(
                        "inventariomesdetalle_costopromedio",
                        pd.Series(0, index=df.index),
                    ),
                    "sum",
                )
            )
        return ctx

    def _ctx_reajustes(self) -> dict:
        """Analiza el volumen y naturaleza de los reajustes."""
        df = self.df
        col = "inventariomesdetalle_reajuste"
        if col not in df.columns:
            return {
                "count_reajustes": 0,
                "reajuste_positivo_sum": "0.00",
                "reajuste_negativo_sum": "0.00",
                "producto_max_reajuste": "N/A",
                "pct_reajustados": "0.00",
            }

        con_reajuste = df[df[col] != 0]
        positivos = df[df[col] > 0][col]
        negativos = df[df[col] < 0][col]

        max_row = df.loc[df[col].abs().idxmax()] if not df.empty else None

        return {
            "count_reajustes": len(con_reajuste),
            "reajuste_positivo_sum": _fmt(_safe_stat(positivos, "sum")),
            "reajuste_negativo_sum": _fmt(_safe_stat(negativos, "sum")),
            "producto_max_reajuste": (
                max_row["producto_nombre"] if max_row is not None else "N/A"
            ),
            "pct_reajustados": _pct(len(con_reajuste), len(df)),
        }

    def _ctx_rankings(self) -> dict:
        """Top 10 para cada ranking del reporte."""
        df = self.df

        # Top 10 mayor faltante en importe
        top_faltantes = (
            df[df["inventariomesdetalle_diferencia"] < 0]
            .nsmallest(10, "inventariomesdetalle_difimporte")
            .copy()
        )
        total_faltantes = df["inventariomesdetalle_difimporte"].clip(upper=0).sum()
        top_faltantes["pct_sobre_faltantes"] = top_faltantes[
            "inventariomesdetalle_difimporte"
        ].apply(lambda x: _pct(x, total_faltantes) if total_faltantes else "0.00")

        # Top 10 mayor valor de inventario físico
        top_valor = df.nlargest(10, "inventariomesdetalle_importefisico").copy()

        # Top 10 mayor rotación (egresos por venta)
        top_rotacion = df.nlargest(10, "inventariomesdetalle_egresoventa").copy()
        top_rotacion["egreso_importe_estimado"] = (
            top_rotacion["inventariomesdetalle_egresoventa"]
            * top_rotacion["inventariomesdetalle_costopromedio"]
        ).apply(_fmt)

        # Porcentaje del top10 sobre el total de faltantes
        pct_top10 = (
            _pct(
                top_faltantes["inventariomesdetalle_difimporte"].sum(),
                total_faltantes,
            )
            if total_faltantes
            else "0.00"
        )

        return {
            "top_faltantes": top_faltantes.to_dict("records"),
            "top_valor": top_valor.to_dict("records"),
            "top_rotacion": top_rotacion.to_dict("records"),
            "pct_top10_faltantes": pct_top10,
        }

    def _ctx_aclaraciones(self) -> dict:
        """Analiza el estado de las aclaraciones registradas."""
        df = self.df
        col_ac = "inventariomesdetalle_aclaracion"
        col_dif = "inventariomesdetalle_diferencia"

        tiene_dif = df[col_dif] != 0
        tiene_acl = (
            df[col_ac].notna() & (df[col_ac] != "")
            if col_ac in df.columns
            else pd.Series(False, index=df.index)
        )
        con_acl_y_dif = tiene_dif & tiene_acl

        aclaraciones = df[tiene_acl].to_dict("records") if col_ac in df.columns else []

        return {
            "aclaraciones": aclaraciones,
            "count_aclaraciones": int(tiene_acl.sum()),
            "pct_aclaradas": _pct(int(con_acl_y_dif.sum()), int(tiene_dif.sum())),
        }

    def _ctx_validacion_catalogo(self) -> dict:
        """Productos pendientes de validación en catálogo TALOS."""
        return {
            "pendientes_validacion": self.pendientes,
            "count_pendientes_validacion": len(self.pendientes),
        }

    def _ctx_conclusiones(self, ctx: dict) -> dict:
        """
        Genera textos de conclusión automáticos basados en los KPIs calculados.
        Estos textos se insertan en la Sección XII del reporte.
        """
        tasa_rev = float(ctx.get("tasa_revision", 0))
        tasa_acl = float(ctx.get("pct_aclaradas", 0))
        pct_raj = float(ctx.get("pct_reajustados", 0))
        pct_top10 = float(ctx.get("pct_top10_faltantes", 0))
        total_prod = len(self.df)
        exactos = int(self.df["_exacto"].sum())
        tasa_exact = (exactos / total_prod * 100) if total_prod else 0

        def nivel(val: float, bajo: float, alto: float) -> str:
            if val >= alto:
                return "alto"
            if val >= bajo:
                return "aceptable"
            return "bajo"

        return {
            "tasa_exactitud": f"{tasa_exact:.1f}",
            "conclusion_exactitud": (
                "El nivel de exactitud es satisfactorio."
                if tasa_exact >= 80
                else "Se recomienda reforzar el proceso de conteo físico."
            ),
            "conclusion_concentracion": (
                "Los faltantes están concentrados en pocos productos — revisar esos SKU prioritariamente."
                if pct_top10 >= 70
                else "Los faltantes están distribuidos — puede indicar un problema sistémico."
            ),
            "conclusion_revision": (
                "La cobertura de revisión es adecuada."
                if tasa_rev >= 90
                else f"Solo el {tasa_rev:.1f}% fue revisado. Se recomienda completar la revisión antes del cierre."
            ),
            "conclusion_reajustes": (
                "El volumen de reajustes es normal."
                if pct_raj <= 15
                else f"El {pct_raj:.1f}% de productos tuvo reajuste — revisar los procesos de captura."
            ),
            "conclusion_aclaraciones": (
                "La mayoría de las diferencias cuenta con aclaración registrada."
                if tasa_acl >= 70
                else "El bajo porcentaje de aclaraciones requiere seguimiento del encargado."
            ),
        }

    # ── Detalle por categoría ─────────────────────────────────────────────────

    def _detalle_categoria(self, categoria: str) -> list[dict]:
        """Retorna los registros de una categoría formateados para la tabla."""
        sub = self.df[self.df["categoria_nombre"] == categoria].copy()
        if sub.empty:
            return []

        # Formatear columnas monetarias
        money_cols = [
            "inventariomesdetalle_costopromedio",
            "inventariomesdetalle_importefisico",
            "inventariomesdetalle_difimporte",
        ]
        for col in money_cols:
            if col in sub.columns:
                sub[col] = sub[col].apply(_fmt)

        return sub.to_dict("records")

    # ── Datos para gráficas ───────────────────────────────────────────────────

    def get_chart_data(self) -> dict:
        """
        Extrae datos listos para pasarle al ChartGenerator.
        Separado del contexto principal para mantener el generador de
        gráficas desacoplado del procesador de datos.
        """
        df = self.df
        h = self.header

        return {
            # Pie de categorías
            "pie_categorias": {
                "labels": [CAT_ALIMENTOS, CAT_BEBIDAS, CAT_MISC],
                "values": [
                    float(h.get("inventariomes_finalalimentos", 0) or 0),
                    float(h.get("inventariomes_finalbebidas", 0) or 0),
                    float(h.get("inventariomes_finalmiscelaneos", 0) or 0),
                ],
            },
            # Barras faltantes vs sobrantes
            "bar_faltantes_sobrantes": {
                "faltantes": abs(float(h.get("inventariomes_faltantes", 0) or 0)),
                "sobrantes": float(h.get("inventariomes_sobrantes", 0) or 0),
            },
            # Histograma de diferencias en importe
            "hist_difimporte": df["inventariomesdetalle_difimporte"].dropna().tolist(),
            # Top 10 faltantes (bar horizontal)
            "top10_faltantes": (
                df[df["inventariomesdetalle_diferencia"] < 0]
                .nsmallest(10, "inventariomesdetalle_difimporte")[
                    ["producto_nombre", "inventariomesdetalle_difimporte"]
                ]
                .to_dict("records")
            ),
            # Donut revisados vs pendientes
            "donut_revision": {
                "revisados": int(
                    df.get(
                        "inventariomesdetalle_revisada", pd.Series(0, index=df.index)
                    ).sum()
                ),
                "pendientes": int(
                    (
                        df.get(
                            "inventariomesdetalle_revisada",
                            pd.Series(0, index=df.index),
                        )
                        == 0
                    ).sum()
                ),
            },
            # Heatmap tipo_movimiento × categoría
            "heatmap_movimientos": self._build_heatmap_data(),
        }

    def _build_heatmap_data(self) -> dict:
        """Construye la matriz para el heatmap de movimientos × categoría."""
        df = self.df
        categorias = [CAT_ALIMENTOS, CAT_BEBIDAS, CAT_MISC]
        movimientos = [
            ("Ing. compra", "inventariomesdetalle_ingresocompra"),
            ("Eg. venta", "inventariomesdetalle_egresoventa"),
            ("Ing. req.", "inventariomesdetalle_ingresorequisicion"),
            ("Eg. req.", "inventariomesdetalle_egresorequisicion"),
            ("Tablajería", "inventariomesdetalle_ingresoordentablajeria"),
            ("Devolución", "inventariomesdetalle_egresodevolucion"),
            ("Reajuste", "inventariomesdetalle_reajuste"),
        ]
        costo_col = "inventariomesdetalle_costopromedio"

        matrix = []
        for mov_label, mov_col in movimientos:
            row = {"tipo": mov_label, "valores": {}}
            for cat in categorias:
                sub = df[df["categoria_nombre"] == cat]
                if sub.empty or mov_col not in sub.columns:
                    row["valores"][cat] = 0.0
                else:
                    importe = (
                        sub[mov_col].abs()
                        * sub.get(costo_col, pd.Series(1, index=sub.index))
                    ).sum()
                    row["valores"][cat] = round(float(importe), 2)
            matrix.append(row)

        return {
            "categorias": categorias,
            "movimientos": [r["tipo"] for r in matrix],
            "matrix": [list(r["valores"].values()) for r in matrix],
        }
