#!/bin/bash
# cron/cron_pdf.sh
# Indexes the most recent PDF report from the reports folder.
# Add to crontab: 0 3 * * 0 /bin/bash /home/rene_abraham_calzadilla_calderon/talos-server/cron/cron_pdf.sh

VENV="/home/rene_abraham_calzadilla_calderon/talos-server/rag/.rag_env/bin/activate"
SCRIPT="/home/rene_abraham_calzadilla_calderon/talos-server/indexers/indexar_pdf.py"
REPORTS_DIR="/home/rene_abraham_calzadilla_calderon/talos-server/reportes"
LOG="/home/rene_abraham_calzadilla_calderon/talos-server/logs/cron_pdf.log"

mkdir -p "$(dirname "$LOG")"
mkdir -p "$REPORTS_DIR"

LATEST_PDF=$(ls -t "$REPORTS_DIR"/*.pdf 2>/dev/null | head -1)

echo "──────────────────────────────────────" >> "$LOG"
echo "[$(date)] Starting PDF indexing..." >> "$LOG"

if [ -z "$LATEST_PDF" ]; then
    echo "[$(date)] No PDF found in $REPORTS_DIR" >> "$LOG"
    exit 1
fi

echo "[$(date)] Processing: $LATEST_PDF" >> "$LOG"

source "$VENV"
python3 "$SCRIPT" "$LATEST_PDF" >> "$LOG" 2>&1

echo "[$(date)] Done." >> "$LOG"
