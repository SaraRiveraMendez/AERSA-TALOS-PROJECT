"""
app/services/chart_generator.py
Genera las 6 gráficas del reporte como imágenes PNG en base64.
Listas para incrustar directamente en el HTML con <img src="data:image/png;base64,...">

Gráficas:
    1. Pie       — Composición del inventario por categoría
    2. Barras    — Faltantes vs Sobrantes
    3. Histograma — Distribución de diferencias en importe
    4. Barras H  — Top 10 productos con mayor faltante
    5. Donut     — Revisados vs Pendientes
    6. Heatmap   — Movimientos por tipo × categoría
"""

from __future__ import annotations

import io
import base64
from typing import Any

import matplotlib

matplotlib.use("Agg")  # Sin GUI — indispensable en servidor Windows/Linux
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# ── Paleta TALOS ──────────────────────────────────────────────────────────────
AZUL = "#2563EB"
AZUL_CLARO = "#93C5FD"
ROJO = "#DC2626"
ROJO_CLARO = "#FCA5A5"
VERDE = "#16A34A"
VERDE_CLARO = "#86EFAC"
GRIS = "#6B7280"
GRIS_CLARO = "#F3F4F6"
NARANJA = "#D97706"
MORADO = "#7C3AED"

PALETA_CATS = [AZUL, VERDE, NARANJA]  # Alimentos, Bebidas, Misceláneos

# Tamaño estándar para todas las gráficas
FIG_W, FIG_H = 7, 4


def _money(x: float) -> str:
    return f"${x:,.0f}"


def _to_base64(fig: plt.Figure) -> str:
    """Convierte una figura matplotlib a string base64 PNG."""
    buf = io.BytesIO()
    fig.savefig(
        buf,
        format="png",
        bbox_inches="tight",
        dpi=120,
        facecolor="white",
        edgecolor="none",
    )
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def _base_fig(w: float = FIG_W, h: float = FIG_H) -> tuple[plt.Figure, plt.Axes]:
    fig, ax = plt.subplots(figsize=(w, h))
    fig.patch.set_facecolor("white")
    ax.set_facecolor(GRIS_CLARO)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#D1D5DB")
    ax.tick_params(colors=GRIS, labelsize=9)
    return fig, ax


# ── 1. Pie — Composición por categoría ───────────────────────────────────────


def chart_pie_categorias(data: dict) -> str:
    """
    data = {
        "labels": ["Alimentos", "Bebidas", "Misceláneos"],
        "values": [3169.95, 90618.70, 0.0]
    }
    """
    labels = data["labels"]
    values = data["values"]

    # Filtrar categorías con valor > 0
    pairs = [(l, v) for l, v in zip(labels, values) if v > 0]
    if not pairs:
        pairs = [("Sin datos", 1)]
    labels_f, values_f = zip(*pairs)
    colores = PALETA_CATS[: len(labels_f)]

    fig, ax = plt.subplots(figsize=(6, 4))
    fig.patch.set_facecolor("white")

    wedges, texts, autotexts = ax.pie(
        values_f,
        labels=None,
        colors=colores,
        autopct="%1.1f%%",
        startangle=90,
        wedgeprops={"linewidth": 1.5, "edgecolor": "white"},
        pctdistance=0.75,
    )
    for at in autotexts:
        at.set_fontsize(10)
        at.set_color("white")
        at.set_fontweight("bold")

    ax.legend(
        wedges,
        [f"{l}  ${v:,.0f}" for l, v in zip(labels_f, values_f)],
        loc="lower center",
        bbox_to_anchor=(0.5, -0.15),
        ncol=len(labels_f),
        fontsize=9,
        frameon=False,
    )
    ax.set_title(
        "Composición del inventario físico",
        fontsize=12,
        fontweight="bold",
        color="#1F2937",
        pad=12,
    )
    return _to_base64(fig)


# ── 2. Barras — Faltantes vs Sobrantes ───────────────────────────────────────


def chart_bar_faltantes_sobrantes(data: dict) -> str:
    """
    data = {"faltantes": 8784.66, "sobrantes": 12225.19}
    """
    fig, ax = _base_fig(5, 4)

    categorias = ["Faltantes", "Sobrantes"]
    valores = [data["faltantes"], data["sobrantes"]]
    colores = [ROJO, VERDE]

    bars = ax.bar(
        categorias, valores, color=colores, width=0.5, edgecolor="white", linewidth=1.5
    )

    for bar, val in zip(bars, valores):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(valores) * 0.02,
            f"${val:,.2f}",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
            color="#1F2937",
        )

    ax.set_ylabel("Importe ($)", fontsize=10, color=GRIS)
    ax.set_title(
        "Faltantes vs Sobrantes", fontsize=12, fontweight="bold", color="#1F2937"
    )
    ax.set_ylim(0, max(valores) * 1.2)
    ax.yaxis.set_major_formatter(
        matplotlib.ticker.FuncFormatter(lambda x, _: f"${x:,.0f}")
    )
    return _to_base64(fig)


# ── 3. Histograma — Distribución de diferencias en importe ───────────────────


def chart_histograma_diferencias(valores: list[float]) -> str:
    datos = [v for v in valores if v != 0]
    if not datos:
        datos = [0]

    fig, ax = _base_fig()

    n, bins, patches = ax.hist(
        datos,
        bins=min(20, max(5, int(len(datos) ** 0.5))),  # bins dinámicos
        edgecolor="white",
        linewidth=0.8,
    )

    # Colorear por signo
    for patch, left in zip(patches, bins[:-1]):
        patch.set_facecolor(ROJO_CLARO if left < 0 else AZUL)

    # 🔥 Líneas estadísticas
    mean = np.mean(datos)
    median = np.median(datos)

    ax.axvline(
        mean, color=AZUL, linestyle="--", linewidth=1.5, label=f"Media {_money(mean)}"
    )
    ax.axvline(
        median,
        color=MORADO,
        linestyle=":",
        linewidth=1.5,
        label=f"Mediana {_money(median)}",
    )
    ax.axvline(0, color=GRIS, linestyle="-", linewidth=1)

    ax.set_title(
        "Distribución de diferencias en importe", fontsize=12, fontweight="bold"
    )
    ax.set_xlabel("Importe ($)")
    ax.set_ylabel("Frecuencia")

    ax.legend(fontsize=8, frameon=False)

    return _to_base64(fig)


# ── 4. Barras horizontales — Top 10 faltantes ────────────────────────────────


def chart_top10_faltantes(data: list[dict]) -> str:
    """
    data = [{"producto_nombre": ..., "inventariomesdetalle_difimporte": -1393.92}, ...]
    Ordenado de mayor a menor faltante (más negativo primero).
    """
    if not data:
        fig, ax = _base_fig()
        ax.text(
            0.5,
            0.5,
            "Sin faltantes",
            ha="center",
            va="center",
            transform=ax.transAxes,
            fontsize=12,
            color=GRIS,
        )
        return _to_base64(fig)

    # Tomar máximo 10, ordenar para que el mayor faltante quede arriba
    items = sorted(data, key=lambda x: x["inventariomesdetalle_difimporte"])[:10]
    nombres = [x["producto_nombre"][:35] for x in items]
    valores = [abs(x["inventariomesdetalle_difimporte"]) for x in items]

    fig, ax = plt.subplots(figsize=(8, max(3, len(items) * 0.55)))
    fig.patch.set_facecolor("white")
    ax.set_facecolor(GRIS_CLARO)
    ax.spines[["top", "right"]].set_visible(False)

    bars = ax.barh(nombres, valores, color=ROJO_CLARO, edgecolor="white", linewidth=0.8)
    for bar, val in zip(bars, valores):
        ax.text(
            val + max(valores) * 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"${val:,.2f}",
            va="center",
            fontsize=8.5,
            color="#1F2937",
        )

    ax.set_xlabel("Importe faltante ($)", fontsize=10, color=GRIS)
    ax.set_title(
        "Top 10 — Mayor faltante en importe",
        fontsize=12,
        fontweight="bold",
        color="#1F2937",
    )
    ax.xaxis.set_major_formatter(
        matplotlib.ticker.FuncFormatter(lambda x, _: f"${x:,.0f}")
    )
    fig.tight_layout()
    return _to_base64(fig)


# ── 5. Donut — Revisados vs Pendientes ───────────────────────────────────────


def chart_donut_revision(data: dict) -> str:
    """data = {"revisados": 3, "pendientes": 152}"""
    revisados = data.get("revisados", 0)
    pendientes = data.get("pendientes", 0)
    total = revisados + pendientes or 1

    fig, ax = plt.subplots(figsize=(5, 4))
    fig.patch.set_facecolor("white")

    valores = [revisados, pendientes]
    colores = [VERDE, NARANJA]
    labels = [f"Revisados\n{revisados}", f"Pendientes\n{pendientes}"]

    wedges, _, autotexts = ax.pie(
        valores,
        labels=None,
        colors=colores,
        autopct="%1.0f%%",
        startangle=90,
        wedgeprops={"linewidth": 2, "edgecolor": "white", "width": 0.55},
        pctdistance=0.8,
    )
    for at in autotexts:
        at.set_fontsize(10)
        at.set_fontweight("bold")

    # Texto central
    ax.text(
        0,
        0,
        f"{total}\nproductos",
        ha="center",
        va="center",
        fontsize=11,
        fontweight="bold",
        color="#1F2937",
    )

    pct_rev = (revisados / total) * 100 if total else 0

    ax.text(
        0,
        0,
        f"{pct_rev:.0f}%\nrevisado",
        ha="center",
        va="center",
        fontsize=11,
        fontweight="bold",
    )

    ax.legend(
        wedges,
        labels,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.12),
        ncol=2,
        fontsize=9,
        frameon=False,
    )
    ax.set_title(
        "Estado de revisión", fontsize=12, fontweight="bold", color="#1F2937", pad=10
    )
    return _to_base64(fig)


# ── 6. Heatmap — Movimientos por tipo × categoría ────────────────────────────


def chart_heatmap_movimientos(data: dict) -> str:
    """
    data = {
        "categorias":  ["Alimentos", "Bebidas", "Misceláneos"],
        "movimientos": ["Ing. compra", "Eg. venta", ...],
        "matrix":      [[val, val, val], ...]
    }
    """
    categorias = data.get("categorias", [])
    movimientos = data.get("movimientos", [])
    matrix = np.array(data.get("matrix", [[0]]), dtype=float)

    if matrix.size == 0 or matrix.max() == 0:
        fig, ax = _base_fig()
        ax.text(
            0.5,
            0.5,
            "Sin movimientos",
            ha="center",
            va="center",
            transform=ax.transAxes,
            fontsize=12,
            color=GRIS,
        )
        return _to_base64(fig)

    fig, ax = plt.subplots(figsize=(7, max(3, len(movimientos) * 0.6)))
    fig.patch.set_facecolor("white")

    im = ax.imshow(matrix, cmap="Blues", aspect="auto")

    ax.set_xticks(range(len(categorias)))
    ax.set_xticklabels(categorias, fontsize=10)
    ax.set_yticks(range(len(movimientos)))
    ax.set_yticklabels(movimientos, fontsize=9)

    # Valores en cada celda
    for i in range(len(movimientos)):
        for j in range(len(categorias)):
            val = matrix[i, j]
            color = "white" if val > matrix.max() * 0.6 else "#1F2937"
            ax.text(
                j,
                i,
                f"${val:,.0f}" if val > 0 else "—",
                ha="center",
                va="center",
                fontsize=8,
                color=color,
            )

    plt.colorbar(im, ax=ax, label="Importe estimado ($)", shrink=0.8)
    ax.set_title(
        "Movimientos por tipo y categoría",
        fontsize=12,
        fontweight="bold",
        color="#1F2937",
    )
    fig.tight_layout()
    return _to_base64(fig)


# ── Entry point ───────────────────────────────────────────────────────────────


def generate_all_charts(chart_data: dict) -> dict[str, str]:
    """
    Genera las 6 gráficas y retorna un dict de base64 strings.
    Uso en el PDF builder:
        charts = generate_all_charts(processor.get_chart_data())
        # charts["pie"], charts["barras"], etc.
    """
    return {
        "pie": chart_pie_categorias(chart_data["pie_categorias"]),
        "barras": chart_bar_faltantes_sobrantes(chart_data["bar_faltantes_sobrantes"]),
        "histograma": chart_histograma_diferencias(chart_data["hist_difimporte"]),
        "top10": chart_top10_faltantes(chart_data["top10_faltantes"]),
        "donut": chart_donut_revision(chart_data["donut_revision"]),
        "heatmap": chart_heatmap_movimientos(chart_data["heatmap_movimientos"]),
    }
