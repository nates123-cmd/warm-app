"""Telegram digest of today's warm jobs, sent through the OpenClaw bot."""
import json
import os
import urllib.parse
import urllib.request


def main():
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat = os.environ["TELEGRAM_CHAT_ID"]
    url = os.environ["SUPABASE_URL"].rstrip("/")
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    owner = os.environ["WARM_OWNER_ID"]

    req = urllib.request.Request(
        f"{url}/rest/v1/warm_feed?owner_id=eq.{owner}&status=eq.new"
        f"&contact_name=not.is.null&order=strength.desc&limit=8",
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        rows = json.load(resp)

    if not rows:
        return

    lines = [f"*{len(rows)} warm job{'s' if len(rows) != 1 else ''}*", ""]
    for r in rows:
        others = (r.get("contacts_at_company") or 1) - 1
        extra = f" +{others}" if others > 0 else ""
        lines.append(f"• {r['title']} — {r['company_raw']}")
        lines.append(f"  {r['contact_name']} via {r.get('source_name')}{extra}")
    lines.append("")
    lines.append(os.environ.get("WARM_APP_URL", ""))

    body = urllib.parse.urlencode({
        "chat_id": chat, "text": "\n".join(lines),
        "parse_mode": "Markdown", "disable_web_page_preview": "true",
    }).encode()
    urllib.request.urlopen(
        urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage", data=body),
        timeout=20).read()
    print(f"sent digest: {len(rows)} jobs")


if __name__ == "__main__":
    main()
