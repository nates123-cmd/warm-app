"""Pull the alias table the app has taught us, so the next match respects it."""
import argparse
import json
import os
import urllib.request


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--owner", default=os.environ.get("WARM_OWNER_ID"))
    ap.add_argument("--out", default="data/aliases.json")
    args = ap.parse_args()

    url = os.environ["SUPABASE_URL"].rstrip("/")
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    owner = args.owner

    req = urllib.request.Request(
        f"{url}/rest/v1/warm_company_aliases"
        f"?owner_id=eq.{owner}&select=alias_norm,canonical_norm",
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        rows = json.load(resp)

    aliases = {r["alias_norm"]: r["canonical_norm"] for r in rows}
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as fh:
        json.dump(aliases, fh, indent=1)
    print(f"{len(aliases)} aliases -> {args.out}")


if __name__ == "__main__":
    main()
