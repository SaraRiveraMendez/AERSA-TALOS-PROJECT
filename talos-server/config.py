# Shared configuration ───────────────────────────────────
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "12345678",
    "database": "talos_tecmty"
}

OLLAMA_URL = "http://localhost:11434/api/generate"
MODELO_LLM = "llama3.2:3b"
MODELO_EMBEDDING = "BAAI/bge-m3"

MILVUS_PATH = "/home/rene_abraham_calzadilla_calderon/talos-server/milvus_talos.db"
COLECCION_DB = "inventario"
COLECCION_PDF = "reportes"

# API key for protected endpoints
API_KEY = "talos-secret-2026"
