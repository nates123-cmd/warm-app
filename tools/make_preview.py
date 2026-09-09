"""Build the local preview fixture from real match output.

Writes to public/ (gitignored) so the preview page can fetch it without the
repo ever carrying real contact names.
"""
import json
import os

matches = [json.loads(l) for l in open("data/matches.jsonl", encoding="utf-8")]
labels = {"nate": "your own network"}

best = {}
for m in matches:
    cur = best.get(m["linkedin_job_id"])
    if cur is None or m["strength"] > cur["strength"]:
        best[m["linkedin_job_id"]] = m

rows = [{
    "id": m["linkedin_job_id"], "title": m["title"], "company_raw": m["company_raw"],
    "location": m["location"], "url": m["url"], "posted_on": m["posted_on"],
    "strength": m["strength"], "confidence": m["confidence"],
    "contacts_at_company": m["contacts_at_company"],
    "contact_name": m["contact_name"], "contact_role": m["contact_role"],
    "source_label": labels.get(m["source"], m["source"].title()),
} for m in sorted(best.values(), key=lambda x: -x["strength"])]

os.makedirs("public", exist_ok=True)
with open("public/previewData.json", "w", encoding="utf-8") as fh:
    json.dump(rows, fh, indent=1)
print(f"{len(rows)} preview rows -> public/previewData.json")
