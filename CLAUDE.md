# CLAUDE.md — how to work in this folder

Read this file, then only the file the task row below names. `README.md` and
`PLAN.md` explain *why* things are the way they are — read them when changing
behaviour, not when running a task.

Job-hunt pipeline for junior AI/ML/DS roles in Israel. `jobs.json` is the
store; `build_html.py` renders `Job_applications.html` from it; scrapers and
the Gmail task feed it only through `ingest.py`.

## Before touching anything — every session, and again after any pause

1. `git status --short && git log --oneline -5` — this is how you learn what
   other sessions changed; commit messages are the change feed.
2. Re-read every file you are about to edit. Never edit from a copy you read
   earlier in the conversation.
3. One session works on this folder at a time. If `git status` shows changes
   that are not yours, stop and ask before doing anything.

## Task → read → may change → then run

| Task | Read | May change | Then |
|---|---|---|---|
| Tailor a CV for one job / all unfitted jobs | `skills/cv-tailor/SKILL.md` Part A, `prompts/tailor_cvs.md` | `cv/tailored/<id>.*`; on the record only `cv_variant`, `cv_tailored_at` (and the archived/fit outcome of Step 0) | `python build_html.py` |
| Update a base CV variant | `skills/cv-tailor/SKILL.md` Part B | `cv/variants/<archetype>.html` + `.pdf` | — |
| Scrape LinkedIn | `prompts/scrape.md` | `scrape_raw.json` only | `python ingest.py scrape_raw.json && python build_html.py` |
| Scrape big-tech boards | `prompts/scrape-bigtech.md` | `scrape_raw.json` only | same |
| Import my own applications from Gmail + sync replies | `prompts/gmail_sync.md` | `gmail_raw.json`; the Step 6 patch on `jobs.json` | `python ingest.py gmail_raw.json && python build_html.py` |
| Change a gate, threshold or title pattern | `config.json`; `build_html.py` `is_relevant` / `compute_fit` only for new logic | those + a case in `tests/test_gates.py` | `python tests/test_gates.py` |
| Change the dashboard | `templates/dashboard.html` | that file | `python build_html.py` |
| Change the schema or status lifecycle | `README.md` (Schema), `PLAN.md` | `build_html.py`, `ingest.py`, tests, README | tests, then build |
| Change when/what the scheduled tasks run | the task's `prompts/*.md` | that prompt file | edit the file; the task re-reads it each run |

## Rules

- Never edit `jobs.json` by hand. Its writers are `ingest.py` (scrapes,
  imports), `build_html.py` (maintenance), the dashboard (your clicks), the
  Gmail task's Step 6 patch, and the CV skill (`cv_*` fields). Nothing is ever
  deleted from it — archive.
- Never write `["N/A"]`; use empty arrays.
- Scraping needs Chrome open with the Claude extension. Read pages with
  `navigate` + `get_page_text` + `read_page` (batched via `browser_batch`);
  no injected JavaScript. Details in `prompts/scrape.md`.
- Finish every task, including scheduled runs, with a commit:
  `git -c user.name=mikigit97 -c user.email=mickaelz@post.bgu.ac.il add -A && git -c user.name=mikigit97 -c user.email=mickaelz@post.bgu.ac.il commit -m "<task>: <one line>"`
  (`scrape_raw.json`, `gmail_raw.json`, `backups/` are gitignored.)
- Timezone Asia/Jerusalem; scheduled-task crons are stored in UTC.
- If a prompt file and this file disagree, the prompt file wins for that
  task — and fix this file in the same commit.

## Automation (cloud scheduled tasks, created 2026-09-16)

Scrape jobs Sun–Thu 08:00 & 16:00 · Scrape big tech Sun 16:00 · Gmail sync
Sun–Thu 16:05 · Fit CVs on demand. Each task's prompt is one line: open this
folder, read its `prompts/*.md`, follow it. Change behaviour by editing the
prompt file, not the task. They run only while the desktop app is open on
the PC.

## Layout

`jobs.json` store · `build_html.py` migrate/maintain/fit/render ·
`ingest.py` gates + dedup + imports · `config.json` thresholds and regexes ·
`state.json` last-scrape per source · `templates/dashboard.html` ·
`tests/test_gates.py` · `prompts/` task texts · `skills/cv-tailor/SKILL.md`
CV rules · `cv/experience_bank/` content pool · `cv/variants/` base CVs ·
`cv/tailored/` per-job CVs (auto-deleted when the job is archived/rejected) ·
`cv/render_pdf.py` one-page renderer (`pip install weasyprint pymupdf
--break-system-packages` if missing).
