# Warm

LinkedIn job postings, ranked by who you already know there.

Scrapes public job listings daily, matches each posting's company against the
networks of people you trust, and surfaces only the openings where you have a
real introduction — ranked so a mentor on the board of a 40-person firm beats
being one of fifty acquaintances at Amazon.

## How it works

```
LinkedIn guest endpoint ──> scrape_jobs.py ──┐
                                             ├──> match.py ──> load_supabase.py ──> Supabase
connection CSVs ──> import_contacts.py ──────┘                                          │
                                                                                        v
                                                                            PWA (GitHub Pages)
```

**Jobs.** LinkedIn's `/jobs-guest/` endpoint serves job cards to anonymous
clients — no login, no headless browser. Each card carries the company's
LinkedIn slug, which is a better join key than the display name. Pace requests
and let `f_TPR=r86400` trim to the last 24h rather than paging deep.

**Connections.** You cannot scrape someone else's network, so this is the one
genuinely manual step: each trusted person exports their own list via
*Settings → Data Privacy → Get a copy of your data → Connections*. Drop the CSV
into the app's Import tab. Refresh every six months or so.

**Matching.** Company names are normalized identically on both sides
(`tools/normalize.py` and `src/lib/normalize.js`, kept honest by
`tests/parity.test.js`). Exact matches ship; near misses land in the Review tab,
where one tap writes a permanent alias.

Fuzzy matching compares only *distinctive* tokens. Raw string similarity pairs
"Bowman Consulting" with "Grogan Consulting" and "IQVIA" with "Visa", because
generic industry words dominate the comparison.

**Ranking.** `strength = rarity + seniority + source trust`, where rarity is
inverse-log in the number of contacts at that company. One senior contact at a
small firm outranks thirty at Amazon.

## Two axes

Warmth answers *can I get a look in*. Fit answers *do I even want this*. They are
scored independently, and the jobs that land on both are the ones to act on
first — that is the **Best** tab.

Fit needs the job description, which the search endpoint does not return, so
`enrich_jobs.py` fetches each posting's detail page for the description plus
LinkedIn's own structured fields (seniority, employment type, function,
industries) and parses the salary range out of the body text.

Scoring is transparent by design: every score carries its reasons, because an
unexplained number is neither actionable nor debuggable. Title match dominates,
then seniority, matching themes, salary against a floor, and workplace
preference. Excluded titles and phrases are a hard reject, not a penalty.

Bands were **calibrated against jobs the user had already saved by hand** —
those scored 57–78, median 66 — so `strong` is 65 and `worth a look` is 48. An
earlier 70 cut caught only one of her four picks. `tests/test_fit.py` pins that
relationship so it cannot drift.

Someone's searches and criteria live in `profiles/<name>.json` (gitignored — the
repo is public). `apply_profile.py` attaches them to their account after they
have signed in once.

## Several people at once

Each job hunter is one row in `warm_profiles` (their searches, their Telegram
chat id) and one `owner_id` everywhere else. RLS keeps the networks separate:
nobody sees anyone else's contacts. The daily job loops every active profile,
matching each person only against their own imported connections.

Someone new signs in with their email, sets their searches under **Setup**, and
drops their connection CSVs into **Import**. Nothing to configure by hand.

```bash
python3 tools/list_profiles.py                    # who is active
python3 tools/run_profile.py --owner <uuid>       # one person, end to end
python3 tools/find_chat_id.py                     # after they message the bot
./tools/run_daily.sh                              # everyone (cron entry point)
```

The digest only ever sends a job once — `warm_jobs.digest_sent_at` is stamped on
send, so the same opening never reappears tomorrow even if it is still untriaged.

## Layout

| Path | What |
|---|---|
| `tools/scrape_jobs.py` | LinkedIn guest-endpoint scraper |
| `tools/import_contacts.py` | Parses all five CSV export shapes |
| `tools/match.py` | Company matching + strength ranking |
| `tools/load_supabase.py` | Emits idempotent upsert SQL |
| `tools/enrich_jobs.py` | Fetches descriptions + structured fields + salary |
| `tools/fit.py` | Fit scoring and the band thresholds |
| `tools/apply_profile.py` | Attaches a profiles/*.json to a signed-in account |
| `tools/run_profile.py` | One person, end to end |
| `tools/run_daily.sh` | Every active profile (cron entry point) |
| `tools/digest.py` | Telegram digest, sends each job once |
| `tools/fetch_contacts.py` | Materializes one owner's contacts for the matcher |
| `src/lib/parseContacts.js` | Browser port of the importer |
| `supabase/migrations/` | Schema, RLS, and the `warm_feed` view |

## Running it

```bash
npm install && npm run dev          # app at :5173
open preview.html                   # surfaces without the OTP gate

# one-off local pipeline
python3 tools/import_contacts.py ~/Downloads/Connections.csv:nate
python3 tools/scrape_jobs.py --tpr r604800
python3 tools/match.py
python3 tools/load_supabase.py --owner "$WARM_OWNER_ID"
supabase db query --linked -f data/load.sql

npx vitest run                                       # JS/Python parser parity
python3 -m unittest discover -s tests -p 'test_*.py' # matcher regressions
```

Edit `tools/queries.json` to change which titles and locations get pulled.

## Notes

- The scraper is rate-limited in practice. Keep `--delay` at 2s or above; the
  endpoint repeats its last page rather than returning empty, which is why
  paging stops on the first duplicate.
- `warm_jobs` upserts with `do nothing` so a re-scrape never clobbers triage
  state.
- All tables are RLS'd to `auth.uid()`; the daily job writes with the service
  role and an explicit owner id.
- **Views need `security_invoker = on`.** Without it a view runs with definer
  rights and returns every owner's rows to any caller, straight past RLS.
  `create or replace view` also cannot insert a column mid-list — drop first,
  and restate `security_invoker`, which is not inherited.
- Enrichment is one request per posting, so only ever enrich what has no
  description yet. A re-scrape refreshes enrichment and fit but must never
  touch `status`, `note` or `digest_sent_at` — those belong to the person.
- Excluded titles match on word boundaries. A bare `"art"` correctly rejects
  "Associate Creative Director Art" without touching "Marketplace Partnership";
  `"art director"` alone misses it, since that word order never appears.
- Fuzzy auto-accept requires a *shared identifying word*, never mere string
  closeness. "Dynamic Resources" and "Dynamics Ventures" both reduce to one
  near-identical token and are unrelated companies; that case gets asked about,
  never assumed. See `tests/test_match.py`.
