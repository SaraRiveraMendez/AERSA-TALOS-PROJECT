# ── Build stage ────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Dependencias del sistema para WeasyPrint (renderizado PDF)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt


# ── Runtime stage ───────────────────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Solo las libs de sistema que necesita WeasyPrint en runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libgdk-pixbuf2.0-0 \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Copiar paquetes instalados desde el builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copiar código fuente
COPY app/ ./app/
COPY .env.example .env

# Directorio para almacenar PDFs generados (mount en OCI)
RUN mkdir -p /app/storage/reports

# Usuario no-root para producción
RUN useradd -m -u 1000 talos && chown -R talos:talos /app
USER talos

EXPOSE 8000

# Health check para OCI Container Instances
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]