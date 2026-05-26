"""
app/services/chart_generator.py
Genera las 6 gráficas del reporte como PNG base64.
Versión mejorada: tamaños más grandes, colores más vivos, tipografía consistente.
"""

from __future__ import annotations
import io, base64
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.patches as mpatches
import numpy as np

# ── Paleta ────────────────────────────────────────────────────────────────────
AZUL = "#2563EB"
TEAL = "#0891B2"
VERDE = "#16A34A"
ROJO = "#DC2626"
NARANJA = "#D97706"
MORADO = "#7C3AED"
GRIS = "#64748B"
GRIS_L = "#F1F5F9"
BLANCO = "#FFFFFF"

PALETA = [AZUL, VERDE, NARANJA, TEAL, MORADO, ROJO]

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "grid.color": "#E2E8F0",
        "grid.linewidth": 0.7,
        "figure.facecolor": BLANCO,
        "axes.facecolor": BLANCO,
    }
)


def _b64(fig: plt.Figure) -> str:
    buf = io.BytesIO()
    fig.savefig(
        buf,
        format="png",
        bbox_inches="tight",
        dpi=130,
        facecolor=BLANCO,
        edgecolor="none",
    )
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()


def _money(x, _):
    if abs(x) >= 1000:
        return f"${x/1000:.0f}k"
    return f"${x:.0f}"


# ── 1. Pie — Composición por categoría ───────────────────────────────────────
def chart_pie_categorias(data: dict) -> str:
    labels = data["labels"]
    values = data["values"]
    pairs = [(l, v) for l, v in zip(labels, values) if v > 0]
    if not pairs:
        pairs = [("Sin datos", 1)]
    labs, vals = zip(*pairs)
    cols = PALETA[: len(labs)]

    fig, ax = plt.subplots(figsize=(6, 4.5))
    wedges, _, autotexts = ax.pie(
        vals,
        colors=cols,
        autopct="%1.1f%%",
        startangle=90,
        wedgeprops={"linewidth": 2, "edgecolor": BLANCO},
        pctdistance=0.72,
    )
    for at in autotexts:
        at.set_fontsize(11)
        at.set_color(BLANCO)
        at.set_fontweight("bold")

    ax.legend(
        wedges,
        [f"{l}  ${v:,.0f}" for l, v in zip(labs, vals)],
        loc="lower center",
        bbox_to_anchor=(0.5, -0.08),
        ncol=len(labs),
        fontsize=9,
        frameon=False,
    )
    ax.set_title(
        "Composición del inventario físico",
        fontsize=13,
        fontweight="bold",
        color="#1E293B",
        pad=14,
    )
    fig.tight_layout()
    return _b64(fig)


# ── 2. Barras — Faltantes vs Sobrantes ───────────────────────────────────────
def chart_bar_faltantes_sobrantes(data: dict) -> str:
    cats = ["Faltantes", "Sobrantes"]
    vals = [data["faltantes"], data["sobrantes"]]
    cols = [ROJO, VERDE]

    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    bars = ax.bar(
        cats, vals, color=cols, width=0.5, edgecolor=BLANCO, linewidth=1.5, zorder=3
    )
    for bar, val in zip(bars, vals):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(vals) * 0.02,
            f"${val:,.2f}",
            ha="center",
            va="bottom",
            fontsize=11,
            fontweight="bold",
            color="#1E293B",
        )

    ax.set_ylabel("Importe ($)", fontsize=10, color=GRIS)
    ax.set_title(
        "Faltantes vs Sobrantes", fontsize=13, fontweight="bold", color="#1E293B"
    )
    ax.set_ylim(0, max(vals) * 1.22)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(_money))
    ax.spines["left"].set_color("#E2E8F0")
    ax.spines["bottom"].set_color("#E2E8F0")
    fig.tight_layout()
    return _b64(fig)


# ── 3. Histograma — Distribución de diferencias ───────────────────────────────
def chart_histograma_diferencias(valores: list[float]) -> str:
    datos = [v for v in valores if v != 0]
    if not datos:
        datos = [0]

    fig, ax = plt.subplots(figsize=(7, 4.5))
    n, bins, patches = ax.hist(
        datos, bins=15, color=AZUL, edgecolor=BLANCO, linewidth=0.8, zorder=3
    )
    for patch, left in zip(patches, bins[:-1]):
        if left < 0:
            patch.set_facecolor(ROJO)
            patch.set_alpha(0.8)

    ax.axvline(0, color=GRIS, linewidth=1.5, linestyle="--", alpha=0.7)
    ax.set_xlabel("Importe de diferencia ($)", fontsize=10, color=GRIS)
    ax.set_ylabel("Número de productos", fontsize=10, color=GRIS)
    ax.set_title(
        "Distribución de diferencias en importe",
        fontsize=13,
        fontweight="bold",
        color="#1E293B",
    )

    leyenda = [
        mpatches.Patch(color=ROJO, label="Faltantes"),
        mpatches.Patch(color=AZUL, label="Sobrantes"),
    ]
    ax.legend(handles=leyenda, fontsize=9, frameon=False)
    fig.tight_layout()
    return _b64(fig)


# ── 4. Barras horizontales — Top 10 faltantes ────────────────────────────────
def chart_top10_faltantes(data: list[dict]) -> str:
    if not data:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(
            0.5,
            0.5,
            "Sin faltantes",
            ha="center",
            va="center",
            transform=ax.transAxes,
            fontsize=13,
            color=GRIS,
        )
        return _b64(fig)

    items = sorted(data, key=lambda x: x["inventariomesdetalle_difimporte"])[:10]
    nombres = [x["producto_nombre"][:40] for x in items]
    valores = [abs(x["inventariomesdetalle_difimporte"]) for x in items]

    fig, ax = plt.subplots(figsize=(9, max(3.5, len(items) * 0.6)))
    bars = ax.barh(
        nombres,
        valores,
        color=ROJO,
        alpha=0.85,
        edgecolor=BLANCO,
        linewidth=0.8,
        zorder=3,
    )
    for bar, val in zip(bars, valores):
        ax.text(
            val + max(valores) * 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"${val:,.2f}",
            va="center",
            fontsize=9,
            color="#1E293B",
        )

    ax.set_xlabel("Importe faltante ($)", fontsize=10, color=GRIS)
    ax.set_title(
        "Top 10 — Mayor faltante en importe",
        fontsize=13,
        fontweight="bold",
        color="#1E293B",
    )
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(_money))
    ax.invert_yaxis()
    fig.tight_layout()
    return _b64(fig)


# ── 5. Donut — Revisados vs Pendientes ───────────────────────────────────────
def chart_donut_revision(data: dict) -> str:
    revisados = data.get("revisados", 0)
    pendientes = data.get("pendientes", 0)
    total = revisados + pendientes or 1

    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    vals = [revisados, pendientes]
    cols = [VERDE, NARANJA]
    labs = [f"Revisados\n{revisados}", f"Pendientes\n{pendientes}"]

    wedges, _, autotexts = ax.pie(
        vals,
        colors=cols,
        autopct="%1.0f%%",
        startangle=90,
        wedgeprops={"linewidth": 2.5, "edgecolor": BLANCO, "width": 0.55},
        pctdistance=0.8,
    )
    for at in autotexts:
        at.set_fontsize(11)
        at.set_fontweight("bold")

    ax.text(
        0,
        0,
        f"{total}\nproductos",
        ha="center",
        va="center",
        fontsize=12,
        fontweight="bold",
        color="#1E293B",
    )
    ax.legend(
        wedges,
        labs,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.1),
        ncol=2,
        fontsize=9,
        frameon=False,
    )
    ax.set_title(
        "Estado de revisión", fontsize=13, fontweight="bold", color="#1E293B", pad=12
    )
    fig.tight_layout()
    return _b64(fig)


# ── 6. Heatmap — Movimientos por tipo × categoría ────────────────────────────
def chart_heatmap_movimientos(data: dict) -> str:
    cats = data.get("categorias", [])
    movs = data.get("movimientos", [])
    matrix = np.array(data.get("matrix", [[0]]), dtype=float)

    if matrix.size == 0 or matrix.max() == 0:
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.text(
            0.5,
            0.5,
            "Sin movimientos registrados",
            ha="center",
            va="center",
            transform=ax.transAxes,
            fontsize=12,
            color=GRIS,
        )
        return _b64(fig)

    fig, ax = plt.subplots(figsize=(8, max(3.5, len(movs) * 0.65)))
    im = ax.imshow(matrix, cmap="Blues", aspect="auto", vmin=0)

    ax.set_xticks(range(len(cats)))
    ax.set_xticklabels(cats, fontsize=10)
    ax.set_yticks(range(len(movs)))
    ax.set_yticklabels(movs, fontsize=9)

    for i in range(len(movs)):
        for j in range(len(cats)):
            val = matrix[i, j]
            color = BLANCO if val > matrix.max() * 0.55 else "#1E293B"
            txt = f"${val:,.0f}" if val > 0 else "—"
            ax.text(j, i, txt, ha="center", va="center", fontsize=8.5, color=color)

    plt.colorbar(im, ax=ax, label="Importe ($)", shrink=0.8)
    ax.set_title(
        "Movimientos por tipo y categoría",
        fontsize=13,
        fontweight="bold",
        color="#1E293B",
    )
    fig.tight_layout()
    return _b64(fig)


# ── Entry point ───────────────────────────────────────────────────────────────
def generate_all_charts(chart_data: dict) -> dict[str, str]:
    return {
        "pie": chart_pie_categorias(chart_data["pie_categorias"]),
        "barras": chart_bar_faltantes_sobrantes(chart_data["bar_faltantes_sobrantes"]),
        "histograma": chart_histograma_diferencias(chart_data["hist_difimporte"]),
        "top10": chart_top10_faltantes(chart_data["top10_faltantes"]),
        "donut": chart_donut_revision(chart_data["donut_revision"]),
        "heatmap": chart_heatmap_movimientos(chart_data["heatmap_movimientos"]),
    }
