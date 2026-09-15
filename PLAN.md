# PLAN — Job Application Automation (v2)

## Architecture

Claude-native, semi-automated, token-efficient pipeline using three Claude
surfaces plus the Gmail connector. No server, no database.

| Concern | Decision |
|---|---|
| Scheduling | Cowork scheduled tasks + Chrome extension scheduled shortcuts |
| Browser automation | Claude for Chrome, accessibility tree + page-state JS (not screenshots) |
| Gmail | MCP connector, invoked from Cowork |
| Store | Single `jobs.json`, schema v2. One `status` field, one owner per field, nothing ever deleted |
| Config | `config.json` — thresholds and title/agency patterns; no magic numbers in code |
| Tracker UI | `templates/dashboard.html` → `Job_applications.html`, built by `build_html.py`; single responsive file, no external scripts |
| User edits | Dashboard patches its own fields into `jobs.json` via the File System Access API |
| CV | `cv/variants/` (three durable archetype CVs) + per-posting fit into `cv/tailored/<id>` |
| Relevance | Gates in `build_html.py` and the scraper prompts, mirrored; a fit tier for sorting |

## Data flow

```
Chrome scraper ──┐  position/company/link/requirements/extraction_ok, status=new   (via ingest.py)
Gmail sync ──────┤  last_email, status (forward only); self-sent applications → applied (via ingest.py)
Dashboard ───────┤  status/applied_at/followed_up_at/notes/phone/agency + overrides
Fit CVs ─────────┘  cv_variant, cv_tailored_at; 4–5y postings not covered → archived/fit
                 ▼
             jobs.json ──► build_html.py ──► Job_applications.html
                            (migrate, derive years_min/dedup_key/extraction_ok,
                             archive expired/irrelevant/duplicate `new`, fit tier,
                             purge cv/tailored for archived+rejected)
```

## Status model

`new → applied → interview → offer | rejected`, plus `archived` (reason:
skipped / expired / irrelevant / duplicate / fit). `status_source` records the writer
(`user`, `gmail`, `scraper`, `maintain`, `fit`; `auto_apply` only on old records);
`status_changed_at` the time. `applied_at` is set once. Gmail never downgrades.
Archived/rejected records stay in the file as dedup memory.

## Relevance gates (config.json)

Applied to `status: new` only; `manual-` ids exempt.
1. Title must match a role family: `ai` (AI/LLM/NLP/GenAI) or `ds` (data scientist / ML / algorithm / CV / research).
2. No seniority word (senior, lead, principal, staff, manager, head of, …; בכיר, מנהל, ראש צוות, מוביל צוות).
3. No teaching title (mentor, instructor, מנחה, הדרכה, …). No clinical title (nurse, physician, …). No excluded role (`excluded_titles`: product owner, DevOps, full-stack, Salesforce, Power BI, DSP / signal processing / navigation / radar, bootcamp — titles that only mention AI).
4. AllJobs anonymous company (חברה חסויה) dropped — toggle `drop_anonymous_alljobs` (dormant: AllJobs is no longer scraped).
5. Years, whenever a figure was parsed (verified or not): ≤ `years_max` (3) always fine; `years_max` < n ≤ `years_soft_max` (5) kept as tier *weak* and fitted a CV only if the Fit CVs coverage check finds the mandatory requirements in the experience bank (else `archived / fit`); > `years_soft_max` dropped. No figure → no gate.
6. Expiry after `expiry_days` (21). Secondary dedup on normalized company|position.

Fit tier (sorting only): strong = family + (junior title or ≤2y) + verified + not agency;
weak = unverified or agency or years_min > years_max; ok otherwise (3y is ok).

## Schedules

| Event | When | Runs in |
|---|---|---|
| `/scrape-jobs` | Sun–Thu 08:00, 16:00 | Chrome shortcut |
| `/scrape-bigtech` | Sun 16:00 | Chrome shortcut |
| Gmail sync | Sun–Thu 16:05 | Cowork scheduled task |
| Fit CVs | on demand | Cowork saved task |
| Review / apply | whenever | Dashboard |

## Token-cost notes

- Scraping: accessibility tree + page-state JSON (~2–4K tokens per posting).
- Gmail sync: snippets + subject only.
- Fit CVs: reuses a built variant — a few thousand tokens per posting. Building a variant (rare) ~20K.

## Prompt contract (all writers are on schema v2)

`prompts/scrape.md` (LinkedIn only since 2026-09-15) and `scrape-bigtech.md`
only extract: they compute the LinkedIn window from `state.json`, re-open
unverified `new` records (max 2 attempts), and dump raw postings to
`scrape_raw.json`. `ingest.py` then applies the gates, marks
`extraction_ok`, flags agencies, drops duplicates by `dedup_key`, and
updates `state.json` — with the same functions `build_html.py` uses.
`gmail_sync.md` first imports application confirmations for jobs the user
applied to on their own (`gmail_raw.json` → `ingest.py`: new `applied`
records, or `new → applied` promotion by company|position), then matches
company, position-in-subject and ATS senders for replies, and only moves
status forward when the email is newer than `status_changed_at`.
`auto_apply.md` was retired with the AllJobs/Drushim boards.
