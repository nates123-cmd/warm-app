"""Thin PostgREST helper for the daily job.

The cron runs as the service role and must therefore name the owner explicitly
on every call; RLS is not doing that work here.
"""
import json
import os
import urllib.parse
import urllib.request


def _env():
    return os.environ["SUPABASE_URL"].rstrip("/"), os.environ["SUPABASE_SERVICE_ROLE_KEY"]


def _headers(key, extra=None):
    h = {"apikey": key, "Authorization": f"Bearer {key}",
         "Content-Type": "application/json"}
    if extra:
        h.update(extra)
    return h


def select(table, params, timeout=30):
    """GET rows, following PostgREST's range pagination to the end."""
    url, key = _env()
    out, offset, page = [], 0, 1000
    while True:
        q = dict(params)
        q["limit"] = page
        q["offset"] = offset
        req = urllib.request.Request(
            f"{url}/rest/v1/{table}?{urllib.parse.urlencode(q)}",
            headers=_headers(key))
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            rows = json.load(resp)
        out.extend(rows)
        if len(rows) < page:
            return out
        offset += page


def patch(table, params, body, timeout=30):
    url, key = _env()
    req = urllib.request.Request(
        f"{url}/rest/v1/{table}?{urllib.parse.urlencode(params)}",
        data=json.dumps(body).encode(),
        headers=_headers(key, {"Prefer": "return=minimal"}),
        method="PATCH")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status
