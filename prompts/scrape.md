# Chrome shortcut: /scrape-jobs  (schema v2)

Save this as a Claude in Chrome shortcut. Schedule it Sunday–Thursday at 08:00
and 16:00. It scrapes LinkedIn (Israel) and appends new postings to
`jobs.json` at the Cowork project root, then rebuilds the dashboard.
AllJobs and Drushim were dropped on 2026-09-15 at the user's request (the
methods that worked for them are in git history, commit 08cf43f).

The big-company careers pages (NVIDIA, Google, Apple, Amazon) live in a
separate shortcut, `/scrape-bigtech`, scheduled **weekly** (Sunday 16:00).

---

You are running the Israel junior AI / ML / Data-Science job scraper. Follow
the steps below exactly. Read pages with `get_page_text` (rendered text) and
`read_page` (accessibility tree, for links/ids) — no page-state JavaScript is
needed for LinkedIn any more (Step 1 covers why); never screenshots.

## Step 0 — Load the tracker, the config and the scrape state

Read three files from the Cowork project root:

1. `config.json` — only for the title pre-filter (Step 1 / Step 2):
   `role_families` (`ai`, `ds`), `seniority_titles`, `teaching_titles`,
   `excluded_titles`.
   Each is a list of regex fragments; treat a list as one case-insensitive
   alternation (`(?:a|b|c)`, flag `i`). Everything else in the file is
   consumed by `ingest.py` / `build_html.py`, not by you.
2. `jobs.json` — a JSON array of records in **schema v2**:

```json
{
  "id": "<company-first-word>-<6-char-hash-of-link>",
  "position": "...", "company": "...", "source": "LinkedIn|Gmail|BigTech…",
  "link": "https://...", "scraped_at": "2026-09-14T08:00:00Z",
  "location": null, "date": null, "description": null,
  "responsibilities": [], "requirements": [], "nice_to_have": [],
  "extraction_ok": false, "extraction_attempts": 1, "years_min": null,
  "agency": false, "dedup_key": "company|position",
  "status": "new", "status_source": "scraper", "status_changed_at": "2026-09-14T08:00:00Z",
  "applied_at": null, "applied_via": null, "followed_up_at": null, "archive_reason": null,
  "last_email": null, "cv_variant": null, "cv_tailored_at": null,
  "notes": "", "recruiter_phone": ""
}
```

   If you meet a record with the old fields (`status_manual`, `status_auto`,
   `interested`, `deleted`) leave it exactly as it is — `build_html.py`
   migrates it at the end of this run.

3. `state.json` — `{"sources": {"LinkedIn": {"last_scrape_at": "..."}, ...}}`.
   Missing file or key → treat as never scraped.

Keep in memory:
- `existing_by_link` — link → record, for **every** record regardless of
  status. You use it only to avoid re-opening detail pages you already
  have verified text for; `ingest.py` does the real dedup.
- `to_verify` — records with `status == "new"`, `extraction_ok == false`,
  `extraction_attempts < 2`, and `source == "LinkedIn"`. You will re-open
  these (Step 1b) before scraping anything new.

### Field ownership — the scraper's lane

| Fields | Scraper may write? |
|---|---|
| `id`, `position`, `company`, `source`, `link`, `scraped_at`, `location`, `date`, `description`, `responsibilities`, `requirements`, `nice_to_have`, `extraction_ok`, `extraction_attempts`, `years_min`, `agency`, `dedup_key` | Yes. On an existing record: only fill fields that are empty/null, and update `extraction_ok` / `extraction_attempts` / `years_min` when you re-verify it. |
| `status`, `status_source`, `status_changed_at`, `applied_at`, `applied_via` | Never (`ingest.py` sets them for imports). |
| `followed_up_at`, `archive_reason`, `notes`, `recruiter_phone`, `last_email`, `cv_variant`, `cv_tailored_at` | Never. |

A non-empty value in any scraper field means someone (a previous run, or the
user via Edit) already set it — do not overwrite it.

## Step 0.5 — What you decide vs. what `ingest.py` decides

You extract. `ingest.py` (Step 2) gates, dedups, and writes, using the same
Python functions as `build_html.py`, so there is nothing to compute by hand:
no years parsing, no dedup keys, no agency matching. The only judgement calls
in this shortcut are the title pre-filter in Step 2 (optional, time-saving)
and what counts as a description / requirement line when a page's headers
are irregular.

## Step 1 — LinkedIn

Both guest endpoints render as ordinary pages when you navigate a tab to
them directly — no script injection needed. Read them with the standard
browser tools: `navigate`, then `get_page_text` (rendered text) and, on
search-results pages, `read_page` (accessibility tree, for the actual links
and job ids). Chain a whole sequence of these into one `browser_batch` call
whenever you can predict the steps ahead — that's what keeps this fast
despite there being no more `window.__RAW_LI` batching.

Method notes (rewritten 2026-09-16, confirmed live against real search and
detail pages; the previous inject-JS-and-dump-to-`<pre>` method is in git
history, commit 642c8e2):

- **No JS injection, no ~1 KB output truncation, no query-string-content
  block.** Those three problems were properties of `javascript_tool`'s own
  return channel. `navigate` / `get_page_text` / `read_page` don't go
  through it, so none of the old workarounds (base64, `<pre>` dumps,
  slicing) apply here — read the page, you get the whole thing.
- Get a tab once at the start of the run (`tabs_context_mcp
  {createIfEmpty: true}`), reuse its `tabId` for every action, and
  `tabs_close_mcp` it when you're done.
- **Rate limits are still there** — this is the same guest API, just read a
  different way, so assume the same ceiling seen before (HTTP 429 after
  roughly 60 requests in a few minutes) until proven otherwise. Batch **no
  more than ~10 navigate+get_page_text pairs per `browser_batch` call**;
  after each batch, check whether any page came back as a sign-in wall /
  CAPTCHA / error instead of a job page. If so, stop, wait 90 s, and resume
  from where you left off.
- **There is no persistent script state any more** — each `navigate` is a
  fresh page load, so there's no `window.__LI_ALL` to collect into. Track
  which job ids you've already seen yourself: a plain running list kept in
  this conversation is enough for one run; cross-check new ids against
  `existing_by_link` (Step 0) so you don't re-fetch a detail you already
  have verified text for.
- **Pre-filter on the title before fetching a detail** (Step 2, gates
  2a–2d'): read each card's title against `config.json`'s `role_families`,
  `seniority_titles`, `teaching_titles`, `excluded_titles` regexes yourself
  and skip anything that fails. This halves the detail fetches. Never
  pre-filter on years.

### Search results

For each query × page (`start` = 0, 10, 20), in one `browser_batch` call:

1. `navigate` to the search URL (template below).
2. `read_page` with `filter: "interactive"` — the job's own link is every
   **odd**-numbered link in DOM order (`[ref_1]`, `[ref_3]`, …; the
   even-numbered ones link to the company page instead). Pull the numeric
   id out of its href with `/jobs/view/[^"]*-(\d{9,})`.
3. `get_page_text` — cards come back in the same order as the links. Each
   card reads as: title line, **the same title repeated**, company,
   location, an optional status line (`Actively Hiring` / `Be an early
   applicant`), a relative date (`N days/weeks/months ago`), sometimes
   `Apply Now` on the same line. Split on the repeated-title boundary to get
   one block per card, and pair block *N* with job-link *N* from step 2 —
   they're in the same order because both reflect the page's DOM order.

| Purpose | URL |
|---|---|
| Search page (10 cards/call) | `https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=<q>&location=Israel&f_TPR=r<WINDOW_SECONDS>&sortBy=DD&start=<0,10,20>` |

Run **each** of these keyword queries, three pages each (`start` = 0, 10,
20 → up to 30 cards per query):

| # | `keywords` |
|---|---|
| 1 | `"data scientist"` |
| 2 | `"machine learning engineer" OR "ML engineer"` |
| 3 | `"AI engineer"` |
| 4 | `"NLP engineer" OR "LLM engineer"` |
| 5 | `"algorithm developer" OR "algorithm engineer"` |
| 6 | `מדען נתונים OR למידת מכונה OR מהנדס אלגוריתמים` |

- `f_TPR=r<seconds>`: seconds since `sources.LinkedIn.last_scrape_at` in
  `state.json`, rounded up to the hour, **minimum 21600 (6 h), maximum
  604800 (7 d)**; no entry → 604800.
- No `f_E` (experience-level) filter — the gates do that job.
- The same job can appear under several queries — dedup by the numeric id
  you already collected, same as before.
- Stop paginating a query once a page returns fewer than 10 cards (end of
  results for that window).

### Job details

For each surviving, not-yet-seen job id, in `browser_batch` batches of
~8–10 pairs:

1. `navigate` to `https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/<ID>`.
2. `get_page_text`.

| Purpose | URL |
|---|---|
| One posting's full text | `https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/<ID>` |

The page reads as: title line, `Company Location` line, `<age> · <N
applicants>` line, then the description — plain prose first, then bulleted
sections. Split it the same way the old JS classifier did, just by reading
it yourself: a short line matching `about the (role|job|company|team)` /
`who we are` starts the description block; `responsibilit|what you('ll|
will) do|your role|day to day` starts responsibilities; `requirement|
qualification|what you bring|must have|who you are|skills` starts
requirements; `nice to have|bonus|preferred|advantage` starts
nice-to-have. `Seniority level` / `Employment type` / `Job function` /
`Industries` near the bottom are LinkedIn's own coarse metadata, not
requirements text — ignore them for gating (one live posting showed
"Seniority level: Director" while its actual text asked for "4+ years";
trust the title/years gates, not this field).

Write `position`, `company`, `location`, `date` from the search-results card
(Company/location there are usually cleaner than re-splitting the detail
page's `Company Location` line); write `description` /
`responsibilities` / `requirements` / `nice_to_have` from the detail page.

## Step 1b — Re-verify unverified postings (before scraping new ones)

For each record in `to_verify` (Step 0), take the numeric id out of its
`link`, `navigate` to `https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/<ID>`,
and `get_page_text` — same "Job details" method as Step 1.
Then add what you extracted to `scrape_raw.json` (Step 2) under that
record's `source`, with the **same `link`**. `ingest.py` merges only empty
fields, bumps `extraction_attempts`, and recomputes `extraction_ok`. If it is
still unverified after this, leave it — the dashboard shows it as
*unverified* and the user can paste the requirements by hand.

Cap this pass at 10 records per run; oldest `scraped_at` first.

## Step 2 — Hand everything to `ingest.py` (it applies the gates)

You do **not** build records, gate, or dedup by hand. Write every posting you
extracted (verified or not) to `scrape_raw.json` at the project root in this
shape, then run the two commands:

```json
{"scraped_at": "<ISO-8601 UTC of this run>",
 "batches": [
   {"source": "LinkedIn", "finished": true,
    "postings": [
      {"position": "...", "company": "...", "link": "<canonical URL, see templates below>",
       "location": null, "date": "YYYY-MM-DD or null", "description": "prose lead-in or null",
       "responsibilities": ["..."], "requirements": ["..."], "nice_to_have": [],
       "applied_date": null}
    ]}
 ]}
```

```
python ingest.py scrape_raw.json
python build_html.py
```

- `finished: false` when you had to stop early (login / CAPTCHA / second
  429); the `state.json` window is then left alone so the next run still
  covers the gap.
- `applied_date` stays `null` here (the Gmail task uses it for applications
  the user sent themselves).
- Arrays may be empty. **Never write `["N/A"]`.** Strings are fine too —
  `ingest.py` splits them on line breaks / bullets.
- Include postings you re-extracted for Step 1b: a `link` that already
  exists in `jobs.json` is treated as an enrichment, never as a duplicate.

Canonical `link` templates — always build the URL yourself from the
extracted id, never trust the DOM anchor's href:

| Source | Template |
|---|---|
| LinkedIn | `https://www.linkedin.com/jobs/view/<ID>/` |

### What `ingest.py` does with each posting (for reference — same code as `build_html.py`)

| # | Gate | Where | Rule | Outcome |
|---|---|---|---|---|
| 2a | Role family | title | must match `role_families.ai` **or** `role_families.ds` | *drop* (`family`) |
| 2b | Seniority | title | matches `seniority_titles` | *drop* (`senior`) |
| 2c | Teaching | title | matches `teaching_titles` | *drop* (`teaching`) |
| 2d | Clinical | title | matches `clinical_titles` | *drop* (`clinical`). ML roles at medtech companies are **kept**. |
| 2d' | Excluded role | title | matches `excluded_titles` (product/devops/full-stack/DSP/signal-processing/navigation/bootcamp… titles that only *mention* AI) | *drop* (`other`) |
| 2e | Anonymous employer | company | `anonymous_companies` on AllJobs-sourced records only (dormant now) | *drop* (`anonymous`) |
| 2f | Verified? | text | ≥2 requirement lines or ≥200-char description → `extraction_ok` | *flag* only |
| 2g | Years | text | lower bound of the stated range > `years_soft_max` (5), whenever a figure could be parsed (verified or not). 4–5 stays as tier *weak* for the Fit CVs step to judge; ≤ `years_max` (3) is always fine | *drop* (`years`) |
| 2h | Agency | company | `agencies` list / `agency_patterns` | *flag* |
| 2i | Known link | link | already in `jobs.json` (any status) | enrich empty fields; `applied_date` on a `new` record → `applied` |
| 2j | Duplicate | key | normalized company\|position already known | *drop* (`duplicate`) |

Records land as `status: "new"`, `status_source: "scraper"` — or, when a
posting carries `applied_date` (Gmail import), as `status: "applied"`,
`applied_via: "manual"`, `applied_at: <date>`, with an import note. Gates
2a–2g are skipped for those imports.

**Use 2a–2d' yourself as a pre-filter** (the title pre-filter described in
Step 1) so you never fetch a detail for a card whose *title* `ingest.py`
would drop anyway. Never pre-filter on years or on anything you'd need the
detail page for.

## Step 3 — After the two commands

`ingest.py` prints one line (new / enriched / imported / duplicates /
filtered by reason / agency / unverified). `build_html.py` prints the
migration, maintenance and fit-tier summary. Put both in your report. Do not
write any other files; do not edit `jobs.json` directly.

Then commit (scratch files are gitignored):

```
git -c user.name=mikigit97 -c user.email=mickaelz@post.bgu.ac.il add -A && git -c user.name=mikigit97 -c user.email=mickaelz@post.bgu.ac.il commit -m "scrape: <new N, enriched E, window r<seconds>>"
```

## Step 4 — Summary

```
LinkedIn: <cards seen / detail fetched / pre-filtered, window r<seconds>, 429s: n> · stopped early: <no | reason>
ingest:  <the line ingest.py printed>
build:   <the lines build_html.py printed>
```

## Guardrails

- **Login / CAPTCHA**: pause and wait for the user. Do not retry
  automatically. If it isn't resolved, stop with `finished: false` so the
  `state.json` entry stays unchanged.
- **Runtime cap**: 10 minutes total (the previous JS-batched method did a
  full run with ~100 LinkedIn details and two rate-limit pauses in ~8; this
  method's wall-clock under the same load hasn't been re-measured — if it
  runs long, that's information for next time, not a reason to blow past
  the cap). If exceeded, dump what you have, write `scrape_raw.json` with
  `finished: false`, and stop.
- **HTTP 429 (or a sign-in/CAPTCHA page in place of a job page) from
  LinkedIn**: pause 90 s, then resume the `browser_batch` sequence from the
  first id/page you hadn't gotten to yet; after a second 429 in the same
  run, stop with `finished: false`.
- **Per query**: 30 LinkedIn cards (3 API pages).
- **`requests` in the Python sandbox is proxy-blocked** — all scraping goes
  through Claude in Chrome.
- **Never write `["N/A"]`; never edit `jobs.json` by hand** — `ingest.py`
  is the only writer in this shortcut.
- **If `scrape_raw.json` or `jobs.json` is write-locked**, print the error
  and stop; do not fall back to a sibling file.
