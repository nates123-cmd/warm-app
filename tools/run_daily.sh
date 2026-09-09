#!/usr/bin/env bash
# Daily Warm run. Cron this on the Beelink:
#   30 6 * * * cd ~/apps/warm-app && ./tools/run_daily.sh >> ~/logs/warm.log 2>&1
#
# Required env (keep in ~/.config/warm.env, chmod 600 — never in the repo):
#   SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, WARM_OWNER_ID, DATABASE_URL
# Optional: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, WARM_APP_URL
set -euo pipefail
cd "$(dirname "$0")/.."

[ -f ~/.config/warm.env ] && set -a && . ~/.config/warm.env && set +a

: "${SUPABASE_URL:?}" "${SUPABASE_SERVICE_ROLE_KEY:?}" "${WARM_OWNER_ID:?}" "${DATABASE_URL:?}"

echo "=== warm $(date -Is) ==="

python3 tools/fetch_aliases.py
python3 tools/scrape_jobs.py --tpr r86400 --max-pages 4
python3 tools/match.py
python3 tools/load_supabase.py --owner "$WARM_OWNER_ID"

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -q -f data/load.sql
echo "loaded"

if [ -n "${TELEGRAM_BOT_TOKEN:-}" ]; then
  python3 tools/digest.py || echo "digest failed (non-fatal)"
fi
