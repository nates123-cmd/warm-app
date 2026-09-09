"""Build the local preview fixture from real pipeline output.

Writes to public/ (gitignored) so the preview page can fetch it without the
repo ever carrying real contact names.
"""
import argparse
import json
import os

ap = argparse.ArgumentParser()
ap.add_argument("--jobs", default="data/jobs.jsonl")
ap.add_argument("--matches", default="data/matches.jsonl")
args = ap.parse_args()

best = {}
if os.path.exists(args.matches):
    for line in open(args.matches, encoding="utf-8"):
        m = json.loads(line)
        cur = best.get(m["linkedin_job_id"])
        if cur is None or m["strength"] > cur["strength"]:
            best[m["linkedin_job_id"]] = m

labels = {"nate": "your own network"}
rows = []
for line in open(args.jobs, encoding="utf-8"):
    j = json.loads(line)
    if j.get("fit") in (None, -1):
        continue
    m = best.get(j["linkedin_job_id"])
    rows.append({
        "id": j["linkedin_job_id"], "title": j["title"],
        "company_raw": j["company_raw"], "location": j["location"],
        "url": j["url"], "posted_on": j["posted_on"],
        "fit": j["fit"], "fit_reasons": j.get("fit_reasons") or [],
        "salary_min": j.get("salary_min"), "salary_max": j.get("salary_max"),
        "workplace": j.get("workplace"), "seniority_level": j.get("seniority_level"),
        "contacts_at_company": m["contacts_at_company"] if m else None,
        "contact_name": m["contact_name"] if m else None,
        "contact_role": m["contact_role"] if m else None,
        "strength": m["strength"] if m else None,
        "source_label": labels.get(m["source"], m["source"].title()) if m else None,
    })

rows.sort(key=lambda r: -(r["fit"] or 0))
os.makedirs("public", exist_ok=True)
with open("public/previewData.json", "w", encoding="utf-8") as fh:
    json.dump(rows, fh, indent=1)
print(f"{len(rows)} preview rows -> public/previewData.json")
