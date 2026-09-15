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
the steps below exactly. Use the accessibility tree or page-state JavaScript,
never screenshots.

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

LinkedIn can be read without scrolling its virtualised list or opening one
detail page at a time: two guest endpoints answer `fetch()` from any tab on
linkedin.com. Open **one tab** on any `linkedin.com/jobs/...` page, run the
code below in it, and collect results in `window.__RAW_LI`.

Method notes (learned on the 2026-09-15 live run):

- **Tool output is truncated at ~1 KB.** Never return a large object from
  `javascript_tool`. Instead write it into the page and read it back with
  `get_page_text` (cap ≈ 50 KB):
  ```javascript
  document.body.innerHTML = '<pre>@@START@@' + JSON.stringify(window.__RAW_LI) + '@@END@@</pre>';
  ```
  then call `get_page_text` on that tab and copy the text between the
  markers into `scrape_raw.json`. Do this only when you are done with the
  page — it replaces the DOM. If the payload exceeds ~45 KB, dump it in
  slices (`JSON.stringify(x).slice(0, 45000)`, then `.slice(45000, 90000)`)
  and concatenate.
- **Do not `return` or echo function sources that contain URLs** — the
  extension blanks any output that looks like a query string. Return counts
  and ids only.
- **Rate limits.** The guest API answers HTTP 429 after roughly 60 requests
  in a few minutes. Space detail fetches ~2 s apart, and if a fetch returns
  429 stop, wait 60–120 s, then resume from where you stopped. A record whose
  detail fetch failed is still written (with `description: null`,
  `requirements: []`) so `ingest.py` can mark it unverified and Step 1b can
  retry it next run.
- **Pre-filter on the title before fetching a detail** (Step 2, gates 2a–2d'):
  build the four regexes from `config.json` once, as `window.__FAM`,
  `__SEN`, `__TEACH`, `__EXCL`, and skip cards whose title fails them. This
  halves the detail fetches. Never pre-filter on years.

### Guest search + posting APIs

Two endpoints, both work with the normal logged-in cookie and need no
scrolling:

| Purpose | URL |
|---|---|
| Search page (10 cards per call) | `https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=<q>&location=Israel&f_TPR=r<WINDOW_SECONDS>&sortBy=DD&start=<0,10,20>` |
| One posting's full text | `https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/<ID>` |

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
- The same job appears under several queries; `__LI_ALL` is keyed by job id
  so it is collected once.
- Open any `linkedin.com/jobs/...` page in the tab first so `fetch()` runs
  same-origin with the session cookie.

```javascript
// ---- LinkedIn: define once per tab -------------------------------------
window.__LI_ALL = window.__LI_ALL || {};          // id -> card
window.__LI_WINDOW = 604800;                      // set from state.json

window.__liSearch = async function (q, start) {
  const url = 'https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search'
    + '?keywords=' + encodeURIComponent(q) + '&location=Israel&f_TPR=r' + window.__LI_WINDOW
    + '&sortBy=DD&start=' + (start || 0);
  const r = await fetch(url, { credentials: 'include' });
  if (r.status === 429) throw new Error('429');
  const html = await r.text();
  const out = {}; const re = /<li[\s\S]*?<\/li>/g; let m;
  while ((m = re.exec(html))) {
    const li = m[0];
    const idm = li.match(/\/jobs\/view\/[^"'?]*?-?(\d{9,})/) || li.match(/data-entity-urn="urn:li:jobPosting:(\d+)"/);
    if (!idm) continue;
    const id = idm[1]; if (out[id]) continue;
    const g = rx => { const x = li.match(rx); return x ? x[1].replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim() : ''; };
    out[id] = {
      title:   g(/class="base-search-card__title[^"]*"[^>]*>([\s\S]*?)<\//),
      company: g(/class="base-search-card__subtitle[^"]*"[^>]*>([\s\S]*?)<\/h4>/),
      loc:     g(/class="job-search-card__location[^"]*"[^>]*>([\s\S]*?)<\//),
      posted:  g(/datetime="([^"]+)"/),          // YYYY-MM-DD
    };
  }
  return { status: r.status, n: Object.keys(out).length, out };
};

window.__liQuery = async function (q) {
  let added = 0, seen = 0;
  for (const start of [0, 10, 20]) {
    const t = await window.__liSearch(q, start); seen += t.n;
    for (const [id, c] of Object.entries(t.out)) if (!window.__LI_ALL[id]) { window.__LI_ALL[id] = c; added++; }
    if (t.n < 10) break;
    await new Promise(r => setTimeout(r, 1200));
  }
  return { q, seen, added, total: Object.keys(window.__LI_ALL).length };
};

window.__liDetail = async function (id) {
  const r = await fetch('https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/' + id, { credentials: 'include' });
  if (r.status === 429) throw new Error('429');
  const html = await r.text();
  const i = html.indexOf('show-more-less-html__markup'); if (i < 0) return null;
  const start = html.indexOf('>', i) + 1; const end = html.indexOf('</section>', start);
  let frag = html.slice(start, end > 0 ? end : start + 20000);
  frag = frag.replace(/<br\s*\/?>/gi, '\n').replace(/<\/(p|li|div|h\d)>/gi, '\n').replace(/<li[^>]*>/gi, '• ').replace(/<[^>]+>/g, '');
  const ta = document.createElement('textarea'); ta.innerHTML = frag; const text = ta.value;   // decodes &amp; etc.
  const lines = text.split('\n').map(s => s.replace(/\s+/g, ' ').trim()).filter(Boolean);
  const desc = [], resp = [], req = [], nice = []; let cur = 'd';
  for (const raw of lines) {
    const line = raw.replace(/^[•*\-–\s]+/, '').trim(); const ll = line.toLowerCase();
    if (line.length < 60 && /(about the (?:role|job|company|team)|who we are|company description|job description|the role)/.test(ll)) { cur = 'd'; continue; }
    if (line.length < 60 && /(responsibilit|what you will do|what you'll do|what you’ll do|you will:|your role|day to day|in this role)/.test(ll)) { cur = 'r'; continue; }
    if (line.length < 60 && /(requirement|qualification|you will need|what you bring|must have|who you are|what we're looking for|what we are looking for|skills)/.test(ll)) { cur = 'q'; continue; }
    if (line.length < 60 && /(nice to have|bonus|preferred|advantage|plus:)/.test(ll)) { cur = 'n'; continue; }
    if (line.length < 8 || /^show (more|less)$/i.test(line)) continue;
    if (cur === 'r') resp.push(line); else if (cur === 'q') req.push(line); else if (cur === 'n') nice.push(line); else desc.push(line);
  }
  return { description: desc.join(' ').slice(0, 600) || null, responsibilities: resp.slice(0, 4), requirements: req.slice(0, 6), nice_to_have: nice.slice(0, 3) };
};

// Fetch details for every collected card that passes the title pre-filter.
// Resumable: cards already in __RAW_LI or __LI_SKIP are not touched again.
window.__RAW_LI = window.__RAW_LI || {}; window.__LI_SKIP = window.__LI_SKIP || {};
window.__liRun = async function (max) {
  let done = 0, pre = 0, rate = false;
  for (const [id, c] of Object.entries(window.__LI_ALL)) {
    if (window.__RAW_LI[id] || window.__LI_SKIP[id]) continue;
    if (done >= max) break;
    const t = c.title;
    if (!window.__FAM.test(t) || window.__SEN.test(t) || window.__TEACH.test(t) || window.__EXCL.test(t)) { window.__LI_SKIP[id] = t; pre++; continue; }
    const rec = { position: t, company: c.company, link: 'https://www.linkedin.com/jobs/view/' + id + '/', location: c.loc || null,
                  date: c.posted || null, description: null, responsibilities: [], requirements: [], nice_to_have: [], applied_date: null };
    try { const d = await window.__liDetail(id); if (d) Object.assign(rec, d); }
    catch (e) { if (String(e).includes('429')) { rate = true; break; } }
    window.__RAW_LI[id] = rec; done++;
    await new Promise(r => setTimeout(r, 1800));
  }
  const remaining = Object.keys(window.__LI_ALL).filter(id => !window.__RAW_LI[id] && !window.__LI_SKIP[id]).length;
  return { fetched: done, prefiltered: pre, stored: Object.keys(window.__RAW_LI).length, remaining, rateLimited: rate };
};
```

Call sequence (one `javascript_tool` call each, so a 45-second CDP timeout
never bites): `__liQuery(q1)` … `__liQuery(q6)` with a 3 s pause between
queries, then `__liRun(12)` repeatedly until `remaining` is 0. If
`rateLimited` comes back `true`, wait 90 s and call `__liRun` again — it
resumes. Finally dump `window.__RAW_LI` through the `<pre>` channel.
`Object.values(window.__RAW_LI)` is the LinkedIn `postings` array.

The old DOM route (`#job-details`, `currentJobId`, standalone `/jobs/view/`
scroll-and-wait) is no longer needed; it is slower and the list is
virtualised to ~7 visible cards.

## Step 1b — Re-verify unverified postings (before scraping new ones)

For each record in `to_verify` (Step 0), open its `link` and run the same
extractor you would use for its `source` (`__liDetail(<id>)` for the numeric id in its `link`).
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

**Use 2a–2d' yourself as a pre-filter** (the `__FAM` / `__SEN` / `__TEACH`
/ `__EXCL` regexes in Step 1) so you never fetch a detail for a card whose
*title* `ingest.py` would drop anyway. Never pre-filter on years or on
anything you'd need the detail page for.

## Step 3 — After the two commands

`ingest.py` prints one line (new / enriched / imported / duplicates /
filtered by reason / agency / unverified). `build_html.py` prints the
migration, maintenance and fit-tier summary. Put both in your report. Do not
write any other files; do not edit `jobs.json` directly.

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
- **Runtime cap**: 10 minutes total (a full run with ~100 LinkedIn details
  and two rate-limit pauses takes ~8). If exceeded, dump what you have,
  write `scrape_raw.json` with `finished: false`,
  and stop.
- **HTTP 429 from LinkedIn**: pause 90 s, resume with `__liRun`; after a
  second 429 in the same run, stop with `finished: false`.
- **Per query**: 30 LinkedIn cards (3 API pages).
- **`requests` in the Python sandbox is proxy-blocked** — all scraping goes
  through Claude in Chrome.
- **Never write `["N/A"]`; never edit `jobs.json` by hand** — `ingest.py`
  is the only writer in this shortcut.
- **If `scrape_raw.json` or `jobs.json` is write-locked**, print the error
  and stop; do not fall back to a sibling file.
