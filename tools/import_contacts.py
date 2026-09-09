"""Parse LinkedIn connection exports and Sales Navigator scrapes into a single
contact/affiliation table.

Five shapes exist in the wild (see detect_shape). Each yields the same record:
    {source, full_name, linkedin_url, email, company_raw, role}
A contact with several board seats produces several records; that is the point.
"""
import argparse
import csv
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from normalize import norm_company, norm_person  # noqa: E402

csv.field_size_limit(10 ** 7)

OFFICIAL_HEADER = ["first name", "last name", "url"]
def read_rows(path):
    """Return (header, rows), skipping LinkedIn's 3-line 'Notes:' preamble."""
    with open(path, encoding="utf-8-sig", errors="replace", newline="") as fh:
        rows = [r for r in csv.reader(fh) if any(c.strip() for c in r)]
    for i, row in enumerate(rows):
        low = [c.strip().lower() for c in row]
        if low[:3] == OFFICIAL_HEADER:
            return low, rows[i + 1:]
    return [c.strip().lower() for c in rows[0]], rows[1:]


def split_blob(cell):
    """'Sales Director\n   \n   \n   CrowdStrike' -> ('Sales Director', 'CrowdStrike')

    Sales Navigator scrapes glue the headline and the company together with a
    run of blank lines. First non-empty line is the role, last is the company.
    """
    parts = [p.strip() for p in (cell or "").split("\n") if p.strip()]
    if len(parts) >= 2:
        return parts[0], parts[-1]
    return (parts[0] if parts else ""), ""


def row_records(row, header):
    """Extract (company_raw, role) pairs from one scrape row.

    The files are heterogeneous *within* a single export: the company sometimes
    sits in its own column, sometimes only inside a newline blob, and is often
    absent entirely. Prefer the blob, since when both exist the blob is the one
    that is actually populated.
    """
    cells = [(c or "").strip() for c in row]
    idx = {name: i for i, name in enumerate(header)}

    # A blob is any cell carrying an embedded newline.
    for cell in reversed(cells[1:]):
        if "\n" in cell:
            role, company = split_blob(cell)
            if company:
                return [(company, role)]

    # Explicit columns, when the scrape actually filled them in.
    ci, ri = idx.get("company"), idx.get("role")
    if ci is not None and ci < len(cells) and cells[ci]:
        return [(cells[ci], cells[ri] if ri is not None and ri < len(cells) else "")]

    # Bare 3-column name/company/role.
    if len(cells) >= 3 and cells[1] and not cells[1].isdigit():
        return [(cells[1], cells[2])]

    return []


def parse(path, source):
    header, rows = read_rows(path)
    official = header[:3] == OFFICIAL_HEADER
    shape = "official" if official else "scrape"
    out, no_company, no_name = [], 0, 0

    for row in rows:
        def col(i):
            return (row[i].strip() if len(row) > i and row[i] else "")

        if official:
            name = " ".join(x for x in (col(0), col(1)) if x)
            url, email = col(2), col(3)
            recs = [(col(4), col(5))]
        else:
            name, url, email = col(0), "", ""
            recs = row_records(row, header)

        if not name or not norm_person(name):
            no_name += 1
            continue

        emitted = False
        for company_raw, role in recs:
            if not norm_company(company_raw):
                continue
            out.append({
                "source": source,
                "full_name": name,
                "person_norm": norm_person(name),
                "linkedin_url": url,
                "email": email,
                "company_raw": company_raw,
                "company_norm": norm_company(company_raw),
                "role": role,
            })
            emitted = True
        if not emitted:
            no_company += 1

    return shape, out, no_company, no_name


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+", help="path[:source_name] pairs")
    ap.add_argument("--out", default="data/contacts.jsonl")
    args = ap.parse_args()

    all_recs, report = [], []
    for spec in args.files:
        path, _, source = spec.partition(":")
        source = source or os.path.splitext(os.path.basename(path))[0]
        shape, recs, no_company, no_name = parse(path, source)
        report.append((os.path.basename(path), source, shape, len(recs), no_company, no_name))
        all_recs.extend(recs)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        for r in all_recs:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    w = max(len(r[0]) for r in report)
    print(f"{'file'.ljust(w)}  {'source':<10} {'shape':<8} {'kept':>6} {'no-co':>7} {'no-name':>8}")
    for f, s, shape, kept, no_company, no_name in report:
        print(f"{f.ljust(w)}  {s:<10} {shape:<8} {kept:>6} {no_company:>7} {no_name:>8}")
    people = len({(r["source"], r["person_norm"]) for r in all_recs})
    print(f"\n{len(all_recs)} affiliations / {people} people / "
          f"{len({r['company_norm'] for r in all_recs})} distinct companies -> {args.out}")


if __name__ == "__main__":
    main()
