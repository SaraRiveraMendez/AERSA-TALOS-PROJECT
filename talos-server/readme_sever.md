# TALOS — Sistema de Auditoría de Inventario con IA

Sistema de análisis y auditoría de inventario para restaurantes y bares, desarrollado como proyecto escolar en el Instituto Tecnológico y de Estudios Superiores de Monterrey (ITESM). Combina generación automática de reportes, detección de transferencias entre almacenes y un asistente conversacional basado en RAG (Retrieval-Augmented Generation) que responde preguntas en lenguaje natural sobre los datos de inventario.

🌐 **Demo en vivo:** https://pejelagartopiloto.site

---

## Tabla de contenidos

1. [Descripción del problema](#descripción-del-problema)
2. [Solución propuesta](#solución-propuesta)
3. [Arquitectura](#arquitectura)
4. [Stack tecnológico](#stack-tecnológico)
5. [Estructura del proyecto](#estructura-del-proyecto)
6. [Instalación](#instalación)
7. [Configuración](#configuración)
8. [Iniciar los servicios](#iniciar-los-servicios)
9. [Indexación inicial](#indexación-inicial)
10. [API Reference](#api-reference)
11. [Pipeline RAG](#pipeline-rag)
12. [Sistema de transferencias](#sistema-de-transferencias)
13. [Automatización](#automatización)
14. [Frontend](#frontend)
15. [Infraestructura](#infraestructura)
16. [Dockerización](#dockerización)

---

## Descripción del problema

Las cadenas de restaurantes y bares realizan cierres semanales de inventario físico. El proceso genera grandes volúmenes de datos que los auditores deben analizar manualmente para identificar:

- Productos con faltantes o sobrantes significativos
- Transferencias de productos entre almacenes no registradas en el sistema
- Patrones anómalos que puedan indicar errores o irregularidades
- Prioridades de revisión entre cientos de productos

Este análisis es tedioso, propenso a errores humanos y requiere experiencia en auditoría para interpretarse correctamente.

---

## Solución propuesta

TALOS automatiza el análisis de inventario en tres componentes:

**1. Generación automática de reportes** — Cada domingo, el sistema extrae los datos del cierre semanal, genera gráficas estadísticas, calcula KPIs, detecta outliers y produce un reporte PDF completo por inventario.

**2. Detección de transferencias** — Identifica automáticamente movimientos de productos entre almacenes que no fueron registrados en el sistema, reduciendo falsas alarmas en los reportes.

**3. Asistente RAG** — Los auditores pueden hacer preguntas en lenguaje natural sobre los datos de inventario, los reportes generados y las buenas prácticas de auditoría. El sistema recupera contexto relevante y genera respuestas precisas usando un LLM local.

---

## Arquitectura

```
Usuario / Navegador
        │
        ▼ HTTPS
   Nginx :443
   ├── /                → Frontend (HTML estático)
   ├── /api/rag/        → RAG API :8000
   └── /api/reports/    → Reports API :8001
        │                       │
        ▼                       ▼
   Ollama :11434           MySQL :3306
   llama3.2:3b (CPU)       talos_tecmty
        │
        ▼
   Milvus Lite (embebido en RAG API)
   ├── inventario   — 5,000 registros de MySQL
   ├── reportes     — chunks de PDFs de auditoría
   └── conocimiento — buenas prácticas de auditoría
```

Para diagramas detallados ver `/docs`:
- `talos_architecture.drawio` — arquitectura general del servidor
- `talos_rag_pipeline.drawio` — pipeline de vectorización y consulta RAG

---

## Stack tecnológico

| Componente | Tecnología | Justificación |
|---|---|---|
| LLM | Llama 3.2 3B (via Ollama) | Modelo local, sin envío de datos a APIs externas |
| Embeddings | BGE-M3 (BAAI/bge-m3) | Estado del arte multilingüe, 1024 dimensiones |
| Similitud | Coseno (normalización L2) | Captura similitud semántica independiente de magnitud |
| Vector DB | Milvus Lite | Embebido, sin servidor separado, ideal para prototipo |
| RAG API | FastAPI + uvicorn | Async, rápido, documentación automática |
| Reports API | FastAPI + SQLAlchemy async | Operaciones async con APScheduler integrado |
| Base de datos | MySQL 8.0 | Sistema existente del cliente TALOS |
| Generación PDF | Playwright + Chromium | Renderizado fiel de HTML/CSS a PDF |
| Gráficas | Matplotlib | Generación server-side sin dependencias del cliente |
| Templates | Jinja2 | Renderizado HTML dinámico |
| Scheduler | APScheduler | Jobs async integrados en la Reports API |
| Reverse proxy | Nginx | Unifica APIs y frontend, maneja HTTPS y timeouts |
| HTTPS | Let's Encrypt (Certbot) | Certificado gratuito con renovación automática |
| Servidor | Google Cloud e2-standard-4 | 4 vCPUs, 16 GB RAM, Ubuntu 22.04 LTS |

---

## Estructura del proyecto

```
talos-server/
├── api/
│   └── main.py                      # RAG API — FastAPI, puerto 8000
├── app/
│   ├── main.py                      # Reports API — FastAPI, puerto 8001
│   ├── config.py                    # Configuración (lee .env)
│   ├── db/
│   │   ├── connection.py            # Conexión async SQLAlchemy
│   │   ├── queries.py               # Queries de inventario y vistas limpias
│   │   └── transferencia_queries.py # Queries de transferencias
│   ├── models.py                    # Modelos Pydantic
│   ├── routers/
│   │   ├── reports.py               # Endpoints de reportes PDF
│   │   └── transferencias.py        # Endpoints de transferencias
│   ├── services/
│   │   ├── data_processor.py        # Procesamiento de datos de inventario
│   │   ├── chart_generator.py       # Generación de 6 gráficas (matplotlib)
│   │   ├── html_generator.py        # Renderizado HTML (Jinja2)
│   │   ├── pdf_generator.py         # Generación PDF (Playwright)
│   │   ├── pdf_worker.py            # Worker subproceso para Playwright
│   │   └── transfer_detector.py     # Detección automática de transferencias
│   └── templates/
│       └── reporte.html             # Template Jinja2 del reporte
├── indexers/
│   ├── indexar_db.py                # Vectorizar datos MySQL → Milvus
│   └── indexar_pdf.py               # Vectorizar PDFs → Milvus
├── rag/
│   ├── vectorizacion_split_sql.py   # Pipeline BGE-M3 para datos SQL
│   ├── vectorizacion_split_reportes.py # Pipeline BGE-M3 para PDFs
│   └── requirements.txt             # Dependencias RAG API
├── database/
│   ├── talos_tecmty_utf8.sql        # Dump principal (UTF-8, ~4 GB)
│   ├── view_clean_tables.sql        # 4 vistas limpias de auditoría
│   └── transferencia.sql            # Tabla de transferencias
├── frontend/
│   └── index.html                   # Dashboard (HTML/CSS/JS estático)
├── knowledge/
│   └── buenas_practicas_auditoria.txt  # Base de conocimiento RAG
├── cron/
│   └── cron_db.sh                   # Script de reindexación semanal
├── reportes/                        # PDFs generados (gitignored)
├── milvus_talos.db/                 # Base vectorial Milvus (gitignored)
├── config.py                        # Configuración compartida RAG API
├── nginx.conf                       # Configuración Nginx con HTTPS
├── requirements.txt                 # Dependencias unificadas
├── .env                             # Variables de entorno (gitignored)
├── README.md                        # Este archivo
└── DOCKER_README.md                 # Guía de dockerización
```

---

## Instalación

### Prerrequisitos

- Ubuntu 22.04 LTS
- Python 3.10+
- MySQL 8.0
- 16 GB RAM mínimo

### 1. Clonar el repositorio

```bash
git clone https://github.com/SaraRiveraMendez/AERSA-TALOS-PROJECT.git
cd AERSA-TALOS-PROJECT/talos-server
```

### 2. Crear el entorno virtual e instalar dependencias

```bash
python3 -m venv rag/.rag_env
source rag/.rag_env/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
python -m playwright install-deps
```

### 3. Configurar MySQL

```bash
# Crear base de datos
mysql -u root -p -e "CREATE DATABASE talos_tecmty CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# Importar dump principal (puede tardar varios minutos, ~4 GB)
mysql -u root -p talos_tecmty < database/talos_tecmty_utf8.sql

# Crear vistas limpias de auditoría
mysql -u root -p talos_tecmty < database/view_clean_tables.sql

# Crear tabla de transferencias
mysql -u root -p talos_tecmty < database/transferencia.sql
```

### 4. Instalar Ollama y descargar el modelo

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2:3b
```

### 5. Configurar Nginx

```bash
sudo apt install nginx -y
sudo cp nginx.conf /etc/nginx/sites-available/talos
sudo ln -s /etc/nginx/sites-available/talos /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

### 6. Configurar HTTPS (opcional pero recomendado)

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d tudominio.com -d www.tudominio.com
```

---

## Configuración

### config.py (RAG API)

```python
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "TU_PASSWORD",
    "database": "talos_tecmty",
    "charset": "utf8mb4",
    "use_unicode": True
}

OLLAMA_URL = "http://localhost:11434/api/generate"
MODELO_LLM = "llama3.2:3b"
MODELO_EMBEDDING = "BAAI/bge-m3"
MILVUS_PATH = "/ruta/a/talos-server/milvus_talos.db"
COLECCION_DB = "inventario"
COLECCION_PDF = "reportes"
COLECCION_CONOCIMIENTO = "conocimiento"
API_KEY = "cambia-esto-en-produccion"
```

### .env (Reports API)

```env
APP_ENV=production
APP_HOST=0.0.0.0
APP_PORT=8001
DATABASE_URL=mysql+aiomysql://root:PASSWORD@localhost:3306/talos_tecmty
SCHEDULER_DAY_OF_WEEK=sun
SCHEDULER_HOUR=23
SCHEDULER_MINUTE=0
SCHEDULER_TIMEZONE=America/Mexico_City
STORAGE_BACKEND=local
STORAGE_LOCAL_PATH=./reportes
```

### frontend/index.html

Actualizar las URLs de las APIs (líneas ~880):

```javascript
const RAG_API = 'https://tudominio.com/api/rag';
const REP_API = 'https://tudominio.com/api/reports';
const API_KEY = 'tu-api-key';
```

---

## Iniciar los servicios

```bash
source rag/.rag_env/bin/activate
cd /ruta/a/talos-server

# RAG API (puerto 8000)
tmux new -s api
uvicorn api.main:app --host 0.0.0.0 --port 8000

# Reports API (puerto 8001) — nueva ventana tmux
tmux new -s reports
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

Verificar que todo corre:

```bash
curl https://tudominio.com/api/rag/
curl https://tudominio.com/api/reports/health
```

---

## Indexación inicial

Después de instalar, indexar los datos en Milvus por primera vez:

```bash
source rag/.rag_env/bin/activate

# 1. Indexar datos de MySQL (registros con discrepancias, últimos 90 días)
curl -X POST https://tudominio.com/api/rag/index/db \
  -H "Content-Type: application/json" \
  -H "X-API-Key: tu-api-key" \
  -d '{"days": 90, "limit": 5000}'

# 2. Indexar un reporte PDF
python3 indexers/indexar_pdf.py reportes/reporte_XXXXXX.pdf

# 3. Indexar base de conocimiento (solo una vez)
python3 - << 'EOF'
import sys
from pathlib import Path
from sentence_transformers import SentenceTransformer
from pymilvus import MilvusClient
sys.path.append(".")
from config import MODELO_EMBEDDING, MILVUS_PATH

texto = Path("knowledge/buenas_practicas_auditoria.txt").read_text(encoding="utf-8")
chunks = [c.strip() for c in texto.split("---") if len(c.strip()) > 100]
embedder = SentenceTransformer(MODELO_EMBEDDING)
embeddings = embedder.encode(chunks, normalize_embeddings=True, show_progress_bar=True)
milvus = MilvusClient(MILVUS_PATH)
if not milvus.has_collection("conocimiento"):
    milvus.create_collection(collection_name="conocimiento", dimension=1024)
data = [{"id": i, "vector": embeddings[i].tolist(), "texto": chunks[i]} for i in range(len(chunks))]
milvus.upsert(collection_name="conocimiento", data=data)
print(f"Indexados {len(chunks)} chunks de conocimiento")
EOF
```

---

## API Reference

### RAG API — puerto 8000

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| `GET` | `/` | — | Estado de la API |
| `GET` | `/status` | — | Documentos indexados por colección |
| `POST` | `/ask` | — | Consulta RAG en lenguaje natural |
| `POST` | `/index/db` | X-API-Key | Reindexar datos de MySQL en Milvus |
| `POST` | `/index/pdf` | X-API-Key | Indexar un reporte PDF en Milvus |

**Ejemplo — consulta RAG:**

```bash
curl -X POST https://tudominio.com/api/rag/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "¿Cuáles son los 3 productos con mayor faltante?",
    "collection": "reportes",
    "top_k": 3
  }'
```

**Parámetros de `/ask`:**
- `question` — pregunta en lenguaje natural
- `collection` — `"inventario"`, `"reportes"`, o `null` para buscar en ambas. La colección `conocimiento` siempre se incluye.
- `top_k` — número de fragmentos a recuperar por colección (default: 3)

### Reports API — puerto 8001

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/health` | Estado de la API y conexión a BD |
| `GET` | `/docs` | Documentación Swagger interactiva |
| `POST` | `/reports/generate` | Genera reporte PDF de un inventario (background) |
| `GET` | `/reports/{id}/status` | Estado del reporte: `pending` / `ready` |
| `GET` | `/reports/{id}/download` | Descarga el PDF generado |
| `POST` | `/transferencias/` | Registrar transferencia manual (queda confirmada) |
| `GET` | `/transferencias/inventario/{id}` | Listar transferencias de un inventario |
| `GET` | `/transferencias/almacen/{id}` | Listar por almacén y rango de fechas |
| `POST` | `/transferencias/detectar/{idsucursal}` | Detectar transferencias automáticamente |
| `PATCH` | `/transferencias/{id}/confirmar` | Auditor confirma (descuenta del faltante) |
| `PATCH` | `/transferencias/{id}/rechazar` | Auditor rechaza (era pérdida real) |

---

## Pipeline RAG

El sistema RAG opera en dos fases:

### Indexación

```
Fuente de datos
├── MySQL (vw_inventariomesdetalle_limpio)
│     → row_to_text() → texto natural por producto
├── PDF (reportes de auditoría)
│     → pdfplumber → chunks de 800 caracteres
└── TXT (buenas prácticas)
      → split por sección "---"
           │
           ▼
      BGE-M3 (BAAI/bge-m3)
      normalize_embeddings=True
      Vectores de 1024 dimensiones
           │
           ▼
      Milvus Lite → colecciones: inventario | reportes | conocimiento
```

### Consulta

```
Pregunta del usuario
      │
      ▼ BGE-M3
Vector de consulta (1024d)
      │
      ▼ similitud coseno
Milvus.search() — top_k fragmentos por colección
      │
      ▼
Contexto concatenado
      │
      ▼
Prompt en inglés + contexto + pregunta
      │
      ▼ Ollama (llama3.2:3b, CPU)
Respuesta en español
```

**¿Por qué similitud coseno?**
Con vectores normalizados (L2), la similitud coseno captura similitud semántica independientemente de la magnitud del vector. Es superior a distancia euclidiana para texto y a BM25 porque entiende sinónimos y paráfrasis.

---

## Sistema de transferencias

Cuando un producto se mueve físicamente entre almacenes sin registrarse, el cierre reporta un faltante en el almacén origen y un sobrante en el destino — inflando las pérdidas reportadas.

### Flujo

```
Cierre semanal
      │
      ▼ POST /transferencias/detectar/{idsucursal}
TransferDetector:
  Producto X con diferencia negativa en Almacén A
  Y diferencia positiva en Almacén B
  mismo cierre — cantidades coinciden dentro del ±15%
      │
      ├── PATCH /confirmar → pérdida real = faltante bruto - transferencias
      └── PATCH /rechazar  → se mantiene como pérdida real
```

---

## Automatización

### Reindexación semanal de MySQL

```bash
crontab -e
# Agregar:
0 2 * * 0 /bin/bash /ruta/a/talos-server/cron/cron_db.sh
```

Corre cada domingo a las 2:00 AM.

### Generación automática de reportes

APScheduler integrado en la Reports API. Se activa automáticamente al iniciar la API y genera reportes PDF cada domingo a las 23:00 (México) para todos los inventarios cerrados en los últimos 7 días.

---

## Frontend

Dashboard web en `frontend/index.html` con 4 módulos:

| Tab | Funcionalidad |
|-----|---------------|
| **Chat RAG** | Asistente conversacional con selector de fuente (PDF/DB/ambas) y control de top_k |
| **Reportes PDF** | Visualizador de PDFs, generación de nuevos reportes |
| **Administrador** | Reindexar DB y PDFs (requiere API key), estado del sistema |
| **Transferencias** | Listar, detectar automáticamente, confirmar/rechazar |

---

## Infraestructura

- **Servidor:** Google Cloud e2-standard-4 — 4 vCPUs, 16 GB RAM, 50 GB SSD
- **OS:** Ubuntu 22.04 LTS — región us-central1 (Iowa)
- **Dominio:** Namecheap — A Records apuntando a IP del servidor
- **HTTPS:** Let's Encrypt via Certbot — renovación automática cada 90 días
- **Costo:** ~$3.10 USD/día

### Notas para producción

- Mover credenciales de `config.py` a variables de entorno
- Cambiar API key antes de desplegar
- Sin GPU: respuestas del LLM toman 30-90 segundos en CPU
- Para escalar: GPU para Ollama, Milvus standalone, múltiples workers

---

## Dockerización

Ver `DOCKER_README.md` para la guía completa de dockerización.

---

## Equipo

Proyecto escolar — 8vo Semestre, ITESM Campus Monterrey

**Repositorio:** https://github.com/SaraRiveraMendez/AERSA-TALOS-PROJECT
