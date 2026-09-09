"""Score how well a posting matches what someone actually wants.

Independent of who they know there. Warmth answers "can I get a look in";
fit answers "do I even want this". The feed needs both, and the jobs that
score on both axes are the ones worth acting on first.

Every score carries its reasons, because an unexplained number is not
actionable and cannot be debugged.
"""
import argparse
import json
import os
import re
import sys

HARD_REJECT = -1  # excluded outright, never surfaced as a match


def _has(text, term):
    """Word-boundary containment, so 'lead' does not match 'leadership'."""
    return re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text) is not None


def score(job, crit):
    """Return (fit 0-100 or HARD_REJECT, reasons)."""
    title = (job.get("title") or "").lower()
    desc = (job.get("description") or "").lower()
    reasons = []

    for bad in crit.get("titles_exclude", []):
        if _has(title, bad.lower()):
            return HARD_REJECT, [f"title contains “{bad}”"]
    for bad in crit.get("keywords_bad", []):
        if bad.lower() in desc:
            return HARD_REJECT, [f"description mentions “{bad}”"]

    points = 0

    # Title is the strongest signal available, so it carries the most weight.
    strong = [t for t in crit.get("titles_strong", []) if t.lower() in title]
    target = [t for t in crit.get("titles_target", []) if _has(title, t.lower())]
    if strong:
        points += 45
        reasons.append(f"title matches “{strong[0]}”")
    elif target:
        points += 30
        reasons.append(f"title matches “{target[0]}”")
    else:
        reasons.append("title is not a direct match")

    sen = job.get("seniority_level")
    if sen:
        if sen in crit.get("seniority_avoid", []):
            points -= 15
            reasons.append(f"seniority is {sen}")
        elif sen in crit.get("seniority_target", []):
            points += 12
            reasons.append(f"seniority is {sen}")

    good = [k for k in crit.get("keywords_good", []) if k.lower() in desc]
    if good:
        points += min(len(good) * 3, 21)
        reasons.append(f"{len(good)} matching themes incl. {', '.join(good[:3])}")

    floor = crit.get("min_salary")
    lo, hi = job.get("salary_min"), job.get("salary_max")
    if floor and hi:
        if hi < floor:
            points -= 25
            reasons.append(f"pays up to ${hi:,}, below your floor")
        elif lo and lo >= floor:
            points += 12
            reasons.append(f"pays ${lo:,}–${hi:,}")
        else:
            points += 5
            reasons.append(f"pays ${lo:,}–${hi:,}" if lo else f"pays up to ${hi:,}")
    elif lo and hi:
        reasons.append(f"pays ${lo:,}–${hi:,}")

    pref = crit.get("workplace_pref", "any")
    place = job.get("workplace")
    if pref != "any" and place:
        if place == pref:
            points += 8
            reasons.append(place)
        else:
            points -= 8
            reasons.append(f"{place}, you prefer {pref}")
    elif place:
        reasons.append(place)

    if job.get("employment_type") in ("Contract", "Part-time", "Temporary"):
        points -= 10
        reasons.append(job["employment_type"].lower())

    if not desc:
        # Unenriched: title-only evidence, so keep the score honest.
        points = min(points, 45)
        reasons.append("description not fetched yet")

    return max(0, min(100, points)), reasons


# Calibrated against jobs the person had already saved by hand: those scored
# 57-78, median 66. A 70 cut caught only one of four, so it sat too high.
STRONG = 65
WORTH = 48


def band(fit):
    if fit == HARD_REJECT:
        return "excluded"
    if fit >= STRONG:
        return "strong"
    if fit >= WORTH:
        return "worth a look"
    return "weak"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", default="data/jobs.jsonl")
    ap.add_argument("--profile", required=True, help="path to a profiles/*.json")
    ap.add_argument("--out", default="data/jobs.jsonl")
    ap.add_argument("--show", type=int, default=0)
    args = ap.parse_args()

    with open(args.profile) as fh:
        crit = json.load(fh)["fit_criteria"]
    with open(args.jobs, encoding="utf-8") as fh:
        jobs = [json.loads(line) for line in fh if line.strip()]

    for j in jobs:
        j["fit"], j["fit_reasons"] = score(j, crit)

    with open(args.out, "w", encoding="utf-8") as fh:
        for j in jobs:
            fh.write(json.dumps(j, ensure_ascii=False) + "\n")

    kept = [j for j in jobs if j["fit"] != HARD_REJECT]
    strong = [j for j in kept if j["fit"] >= STRONG]
    look = [j for j in kept if WORTH <= j["fit"] < STRONG]
    print(f"{len(jobs)} scored: {len(strong)} strong, {len(look)} worth a look, "
          f"{len(kept) - len(strong) - len(look)} weak, "
          f"{len(jobs) - len(kept)} excluded")

    if args.show:
        for j in sorted(kept, key=lambda x: -x["fit"])[:args.show]:
            print(f"\n  {j['fit']:>3}  {j['title'][:58]}")
            print(f"       {j['company_raw']} · {j['location']}")
            print(f"       {'; '.join(j['fit_reasons'][:3])}")


if __name__ == "__main__":
    main()
