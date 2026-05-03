"""
app/services/pdf_worker.py
Script standalone que corre Playwright sin interferencia del event loop de FastAPI.
Se ejecuta como subproceso: python -m app.services.pdf_worker <html_path> <pdf_path>
"""

import sys
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    html_path = Path(sys.argv[1])
    pdf_path = Path(sys.argv[2])

    html_content = html_path.read_text(encoding="utf-8")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html_content, wait_until="networkidle")
        page.pdf(
            path=str(pdf_path),
            format="A4",
            print_background=True,
            margin={
                "top": "15mm",
                "bottom": "15mm",
                "left": "12mm",
                "right": "12mm",
            },
        )
        browser.close()
    print(f"PDF generado: {pdf_path}")


if __name__ == "__main__":
    main()
