"""
indexers/indexar_pdf.py
Extracts text from audit PDFs using pdfplumber and indexes
the content into Milvus Lite using BGE-M3 embeddings.
"""

import logging
import sys
from pathlib import Path

import pdfplumber
from pymilvus import MilvusClient
from sentence_transformers import SentenceTransformer

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import MODELO_EMBEDDING, MILVUS_PATH, COLECCION_PDF

log = logging.getLogger(__name__)
CHUNK_SIZE = 800
OVERLAP = 100


def chunk_text(text: str) -> list[str]:
    chunks = []
    for i in range(0, len(text), CHUNK_SIZE - OVERLAP):
        chunk = text[i:i + CHUNK_SIZE].strip()
        if len(chunk) > 50:
            chunks.append(chunk)
    return chunks


def indexar_pdf(ruta_pdf: str, embedder: SentenceTransformer = None) -> dict:
    if not Path(ruta_pdf).exists():
        raise FileNotFoundError(f"File not found: {ruta_pdf}")

    log.info(f"Extracting text from PDF: {ruta_pdf}")

    texts = []
    with pdfplumber.open(ruta_pdf) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text:
                chunks = chunk_text(text)
                texts.extend(chunks)
                log.info(f"Page {i+1}: {len(chunks)} chunks")

    if not texts:
        log.warning("No text found in PDF.")
        return {"indexed": 0}

    log.info(f"Vectorizing {len(texts)} chunks...")

    if embedder is None:
        embedder = SentenceTransformer(MODELO_EMBEDDING)

    embeddings = embedder.encode(
        texts, normalize_embeddings=True, show_progress_bar=True
    )

    milvus = MilvusClient(MILVUS_PATH)
    if not milvus.has_collection(COLECCION_PDF):
        milvus.create_collection(collection_name=COLECCION_PDF, dimension=1024)

    data = [
        {"id": i, "vector": embeddings[i].tolist(), "texto": texts[i]}
        for i in range(len(texts))
    ]
    milvus.upsert(collection_name=COLECCION_PDF, data=data)
    log.info(f"Done: {len(texts)} chunks saved to '{COLECCION_PDF}'.")

    return {"indexed": len(texts), "pdf": ruta_pdf}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) < 2:
        print("Usage: python indexar_pdf.py <path_to_pdf>")
        sys.exit(1)
    result = indexar_pdf(sys.argv[1])
    print(f"✓ {result['indexed']} chunks indexed from {result['pdf']}.")
