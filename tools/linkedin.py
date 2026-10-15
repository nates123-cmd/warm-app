"""One polite GET against LinkedIn's guest endpoints, shared by both scrapers.

A 429 means LinkedIn wants us to back off, not that the posting is gone, so we
wait (Retry-After when it sends one, else 30-45s) and try exactly once more.
Anything else, and a second 429, goes back to the caller to skip.
"""
import random
import time
import urllib.error
import urllib.request

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
BACKOFF = (30, 45)


def get(url, timeout=25):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    })
    for attempt in (1, 2):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or attempt == 2:
                raise
            wait = exc.headers.get("Retry-After")
            time.sleep(int(wait) if wait and wait.isdigit() else random.uniform(*BACKOFF))
