"""Fetch each posting's detail page for the fields fit scoring needs.

The search endpoint returns only title/company/location/date. The guest *detail*
endpoint returns the full description plus LinkedIn's own structured criteria
(seniority, employment type, function, industries), which is what makes a
meaningful fit score possible at all.

One request per job, so only ever enrich jobs that have not been enriched.
"""
import argparse
import html as htmllib
import json
import os
import random
import re
import sys
import time
import urllib.request

DETAIL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{}"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

DESC_RE = re.compile(r'description__text.*?<div[^>]*>(.*?)</div>\s*</div>', re.S)
CRIT_RE = re.compile(
    r'description__job-criteria-subheader[^>]*>(.*?)</h3>.*?'
    r'description__job-criteria-text[^>]*>(.*?)</span>', re.S)

# "$80,000 - $110,000", "$80,000.00-$110,000.00", "$45 - $60 per hour"
PAY_RE = re.compile(
    r'\$\s*([\d,]+(?:\.\d+)?)\s*(?:-|–|to)\s*\$?\s*([\d,]+(?:\.\d+)?)', re.I)
HOURLY_RE = re.compile(r'(per hour|/\s*hour|hourly|an hour)', re.I)


def strip_tags(s):
    return htmllib.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or ""))).strip()


def parse_pay(text):
    """Return (min, max) annualized, or (None, None). Ignores nonsense ranges."""
    for m in PAY_RE.finditer(text or ""):
        try:
            lo = float(m.group(1).replace(",", ""))
            hi = float(m.group(2).replace(",", ""))
        except ValueError:
            continue
        if hi < lo:
            continue
        window = text[max(0, m.start() - 60):m.end() + 60]
        if HOURLY_RE.search(window) or (lo < 500 and hi < 500):
            lo, hi = lo * 2080, hi * 2080
        # Below this it is not an annual salary; above it, it is not a salary.
        if 20000 <= lo <= 2000000 and hi <= 2000000:
            return int(lo), int(hi)
    return None, None


def parse_workplace(title, location, description):
    blob = f"{title} {location} {description[:1500]}".lower()
    if re.search(r"\b(fully remote|100% remote|remote position|work from home)\b", blob):
        return "remote"
    if "hybrid" in blob:
        return "hybrid"
    if re.search(r"\b(on-?site|in office|in-person)\b", blob):
        return "onsite"
    if re.search(r"\bremote\b", blob):
        return "remote"
    return None


def fetch(job_id, timeout=25):
    req = urllib.request.Request(DETAIL.format(job_id), headers={
        "User-Agent": UA, "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


def enrich(job, delay=2.0, verbose=True):
    try:
        page = fetch(job["linkedin_job_id"])
    except Exception as exc:
        if verbose:
            print(f"    {job['linkedin_job_id']}: {exc}", file=sys.stderr)
        return None
    m = DESC_RE.search(page)
    description = strip_tags(m.group(1)) if m else ""
    crit = {strip_tags(k).rstrip(":").lower(): strip_tags(v)
            for k, v in CRIT_RE.findall(page)}
    lo, hi = parse_pay(description)
    time.sleep(delay + random.random())
    return {
        "description": description,
        "seniority_level": crit.get("seniority level"),
        "employment_type": crit.get("employment type"),
        "job_function": crit.get("job function"),
        "industries": crit.get("industries"),
        "salary_min": lo, "salary_max": hi,
        "workplace": parse_workplace(job["title"], job.get("location", ""), description),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", default="data/jobs.jsonl")
    ap.add_argument("--out", default="data/jobs.jsonl")
    ap.add_argument("--delay", type=float, default=2.0)
    ap.add_argument("--limit", type=int, default=0, help="0 = no cap")
    args = ap.parse_args()

    with open(args.jobs, encoding="utf-8") as fh:
        jobs = [json.loads(line) for line in fh if line.strip()]

    todo = [j for j in jobs if not j.get("description")]
    if args.limit:
        todo = todo[:args.limit]
    print(f"enriching {len(todo)} of {len(jobs)} jobs")

    ok = 0
    for i, job in enumerate(todo, 1):
        extra = enrich(job, args.delay)
        if extra:
            job.update(extra)
            ok += 1
        if i % 10 == 0 or i == len(todo):
            print(f"  {i}/{len(todo)} ({ok} ok)")

    with open(args.out, "w", encoding="utf-8") as fh:
        for j in jobs:
            fh.write(json.dumps(j, ensure_ascii=False) + "\n")
    priced = sum(1 for j in jobs if j.get("salary_min"))
    print(f"{ok} enriched, {priced} with salary -> {args.out}")


if __name__ == "__main__":
    main()
