# Job Application Automation — README

Semi-automated pipeline for Data Science / AI Engineer roles in Israel.
You review and apply; Claude scrapes, tailors, and tracks replies.

## One-time setup

### 1. Prerequisites
- Claude Pro or higher (for Cowork + Chrome extension)
- Cowork desktop app installed (Windows or Mac)
- Claude for Chrome extension installed in Chrome or Edge
- Gmail connector enabled (Settings → Connectors → Google Workspace)

### 2. Open this folder as a Cowork project
Cowork → New Project → point at this folder (`job_automation/`).
This makes the folder persistent across sessions with its own memory.

### 3. Confirm your CV inputs
- `cv/base_cv.html` — your visual template. Already in place. Edit the HTML directly if you want to change the layout, colors, or section order.
- `cv/experience_bank/` — your content pool. Seeded with everything already in your HTML CV. Expand it over time with projects, coursework, and roles that don't fit on the one-pager. See `cv/experience_bank/README.md` for the file format.

### 4. Enable the `cv-tailor` skill
In Claude Settings → Skills, point at `skills/cv-tailor/SKILL.md` or enable it project-scoped. Cowork autoloads it when tailoring runs.

### 5. Install the Chrome shortcuts
- Open the Chrome extension side panel
- Paste the contents of `prompts/scrape.md` as a new shortcut named `/scrape-jobs`
- Click the clock icon → schedule for Sun–Thu at 08:00 and 16:00
- Paste the contents of `prompts/scrape-bigtech.md` as a second shortcut named `/scrape-bigtech`
- Click the clock icon → schedule for Sun–Thu at 16:00 only (big-tech careers pages update slowly, so once a day is enough)

### 6. Install the Cowork scheduled tasks
- Cowork → Scheduled Tasks → New
  - Task A: Paste `prompts/gmail_sync.md`, schedule Sun–Thu 16:05
  - Task B: Paste `prompts/tailor_cvs.md` as a saved on-demand task named "Tailor CVs for Vs"

## Daily workflow

The tracker is a single HTML file (`Job_applications.html`) backed by
`jobs.json`. `jobs.json` is the only store for postings — there is no
`positions/` folder and no xlsx.

**08:00 & 16:00 — automatic (`/scrape-jobs`)**
Chrome shortcut runs. It reads `jobs.json`, scrapes LinkedIn / AllJobs /
Drushim, appends new postings (dedup by `link`), enriches existing ones,
saves `jobs.json`, and runs `python build_html.py` to rebuild the tracker.

**16:00 — automatic (`/scrape-bigtech`)**
Second Chrome shortcut runs once a day. It scrapes the Israel careers pages
of NVIDIA, Google, Apple, and Amazon, then does the same dedup-and-rebuild
against `jobs.json`. Big-tech pages change slowly, so one pass per day is
enough.

**After scraping, the tracker refreshes itself.** If you ever want to rebuild
manually:

```
python build_html.py   # jobs.json → Job_applications.html (embeds data inline)
```

**Review in the tracker**
Open `Job_applications.html` in Chrome or Edge. Click **"Link folder…"**
once and pick this folder — the HTML will persist every edit (status,
👍/👎, notes, recruiter phone, plus any field overrides) directly into
`jobs.json` via a field-scoped patch (read → modify only your fields for
that id → write). Scraper and Gmail-sync fields on every entry are
preserved unless you explicitly override them. Mark 👍 on jobs you want
to pursue. The **Delete** button on each card removes the entire entry
from `jobs.json`.

**Editing fields on a card.** Click **Edit** on any card to open a form
where you can change position, company, source, link, location,
recruiter phone, requirements, responsibilities, nice-to-have, and
notes. Edits to scraper-owned fields are stored as user overrides in
`jobs.json` for that entry; future scraper runs only fill empty fields,
so your edits stick.

**Adding a job manually.** The **+ New job** button at the top opens the
same form blank. Fill at least position or company; the entry gets a
fresh `id` of the form `manual-<6-char-hex>` and lands in `jobs.json`.

**After reviewing**
In Cowork, say "Tailor CVs for Vs" (or click the saved task). Wait. New
`.html` files appear in `cv/tailored/`.

**When you want to apply**
1. Open the tailored `.html` in Chrome → click "Download as PDF".
2. Open the job link. Apply manually (or use Chrome's form-fill shortcut, optional).
3. In the tracker: set `Status` → `Applied`.

**16:05 — automatic**
Gmail sync scans replies. For each non-final position (not `Rejected` /
`Offer`), it searches the Gmail connector for the most recent thread from
that company. If the thread link differs from what's stored in
`jobs.json[i].last_email.thread_link`, it classifies the new email, updates
`last_email` and `status_auto` inside the job record, and rebuilds the HTML.

## Tracker status — how it's derived

Each card shows one effective status computed in this priority order:

1. **Manual override** (`status_manual` in the state file) — what you set in
   the HTML.
2. **`status_auto`** — written by the Gmail sync task based on the most
   recent email.
3. **Last-email classification** — if `status_auto` isn't set but
   `last_email.classification` is, the HTML maps it
   (`Auto_ack` → `Applied`, `Interview` → `Interview`, etc.).
4. **`New`** — default when nothing else applies.

Status values: `New`, `Applied`, `Interview`, `Offer`, `Rejected`, `Archived`.

The Gmail sync task **never downgrades** — once a position reaches
`Interview`, an `Auto_ack` reply can't push it back to `Applied`. Priority
high-to-low: `Offer > Interview > Rejected > Applied > (empty)`.

## The experience bank — how to maintain it

The bank lives at `cv/experience_bank/` and is structured one `.md` per item:
- `research/` — research projects, theses, capstones
- `work/` — paid/unpaid roles
- `education/` — degrees (high-level)
- `skills/` — skill clusters with evidence
- `military/` — IDF service
- `volunteering/` — community work

Each file has YAML frontmatter with `tags`, `priority`, and a body with Short/Medium/Long phrasing variations. See `cv/experience_bank/README.md` for the format and tag conventions.

**When you add new experience:** copy the closest existing file, edit frontmatter + body, save with a descriptive filename. No index to update — `cv-tailor` scans frontmatter at runtime.

**Why a bank?** The base HTML can only fit ~3 research projects + ~3 work entries on one page. The bank can hold everything you've done, and the tailoring step picks the best subset for each specific job. A job that wants recsys experience gets your Deezer project; a job that wants anomaly detection gets your autoencoder project; the same base template holds both.

## Token-efficiency notes

- Scraping uses Chrome's **accessibility tree** and page-state JSON, not screenshots (~2–4K tokens/position vs 30K+).
- Gmail sync uses the MCP connector with snippets only, not full bodies.
- All postings live in a single `jobs.json`; no per-position markdown files.
- CV tailoring uses a `grep`-based tag index to load only ~10 bank files per run, not all of them.

## File reference

| Path | Purpose |
|---|---|
| `Job_applications.html` | Interactive tracker (open in Chrome/Edge). Rebuilt by `build_html.py`. |
| `jobs.json` | Single store for everything about a posting: scraped fields, Gmail-derived fields, and your edits. Writers share this one file and only touch their own fields per entry. |
| `build_html.py` | Reads `jobs.json` → writes `Job_applications.html` (data embedded inline). |
| `cv/base_cv.html` | Visual template (fonts, layout, print button) |
| `cv/experience_bank/**/*.md` | Content pool — one entry per file |
| `cv/tailored/<id>.html` | Generated tailored CV |
| `skills/cv-tailor/SKILL.md` | Tailoring rules |
| `prompts/scrape.md` | Chrome shortcut text for LinkedIn / AllJobs / Drushim (writes directly to `jobs.json`) |
| `prompts/scrape-bigtech.md` | Chrome shortcut text for NVIDIA / Google / Apple / Amazon careers pages (writes to `jobs.json`) |
| `prompts/gmail_sync.md` | Cowork scheduled-task text (updates `last_email` / `status_auto`) |
| `prompts/tailor_cvs.md` | Cowork on-demand task text |

## `jobs.json` entry schema

```json
{
  "id": "company-abc123",
  "position": "Data Scientist",
  "company": "Acme Corp",
  "source": "LinkedIn",
  "link": "https://...",
  "scraped_at": "2026-04-22T15:58:39Z",
  "location": "Tel Aviv",
  "date": "2026-04-21",
  "description": "We're hiring a Data Scientist to join our analytics team…",
  "responsibilities": ["..."],
  "requirements": ["..."],
  "nice_to_have": [],
  "last_email": {
    "thread_link": "https://mail.google.com/mail/u/0/#inbox/<id>",
    "classification": "Interview",
    "date": "2026-04-22",
    "subject": "Re: your application for Data Scientist"
  },
  "status_auto": "Interview",
  "status_manual": null,
  "interested": "yes",
  "notes": "Recruiter is Dana",
  "recruiter_phone": "+972 50-123-4567"
}
```

Every field except `id` / `position` / `company` / `source` / `link` /
`scraped_at` can be `null` (or `""` for `notes` / `recruiter_phone`).

## Who writes what

| Field | Writer |
|---|---|
| `id`, `position`, `company`, `source`, `link`, `scraped_at`, `location`, `date`, `description`, `responsibilities`, `requirements`, `nice_to_have` | Scraper (you can also override any of these from the HTML) |
| `last_email`, `status_auto` | Gmail sync |
| `status_manual`, `interested`, `notes`, `recruiter_phone` | You, via the HTML tracker |

Each writer does a read-modify-write on `jobs.json` and patches only its own
fields per entry — the other fields on every entry survive. This is how three
separate processes share one file without a merge step.

`status_manual` always wins over `status_auto`. Clearing it via the **Auto**
toggle hands control back to the email-derived status.

**Overrides on scraper-owned fields.** When you edit a scraper field
(position, requirements, link, …) from the HTML, the new value is written
straight into `jobs.json[i].<field>` in place of the scraper value. The
scraper's dedup pass only fills empty/null fields, so your edit survives
future scraper runs. To hand control back to the scraper for a field, clear
the field in the Edit dialog and re-save — the next scrape will repopulate it.

## Troubleshooting

**Scraper wrote 0 rows** — likely hit a login or CAPTCHA. Open the board manually, log in, re-run.

**Gmail sync misclassifies** — edit the Step 5 rubric in `prompts/gmail_sync.md`.

**Tailored CV contains a claim I didn't make** — the skill forbids this. Tell Cowork: "audit the tailored CV at `cv/tailored/<id>.html` against `cv/experience_bank/` — flag any claim not sourced from a bank file." Then add the missing entry to the bank OR remove the claim.

**Tailored CV overflows one page** — drop `priority: 3` entries from the bank first, then `priority: 2`. You can also lower priority of specific items in their frontmatter.

**Duplicate postings in tracker** — the scraper dedups by `link`. If boards rewrite URLs, add `Company + Position` as a secondary dedup key in `prompts/scrape.md`.

**New jobs don't appear in the HTML after scraping** — you forgot to rebuild: `python build_html.py`. The HTML embeds data at build time; it does not read `jobs.json` at runtime (browser security blocks `file://` pages from reading local JSON).

**My edits disappeared after rebuilding the HTML** — edits live in
`jobs.json` (plus a localStorage mirror, keyed by job `id`). Rebuilds embed
the current `jobs.json` as the starting snapshot, so a rebuild picks up
everything you saved. If you edited in one browser without linking the
folder, those edits only exist in that browser's localStorage — open the
rebuilt HTML in the same browser, or use Import JSON.

## What's not automated (and why)

- **Clicking Submit on applications.** You review each tailored CV and submit yourself. Keeps a human in the loop, avoids bot detection on ATSs.
- **Scraping behind logins.** LinkedIn throttles aggressive automation. The scraper pauses on login/CAPTCHA; session cookies carry forward.
- **Writing cover letters.** Out of scope for v1. Can be added as a second skill (`cover-letter`) that draws from the same experience bank.
