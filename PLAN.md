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
Chrome scraper ──┐  position/company/link/requirements/extraction_ok, status=new
Gmail sync ──────┤  last_email, status (forward only)
Dashboard ───────┤  status/applied_at/followed_up_at/notes/phone/agency + overrides
Fit CVs ─────────┤  cv_variant, cv_tailored_at
Auto-apply ──────┘  status=applied, applied_via=auto
                 ▼
             jobs.json ──► build_html.py ──► Job_applications.html
                            (migrate, derive years_min/dedup_key/extraction_ok,
                             archive expired/irrelevant/duplicate `new`, fit tier,
                             purge cv/tailored for archived+rejected)
```

## Status model

`new → applied → interview → offer | rejected`, plus `archived` (reason:
skipped / expired / irrelevant / duplicate). `status_source` records the writer;
`status_changed_at` the time. `applied_at` is set once. Gmail never downgrades.
Archived/rejected records stay in the file as dedup memory.

## Relevance gates (config.json)

Applied to `status: new` only; `manual-` ids exempt.
1. Title must match a role family: `ai` (AI/LLM/NLP/GenAI) or `ds` (data scientist / ML / algorithm / CV / research).
2. No seniority word (senior, lead, principal, staff, manager, head of, …; בכיר, מנהל, ראש צוות, מוביל צוות).
3. No teaching title (mentor, instructor, מנחה, הדרכה, …). No clinical title (nurse, physician, …).
4. AllJobs anonymous company (חברה חסויה) dropped — toggle `drop_anonymous_alljobs`.
5. `years_min > years_max` (3) only when `extraction_ok`; unverified postings are never gated on years.
6. Expiry after `expiry_days` (21). Secondary dedup on normalized company|position.

Fit tier (sorting only): strong = family + (junior title or ≤2y) + verified + not agency;
weak = unverified or agency or years_min == years_max; ok otherwise.

## Schedules

| Event | When | Runs in |
|---|---|---|
| `/scrape-jobs` | Sun–Thu 08:00, 16:00 | Chrome shortcut |
| `/scrape-bigtech` | Sun 16:00 | Chrome shortcut |
| Gmail sync | Sun–Thu 16:05 | Cowork scheduled task |
| Fit CVs | on demand | Cowork saved task |
| Auto-apply | on demand (AllJobs/Drushim only) | Cowork saved task |
| Review / apply | whenever | Dashboard |

## Token-cost notes

- Scraping: accessibility tree + page-state JSON (~2–4K tokens per posting).
- Gmail sync: snippets + subject only.
- Fit CVs: reuses a built variant — a few thousand tokens per posting. Building a variant (rare) ~20K.

## Batch 2 (pending)

Rewrite `prompts/scrape.md`, `scrape-bigtech.md`, `gmail_sync.md`,
`auto_apply.md` to schema v2: five LinkedIn queries with a dynamic time window
from `state.json`, `years_min` parser, verify-or-flag extraction with a
re-enrich pass, `dedup_key`, clinical-only medical filter, agency flag, Drushim
already-applied import, ATS-sender matching in Gmail sync, fitted-CV upload +
`applied_via: auto` in auto-apply. Then one live `/scrape-jobs` run to verify.
