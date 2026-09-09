"""Run the full pipeline for one profile: scrape their queries, match against
their contacts, load, and optionally send their digest.
"""
import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import select  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(*cmd):
    subprocess.run([sys.executable, *cmd], cwd=ROOT, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--owner", required=True)
    ap.add_argument("--tpr", default="r86400")
    ap.add_argument("--max-pages", type=int, default=4)
    ap.add_argument("--skip-digest", action="store_true")
    ap.add_argument("--skip-enrich", action="store_true")
    args = ap.parse_args()

    profiles = select("warm_profiles", {"owner_id": f"eq.{args.owner}", "select": "*"})
    if not profiles:
        print(f"no profile for {args.owner}", file=sys.stderr)
        return 1
    p = profiles[0]
    name = p.get("display_name") or args.owner[:8]
    queries = p.get("queries") or []
    if not queries:
        print(f"{name}: no queries configured, skipping")
        return 0

    print(f"--- {name}: {len(queries)} quer{'y' if len(queries) == 1 else 'ies'} ---")

    qpath = os.path.join(ROOT, "data", f"queries_{args.owner}.json")
    os.makedirs(os.path.dirname(qpath), exist_ok=True)
    with open(qpath, "w") as fh:
        json.dump(queries, fh)

    run("tools/fetch_aliases.py", "--owner", args.owner)
    run("tools/fetch_contacts.py", "--owner", args.owner)
    run("tools/scrape_jobs.py", "--queries", qpath,
        "--tpr", args.tpr, "--max-pages", str(args.max_pages))

    # Fit needs the description, which only the detail endpoint carries.
    if not args.skip_enrich:
        run("tools/enrich_jobs.py")
    crit_path = os.path.join(ROOT, "data", f"criteria_{args.owner}.json")
    with open(crit_path, "w") as fh:
        json.dump({"fit_criteria": p.get("fit_criteria") or {}}, fh)
    run("tools/fit.py", "--profile", crit_path)

    run("tools/match.py")
    run("tools/load_supabase.py", "--owner", args.owner)

    load_sql = os.path.join(ROOT, "data", "load.sql")
    if os.environ.get("DATABASE_URL"):
        cmd = ["psql", os.environ["DATABASE_URL"], "-v", "ON_ERROR_STOP=1", "-q", "-f", load_sql]
    else:
        cmd = ["supabase", "db", "query", "--linked", "-f", load_sql]
    subprocess.run(cmd, cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    print(f"{name}: loaded")

    if args.skip_digest or not p.get("digest_enabled") or not p.get("telegram_chat_id"):
        return 0
    if not os.environ.get("TELEGRAM_BOT_TOKEN"):
        print(f"{name}: no bot token, digest skipped")
        return 0
    try:
        run("tools/digest.py", "--owner", args.owner,
            "--chat-id", str(p["telegram_chat_id"]), "--name", name)
    except subprocess.CalledProcessError:
        print(f"{name}: digest failed (non-fatal)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
