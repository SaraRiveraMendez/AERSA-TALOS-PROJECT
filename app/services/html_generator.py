"""
app/services/html_generator.py
Renderiza el template Jinja2 con el contexto y las gráficas.
"""

from pathlib import Path
from jinja2 import Environment, FileSystemLoader


def render_report_html(context: dict, charts: dict) -> str:
    """
    Combina el contexto del DataProcessor con las gráficas base64
    y retorna el HTML completo listo para Playwright.
    """
    template_dir = Path(__file__).parent.parent / "templates"

    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=False,
    )

    template = env.get_template("reporte.html")
    return template.render(**context, charts=charts)
