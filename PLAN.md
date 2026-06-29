# PLAN — Job Application Automation

## Architecture

Claude-native, semi-automated, token-efficient pipeline using three Claude
surfaces plus the Gmail MCP connector. No external tooling.

| Concern | Decision |
|---|---|
| Scheduling | Cowork scheduled tasks + Chrome extension scheduled shortcuts |
| Browser automation | Claude for Chrome, accessibility-tree + page-state JS (not screenshots) |
| Gmail | MCP connector, invoked from Cowork |
| Posting store | Single `jobs.json` at the Cowork project root — the only file the scraper, Gmail sync, and HTML tracker all read and write |
| Tracker UI | `Job_applications.html`, rebuilt from `jobs.json` by `build_html.py` |
| User edits | Written into `jobs.json` (`status_manual`, `interested`, `notes` fields on the matching entry) via field-scoped read-modify-write from the HTML |
| CV template | `cv/base_cv.html` (existing Tailwind HTML with `window.print()` button) |
| CV content source | `cv/experience_bank/` — structured `.md` files, one per item, with YAML frontmatter tags |
| CV tailoring | Custom `cv-tailor` skill that autoloads in Cowork |
| Tailored output | `.html` per position, opened in Chrome and printed to PDF |

## Why a two-part CV system (template + bank)

Splitting the CV into a visual **template** and a content **bank** solves two problems at once:

1. **Overflow:** the base HTML only fits ~3 research + ~3 work entries on one A4 page. The bank holds everything you've done; tailoring picks the best subset per job.
2. **Drift:** without a single source of truth for content, different CV versions drift over time. The bank is canonical; tailored HTMLs are disposable outputs.

Claims in any tailored CV must trace back to a bank file. The skill enforces this in Step 7 (self-audit).

## Trigger map

| Event | Trigger | Runs in | Touches |
|---|---|---|---|
| Morning scrape | Schedule Sun–Thu 08:00 | Chrome `/scrape-jobs` | `jobs.json`, `Job_applications.html` |
| Afternoon scrape | Schedule Sun–Thu 16:00 | Chrome `/scrape-jobs` | `jobs.json`, `Job_applications.html` |
| Big-tech scrape | Schedule Sun–Thu 16:00 | Chrome `/scrape-bigtech` | `jobs.json`, `Job_applications.html` |
| Gmail sync | Schedule Sun–Thu 16:05 | Cowork task | `jobs.json` (`last_email`, `status_auto`), `Job_applications.html` |
| Review | Manual | You, in the HTML | `jobs.json` (`status_manual`, `interested`, `notes`) |
| Tailor CVs | Manual ("Tailor CVs for Vs") | Cowork saved task | `cv/tailored/` |
| Apply | Manual | You | `jobs.json` (`status_manual` → `Applied`) |

## Data flow

```
Chrome scraper ──┐
                 │  (writes position/company/link/requirements/...)
Gmail sync ──────┤
                 │  (writes last_email, status_auto)
HTML tracker ────┤  (writes status_manual, interested, notes)
                 │
                 ▼
             jobs.json ──► build_html.py ──► Job_applications.html
```

Every writer does a read-modify-write on `jobs.json` and only touches its own
fields per entry. Three processes share one file without needing a merge
layer because their lanes don't overlap.

Why a rebuild step instead of reading JSON at runtime: `file://` pages can't
`fetch()` sibling files due to browser CORS rules. `build_html.py` inlines
`jobs.json` into the HTML as a JS literal, so the tracker opens with a
double-click. The HTML also does its own field-scoped read-modify-write of
`jobs.json` via the File System Access API once you click **Link folder…**.

## Token-cost estimate per run

| Step | Approx input | Approx output |
|---|---|---|
| Scrape one board (30 cards, descriptions from page-state JSON) | 8K | 2K |
| Gmail sync per company | 0.5K (snippet) | 0.2K (classification) |
| CV tailor per position (bank indexed via grep) | 13K (template + reqs + ~10 bank files) | 6K (HTML out) |

A full afternoon cycle with 30 new positions + 20 Gmail-active companies + 5 V-marked tailorings: ~400K input, ~80K output. Fits inside a Cowork session with two passes.

## Open decisions you need to make

1. **Which boards to include** — default LinkedIn Jobs IL, AllJobs, Drushim. Add Comeet, GotFriends, JobMaster?
2. **Keyword set** — default "data scientist" OR "AI engineer". Add "ML engineer", "LLM engineer", "research engineer"?
3. **Dedup strategy** — by `link` only (default) or also `company + position`?
4. **Experience bank language** — seeded in English. If you want Hebrew versions of each entry for Hebrew job posts, add `body_he` sections to each file and update the skill.

## Next steps to activate

1. Unzip into a folder Cowork can see (e.g., `~/Documents/job_automation/`)
2. Open it as a Cowork project
3. Verify `cv/base_cv.html` renders in Chrome (open the file, check the print button works)
4. Read `cv/experience_bank/README.md`, then expand the bank with anything that isn't already there (thesis chapters, coursework projects, side projects)
5. Install the `cv-tailor` skill (Settings → Skills → `skills/cv-tailor/SKILL.md`)
6. Install the Chrome shortcut from `prompts/scrape.md`, schedule Sun–Thu 08:00 and 16:00
7. Install the second Chrome shortcut from `prompts/scrape-bigtech.md`, schedule Sun–Thu 16:00
8. Install the Gmail sync Cowork task from `prompts/gmail_sync.md`, schedule Sun–Thu 16:05
9. Install the CV tailor Cowork saved task from `prompts/tailor_cvs.md` (on-demand, no schedule)
10. Open `Job_applications.html` in Chrome → click **"Link folder…"** and pick this folder so the HTML can patch `jobs.json` on every edit

See `README.md` for the daily workflow and troubleshooting.
