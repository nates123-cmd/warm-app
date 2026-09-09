"""Pull LinkedIn job postings from the public guest endpoint.

No login, no headless browser: /jobs-guest/ serves plain HTML to anonymous
clients. Each card carries the company's LinkedIn slug, which is a far better
join key than the display name.

Rate limits are real. Keep the delay and let f_TPR trim the window instead of
paging deeper.
"""
import argparse
import html as htmllib
import json
import os
import random
import re
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from normalize import norm_company  # noqa: E402

ENDPOINT = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
PAGE_SIZE = 10  # what LinkedIn advances `start` by, regardless of cards returned

CARD_RE = re.compile(r'data-entity-urn="urn:li:jobPosting:(\d+)"')
TITLE_RE = re.compile(r'base-search-card__title">\s*(.*?)\s*</h3>', re.S)
COMPANY_RE = re.compile(
    r'job-search-card-subtitle"[^>]*href="https://www\.linkedin\.com/company/([^"?]+)[^"]*">\s*(.*?)\s*</a>',
    re.S)
LOCATION_RE = re.compile(r'job-search-card__location">\s*(.*?)\s*</span>', re.S)
DATE_RE = re.compile(r'<time[^>]*datetime="([^"]+)"')


def clean(s):
    return htmllib.unescape(re.sub(r"\s+", " ", s or "")).strip()


def fetch(keywords, location, tpr, start, timeout=25):
    qs = urllib.parse.urlencode({
        "keywords": keywords, "location": location,
        "f_TPR": tpr, "start": start,
    })
    req = urllib.request.Request(f"{ENDPOINT}?{qs}", headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


def parse_cards(page, query_label):
    """Split the page on card boundaries so a missing field can't shift fields
    from the next card into this one."""
    bounds = [m.start() for m in CARD_RE.finditer(page)]
    jobs = []
    for i, pos in enumerate(bounds):
        chunk = page[pos:bounds[i + 1] if i + 1 < len(bounds) else len(page)]
        job_id = CARD_RE.search(chunk).group(1)
        company = COMPANY_RE.search(chunk)
        title = TITLE_RE.search(chunk)
        loc = LOCATION_RE.search(chunk)
        date = DATE_RE.search(chunk)
        if not company or not title:
            continue
        slug = htmllib.unescape(company.group(1)).strip("/")
        name = clean(company.group(2))
        jobs.append({
            "linkedin_job_id": job_id,
            "title": clean(title.group(1)),
            "company_slug": slug,
            "company_raw": name,
            "company_norm": norm_company(name),
            "location": clean(loc.group(1)) if loc else "",
            "posted_on": date.group(1) if date else None,
            "url": f"https://www.linkedin.com/jobs/view/{job_id}",
            "query_label": query_label,
        })
    return jobs


def scrape(keywords, location, tpr="r86400", max_pages=4, delay=2.5, verbose=True):
    seen, out = set(), []
    for page_no in range(max_pages):
        try:
            page = fetch(keywords, location, tpr, page_no * PAGE_SIZE)
        except Exception as exc:  # 429 / transient network
            if verbose:
                print(f"    page {page_no}: {exc}", file=sys.stderr)
            break
        cards = parse_cards(page, f"{keywords} @ {location}")
        fresh = [c for c in cards if c["linkedin_job_id"] not in seen]
        for c in fresh:
            seen.add(c["linkedin_job_id"])
        out.extend(fresh)
        if verbose:
            print(f"    page {page_no}: {len(cards)} cards, {len(fresh)} new")
        # LinkedIn repeats the last page forever instead of returning empty.
        if not cards or not fresh:
            break
        time.sleep(delay + random.random())
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--queries", default="tools/queries.json")
    ap.add_argument("--out", default="data/jobs.jsonl")
    ap.add_argument("--tpr", default="r86400", help="r86400=24h, r604800=7d")
    ap.add_argument("--max-pages", type=int, default=4)
    ap.add_argument("--delay", type=float, default=2.5)
    args = ap.parse_args()

    with open(args.queries) as fh:
        queries = json.load(fh)

    all_jobs, by_id = [], {}
    for q in queries:
        print(f"  {q['keywords']} @ {q['location']}")
        for job in scrape(q["keywords"], q["location"], args.tpr,
                          args.max_pages, args.delay):
            by_id.setdefault(job["linkedin_job_id"], job)
    all_jobs = list(by_id.values())

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        for j in all_jobs:
            fh.write(json.dumps(j, ensure_ascii=False) + "\n")
    print(f"\n{len(all_jobs)} unique jobs / "
          f"{len({j['company_slug'] for j in all_jobs})} companies -> {args.out}")


if __name__ == "__main__":
    main()
