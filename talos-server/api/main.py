"""
api/main.py
───────────
TALOS RAG REST API.
All indexing logic lives in indexers/ — this file only
handles routing, request/response models, and auth.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

import requests
from fastapi import FastAPI, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
from pymilvus import MilvusClient
from sentence_transformers import SentenceTransformer

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import (
    API_KEY, COLECCION_DB, COLECCION_PDF, COLECCION_CONOCIMIENTO,
    MODELO_EMBEDDING, MILVUS_PATH, MODELO_LLM, OLLAMA_URL,
)
from indexers.indexar_db import indexar as _indexar_db
from indexers.indexar_pdf import indexar_pdf as _indexar_pdf

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = FastAPI(title="TALOS RAG API", version="2.0")

# ── CORS ───────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API key authentication ─────────────────────────────────
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def require_api_key(key: str = Security(api_key_header)):
    if key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")
    return key

# ── Global state ───────────────────────────────────────────
embedder: SentenceTransformer = None
milvus: MilvusClient = None

# ── Request models ─────────────────────────────────────────
class AskRequest(BaseModel):
    question: str
    top_k: Optional[int] = 3
    collection: Optional[str] = None

class IndexDBRequest(BaseModel):
    days: Optional[int] = 90
    limit: Optional[int] = 5000

class IndexPDFRequest(BaseModel):
    pdf_path: str

# ── Startup ────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    global embedder, milvus
    log.info("Loading embedding model...")
    embedder = SentenceTransformer(MODELO_EMBEDDING)
    log.info("Connecting to Milvus Lite...")
    milvus = MilvusClient(MILVUS_PATH)
    log.info("API ready.")

# ── Helper: call Ollama ────────────────────────────────────
def ask_ollama(context: str, question: str) -> str:
    prompt = f"""You are an expert assistant in inventory auditing for the TALOS system, specialized in restaurants and bars.
You have access to real inventory data, audit reports, and professional auditing best practices.
Use ALL the provided context to give precise and actionable answers.
When the context includes auditing rules or thresholds, apply them explicitly to the data.
Always respond in Spanish, concisely and helpfully.
If the context is not sufficient to answer, say so clearly.

CONTEXT:
{context}

QUESTION: {question}

ANSWER:"""

    resp = requests.post(OLLAMA_URL, json={
        "model": MODELO_LLM,
        "prompt": prompt,
        "stream": False
    }, timeout=300)

    if resp.status_code != 200:
        raise HTTPException(500, "Error contacting Ollama")

    return resp.json().get("response", "").strip()

# ── Public endpoints ───────────────────────────────────────
@app.get("/")
def root():
    return {"status": "ok", "version": "2.0", "message": "TALOS RAG API is running"}

@app.get("/status")
def status():
    result = {}
    for collection in [COLECCION_DB, COLECCION_PDF, COLECCION_CONOCIMIENTO]:
        if milvus.has_collection(collection):
            stats = milvus.get_collection_stats(collection)
            result[collection] = stats["row_count"]
        else:
            result[collection] = 0
    return result

@app.post("/ask")
def ask(req: AskRequest):
    query_vec = embedder.encode(req.question, normalize_embeddings=True).tolist()

    # Determine which data collections to search
    if req.collection:
        data_collections = [req.collection]
    else:
        data_collections = [COLECCION_DB, COLECCION_PDF]

    # Always include the knowledge base
    collections_to_search = data_collections + [COLECCION_CONOCIMIENTO]

    contexts = []
    for collection in collections_to_search:
        if not milvus.has_collection(collection):
            continue
        milvus.load_collection(collection)
        results = milvus.search(
            collection_name=collection,
            data=[query_vec],
            limit=req.top_k,
            output_fields=["texto"]
        )
        if results and results[0]:
            contexts.extend([r["entity"]["texto"] for r in results[0]])

    if not contexts:
        raise HTTPException(404, "No relevant results found")

    context = "\n".join(contexts)
    answer = ask_ollama(context, req.question)

    return {
        "question": req.question,
        "answer": answer,
        "context_used": context,
        "collections": collections_to_search
    }

# ── Protected endpoints ────────────────────────────────────
@app.post("/index/db")
def index_db(req: IndexDBRequest, _: str = Security(require_api_key)):
    """Indexes data from MySQL. Requires X-API-Key header."""
    return _indexar_db(dias=req.days, limite=req.limit, embedder=embedder)

@app.post("/index/pdf")
def index_pdf(req: IndexPDFRequest, _: str = Security(require_api_key)):
    """Indexes a weekly audit PDF. Requires X-API-Key header."""
    try:
        return _indexar_pdf(ruta_pdf=req.pdf_path, embedder=embedder)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
