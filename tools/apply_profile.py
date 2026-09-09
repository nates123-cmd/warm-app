"""Push a profiles/*.json into warm_profiles once that person has signed in.

They have to sign in themselves first — the OTP flow is what creates their
auth user. This then attaches their searches and fit criteria to it.
"""
import argparse
import json
import os
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import _env, _headers, select  # noqa: E402


def find_user(email):
    url, key = _env()
    req = urllib.request.Request(
        f"{url}/auth/v1/admin/users?{urllib.parse.urlencode({'page': 1, 'per_page': 200})}",
        headers=_headers(key))
    with urllib.request.urlopen(req, timeout=25) as resp:
        users = json.load(resp).get("users", [])
    for u in users:
        if (u.get("email") or "").lower() == email.lower():
            return u["id"]
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", required=True)
    ap.add_argument("--email", required=True)
    args = ap.parse_args()

    with open(args.profile) as fh:
        prof = json.load(fh)

    owner = find_user(args.email)
    if not owner:
        raise SystemExit(
            f"No account for {args.email} yet. Have them open the app and sign in "
            f"with that address once, then re-run this.")

    url, key = _env()
    body = json.dumps({
        "owner_id": owner,
        "display_name": prof.get("display_name"),
        "queries": prof.get("queries", []),
        "fit_criteria": prof.get("fit_criteria", {}),
        "active": True,
    }).encode()
    req = urllib.request.Request(
        f"{url}/rest/v1/warm_profiles?on_conflict=owner_id", data=body,
        headers=_headers(key, {"Prefer": "resolution=merge-duplicates,return=minimal"}),
        method="POST")
    with urllib.request.urlopen(req, timeout=25) as resp:
        status = resp.status

    print(f"{prof.get('display_name')} ({owner[:8]}…): {len(prof.get('queries', []))} "
          f"searches, {len(prof.get('fit_criteria', {}))} criteria keys — HTTP {status}")
    existing = select("warm_sources", {"owner_id": f"eq.{owner}", "select": "name"})
    if not existing:
        print("  no connection sources yet — import their CSVs in the app's Import tab")


if __name__ == "__main__":
    main()
