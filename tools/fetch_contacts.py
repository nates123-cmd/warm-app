"""Materialize one owner's contacts from Supabase into the jsonl the matcher
expects, so match.py stays identical whether the data came from a CSV on disk
or from what someone imported through the app.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import select  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--owner", required=True)
    ap.add_argument("--out", default="data/contacts.jsonl")
    args = ap.parse_args()

    sources = {s["id"]: s for s in select(
        "warm_sources", {"owner_id": f"eq.{args.owner}", "select": "id,name,trust"})}
    contacts = {c["id"]: c for c in select(
        "warm_contacts",
        {"owner_id": f"eq.{args.owner}", "select": "id,source_id,full_name,person_norm,linkedin_url"})}
    affs = select(
        "warm_affiliations",
        {"owner_id": f"eq.{args.owner}", "select": "contact_id,company_raw,company_norm,role"})

    rows = []
    for a in affs:
        c = contacts.get(a["contact_id"])
        if not c:
            continue
        s = sources.get(c["source_id"], {})
        rows.append({
            "source": s.get("name", "unknown"),
            "full_name": c["full_name"],
            "person_norm": c["person_norm"],
            "linkedin_url": c.get("linkedin_url") or "",
            "email": "",
            "company_raw": a["company_raw"],
            "company_norm": a["company_norm"],
            "role": a.get("role") or "",
        })

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Trust weights live in the DB; hand them to the matcher alongside.
    with open("data/source_weights.json", "w") as fh:
        json.dump({s["name"]: float(s["trust"]) for s in sources.values()}, fh)

    print(f"{len(rows)} affiliations / {len(contacts)} contacts / "
          f"{len(sources)} sources -> {args.out}")


if __name__ == "__main__":
    main()
