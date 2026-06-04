# TALOS Report API

API de generación automática de reportes de auditoría de inventario para el sistema TALOS. Construida con FastAPI + Python, conectada a MySQL (con arquitectura portable a Google Cloud).

---

## Índice

1. [Contexto del problema](#1-contexto-del-problema)
2. [Arquitectura general](#2-arquitectura-general)
3. [Estructura del proyecto](#3-estructura-del-proyecto)
4. [Instalación y configuración](#4-instalación-y-configuración)
5. [Base de datos](#5-base-de-datos)
6. [Pipeline de generación de reportes](#6-pipeline-de-generación-de-reportes)
7. [Sistema de transferencias](#7-sistema-de-transferencias)
8. [Endpoints de la API](#8-endpoints-de-la-api)
9. [Decisiones de diseño](#9-decisiones-de-diseño)
10. [Migración a Google Cloud](#10-migración-a-google-cloud)
11. [Limitaciones conocidas](#11-limitaciones-conocidas)

---

## 1. Contexto del problema

TALOS es una plataforma SaaS de gestión de inventarios, compras y ventas para grupos restauranteros. Cada semana, los encargados de almacén realizan un conteo físico de productos y el sistema calcula las diferencias entre el stock teórico (lo que debería haber según los movimientos registrados) y el stock físico (lo que realmente se contó).

Antes de esta API, el proceso de auditoría tenía tres problemas principales:

**Proceso manual.** Los reportes se generaban a mano cada semana, consumiendo horas del equipo auditor sin agregar valor analítico.

**Sin análisis estadístico.** No existían estadísticos descriptivos, detección de outliers ni clasificación automática de alertas. Los problemas graves se mezclaban con diferencias menores sin priorización.

**Transferencias no registradas.** Cuando un producto se mueve de un almacén a otro sin registrarse en el sistema, aparece como pérdida en el almacén origen y como ganancia inexplicable en el destino. Sin un mecanismo para detectar y registrar estos movimientos, el reporte inflaba artificialmente las pérdidas.

---

## 2. Arquitectura general

```
Trigger (manual / scheduler semanal)
            │
            ▼
    FastAPI — reports.py
            │
    ┌───────┴────────┐
    │                │
    ▼                ▼
MySQL / Google    transferencia
(vistas limpias)   (confirmadas)
    │
    ▼
DataProcessor
(KPIs · stats · alertas · rankings)
    │
    ▼
ChartGenerator
(6 gráficas matplotlib → base64)
    │
    ▼
HTMLGenerator
(Jinja2 → HTML)
    │
    ▼
PDFGenerator
(Playwright + Chromium → PDF)
    │
    ▼
storage/reports/reporte_{id}.pdf
```

El scheduler corre automáticamente cada domingo a las 23:00 (zona horaria México), buscando todos los inventarios finalizados en los últimos 7 días y generando su reporte.

---

## 3. Estructura del proyecto

```
AERSA-TALOS-PROJECT/
├── app/
│   ├── main.py                      # Entry point, scheduler, lifecycle
│   ├── config.py                    # Variables de entorno con pydantic-settings
│   ├── models.py                    # Modelos Pydantic (request/response)
│   │
│   ├── db/
│   │   ├── connection.py            # Pool async SQLAlchemy (MySQL / Google)
│   │   ├── queries.py               # Queries principales sobre vistas limpias
│   │   └── transferencia_queries.py # Queries CRUD de la tabla transferencia
│   │
│   ├── routers/
│   │   ├── reports.py               # Endpoints de generación de reportes
│   │   └── transferencias.py        # Endpoints de transferencias + detector
│   │
│   ├── services/
│   │   ├── data_processor.py        # KPIs, estadísticos, alertas, rankings
│   │   ├── chart_generator.py       # 6 gráficas matplotlib → base64 PNG
│   │   ├── html_generator.py        # Jinja2 render del template
│   │   ├── pdf_generator.py         # Playwright en thread aislado → PDF
│   │   └── transfer_detector.py     # Detección automática de transferencias
│   │
│   └── templates/
│       └── reporte.html             # Template Jinja2 del reporte
│
├── sql/
│   ├── view_clean_tables.sql        # Definición de las 4 vistas limpias
│   └── transferencia.sql            # Tabla de transferencias
│
├── storage/
│   └── reports/                     # PDFs e HTMLs generados
│
├── .env                             # Variables de entorno (no commitear)
├── .env.example                     # Plantilla de variables
└── requirements.txt
```

---

## 4. Instalación y configuración

### Requisitos

- Python 3.12+
- MySQL 8.0+ (con `caching_sha2_password` — requiere el paquete `cryptography`)
- Playwright con Chromium instalado

### Instalación

```bash
# 1. Crear y activar entorno virtual
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Mac/Linux

# 2. Instalar dependencias
pip install -r requirements.txt
pip install cryptography       # Requerido para autenticación MySQL 8.0

# 3. Instalar Chromium para Playwright
playwright install chromium

# 4. Crear las vistas limpias en MySQL
Get-Content sql/view_clean_tables.sql | mysql -u root -p talos_tecmty   # Windows PowerShell
mysql -u root -p talos_tecmty < sql/view_clean_tables.sql               # Mac/Linux

# 5. Crear la tabla de transferencias
Get-Content sql/transferencia.sql | mysql -u root -p talos_tecmty       # Windows PowerShell
mysql -u root -p talos_tecmty < sql/transferencia.sql                   # Mac/Linux
```

### Configuración

Copia `.env.example` a `.env` y llena las variables:

```env
DATABASE_URL=mysql+aiomysql://usuario:password@localhost:3306/talos_tecmty

APP_ENV=development
STORAGE_LOCAL_PATH=./storage/reports

SCHEDULER_DAY_OF_WEEK=sun
SCHEDULER_HOUR=23
SCHEDULER_MINUTE=0
SCHEDULER_TIMEZONE=America/Mexico_City
```

### Levantar el servidor

```bash
# Desde la raíz del proyecto, con PYTHONPATH apuntando al directorio actual
$env:PYTHONPATH = "."                                          # PowerShell
python -m uvicorn app.main:app --reload --reload-dir app
```

La API queda disponible en `http://127.0.0.1:8000`. La documentación interactiva en `http://127.0.0.1:8000/docs`.

---

## 5. Base de datos

### Vistas limpias

La base `talos_tecmty` contiene datos de 822 empresas desde 2016. Antes de usarlos para análisis fue necesario un proceso de limpieza documentado en `LIMPIEZA.md`. El resultado son 4 vistas que la API consume en lugar de las tablas crudas:

| Vista | Qué filtra / corrige |
|---|---|
| `vw_inventariomes_limpio` | Excluye inventarios en estatus `editando` (363 registros abandonados) y almacenes inactivos (`almacen_estatus = 0`) |
| `vw_inventariomesdetalle_limpio` | Reemplaza nulos con 0, marca outliers (`flag_outlier`), calcula flags de calidad de datos |
| `vw_producto_limpio` | Excluye productos dados de baja y ocultos. Elimina columnas 100% nulas |
| `vw_categoria_limpia` | Sin filtros adicionales — ya estaba limpia |

**Por qué vistas y no tablas nuevas:** las vistas leen siempre los datos más recientes. Si la BD se actualiza, las vistas se actualizan automáticamente sin intervención.

### Flags de calidad de datos (`vw_inventariomesdetalle_limpio`)

| Flag | Significado |
|---|---|
| `flag_outlier = 1` | Stock, diferencia o reajuste mayor a ±10,000 — datos probablemente corruptos |
| `flag_costopromedio_cero = 1` | Sin costo promedio, no se puede calcular importe monetario |
| `flag_stockteorico_no_cuadra = 1` | El stock teórico guardado no coincide con la suma de movimientos |
| `flag_fisico_cero_teorico_positivo = 1` | El sistema tiene stock pero no se contó físicamente |

Las queries del reporte filtran `flag_outlier = 0` y `flag_costopromedio_cero = 0` por defecto, excluyendo automáticamente los 29 productos con stocks de millones que existían en los datos crudos.

### Tabla de transferencias

Nueva tabla creada para este proyecto que no existía en el esquema original:

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

## 6. Pipeline de generación de reportes

El pipeline se dispara con `POST /reports/generate` o automáticamente por el scheduler. Corre en background (`BackgroundTasks` de FastAPI) para no bloquear la respuesta HTTP.

### Paso 1 — Extracción de datos

```python
header         = await fetch_header(db, idinventariomes)
detalle        = await fetch_detalle(db, idinventariomes)
transferencias = await fetch_transferencias_confirmadas(db, idinventariomes)
```

`fetch_header` hace JOIN entre `vw_inventariomes_limpio` y la tabla cruda `inventariomes` para recuperar campos que la vista no expone (`createdat`, `updatedat`, `xls`, `pdf`).

`fetch_detalle` usa las 4 vistas limpias con aliases para mantener compatibilidad con el `DataProcessor`. Los nombres de columna de la vista (`stockteorico_bd`, `diferencia_bd`, etc.) se mapean a los nombres que espera el procesador (`inventariomesdetalle_stockteorico`, `inventariomesdetalle_diferencia`).

### Paso 2 — Procesamiento (`DataProcessor`)

El `DataProcessor` es el núcleo analítico. Recibe los datos crudos y produce un diccionario completo con todos los valores que el template Jinja2 necesita:

- **KPIs:** totales de faltantes, sobrantes, balance neto, tasas de revisión
- **Estadísticos descriptivos:** media, mediana, desviación estándar, IQR, mínimo, máximo — tanto en unidades como en importe
- **Outliers:** productos con z-score ≥ 2σ sobre la distribución de diferencias en importe
- **Alertas por prioridad:** alta (faltantes > 150% de la media), media (sobrantes), baja (sin revisar)
- **Rankings top-10:** mayor faltante, mayor valor de inventario, mayor rotación
- **Análisis de transferencias:** faltante bruto → transferencias confirmadas → pérdida real estimada
- **Conclusiones automáticas:** textos generados en función de los KPIs para la sección final del reporte

### Paso 3 — Gráficas (`ChartGenerator`)

Genera 6 gráficas con matplotlib en memoria (sin escribir archivos temporales), las convierte a PNG y las codifica en base64. Esto permite incrustarlas directamente en el HTML como `<img src="data:image/png;base64,...">`.

| Figura | Tipo | Qué muestra |
|---|---|---|
| 1 | Pie | Composición del inventario por categoría (Alimentos / Bebidas / Misceláneos) |
| 2 | Barras | Faltantes vs Sobrantes en importe absoluto |
| 3 | Barras agrupadas | Faltantes y sobrantes por categoría |
| 4 | Histograma | Distribución de diferencias en importe (rojo = faltante, azul = sobrante) |
| 5 | Barras horizontales | Top 10 productos con mayor faltante |
| 6 | Heatmap | Movimientos por tipo × categoría |

**Por qué matplotlib y no Plotly/D3:** matplotlib genera imágenes estáticas que se incrustan en el PDF sin dependencias externas. Plotly y D3 requieren JavaScript, lo cual es incompatible con PDF estático.

### Paso 4 — Renderizado HTML (`HTMLGenerator`)

Jinja2 combina el contexto del `DataProcessor` con las imágenes base64 del `ChartGenerator` y renderiza el template `reporte.html`. El HTML generado se guarda en `storage/reports/reporte_{id}.html` — útil para depuración visual en el navegador antes de revisar el PDF.

### Paso 5 — Generación del PDF (`PDFGenerator`)

Playwright lanza Chromium, carga el HTML y lo exporta como PDF con márgenes y formato A4. 

**Por qué Playwright y no WeasyPrint:** WeasyPrint tiene soporte limitado de CSS moderno y en Windows requiere dependencias del sistema (Pango, Cairo) que son difíciles de instalar. Playwright usa Chromium real, lo que garantiza que el PDF se ve exactamente igual que en el navegador.

**Problema de Windows con asyncio:** `asyncio.create_subprocess_exec` y `asyncio.to_thread` no funcionan correctamente en Windows dentro del event loop de FastAPI porque el `ProactorEventLoop` no soporta subprocesos de la misma manera que en Linux. La solución fue usar `subprocess.run` (bloqueante) dentro de un `threading.Thread` nativo, completamente aislado del event loop de FastAPI.

---

## 7. Sistema de transferencias

### El problema

Cuando un producto se mueve físicamente de un almacén a otro sin registrarse en el sistema, el cierre semanal reporta:
- **Almacén origen:** faltante (el producto ya no está)
- **Almacén destino:** sobrante (el producto apareció sin explicación)

Sin un mecanismo para identificar estos movimientos, el reporte infla las pérdidas reales y genera alertas falsas.

### Solución en tres partes

**1. Registro manual** (`POST /transferencias/`): los usuarios pueden registrar transferencias directamente. Las manuales quedan automáticamente con estatus `confirmada`.

**2. Detección automática** (`POST /transferencias/detectar/{idsucursal}`): el `TransferDetector` analiza el cierre más reciente de una sucursal buscando el patrón:

> Producto X tiene diferencia negativa en almacén A **Y** diferencia positiva en almacén B en el mismo cierre semanal.

Si las cantidades coinciden dentro de un umbral de tolerancia del 15%, registra la transferencia como `detectada` con estatus `pendiente`. Incluye un score de confianza (0-100%) basado en qué tan bien coinciden las cantidades.

**Sincronía de cierres:** en la sucursal analizada (y en la mayoría de las sucursales), todos los almacenes cierran el mismo día. Esto simplifica la detección porque basta comparar por fecha sin necesidad de ventanas de tiempo variables.

**3. Flujo de aprobación del auditor:**

```
Detectada (pendiente)
    │
    ├── PATCH /confirmar → estatus: confirmada
    │       → se descuenta del faltante en el reporte
    │
    └── PATCH /rechazar  → estatus: rechazada
            → se mantiene como pérdida real
```

### Impacto en el reporte

La sección VII del reporte muestra:

- **Faltante bruto:** lo que reporta el inventario antes de ajustes
- **Transferencias confirmadas:** importe total de movimientos validados
- **Pérdida real estimada:** `faltante_bruto - transferencias_confirmadas`

Cada transferencia muestra si fue registrada manualmente o detectada automáticamente.

### Diferencia entre revisión y transferencia

**Revisión** (`inventariomesdetalle_revisada`): flag que el encargado del almacén marca producto por producto durante el conteo físico para indicar "validé este dato". Es una validación del conteo, no del análisis posterior. En la práctica, muchos restaurantes no usan este campo.

**Transferencia confirmada**: acción del auditor durante el análisis posterior al cierre, que clasifica un faltante como movimiento legítimo entre almacenes en lugar de pérdida real.

---

## 8. Endpoints de la API

### Reportes

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/reports/generate` | Genera reporte de un inventario. Corre en background. |
| `GET` | `/reports/{id}/status` | Consulta si el reporte está listo (`pending` / `ready`) |
| `GET` | `/reports/{id}/download` | Descarga el PDF generado |

### Transferencias

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/transferencias/` | Registra transferencia manual (queda `confirmada`) |
| `GET` | `/transferencias/{id}` | Consulta una transferencia específica |
| `GET` | `/transferencias/inventario/{id}` | Lista transferencias de un cierre |
| `GET` | `/transferencias/almacen/{id}` | Lista por almacén, fecha y estatus |
| `POST` | `/transferencias/detectar/{idsucursal}` | Detecta transferencias automáticamente |
| `PATCH` | `/transferencias/{id}/confirmar` | Auditor confirma (descuenta del faltante) |
| `PATCH` | `/transferencias/{id}/rechazar` | Auditor rechaza (era pérdida real) |

### Sistema

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/health` | Estado de la API y conexión a BD |
| `GET` | `/docs` | Documentación interactiva Swagger |

---

## 9. Decisiones de diseño

### Por qué FastAPI y no Django/Flask

FastAPI es async nativo, lo que permite manejar queries pesadas a la BD sin bloquear el servidor. El sistema de tipos con Pydantic valida automáticamente los datos de entrada y genera la documentación Swagger sin código adicional.

### Por qué SQLAlchemy async y no queries directas

SQLAlchemy permite cambiar el motor de BD (MySQL → Nube) cambiando únicamente el `DATABASE_URL` en `.env`, sin modificar ninguna query. El pool de conexiones maneja reconexiones automáticas y reciclado de conexiones.

### Por qué `BackgroundTasks` y no `asyncio.create_task`

`asyncio.create_task` puede cancelarse si el request HTTP termina antes de que el task complete. `BackgroundTasks` de FastAPI garantiza que el task corre hasta completarse independientemente del ciclo de vida del request.

### Por qué las queries usan alias en lugar de cambiar el DataProcessor

Las vistas limpias tienen nombres de columna distintos a las tablas crudas (`stockteorico_bd` en lugar de `inventariomesdetalle_stockteorico`). En lugar de cambiar el `DataProcessor` — que es el componente más complejo — las queries mapean los nombres de las vistas a los nombres que espera el procesador mediante aliases SQL. Así el `DataProcessor` no sabe si los datos vienen de tablas o vistas.

### Por qué el detector usa umbral de tolerancia del 15%

Las cantidades raramente coinciden exactamente porque los movimientos de barra incluyen fracciones decimales (rendimientos de botellas, mermas por derrame). Un umbral del 15% captura transferencias reales con pequeñas diferencias sin generar demasiados falsos positivos.

### Por qué `transferencia_estatus = 'rechazada'` es tan importante como `'confirmada'`

Cuando el auditor rechaza una transferencia sugerida por el detector, está confirmando explícitamente que **era una pérdida real**. Esto alimenta el historial de decisiones y permite mejorar el algoritmo de detección en el futuro con los falsos positivos identificados.

---

## 10. Migración a Google Cloud

La arquitectura está diseñada para migrar a Google Cloud con cambios mínimos:

### Cambios necesarios

**Base de datos:** cambiar `DATABASE_URL` en `.env`:
```
# MySQL (actual)
DATABASE_URL=mysql+aiomysql://usuario:password@localhost:3306/talos_tecmty


**Precauciones al migrar queries a Google Cloud:**
- `LIMIT n` → `FETCH FIRST n ROWS ONLY`
- `GROUP BY` sin agregados (MySQL lo permite, Google no)
- `IFNULL()` → `NVL()`
- La función `_limit()` en `queries.py` ya maneja esta diferencia automáticamente


**Despliegue:** el `Dockerfile` incluido está listo para O Container Instances con multi-stage build, usuario no-root y health check integrado:

```bash
docker build -t talos-report-api .
# Subir a OCI Container Registry y desplegar en Container Instances
```

### Servicios de Google Cloud recomendados

| Componente | Servicio GC |
|---|---|
| API | Container Instances |
| Base de datos | Autonomous Database (Transaction Processing) |
| PDFs almacenados | Object Storage |
| Scheduler | OCI Functions + Events (alternativa al APScheduler interno) |

---

## 11. Limitaciones conocidas

**`inventariomesdetalle_revisada` no disponible en vistas limpias.** La vista `vw_inventariomesdetalle_limpio` no expone este campo. Se recupera mediante un JOIN adicional a la tabla cruda, pero en los inventarios analizados el campo es 0 en todos los registros — los encargados de almacén no usan ese flag en la práctica.

**Detección de transferencias entre sucursales.** El detector actual solo analiza una sucursal a la vez. Las transferencias entre sucursales distintas requieren correr el detector para cada sucursal y cruzar los resultados manualmente.

**PDFs en Windows.** La generación de PDFs con Playwright en Windows requiere ejecutarse en un thread nativo (`threading.Thread`) completamente aislado del event loop de FastAPI, debido a limitaciones del `ProactorEventLoop` de Windows con subprocesos. En Linux (producción en OCI) este workaround no es necesario y se puede usar `asyncio.to_thread` directamente.

**Sin autenticación.** La API actualmente no tiene autenticación. Para producción en Google Cloud se recomienda agregar JWT con `python-jose` o usar OCI API Gateway con autenticación OAuth.

**Scheduler no persistente.** APScheduler almacena los jobs en memoria. Si el servidor se reinicia, el scheduler reconfigura los jobs al arrancar pero no recupera el historial de ejecuciones. Para producción se recomienda usar `APScheduler` con `SQLAlchemyJobStore` o migrar a OCI Functions.

---

*Desarrollado para AERSA — Sistema TALOS, Módulo de Generación de Reportes*
*Stack: FastAPI · SQLAlchemy · pandas · matplotlib · Jinja2 · Playwright · APScheduler*