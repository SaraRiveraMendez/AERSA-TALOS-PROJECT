# TALOS Report API

Automatic inventory-audit report generation API for the TALOS system. Built with FastAPI and Python, connected to MySQL, and designed with a cloud-ready architecture.

---

## Table of Contents

1. [Problem Context](#1-problem-context)
2. [General Architecture](#2-general-architecture)
3. [Project Structure](#3-project-structure)
4. [Installation and Configuration](#4-installation-and-configuration)
5. [Database](#5-database)
6. [Report Generation Pipeline](#6-report-generation-pipeline)
7. [Transfer System](#7-transfer-system)
8. [API Endpoints](#8-api-endpoints)
9. [Design Decisions](#9-design-decisions)
10. [Cloud Migration](#10-cloud-migration)
11. [Known Limitations](#11-known-limitations)

---

## 1. Problem Context

TALOS is a SaaS platform for inventory, purchasing, and sales management in restaurant groups. Each week, warehouse managers perform a physical count of products, and the system calculates the difference between theoretical stock, based on registered movements, and physical stock, based on the actual count.

Before this API, the audit process had three main problems:

**Manual reporting.** Reports were generated manually every week, consuming hours from the audit team without adding analytical value.

**Limited statistical analysis.** There were no descriptive statistics, outlier detection, or automatic alert classification. Severe issues were mixed with minor discrepancies without prioritization.

**Unregistered transfers.** When a product is physically moved from one warehouse to another without being registered in the system, it appears as a shortage in the origin warehouse and as an unexplained surplus in the destination warehouse. Without a mechanism to detect and register these movements, the report can artificially inflate losses.

---

## 2. General Architecture

```text
Trigger (manual / weekly scheduler)
            |
            v
    FastAPI - reports.py
            |
    +-------+--------+
    |                |
    v                v
MySQL / cloud     transferencia
(clean views)     (confirmed)
    |
    v
DataProcessor
(KPIs, stats, alerts, rankings)
    |
    v
ChartGenerator
(6 matplotlib charts -> base64)
    |
    v
HTMLGenerator
(Jinja2 -> HTML)
    |
    v
PDFGenerator
(Playwright + Chromium -> PDF)
    |
    v
storage/reports/reporte_{id}.pdf
```

The scheduler runs automatically every Sunday at 23:00 Mexico City time. It searches for all finalized inventories from the previous seven days and generates their reports.

---

## 3. Project Structure

```text
AERSA-TALOS-PROJECT/
├── app/
│   ├── main.py                      # Entry point, scheduler, lifecycle
│   ├── config.py                    # Environment variables with pydantic-settings
│   ├── models.py                    # Pydantic models (request/response)
│   │
│   ├── db/
│   │   ├── connection.py            # Async SQLAlchemy pool (MySQL / cloud)
│   │   ├── queries.py               # Main queries over clean views
│   │   └── transferencia_queries.py # CRUD queries for the transferencia table
│   │
│   ├── routers/
│   │   ├── reports.py               # Report-generation endpoints
│   │   └── transferencias.py        # Transfer endpoints + detector
│   │
│   ├── services/
│   │   ├── data_processor.py        # KPIs, statistics, alerts, rankings
│   │   ├── chart_generator.py       # 6 matplotlib charts -> base64 PNG
│   │   ├── html_generator.py        # Jinja2 template rendering
│   │   ├── pdf_generator.py         # Playwright in isolated thread -> PDF
│   │   └── transfer_detector.py     # Automatic transfer detection
│   │
│   └── templates/
│       └── reporte.html             # Jinja2 report template
│
├── sql/
│   ├── view_clean_tables.sql        # Definition of the 4 clean views
│   └── transferencia.sql            # Transfer table
│
├── storage/
│   └── reports/                     # Generated PDFs and HTML files
│
├── .env                             # Environment variables (do not commit)
├── .env.example                     # Environment variable template
└── requirements.txt
```

---

## 4. Installation and Configuration

### Requirements

- Python 3.12+
- MySQL 8.0+ with `caching_sha2_password` support, which requires the `cryptography` package
- Playwright with Chromium installed

### Installation

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Mac/Linux

# 2. Install dependencies
pip install -r requirements.txt
pip install cryptography       # Required for MySQL 8.0 authentication

# 3. Install Chromium for Playwright
playwright install chromium

# 4. Create clean views in MySQL
Get-Content sql/view_clean_tables.sql | mysql -u root -p talos_tecmty   # Windows PowerShell
mysql -u root -p talos_tecmty < sql/view_clean_tables.sql               # Mac/Linux

# 5. Create the transfer table
Get-Content sql/transferencia.sql | mysql -u root -p talos_tecmty       # Windows PowerShell
mysql -u root -p talos_tecmty < sql/transferencia.sql                   # Mac/Linux
```

### Configuration

Copy `.env.example` to `.env` and fill in the variables:

```env
DATABASE_URL=mysql+aiomysql://user:password@localhost:3306/talos_tecmty

APP_ENV=development
STORAGE_LOCAL_PATH=./storage/reports

SCHEDULER_DAY_OF_WEEK=sun
SCHEDULER_HOUR=23
SCHEDULER_MINUTE=0
SCHEDULER_TIMEZONE=America/Mexico_City
```

### Run the Server

```bash
# From the project root, with PYTHONPATH pointing to the current directory
$env:PYTHONPATH = "."                                          # PowerShell
python -m uvicorn app.main:app --reload --reload-dir app
```

The API is available at `http://127.0.0.1:8000`. Interactive documentation is available at `http://127.0.0.1:8000/docs`.

---

## 5. Database

### Clean Views

The `talos_tecmty` database contains records from 822 companies since 2016. Before using it for analysis, the data required a cleaning process documented in `LIMPIEZA.md`. The result is a set of 4 views consumed by the API instead of the raw tables:

| View | What it filters or corrects |
|---|---|
| `vw_inventariomes_limpio` | Excludes inventories with `editando` status and inactive warehouses (`almacen_estatus = 0`) |
| `vw_inventariomesdetalle_limpio` | Replaces nulls with 0, marks outliers (`flag_outlier`), and computes data-quality flags |
| `vw_producto_limpio` | Excludes inactive or hidden products and removes fully null columns |
| `vw_categoria_limpia` | No additional filters required |

**Why views instead of new tables:** views always read the most recent data. If the database is updated, the views update automatically without extra intervention.

### Data-Quality Flags (`vw_inventariomesdetalle_limpio`)

| Flag | Meaning |
|---|---|
| `flag_outlier = 1` | Stock, difference, or adjustment above ±10,000, likely corrupted data |
| `flag_costopromedio_cero = 1` | No average cost available, so monetary amount cannot be computed reliably |
| `flag_stockteorico_no_cuadra = 1` | Stored theoretical stock does not match the expected movement balance |
| `flag_fisico_cero_teorico_positivo = 1` | The system shows available stock, but nothing was physically counted |

Report queries filter out `flag_outlier = 0` and `flag_costopromedio_cero = 0` by default, automatically excluding the products with extreme stock values found in the raw data.

### Transfer Table

This project introduces a new table that did not exist in the original schema:

```sql
transferencia (
    idtransferencia,
    idempresa, transferencia_fecha,
    idsucursal_origen, idalmacen_origen, idinventariomes_origen,
    idsucursal_destino, idalmacen_destino, idinventariomes_destino,
    idproducto, transferencia_cantidad, transferencia_costopromedio, transferencia_importe,
    transferencia_tipo,    -- 'interna' | 'entre_sucursales'
    transferencia_origen,  -- 'manual' | 'detectada'
    transferencia_estatus, -- 'pendiente' | 'confirmada' | 'rechazada'
    transferencia_observaciones,
    idusuario_registra, idusuario_confirma,
    transferencia_createdat, transferencia_updatedat
)
```

---

## 6. Report Generation Pipeline

The pipeline is triggered through `POST /reports/generate` or automatically by the scheduler. It runs in the background through FastAPI `BackgroundTasks` so that the HTTP response is not blocked.

### Step 1 - Data Extraction

```python
header         = await fetch_header(db, idinventariomes)
detalle        = await fetch_detalle(db, idinventariomes)
transferencias = await fetch_transferencias_confirmadas(db, idinventariomes)
```

`fetch_header` joins `vw_inventariomes_limpio` with the raw `inventariomes` table to recover fields not exposed by the view, such as `createdat`, `updatedat`, `xls`, and `pdf`.

`fetch_detalle` uses the 4 clean views with aliases to maintain compatibility with the `DataProcessor`. View column names such as `stockteorico_bd` and `diferencia_bd` are mapped to the names expected by the processor, such as `inventariomesdetalle_stockteorico` and `inventariomesdetalle_diferencia`.

### Step 2 - Processing (`DataProcessor`)

`DataProcessor` is the analytical core of the system. It receives raw query results and produces the complete dictionary required by the Jinja2 template:

- **KPIs:** shortage totals, surplus totals, net balance, review rates
- **Descriptive statistics:** mean, median, standard deviation, IQR, minimum, and maximum, both in units and monetary amount
- **Outliers:** products with z-score >= 2 standard deviations over the monetary-difference distribution
- **Priority alerts:** high (shortages above 150% of the mean), medium (surpluses), low (not reviewed)
- **Top-10 rankings:** largest shortage, largest inventory value, highest turnover
- **Transfer analysis:** gross shortage -> confirmed transfers -> estimated real loss
- **Automatic conclusions:** generated text based on KPIs for the final section of the report

### Step 3 - Charts (`ChartGenerator`)

The chart generator creates 6 matplotlib figures in memory, converts them to PNG, and encodes them in base64. This allows the images to be embedded directly into the HTML as `<img src="data:image/png;base64,...">`.

| Figure | Type | What it shows |
|---|---|---|
| 1 | Pie chart | Inventory composition by category (Food / Drinks / Miscellaneous) |
| 2 | Bar chart | Shortages vs. surpluses in absolute monetary amount |
| 3 | Grouped bar chart | Shortages and surpluses by category |
| 4 | Histogram | Distribution of monetary differences (red = shortage, blue = surplus) |
| 5 | Horizontal bar chart | Top 10 products with the largest shortage |
| 6 | Heatmap | Movement type by category |

**Why matplotlib instead of Plotly/D3:** matplotlib generates static images that can be embedded in the PDF without external dependencies. Plotly and D3 require JavaScript, which is not suitable for a static PDF output.

### Step 4 - HTML Rendering (`HTMLGenerator`)

Jinja2 combines the `DataProcessor` context with the base64 images from `ChartGenerator` and renders the `reporte.html` template. The generated HTML is saved to `storage/reports/reporte_{id}.html`, which is useful for visual debugging in the browser before reviewing the final PDF.

### Step 5 - PDF Generation (`PDFGenerator`)

Playwright launches Chromium, loads the HTML, and exports it as an A4 PDF with margins and formatting.

**Why Playwright instead of WeasyPrint:** WeasyPrint has limited support for modern CSS and requires system dependencies on Windows, such as Pango and Cairo. Playwright uses a real Chromium browser, which ensures the PDF matches the browser rendering.

**Windows asyncio issue:** `asyncio.create_subprocess_exec` and `asyncio.to_thread` can behave differently on Windows inside the FastAPI event loop because `ProactorEventLoop` does not support subprocesses in the same way as Linux. The workaround was to use blocking `subprocess.run` inside a native `threading.Thread`, fully isolated from the FastAPI event loop.

---

## 7. Transfer System

### The Problem

When a product is physically moved from one warehouse to another without being registered in the system, the weekly close reports:

- **Origin warehouse:** shortage, because the product is no longer there
- **Destination warehouse:** surplus, because the product appeared without explanation

Without a mechanism to identify these movements, the report inflates real losses and creates false alerts.

### Three-Part Solution

**1. Manual registration** (`POST /transferencias/`): users can register transfers directly. Manual transfers are automatically created with `confirmada` status.

**2. Automatic detection** (`POST /transferencias/detectar/{idsucursal}`): `TransferDetector` analyzes the most recent closing of a branch and searches for the pattern:

> Product X has a negative difference in warehouse A **and** a positive difference in warehouse B during the same weekly close.

If quantities match within a 15% tolerance threshold, the system registers the transfer as `detectada` with `pendiente` status. It also includes a confidence score (0-100%) based on how closely the quantities match.

**Closing-date synchronization:** in the analyzed branch, and in most branches, all warehouses close on the same day. This simplifies detection because records can be compared by date without variable time windows.

**3. Auditor approval flow:**

```text
Detected (pending)
    |
    +-- PATCH /confirmar -> status: confirmed
    |       -> deducted from shortage in the report
    |
    +-- PATCH /rechazar  -> status: rejected
            -> kept as real loss
```

### Impact on the Report

Section VII of the report shows:

- **Gross shortage:** what inventory reports before adjustments
- **Confirmed transfers:** total validated movement amount
- **Estimated real loss:** `gross_shortage - confirmed_transfers`

Each transfer shows whether it was manually registered or automatically detected.

### Difference Between Review and Transfer

**Review** (`inventariomesdetalle_revisada`): a flag that the warehouse manager marks product by product during the physical count to indicate "I validated this data." It validates the count, not the later audit analysis. In practice, many restaurants do not use this field.

**Confirmed transfer:** an auditor action performed after the weekly close that classifies a shortage as a legitimate movement between warehouses instead of a real loss.

---

## 8. API Endpoints

### Reports

| Method | Route | Description |
|---|---|---|
| `POST` | `/reports/generate` | Generates an inventory report. Runs in the background. |
| `GET` | `/reports/{id}/status` | Checks whether the report is ready (`pending` / `ready`) |
| `GET` | `/reports/{id}/download` | Downloads the generated PDF |

### Transfers

| Method | Route | Description |
|---|---|---|
| `POST` | `/transferencias/` | Registers a manual transfer (`confirmada`) |
| `GET` | `/transferencias/{id}` | Retrieves a specific transfer |
| `GET` | `/transferencias/inventario/{id}` | Lists transfers for an inventory close |
| `GET` | `/transferencias/almacen/{id}` | Lists transfers by warehouse, date, and status |
| `POST` | `/transferencias/detectar/{idsucursal}` | Automatically detects transfers |
| `PATCH` | `/transferencias/{id}/confirmar` | Auditor confirms transfer; deducted from shortage |
| `PATCH` | `/transferencias/{id}/rechazar` | Auditor rejects transfer; kept as real loss |

### System

| Method | Route | Description |
|---|---|---|
| `GET` | `/health` | API and database connection status |
| `GET` | `/docs` | Interactive Swagger documentation |

---

## 9. Design Decisions

### Why FastAPI Instead of Django/Flask

FastAPI is async-native, allowing the API to handle heavy database queries without blocking the server. Its Pydantic-based type system validates request data automatically and generates Swagger documentation without additional code.

### Why Async SQLAlchemy Instead of Raw Queries

SQLAlchemy makes the database engine portable by changing only `DATABASE_URL` in `.env`. The connection pool also handles reconnections and connection recycling.

### Why `BackgroundTasks` Instead of `asyncio.create_task`

`asyncio.create_task` may be cancelled if the HTTP request ends before the task completes. FastAPI `BackgroundTasks` ensures the task runs to completion independently from the request lifecycle.

### Why SQL Aliases Instead of Changing `DataProcessor`

The clean views use different column names from the raw tables, such as `stockteorico_bd` instead of `inventariomesdetalle_stockteorico`. Instead of modifying `DataProcessor`, which is the most complex component, queries map view names into the names expected by the processor through SQL aliases. This keeps the processor independent from whether the data comes from raw tables or views.

### Why a 15% Tolerance Threshold for Transfer Detection

Quantities rarely match exactly because bar movements can include decimal fractions, bottle yields, and loss from spills. A 15% threshold captures likely real transfers with small differences while limiting false positives.

### Why `transferencia_estatus = 'rechazada'` Matters

When an auditor rejects a suggested transfer, they explicitly confirm that it was a real loss. This decision history can later be used to improve the detection algorithm using identified false positives.

---

## 10. Cloud Migration

The architecture is designed to migrate to cloud infrastructure with minimal changes.

### Required Changes

**Database:** change `DATABASE_URL` in `.env`:

```env
# Local MySQL
DATABASE_URL=mysql+aiomysql://user:password@localhost:3306/talos_tecmty
```

**Query migration precautions:**

- `LIMIT n` may need to be replaced by `FETCH FIRST n ROWS ONLY`, depending on the target database.
- `GROUP BY` behavior can differ across SQL engines.
- `IFNULL()` may need to be replaced by an equivalent such as `NVL()` or `COALESCE()`.
- The `_limit()` helper in `queries.py` already handles part of this difference.

**Deployment:** the included Dockerfile is intended to support container-based deployment with a non-root user and integrated health checks.

```bash
docker build -t talos-report-api .
# Push to a container registry and deploy to a container runtime
```

### Suggested Cloud Services

| Component | Suggested service |
|---|---|
| API | Container runtime / container instances |
| Database | Managed relational database |
| Stored PDFs | Object storage |
| Scheduler | Cloud scheduler / functions, or APScheduler for local deployments |

---

## 11. Known Limitations

**`inventariomesdetalle_revisada` is not available in the clean views.** The `vw_inventariomesdetalle_limpio` view does not expose this field. It is recovered through an additional JOIN with the raw table, but in the analyzed inventories the field is 0 for all records, meaning warehouse managers do not use this flag in practice.

**Transfers across branches.** The current detector analyzes one branch at a time. Transfers between different branches require running the detector for each branch and manually cross-checking the results.

**PDF generation on Windows.** PDF generation with Playwright on Windows requires a native `threading.Thread` isolated from FastAPI's event loop due to `ProactorEventLoop` subprocess limitations. In Linux production environments, this workaround is usually not necessary and `asyncio.to_thread` can be used directly.

**No authentication.** The API currently has no authentication. For production, JWT authentication with `python-jose` or an API gateway with OAuth is recommended.

**Non-persistent scheduler.** APScheduler stores jobs in memory. If the server restarts, jobs are reconfigured on startup, but execution history is not recovered. For production, use APScheduler with `SQLAlchemyJobStore` or migrate scheduling to a cloud-native scheduler.

---

Developed for AERSA - TALOS System, Report Generation Module  
Stack: FastAPI · SQLAlchemy · pandas · matplotlib · Jinja2 · Playwright · APScheduler
