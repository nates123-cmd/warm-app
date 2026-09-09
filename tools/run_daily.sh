#!/usr/bin/env bash
# Daily Warm run for every active profile. Cron on the Beelink:
#   30 6 * * * cd ~/apps/warm-app && ./tools/run_daily.sh >> ~/logs/warm.log 2>&1
#
# Required env (~/.config/warm.env, chmod 600 — never in the repo):
#   SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, DATABASE_URL
# Optional: TELEGRAM_BOT_TOKEN, WARM_APP_URL
set -euo pipefail
cd "$(dirname "$0")/.."

[ -f ~/.config/warm.env ] && set -a && . ~/.config/warm.env && set +a
: "${SUPABASE_URL:?}" "${SUPABASE_SERVICE_ROLE_KEY:?}"

echo "=== warm $(date -Is) ==="

# One profile failing must not stop the others.
python3 tools/list_profiles.py | while read -r owner name; do
  python3 tools/run_profile.py --owner "$owner" || echo "!! $name failed"
done
