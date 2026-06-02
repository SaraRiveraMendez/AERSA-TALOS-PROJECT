"""
app/services/pdf_generator.py
Usa subprocess.run (bloqueante) en un thread — única solución fiable en Windows.
"""

import sys
import asyncio
import subprocess
import threading
from pathlib import Path


def _run_worker_blocking(html_temp: Path, output_path: Path) -> None:
    """Llama al pdf_worker como subproceso bloqueante. Corre en thread separado."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.services.pdf_worker",
            str(html_temp),
            str(output_path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"pdf_worker falló (código {result.returncode}):\n{result.stderr}"
        )
    print(result.stdout.strip())


async def run_pdf_async(html_content: str, output_path: Path) -> None:
    """Genera el PDF sin bloquear el event loop de FastAPI."""
    html_temp = output_path.with_suffix(".tmp.html")
    html_temp.write_text(html_content, encoding="utf-8")

    error_holder = []

    def _worker():
        try:
            _run_worker_blocking(html_temp, output_path)
        except Exception as e:
            error_holder.append(e)
        finally:
            html_temp.unlink(missing_ok=True)

    thread = threading.Thread(target=_worker)
    thread.start()

    while thread.is_alive():
        await asyncio.sleep(0.2)

    thread.join()

    if error_holder:
        raise error_holder[0]
