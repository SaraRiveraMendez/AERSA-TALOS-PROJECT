# TALOS — Guía de Dockerización

Este documento describe la arquitectura del sistema y todo lo necesario para dockerizar el proyecto.

---

## Arquitectura general

El sistema consta de **tres servicios principales** más una base de datos:

```
┌─────────────────────────────────────────────────────────┐
│                        Nginx :80                        │
│   /          → frontend (HTML estático)                 │
│   /api/rag/  → RAG API :8000                            │
│   /api/reports/ → Reports API :8001                     │
└─────────────────────────────────────────────────────────┘
         │                    │                    │
    ┌────▼────┐          ┌────▼────┐          ┌────▼────┐
    │  RAG    │          │ Reports │          │  MySQL  │
    │ API     │          │  API    │          │ :3306   │
    │ :8000   │          │  :8001  │          │         │
    └────┬────┘          └────┬────┘          └─────────┘
         │                    │
    ┌────▼────┐          ┌────▼────┐
    │  Ollama │          │Playwright│
    │ :11434  │          │(interno) │
    └─────────┘          └─────────┘
         │
    ┌────▼────┐
    │  Milvus │
    │  Lite   │
    │(archivo)│
    └─────────┘
```

---

## Servicios a dockerizar

### 1. RAG API (`api/`)
- **Puerto:** 8000
- **Entrada:** `api/main.py`
- **Framework:** FastAPI + uvicorn
- **Dependencias:** `rag/requirements.txt`
- **Variables de entorno necesarias:** ninguna (usa `config.py`)
- **Volúmenes necesarios:**
  - `./milvus_talos.db` → `/app/milvus_talos.db` (persistencia de embeddings)
  - `./reportes/` → `/app/reportes/` (PDFs generados)
  - `./knowledge/` → `/app/knowledge/` (base de conocimiento)
- **Comando de inicio:**
  ```
  uvicorn api.main:app --host 0.0.0.0 --port 8000
  ```
- **Notas importantes:**
  - Al arrancar descarga el modelo BGE-M3 (~2.3 GB) de HuggingFace si no está en caché. Montar un volumen para `~/.cache/huggingface/` es altamente recomendable.
  - Requiere acceso a Ollama en `localhost:11434`.
  - Requiere acceso a MySQL en `localhost:3306`.

### 2. Reports API (`app/`)
- **Puerto:** 8001
- **Entrada:** `app/main.py`
- **Framework:** FastAPI + uvicorn + APScheduler
- **Dependencias:** `app/requirements.txt`
- **Variables de entorno necesarias** (via `.env`):
  ```
  APP_ENV=production
  APP_HOST=0.0.0.0
  APP_PORT=8001
  DATABASE_URL=mysql+aiomysql://user:password@mysql:3306/talos_tecmty
  SCHEDULER_DAY_OF_WEEK=sun
  SCHEDULER_HOUR=23
  SCHEDULER_MINUTE=0
  SCHEDULER_TIMEZONE=America/Mexico_City
  STORAGE_BACKEND=local
  STORAGE_LOCAL_PATH=./reportes
  ```
- **Volúmenes necesarios:**
  - `./reportes/` → `/app/reportes/`
  - `./app/templates/` → `/app/app/templates/`
- **Comando de inicio:**
  ```
  uvicorn app.main:app --host 0.0.0.0 --port 8001
  ```
- **Notas importantes:**
  - Usa Playwright + Chromium para generar PDFs. Requiere instalar `playwright install chromium` y sus dependencias del sistema durante el build.
  - El scheduler corre automáticamente al iniciar la API.
  - `weasyprint` en el `requirements.txt` de Sara puede reemplazar a Playwright — verificar cuál se usa en producción (`app/services/pdf_generator.py` usa Playwright).

### 3. Frontend (`frontend/`)
- HTML/CSS/JS estático — no necesita contenedor propio.
- Servido directamente por Nginx.
- **Único archivo:** `frontend/index.html`
- **Configuración importante:** las constantes `RAG_API` y `REP_API` al inicio del JS deben apuntar a las rutas correctas según el entorno.

### 4. Nginx (`nginx.conf`)
- Reverse proxy + servidor de archivos estáticos.
- Configuración en `talos-server/nginx.conf`.
- Timeouts configurados a 300s para acomodar las respuestas lentas de Ollama en CPU.

### 5. MySQL
- Versión: **8.0** (el dump fue generado con MySQL 8.0.44).
- Base de datos: `talos_tecmty`.
- El dump de inicialización está en `database/talos_tecmty_utf8.sql`.
- Las vistas limpias están en `database/view_clean_tables.sql` — deben ejecutarse **después** del dump principal.
- La tabla `transferencia` no está en el dump — crearla con el siguiente SQL:
  ```sql
  CREATE TABLE IF NOT EXISTS transferencia (
      idtransferencia             INT NOT NULL AUTO_INCREMENT,
      idempresa                   INT NOT NULL,
      transferencia_fecha         DATE NOT NULL,
      idsucursal_origen           INT NOT NULL,
      idalmacen_origen            INT NOT NULL,
      idinventariomes_origen      INT DEFAULT NULL,
      idsucursal_destino          INT NOT NULL,
      idalmacen_destino           INT NOT NULL,
      idinventariomes_destino     INT DEFAULT NULL,
      idproducto                  INT NOT NULL,
      transferencia_cantidad      DECIMAL(12,4) NOT NULL,
      transferencia_costopromedio DECIMAL(12,4) DEFAULT NULL,
      transferencia_importe       DECIMAL(12,4) DEFAULT NULL,
      transferencia_tipo          VARCHAR(50) NOT NULL DEFAULT 'manual',
      transferencia_origen        VARCHAR(50) NOT NULL DEFAULT 'manual',
      transferencia_estatus       VARCHAR(20) NOT NULL DEFAULT 'pendiente',
      transferencia_observaciones TEXT DEFAULT NULL,
      idusuario_registra          INT DEFAULT NULL,
      idusuario_confirma          INT DEFAULT NULL,
      transferencia_createdat     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      transferencia_updatedat     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      PRIMARY KEY (idtransferencia)
  );
  ```

### 6. Ollama
- Imagen oficial: `ollama/ollama`
- Modelo requerido: `llama3.2:3b` (~2 GB)
- Corre en puerto `11434`
- Montar volumen para persistir modelos descargados: `/root/.ollama`
- Al primer arranque hay que descargar el modelo:
  ```
  ollama pull llama3.2:3b
  ```

---

## Dependencias del sistema (apt) para el contenedor de RAG API

```
libgl1-mesa-glx
libglib2.0-0
ghostscript
python3-tk
```

Estas son requeridas por `camelot-py` y `matplotlib`.

## Dependencias del sistema para el contenedor de Reports API

Playwright necesita estas dependencias para correr Chromium headless:

```bash
playwright install-deps chromium
```

O manualmente:
```
libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2
libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2
libgbm1 libasound2
```

---

## Estructura de archivos relevante para Docker

```
talos-server/
├── api/main.py              ← RAG API entrypoint
├── app/main.py              ← Reports API entrypoint
├── config.py                ← Configuración compartida RAG API
├── .env                     ← Variables de entorno Reports API (NO commitear)
├── rag/requirements.txt     ← Dependencias RAG API
├── app/requirements.txt     ← Dependencias Reports API
├── nginx.conf               ← Configuración Nginx
├── frontend/index.html      ← Frontend estático
├── milvus_talos.db/         ← Base vectorial (volumen persistente)
├── reportes/                ← PDFs generados (volumen persistente)
├── knowledge/               ← Base de conocimiento .txt
└── database/
    ├── talos_tecmty_utf8.sql      ← Dump principal MySQL
    └── view_clean_tables.sql      ← Vistas limpias (correr después del dump)
```

---

## Orden de inicialización recomendado

1. MySQL (esperar a que acepte conexiones)
2. Ollama + pull del modelo
3. RAG API (espera a MySQL y Ollama)
4. Reports API (espera a MySQL)
5. Nginx (espera a ambas APIs)

---

## Notas adicionales

- **Python version:** 3.10.12
- **Milvus Lite** corre embebido dentro de la RAG API — no es un servicio separado. El archivo `milvus_talos.db/` es su almacenamiento en disco.
- **El venv** (`rag/.rag_env/`) no debe copiarse al contenedor — instalar dependencias directamente con pip durante el build.
- **`config.py`** en la raíz de `talos-server/` contiene las credenciales de MySQL y la API key hardcodeadas — en producción deben moverse a variables de entorno.
- El dump de MySQL pesa ~4.1 GB — considerar si incluirlo en la imagen o montarlo como volumen externo.
