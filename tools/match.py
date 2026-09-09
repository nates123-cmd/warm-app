"""Join scraped jobs to contact affiliations, and rank by connection strength.

Two things this gets right that a spreadsheet does not:

1. Fuzzy company matching on *distinctive* tokens only. Raw string similarity
   pairs "Bowman Consulting" with "Grogan Consulting" and "IQVIA" with "Visa",
   because generic industry words dominate the comparison.

2. Ranking. Presence of a connection is not the signal; a mentor on the board of
   a 40-person firm beats being one of 50 acquaintances at Amazon.
"""
import argparse
import collections
import json
import math
import re
from difflib import SequenceMatcher

AUTO = 0.90    # at or above on core tokens: same company
REVIEW = 0.78  # between: ask once, remember forever via the alias table

# Words that say what an industry is, not which company this is.
GENERIC = {
    "consulting", "associates", "partners", "management", "residential",
    "construction", "technologies", "technology", "solutions", "services",
    "systems", "capital", "ventures", "advisors", "advisory", "media",
    "national", "industries", "enterprises", "labs", "studio", "studios",
    "digital", "health", "healthcare", "financial", "insurance", "bank",
    "software", "engineering", "design", "development", "properties",
    "realty", "real", "estate", "energy", "resources", "communications",
}

# Roles that carry real pull. Ordered: first hit wins.
SENIORITY = [
    (re.compile(r"\b(founder|co-?founder|owner)\b", re.I), 5),
    (re.compile(r"\b(board|trustee|chair|chairperson|chairman)\b", re.I), 5),
    (re.compile(r"\b(ceo|coo|cfo|cto|cio|cmo|chief)\b", re.I), 4),
    (re.compile(r"\b(president|partner|managing director)\b", re.I), 4),
    (re.compile(r"\b(vp|vice president|svp|evp|head of|head)\b", re.I), 3),
    (re.compile(r"\b(director|principal)\b", re.I), 2),
    (re.compile(r"\b(manager|lead|senior)\b", re.I), 1),
]


def core(norm):
    """Drop generic industry words, keeping what actually identifies the firm."""
    toks = [t for t in norm.split() if t not in GENERIC]
    return " ".join(toks) if toks else norm


def plausible(a, b):
    """Guard the fuzzy match against short-string coincidence.

    "thermo" vs "hero" scores 0.80 and "nbcuniversal" vs "universal" scores
    0.86 on raw similarity, but neither is the same company. Require a shared
    real token, or near-identity when both sides are a single word.
    """
    ta, tb = set(a.split()), set(b.split())
    if any(t in tb for t in ta if len(t) >= 4):
        return True
    return len(ta) == 1 and len(tb) == 1 and SequenceMatcher(None, a, b).ratio() >= 0.93


def seniority(role):
    for pattern, score in SENIORITY:
        if pattern.search(role or ""):
            return score
    return 0


def load(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def strength(contact, contacts_at_company, source_weights):
    """Higher is a better intro. Rarity dominates; seniority breaks ties."""
    rarity = 1.0 / math.log(contacts_at_company + math.e - 1)
    return round(
        rarity * 6.0
        + seniority(contact.get("role")) * 1.2
        + source_weights.get(contact["source"], 1.0) * 2.0,
        3,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", default="data/jobs.jsonl")
    ap.add_argument("--contacts", default="data/contacts.jsonl")
    ap.add_argument("--aliases", default="data/aliases.json")
    ap.add_argument("--out", default="data/matches.jsonl")
    ap.add_argument("--review-out", default="data/review_queue.jsonl")
    args = ap.parse_args()

    jobs, contacts = load(args.jobs), load(args.contacts)

    # LinkedIn lists the same opening repeatedly under fresh job ids.
    deduped, seen_posting = [], set()
    for j in sorted(jobs, key=lambda x: x.get("posted_on") or ""):
        key = (j["company_slug"], re.sub(r"[^a-z0-9]+", " ", j["title"].lower()).strip())
        if key in seen_posting:
            continue
        seen_posting.add(key)
        deduped.append(j)
    dupes = len(jobs) - len(deduped)
    jobs = deduped
    try:
        with open(args.aliases) as fh:
            aliases = json.load(fh)
    except FileNotFoundError:
        aliases = {}

    # Your own connections are a direct ask; a borrowed network needs a warm
    # handoff first, so it is worth slightly less.
    source_weights = {"nate": 1.5}

    # Dedupe: the same person shows up repeatedly across and within exports.
    by_company = collections.defaultdict(dict)
    for c in contacts:
        key = (c["person_norm"], c["source"])
        prior = by_company[c["company_norm"]].get(key)
        if prior is None or seniority(c["role"]) > seniority(prior["role"]):
            by_company[c["company_norm"]][key] = c
    by_company = {k: list(v.values()) for k, v in by_company.items()}

    core_index = collections.defaultdict(list)
    for k in by_company:
        core_index[core(k)].append(k)

    matches, review, unmatched = [], [], 0
    for job in jobs:
        norm = aliases.get(job["company_norm"], job["company_norm"])
        hits, confidence = by_company.get(norm, []), "exact"

        if not hits:
            jc = core(norm)
            best, best_score = None, 0.0
            for ck, originals in core_index.items():
                if not plausible(jc, ck):
                    continue
                score = SequenceMatcher(None, jc, ck).ratio()
                if score > best_score:
                    best, best_score = originals[0], score
            if best and best_score >= AUTO:
                hits, confidence = by_company[best], "fuzzy"
            elif best and best_score >= REVIEW:
                review.append({
                    "linkedin_job_id": job["linkedin_job_id"],
                    "title": job["title"],
                    "job_company": job["company_raw"],
                    "job_company_norm": job["company_norm"],
                    "candidate_norm": best,
                    "candidate_example": by_company[best][0]["company_raw"],
                    "contact_count": len(by_company[best]),
                    "score": round(best_score, 3),
                })
                unmatched += 1
                continue
            else:
                unmatched += 1
                continue

        n = len(hits)
        for c in hits:
            matches.append({
                "linkedin_job_id": job["linkedin_job_id"],
                "title": job["title"], "company_raw": job["company_raw"],
                "company_slug": job["company_slug"],
                "location": job["location"], "url": job["url"],
                "posted_on": job["posted_on"],
                "contact_name": c["full_name"], "contact_role": c["role"],
                "person_norm": c["person_norm"],
                "contact_company": c["company_raw"],
                "source": c["source"], "linkedin_url": c["linkedin_url"],
                "confidence": confidence,
                "strength": strength(c, n, source_weights),
                "contacts_at_company": n,
            })

    matches.sort(key=lambda m: -m["strength"])
    for path, rows in ((args.out, matches), (args.review_out, review)):
        with open(path, "w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    best_per_job = {}
    for m in matches:
        cur = best_per_job.get(m["linkedin_job_id"])
        if cur is None or m["strength"] > cur["strength"]:
            best_per_job[m["linkedin_job_id"]] = m

    print(f"{len(jobs)} jobs scanned ({dupes} duplicate postings collapsed)")
    print(f"  {len(best_per_job)} with a warm connection ({len(matches)} pairs)")
    print(f"  {len(review)} queued for review")
    print(f"  {unmatched - len(review)} no connection\n")
    print("  ranked by intro strength:")
    for m in sorted(best_per_job.values(), key=lambda x: -x["strength"])[:14]:
        who = f"{m['contact_name']} ({m['source']})"
        extra = f" +{m['contacts_at_company'] - 1}" if m["contacts_at_company"] > 1 else ""
        print(f"    {m['strength']:>5}  {m['company_raw'][:20]:<20} {m['title'][:34]:<34} "
              f"{who[:28]:<28}{extra}")
    if review:
        print("\n  review queue:")
        for r in review:
            print(f"    {r['job_company'][:28]:<28} ~ {r['candidate_example'][:28]:<28} {r['score']}")


if __name__ == "__main__":
    main()
