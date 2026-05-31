"""
indexers/indexar_pdf.py
───────────────────────
Processes a weekly audit PDF report, vectorizes its content
with BGE-M3, and persists the embeddings in Milvus Lite.

Direct usage (cron job):
    python indexar_pdf.py /path/to/report.pdf

Importable from the API:
    from indexers.indexar_pdf import indexar_pdf
"""

import logging
import sys
from pathlib import Path

from pymilvus import MilvusClient
from sentence_transformers import SentenceTransformer

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import MODELO_EMBEDDING, MILVUS_PATH, COLECCION_PDF

log = logging.getLogger(__name__)


def indexar_pdf(ruta_pdf: str, embedder: SentenceTransformer = None) -> dict:
    # Lazy import to avoid loading broken file at API startup
    sys.path.append(str(Path(__file__).resolve().parent.parent / "rag"))
    from vectorizacion_split_reportes import PipelineAuditoriaCompleto, ConvertidorAuditoria

    if not Path(ruta_pdf).exists():
        raise FileNotFoundError(f"File not found: {ruta_pdf}")

    log.info(f"Processing PDF: {ruta_pdf}")

    pipeline = PipelineAuditoriaCompleto()
    data = pipeline.procesar_reporte_pdf(ruta_pdf)

    log.info(
        f"Extracted: {len(data['kpis'])} KPIs, "
        f"{len(data['alertas_faltantes'])} shortages, "
        f"{len(data['alertas_sobrantes'])} surpluses."
    )

    converter = ConvertidorAuditoria()
    texts = []

    for kpi in data.get("kpis", []):
        texts.append(converter.convertir_kpi(kpi))
    for alert in data.get("alertas_faltantes", []):
        texts.append(converter.convertir_alerta(alert))
    for alert in data.get("alertas_sobrantes", []):
        texts.append(converter.convertir_alerta(alert))

    if not texts:
        log.warning("No indexable content found in the PDF.")
        return {"indexed": 0}

    if embedder is None:
        embedder = SentenceTransformer(MODELO_EMBEDDING)

    log.info(f"Vectorizing {len(texts)} fragments from report...")
    embeddings = embedder.encode(texts, normalize_embeddings=True, show_progress_bar=True)

    milvus = MilvusClient(MILVUS_PATH)
    if not milvus.has_collection(COLECCION_PDF):
        milvus.create_collection(collection_name=COLECCION_PDF, dimension=1024)

    data_to_insert = [
        {"id": i, "vector": embeddings[i].tolist(), "texto": texts[i]}
        for i in range(len(texts))
    ]
    milvus.upsert(collection_name=COLECCION_PDF, data=data_to_insert)
    log.info(f"PDF indexing complete: {len(texts)} fragments saved to '{COLECCION_PDF}'.")

    return {"indexed": len(texts), "pdf": ruta_pdf}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage: python indexar_pdf.py <path_to_pdf>")
        sys.exit(1)

    result = indexar_pdf(sys.argv[1])
    print(f"✓ {result['indexed']} fragments indexed from {result['pdf']}.")
