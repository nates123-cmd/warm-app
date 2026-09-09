"""Telegram digest of new warm jobs, one message per profile.

Only sends jobs that have never been sent before, so the same opening never
shows up twice even if it is still sitting untriaged.
"""
import argparse
import json
import os
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import patch, select  # noqa: E402

MAX_JOBS = 10
STRONG = 65   # keep in step with tools/fit.py and src/lib/useFeed.js


def send(token, chat_id, text):
    body = urllib.parse.urlencode({
        "chat_id": chat_id, "text": text,
        "parse_mode": "HTML", "disable_web_page_preview": "true",
    }).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage", data=body)
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.load(resp)


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--owner", required=True)
    ap.add_argument("--chat-id", required=True)
    ap.add_argument("--name", default="")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token and not args.dry_run:
        raise SystemExit("TELEGRAM_BOT_TOKEN not set")
    app_url = os.environ.get("WARM_APP_URL", "")

    # Worth sending on either axis: someone you know there, or a job that
    # closely matches what you are looking for.
    rows = select("warm_feed", {
        "owner_id": f"eq.{args.owner}",
        "status": "eq.new",
        "digest_sent_at": "is.null",
        "or": f"(contact_name.not.is.null,fit.gte.{STRONG})",
        "select": "id,title,company_raw,location,url,contact_name,contact_role,"
                  "source_name,contacts_at_company,strength,fit,salary_min,"
                  "salary_max,workplace",
    })
    # Both axes first, then warm, then fit.
    rows.sort(key=lambda r: (
        -(1 if r.get("contact_name") and (r.get("fit") or 0) >= STRONG else 0),
        -(r.get("strength") or 0),
        -(r.get("fit") or 0),
    ))
    if not rows:
        print(f"{args.name or args.owner}: nothing new")
        return

    top = rows[:MAX_JOBS]
    warm = sum(1 for r in rows if r.get("contact_name"))
    lines = [f"<b>{len(rows)} new job{'s' if len(rows) != 1 else ''} worth a look</b>"]
    if warm:
        lines.append(f"<i>{warm} where you know someone</i>")
    lines.append("")

    for r in top:
        lines.append(f'<a href="{r["url"]}">{esc(r["title"])}</a>')
        meta = esc(r["company_raw"])
        if r.get("location"):
            meta += f" · {esc(r['location'])}"
        lines.append(meta)

        bits = []
        if (r.get("fit") or 0) >= STRONG:
            bits.append("strong match")
        if r.get("salary_min") and r.get("salary_max"):
            bits.append(f"${r['salary_min'] // 1000}k–${r['salary_max'] // 1000}k")
        if r.get("workplace"):
            bits.append(r["workplace"])
        if bits:
            lines.append(" · ".join(bits))

        if r.get("contact_name"):
            others = (r.get("contacts_at_company") or 1) - 1
            extra = f" (+{others} more there)" if others > 0 else ""
            role = f" · {esc(r['contact_role'])}" if r.get("contact_role") else ""
            lines.append(f"↳ {esc(r['contact_name'])}{role} — via {esc(r['source_name'])}{extra}")
        lines.append("")
    if len(rows) > MAX_JOBS:
        lines.append(f"…and {len(rows) - MAX_JOBS} more.")
    if app_url:
        lines.append(f'<a href="{app_url}">Open Warm</a>')

    text = "\n".join(lines)
    if args.dry_run:
        print(text)
        return

    send(token, args.chat_id, text)
    # Mark only what was actually listed; the remainder rolls into tomorrow.
    ids = ",".join(r["id"] for r in top)
    patch("warm_jobs",
          {"owner_id": f"eq.{args.owner}", "id": f"in.({ids})"},
          {"digest_sent_at": "now()"})
    print(f"{args.name or args.owner}: sent {len(top)} of {len(rows)}")


if __name__ == "__main__":
    main()
