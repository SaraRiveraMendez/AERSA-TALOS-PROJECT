#!/bin/bash
# cron/cron_db.sh
# Re-indexes MySQL data every week.
# Add to crontab: 0 2 * * 0 /bin/bash /home/rene_abraham_calzadilla_calderon/talos-server/cron/cron_db.sh

VENV="/home/rene_abraham_calzadilla_calderon/talos-server/rag/.rag_env/bin/activate"
SCRIPT="/home/rene_abraham_calzadilla_calderon/talos-server/indexers/indexar_db.py"
LOG="/home/rene_abraham_calzadilla_calderon/talos-server/logs/cron_db.log"

mkdir -p "$(dirname "$LOG")"

echo "──────────────────────────────────────" >> "$LOG"
echo "[$(date)] Starting DB re-indexing..." >> "$LOG"

source "$VENV"
python3 "$SCRIPT" >> "$LOG" 2>&1

echo "[$(date)] Done." >> "$LOG"
