"""Company-name normalization shared by the importer and the scraper.

Both sides of the match (contact affiliations, scraped job postings) must run
the same function or the equality join in SQL silently misses.
"""
import re
import unicodedata

# Stripped only when they trail the name, so "Group Health" keeps its "group"
# but "Rich Talent Group" does not.
TRAILING_NOISE = {
    "inc", "incorporated", "llc", "llp", "lp", "ltd", "limited", "corp",
    "corporation", "co", "company", "plc", "gmbh", "ag", "nv", "bv", "sa",
    "spa", "pty", "pte", "holdings", "holding", "group", "international",
    "worldwide", "global", "usa", "us",
}

LEADING_NOISE = {"the"}


def norm_company(raw):
    """Normalize a company name to a stable match key. Empty string if unusable."""
    if not raw:
        return ""
    s = unicodedata.normalize("NFKD", str(raw))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    # Drop anything parenthetical or after a separator: "Google (YouTube)",
    # "Acme - Northeast Region", "Acme | Consulting"
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.split(r"\s+[-|/,]\s+", s)[0]
    s = s.replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    tokens = s.split()
    while tokens and tokens[0] in LEADING_NOISE:
        tokens.pop(0)
    while tokens and tokens[-1] in TRAILING_NOISE:
        tokens.pop()
    return " ".join(tokens)


def norm_person(raw):
    """Normalize a person name for dedupe within a source."""
    if not raw:
        return ""
    s = unicodedata.normalize("NFKD", str(raw))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    # Strip trailing credential salad: "Jane Doe, MBA, PMP"
    s = re.split(r",", s)[0]
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())
