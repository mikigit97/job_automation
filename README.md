# Job Application Automation — README (schema v2)

Semi-automated pipeline for junior AI / ML / Data Science roles in Israel.
Claude scrapes, tracks replies, and fits CVs; you review and apply.

## One-time setup

### 1. Prerequisites
- Claude Pro or higher (Cowork + Chrome extension)
- Cowork desktop app (Windows or Mac)
- Claude for Chrome extension in Chrome or Edge
- Gmail connector enabled (Settings → Connectors → Google Workspace)
- Python 3.10+ on your machine. For CV rendering: `pip install weasyprint pymupdf --break-system-packages`

### 2. Open this folder as a Cowork project
Cowork → New Project → `C:\Users\user\OneDrive\PycharmProjects\job_automation`.

### 3. CV inputs
- `cv/base_cv.html` — visual template. Edit directly to change layout/colors.
- `cv/experience_bank/` — content pool, one `.md` per item. Read only when building or updating a variant, not per application. See `cv/experience_bank/README.md`.
- `cv/variants/` — three durable base CVs (`ai-llm-engineer`, `data-scientist-ml`, `software-engineer-ml`), one per role archetype. Each application fits the closest variant. See "The CV variants" below.

### 4. Enable the `cv-tailor` skill
Claude Settings → Skills → point at `skills/cv-tailor/SKILL.md` (or install `cv-tailor.plugin`).

### 5. Chrome shortcuts
- Extension side panel → new shortcut `/scrape-jobs` from `prompts/scrape.md` → schedule Sun–Thu 08:00 and 16:00.
- Second shortcut `/scrape-bigtech` from `prompts/scrape-bigtech.md` → schedule **Sunday 16:00 only** (weekly).

### 6. Cowork tasks
- Scheduled: `prompts/gmail_sync.md`, Sun–Thu 16:05.
- Saved (on demand): `prompts/tailor_cvs.md` as "Fit CVs"; `prompts/auto_apply.md` as "Auto-apply" (AllJobs/Drushim only, never scheduled).

## Daily workflow

Everything lives in one file, `jobs.json`. The dashboard `Job_applications.html` is generated from it by `build_html.py` and writes your edits back into it.

**08:00 & 16:00 — `/scrape-jobs`** (needs Chrome open with the extension). Scrapes LinkedIn (six queries through the guest search/posting APIs, window since the last run) / AllJobs (guest results page; most employers hidden unless logged in) / Drushim (six queries through its JSON search API), re-visits postings whose requirements weren't captured, dumps everything to `scrape_raw.json`, then runs `python ingest.py` (gates, dedup, write) and `python build_html.py`.

**Sunday 16:00 — `/scrape-bigtech`.** Same, for NVIDIA / Google / Apple / Amazon Israel pages. Weekly, because junior openings there are rare.

**16:05 — Gmail sync.** For every applied/interview posting, finds the latest matching thread, classifies it, and moves the status forward (never backward). Rebuilds the dashboard.

**Whenever you sit down — the dashboard.** Open `Job_applications.html` in Chrome. Click **Link folder…** once and pick this project folder; from then on every click is saved into `jobs.json` (field-scoped: only your fields on the record you touched are written).

- **Inbox** — new postings, sorted by fit (● green strong, blue ok, amber weak). `[Applied]` moves it to Applied and stamps `applied_at`. `[Skip]` archives it.
- **Applied** — oldest first, so the ones needing a follow-up are on top. `[Followed up]` stamps `followed_up_at`; `[Interview]` / `[Rejected]` move it on.
- **Interviews** — shows the last email; `[Offer]` / `[Rejected]`.
- **Done** — offers and rejections. Archived postings are hidden unless you toggle "Show archived" (⋯ menu). `[Reopen]` sends anything back to Inbox.
- **Attention strip** (top, only when non-empty): unverified postings (requirements not captured) and applications older than 7 days with no reply.
- Click a row to expand: full posting text, fit reasons, notes, phone, last email, a status dropdown for overrides, and **Edit** (position, company, link, location, phone, agency flag, requirements, notes). Pasting requirements into an unverified posting clears the flag.
- **+ Add** creates a manual entry (`id` = `manual-…`). Manual entries never expire and are never auto-archived.
- **⋯ menu**: Import JSON, Export JSON, Reset local cache, Show archived.

**Before applying — "Fit CVs".** Say it in Cowork or click the saved task. For every `new`/`applied` posting without a CV it picks the closest variant, rewords only the subtitle and summary, renders `cv/tailored/<id>.pdf`, and links it on the row (`CV: <variant> ↗`). Cheap per posting, so it runs on the whole backlog.

**Applying.** Open the posting (↗), attach `cv/tailored/<id>.pdf`, submit, click `[Applied]`. Or run "Auto-apply" for AllJobs/Drushim postings (it fits a CV first if needed and records `applied_via: auto`).

## The status pipeline

One field, `status`: `new → applied → interview → offer | rejected`, plus `archived` for postings you skipped or that expired. `status_source` says who last set it (`user`, `gmail`, `auto_apply`, `scraper`, `maintain`); `status_changed_at` says when.

Rules every writer follows:
- Moving to `applied` sets `applied_at` (once) and `applied_via` (`manual` / `auto`).
- Gmail sync only moves forward (`offer > interview > rejected > applied`) and only when the email is newer than `status_changed_at`.
- Your click in the dashboard always wins — it writes `status_source: user`.
- **Nothing is ever deleted from `jobs.json`.** Archived and rejected records stay (hidden) — they are the memory that stops the scraper from re-adding the same posting. `build_html.py` archives, never removes.

`build_html.py` maintenance on every run (status `new` only, never `manual-` ids):
- older than `expiry_days` (21) → `archived / expired`
- fails a relevance gate (title outside AI/DS families, senior, teaching, clinical or excluded-role title, anonymous AllJobs company, a parsed years figure above `years_max` (3)) → `archived / irrelevant`, reason in notes
- same normalized company|position as another live posting → `archived / duplicate`

Fitted CVs (`cv/tailored/<id>.*`) are deleted when a posting becomes archived or rejected. `cv/variants/` is never touched.

## `jobs.json` record (schema v2)

```json
{
  "id": "acme-1a2b3c",
  "position": "Data Scientist", "company": "Acme", "source": "LinkedIn", "link": "https://…",
  "scraped_at": "2026-09-10T08:00:00Z", "location": "Tel Aviv", "date": "2026-09-09",
  "description": "…", "responsibilities": ["…"], "requirements": ["…"], "nice_to_have": [],
  "extraction_ok": true, "extraction_attempts": 1, "years_min": 2, "agency": false,
  "dedup_key": "acme|data scientist",

  "status": "applied", "status_source": "user", "status_changed_at": "2026-09-11T10:00:00Z",
  "applied_at": "2026-09-11T10:00:00Z", "applied_via": "manual", "followed_up_at": null,
  "archive_reason": null,
  "last_email": { "thread_link": "https://mail.google.com/…", "classification": "Auto_ack", "date": "2026-09-11", "subject": "…" },
  "cv_variant": "data-scientist-ml", "cv_tailored_at": "2026-09-11T09:40:00Z",
  "notes": "", "recruiter_phone": "",
  "fit": { "tier": "ok", "reasons": ["ds", "2y"] }
}
```

`years_min` is the lower bound of the stated experience range (`"3-5 years"` → 3; `"שנתיים"` → 2), counted only when the word experience/ניסיון is nearby. `extraction_ok` is true when ≥2 requirement lines or ≥200 characters of description were captured. `fit` is recomputed at build time and is a sort order, not a judgment.

## Who writes what

| Field | Writer |
|---|---|
| `id`, `position`, `company`, `source`, `link`, `scraped_at`, `location`, `date`, `description`, `responsibilities`, `requirements`, `nice_to_have`, `extraction_ok`, `extraction_attempts` | Scraper (you can override any of these from Edit) |
| `last_email`; `status` → forward moves only | Gmail sync |
| `status`, `status_source`, `status_changed_at`, `applied_at`, `applied_via`, `followed_up_at`, `archive_reason`, `notes`, `recruiter_phone`, `agency` | You, via the dashboard (also auto-apply for its own applications) |
| `cv_variant`, `cv_tailored_at` | Fit CVs |
| `years_min`, `dedup_key`, `fit`, `agency` (initial value only) | `build_html.py` |

Every writer does a field-scoped read-modify-write: it patches only its own fields on the records it touched.

## Configuration — `config.json`

All thresholds and pattern lists live there: `years_max`, `expiry_days`, `followup_days`, `drop_anonymous_alljobs`, the role-family / junior / seniority / teaching / clinical / excluded-role title patterns, the agency list. Edit the JSON, re-run `python build_html.py`. Test the gates with `python tests/test_gates.py`.

## The CV variants — how fitting works

Three durable base CVs in `cv/variants/`:
- `ai-llm-engineer.html` — LLM/GenAI/NLP postings
- `data-scientist-ml.html` — general ML: time-series, anomaly detection, recsys (default when it's a close call)
- `software-engineer-ml.html` — kept for manual entries only; software titles are not scraped

**Fitting** ("Fit CVs") picks the closest variant, copies it to `cv/tailored/<id>.html`, and reworks only the header subtitle and Professional Summary — never the Research/Experience selection. `skills/cv-tailor/SKILL.md`, Part A.

**Updating a variant** is rare: only when the bank gains something that changes what an archetype should lead with, or when two or more postings reveal an archetype the three don't cover. Part B of the same skill; the only path that reads `experience_bank/`.

## File reference

| Path | Purpose |
|---|---|
| `jobs.json` | The store. Schema v2 above. |
| `build_html.py` | Migrate → derive → maintain → fit → render. `--dry-run` reports without writing. |
| `ingest.py` | Turns `scrape_raw.json` (what the browser extracted) into records: gates, dedup, Drushim applied import, `state.json`. Same functions as `build_html.py`. |
| `scrape_raw.json` | Scratch output of the last scrape run (gitignored). |
| `config.json` | Thresholds and pattern lists. |
| `templates/dashboard.html` | Dashboard template (data is embedded at build time). |
| `Job_applications.html` | Generated dashboard. Open in Chrome. |
| `state.json` | `last_scrape_at` per source; written by the scraper, drives the LinkedIn time window. |
| `backups/` | Automatic `jobs.json` backups before migration/maintenance writes (newest 20 kept; gitignored). |
| `tests/test_gates.py` | Unit tests for gates, parsers, migration (`python tests/test_gates.py`). |
| `prompts/scrape.md`, `scrape-bigtech.md` | Chrome shortcut text. |
| `prompts/gmail_sync.md` | Cowork scheduled task. |
| `prompts/tailor_cvs.md`, `prompts/auto_apply.md` | Cowork on-demand tasks. |
| `skills/cv-tailor/SKILL.md` | Fitting rules (Part A), variant maintenance (Part B). |
| `cv/base_cv.html`, `cv/render_pdf.py` | Template and the one-page PDF renderer. |
| `cv/experience_bank/**/*.md` | Content pool. |
| `cv/variants/<archetype>.html` + `.pdf` | Durable base CVs. |
| `cv/tailored/<id>.html` + `.pdf` + `.notes.md` | CV fitted to one posting. Auto-deleted when it's archived/rejected. |

## Troubleshooting

**Scraper wrote 0 rows** — login or CAPTCHA. Open the board manually, log in, re-run.

**A posting shows "unverified"** — the scraper could not read its requirements. Click Edit and paste them (one per line); the flag clears. (The years gate already runs on any figure the scraper could parse, verified or not.) The next scrape also retries automatically (max 2 attempts).

**A posting I want was archived as irrelevant** — the reason is in its notes (expand the row in Done with "Show archived"). Click Reopen; manual overrides are never re-archived in the same run. If the gate itself is wrong, fix the pattern in `config.json` and add a case to `tests/test_gates.py`.

**A good posting got archived as "duplicate"** — it shares a normalized company|position with another live posting. Reopen it if they're genuinely different roles.

**Gmail sync misclassifies** — edit the rubric in `prompts/gmail_sync.md`. Your status click always wins.

**Fitted CV contains a claim I didn't make** — should be rare; fitting only rewords an audited variant. Fix the variant in `cv/variants/`, not just the one tailored file.

**Fitted CV overflows one page** — undo the reword and re-render (skill Hard Rule 4). If the variant itself overflows, drop `priority: 3` bank entries and rebuild it (Part B).

**Edits don't appear after a rebuild** — the dashboard reads the embedded snapshot; if your browser is linked to the folder it reloads `jobs.json` on open. If not linked, edits only exist in that browser's local cache — link the folder (⋯ → your local edits get written in) or Export JSON.

**`build_html.py` says it migrated records** — something wrote v1 fields (`status_manual`, `status_auto`, `interested`, `deleted`) into `jobs.json`, most likely an old copy of a shortcut/task. Harmless — the record is upgraded in place and a backup is in `backups/` — but re-install the shortcut/task from the current `prompts/` text.

## What's not automated (and why)

- **LinkedIn / big-tech applications.** Bot detection risk; you submit those yourself.
- **Scraping when Chrome is closed.** The shortcuts need the extension; the scrape window covers the days you missed (up to 7).
- **Cover letters.** Out of scope.
