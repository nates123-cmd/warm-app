"""Print `owner_id display_name` for each active profile, for run_daily.sh."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import select  # noqa: E402

for p in select("warm_profiles", {"active": "eq.true", "select": "owner_id,display_name"}):
    print(p["owner_id"], (p.get("display_name") or "?").replace(" ", "_"))
