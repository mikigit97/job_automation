# Chrome shortcut: /scrape-jobs  (schema v2)

Save this as a Claude in Chrome shortcut. Schedule it Sunday–Thursday at 08:00
and 16:00. It scrapes three Israeli job boards and appends new postings to
`jobs.json` at the Cowork project root, then rebuilds the dashboard.

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
  "position": "...", "company": "...", "source": "LinkedIn|AllJobs|Drushim",
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
  `extraction_attempts < 2`, and `source` in LinkedIn/AllJobs/Drushim. You
  will re-open these (Step 1b) before scraping anything new.

### Field ownership — the scraper's lane

| Fields | Scraper may write? |
|---|---|
| `id`, `position`, `company`, `source`, `link`, `scraped_at`, `location`, `date`, `description`, `responsibilities`, `requirements`, `nice_to_have`, `extraction_ok`, `extraction_attempts`, `years_min`, `agency`, `dedup_key` | Yes. On an existing record: only fill fields that are empty/null, and update `extraction_ok` / `extraction_attempts` / `years_min` when you re-verify it. |
| `status`, `status_source`, `status_changed_at`, `applied_at`, `applied_via` | Only in one case: a Drushim posting the user already sent a CV to (Step 3). Otherwise never. |
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

## Step 1 — Boards

All three boards can be read without scrolling virtualised lists or opening
one detail page at a time: LinkedIn and Drushim expose guest JSON/HTML
endpoints that `fetch()` can call from any tab on that domain, and AllJobs
renders full card text on the results page. Open **one tab per board**, run
the code below in it, and collect the results in `window.__RAW_<board>`.

Method notes that apply to every board (learned on the 2026-09-15 live run):

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
- **Rate limits.** LinkedIn's guest API answers HTTP 429 after roughly 60
  requests in a few minutes. Space detail fetches ~2 s apart, and if a fetch
  returns 429 stop that board, wait 60–120 s, then resume from where you
  stopped. A record whose detail fetch failed is still written (with
  `description: null`, `requirements: []`) so `ingest.py` can mark it
  unverified and Step 1b can retry it next run.
- **Pre-filter on the title before fetching a detail** (Step 2, gates 2a–2c
  and the `excluded_titles` list): build the four regexes from
  `config.json` once, as `window.__FAM`, `__SEN`, `__TEACH`, `__EXCL`, and
  skip cards whose title fails them. This halves the detail fetches. Never
  pre-filter on years.

### Board 1 — LinkedIn (guest search + posting APIs)

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

### Board 2 — AllJobs

```
https://www.alljobs.co.il/SearchResultsGuest.aspx?page=<1..4>&position=1733&type=&city=&region=
```

- Position code `1733` = Data Scientist. Code `52` returns nothing now;
  `49` still works for the older DS/ML bucket. Four pages of ~26 cards.
- Visit `https://www.alljobs.co.il/` first for the cookie, or the search URL
  redirects to `/ErrorUnderConstruction.html`.
- **Guest view hides most employers.** On the 2026-09-15 run 45 of 56 cards
  were hidden-employer cards; only 5 were kept. Logging in to AllJobs in
  Chrome exposes the names — until then this board contributes little.

**Link template.** Always build
`https://www.alljobs.co.il/Search/UploadSingle.aspx?JobID=<id>` from the
card's `JobID`; the DOM href (`ViewJob.aspx`) 404s.

**Card layout.** Each card's lines, read from the "Location:" /
"מיקום המשרה:" row upward, are `[..., <age>, <position>, <company>,
Location:]` for a named employer and `[..., <age>, <position>, Location:]`
for a hidden one — the company line is simply missing, so a fixed offset
puts the age ("6 ימים", "היום", a date) into `position`. Detect that and
mark the company as `חברה חסויה`; `ingest.py` drops those when
`drop_anonymous_alljobs` is on.

```javascript
const LOC_RE = /(?:^|\n)\s*(?:Location:|מיקום המשרה:)/;
const AGE_RE = /^(?:\d+\s*ימים|יום|היום|אתמול|לפני|\d{1,2}\/\d{1,2}\/\d{2,4})/;
function findCard(anchor) {                       // walk up to the element that holds the Location row
  let node = anchor.parentElement;
  for (let i = 0; i < 10 && node && node !== document.body; i++) { if (LOC_RE.test(node.innerText || '')) return node; node = node.parentElement; }
  return null;
}
function parseCard(lines) {
  const i = lines.findIndex(l => /^(?:Location:|מיקום המשרה:)/.test(l));
  let position, company;
  if (i >= 2 && !AGE_RE.test(lines[i - 2])) { position = lines[i - 2]; company = lines[i - 1]; }
  else if (i >= 1)                            { position = lines[i - 1]; company = 'חברה חסויה'; }
  else                                        { position = lines[0] || ''; company = lines[1] || ''; }
  const location = i >= 0 ? lines[i].replace(/^(?:Location:|מיקום המשרה:)\s*/, '') : null;
  // sections: check headers BEFORE the short-line skip — "דרישות:" is only 7 chars
  const body = i >= 0 ? lines.slice(i + 1) : lines;
  const desc = [], resp = [], req = [], nice = []; let cur = 'd';
  const RA = ['תחומי אחריות', 'responsibilities', 'key responsibilities', 'תפקיד כולל', 'תיאור התפקיד'];
  const QA = ['דרישות', 'requirements', 'qualifications', 'ניסיון מקצועי', 'חובה:', 'must have'];
  const NA = ['יתרון', 'nice to have', 'bonus', 'preferred', 'advantage'];
  const SKIP = ['job type', 'סוג משרה', 'המשרה מיועדת', 'לעוד משרות', 'חברת השמה', 'שלח קורות חיים', 'send cv'];
  for (const line of body) {
    const ll = line.toLowerCase();
    if (line.length < 40 && RA.some(k => ll.includes(k))) { cur = 'r'; continue; }
    if (line.length < 40 && QA.some(k => ll.includes(k))) { cur = 'q'; continue; }
    if (line.length < 40 && NA.some(k => ll.includes(k))) { cur = 'n'; continue; }
    if (SKIP.some(k => ll.includes(k)) || line.length < 8) continue;
    const clean = line.replace(/^[•*\-–\s]+/, '');
    if (cur === 'r') resp.push(clean); else if (cur === 'q') req.push(clean); else if (cur === 'n') nice.push(clean); else desc.push(clean);
  }
  return { position, company, location, description: desc.join(' ').slice(0, 600) || null,
           responsibilities: resp.slice(0, 4), requirements: req.slice(0, 6), nice_to_have: nice.slice(0, 3) };
}
window.__RAW_AJ = window.__RAW_AJ || {};
let hidden = 0;
for (const a of document.querySelectorAll('a[href*="JobID="]')) {
  const id = new URL(a.href).searchParams.get('JobID');
  if (!id || window.__RAW_AJ[id]) continue;
  const card = findCard(a); if (!card) continue;
  const lines = card.innerText.split('\n').map(l => l.trim()).filter(l => l.length > 1);
  const p = parseCard(lines);
  if (p.company === 'חברה חסויה') { hidden++; continue; }        // skip early, they are dropped anyway
  if (!p.position || p.position.length < 4 || AGE_RE.test(p.position)) continue;   // card walk fell through
  window.__RAW_AJ[id] = { position: p.position, company: p.company, link: 'https://www.alljobs.co.il/Search/UploadSingle.aspx?JobID=' + id,
                          location: p.location, date: null, description: p.description, responsibilities: p.responsibilities,
                          requirements: p.requirements, nice_to_have: p.nice_to_have, applied_date: null };
}
JSON.stringify({ kept: Object.keys(window.__RAW_AJ).length, hiddenOnThisPage: hidden });
```

Run it on each of the four pages (`window.__RAW_AJ` accumulates because the
tab stays on alljobs.co.il), then dump `Object.values(window.__RAW_AJ)`
through the `<pre>` channel. Report the hidden count in the summary.

### Board 3 — Drushim (guest JSON API)

Drushim is a Next.js site now; the old `window.__NUXT__` cache and the
`/jobs/subcat/...?experience=1-2` filter URL are gone (the latter returns 0
results). The search page's own data source is a public JSON endpoint that
`fetch()` can call directly from any drushim.co.il tab:

```
https://webapi.drushim.co.il/api/jobs/search?SearchTerm=<q>&page=<0-based>&ssaen=1&isAA=true
```

Response: `ResultList[]` (25 per page), `TotalSearchResultCount`,
`TotalPagesNumber`, `NextPageNumber` (`-1` on the last page). Each item:

```
JobInfo.JobCode, JobInfo.Hash, JobInfo.Date (ISO), JobInfo.SeekerJobStatus
JobContent.Name, JobContent.Description (HTML), JobContent.Requirements (HTML),
JobContent.Experience.NameInHebrew ("1-2 שנים", "שנתיים", "ללא ניסיון" …),
JobContent.Zones[0].NameInHebrew, Company.CompanyDisplayName
```

`JobContent.Requirements` carries the real requirements text (the page's
`__NEXT_DATA__` only has the description), so use the API, not the DOM.
Run these keyword queries, all pages each:

| # | `SearchTerm` |
|---|---|
| 1 | `data scientist` |
| 2 | `machine learning` |
| 3 | `AI engineer` |
| 4 | `NLP` |
| 5 | `מדען נתונים` |
| 6 | `אלגוריתמים` |

```javascript
// Open https://www.drushim.co.il/jobs/search/data%20scientist/?ssaen=1 first (same-origin cookie).
window.__RAW_DR = window.__RAW_DR || {};
const strip = s => (s || '').replace(/<br\s*\/?>|<\/(p|li|div)>/gi, '\n').replace(/<[^>]+>/g, ' ').replace(/&nbsp;/g, ' ').replace(/[ \t]+/g, ' ').trim();
const toLines = s => strip(s).split(/\n|(?<=\.)\s+(?=[A-Zא-ת])|\s+[•·]\s+|\s+-\s+/).map(x => x.trim()).filter(x => x.length > 3);
window.__drQuery = async function (q) {
  let added = 0, page = 0, pages = 1;
  while (page < pages && page < 6) {
    const r = await fetch('https://webapi.drushim.co.il/api/jobs/search?SearchTerm=' + encodeURIComponent(q) + '&page=' + page + '&ssaen=1&isAA=true', { credentials: 'include' });
    const j = await r.json(); pages = j.TotalPagesNumber || 1;
    for (const x of (j.ResultList || [])) {
      const code = String(x.JobInfo.JobCode); if (window.__RAW_DR[code]) continue;
      const exp = x.JobContent.Experience && x.JobContent.Experience.NameInHebrew;
      const req = toLines(x.JobContent.Requirements);
      if (exp) req.unshift('ניסיון: ' + exp);                         // structured field -> years_min parser
      window.__RAW_DR[code] = {
        position: x.JobContent.Name || x.JobContent.FullName || '', company: x.Company.CompanyDisplayName || x.Company.NameInHebrew || '',
        link: 'https://www.drushim.co.il/job/' + code + '/' + String(x.JobInfo.Hash || '').toLowerCase() + '/',
        location: x.JobContent.Zones && x.JobContent.Zones[0] ? x.JobContent.Zones[0].NameInHebrew : null,
        date: (x.JobInfo.Date || '').slice(0, 10) || null,
        description: strip(x.JobContent.Description).slice(0, 600) || null,
        responsibilities: [], requirements: req.slice(0, 7), nice_to_have: [],
        applied_date: null, seeker_status: x.JobInfo.SeekerJobStatus };
      added++;
    }
    if (j.NextPageNumber === -1 || j.NextPageNumber == null) break;
    page = j.NextPageNumber;
    await new Promise(r => setTimeout(r, 800));
  }
  return { q, added, total: Object.keys(window.__RAW_DR).length };
};
```

One `__drQuery(q)` call per query, then dump `Object.values(window.__RAW_DR)`
through the `<pre>` channel.

**Already-applied import.** As a guest every item reports
`SeekerJobStatus: 0` and the page shows no "שלחת קו"ח" badge, so this run
could not import applied jobs. When the user is logged in to Drushim in
Chrome, check whether `SeekerJobStatus` becomes non-zero on jobs they
applied to; if it does, set `applied_date` to `JobInfo.Date`'s date part
(the true send date is not in the payload) and note "date = posting date"
— `ingest.py` then imports the record as `applied`. If the field stays 0
when logged in, fall back to the DOM badge walk described in the git
history of this file (commit f54293f).

Apply the title pre-filter here too: skip items whose `JobContent.Name`
fails `__FAM` / hits `__SEN`, `__TEACH`, `__EXCL` before storing, and keep
the counts for the summary.

## Step 1b — Re-verify unverified postings (before scraping new ones)

For each record in `to_verify` (Step 0), open its `link` and run the same
extractor you would use for its `source` (LinkedIn: `__liDetail(<id>)`;
AllJobs: the card parser on the results page or the `UploadSingle.aspx`
page; Drushim: the search API with the query that found it, matched on
`JobInfo.JobCode`).
Then add what you extracted to `scrape_raw.json` (Step 2) under that
record's `source`, with the **same `link`**. `ingest.py` merges only empty
fields, bumps `extraction_attempts`, and recomputes `extraction_ok`. If it is
still unverified after this, leave it — the dashboard shows it as
*unverified* and the user can paste the requirements by hand.

Cap this pass at 10 records per run; oldest `scraped_at` first.

## Step 2 — Hand everything to `ingest.py` (it applies the gates)

You do **not** build records, gate, or dedup by hand. Write every posting you
extracted (all boards, verified or not) to `scrape_raw.json` at the project
root in this shape, then run the two commands:

```json
{"scraped_at": "<ISO-8601 UTC of this run>",
 "batches": [
   {"source": "LinkedIn", "finished": true,
    "postings": [
      {"position": "...", "company": "...", "link": "<canonical URL, see templates below>",
       "location": null, "date": "YYYY-MM-DD or null", "description": "prose lead-in or null",
       "responsibilities": ["..."], "requirements": ["..."], "nice_to_have": [],
       "applied_date": null}
    ]},
   {"source": "AllJobs", "finished": true, "postings": [...]},
   {"source": "Drushim", "finished": true, "postings": [...]}
 ]}
```

```
python ingest.py scrape_raw.json
python build_html.py
```

- `finished: false` for a board you had to skip (login / CAPTCHA / timeout);
  its `state.json` window is then left alone so the next run still covers
  the gap.
- `applied_date` is Drushim-only: the `YYYY-MM-DD` from the card's
  "שלחת קו"ח ב" badge, else `null`.
- Arrays may be empty. **Never write `["N/A"]`.** Strings are fine too —
  `ingest.py` splits them on line breaks / bullets.
- Include postings you re-extracted for Step 1b: a `link` that already
  exists in `jobs.json` is treated as an enrichment, never as a duplicate.

Canonical `link` templates — always build the URL yourself from the
extracted id, never trust the DOM anchor's href:

| Source | Template |
|---|---|
| LinkedIn | `https://www.linkedin.com/jobs/view/<ID>/` |
| AllJobs | `https://www.alljobs.co.il/Search/UploadSingle.aspx?JobID=<ID>` |
| Drushim | `https://www.drushim.co.il/job/<JobCode>/<hash-lowercase>/` |

### What `ingest.py` does with each posting (for reference — same code as `build_html.py`)

| # | Gate | Where | Rule | Outcome |
|---|---|---|---|---|
| 2a | Role family | title | must match `role_families.ai` **or** `role_families.ds` | *drop* (`family`) |
| 2b | Seniority | title | matches `seniority_titles` | *drop* (`senior`) |
| 2c | Teaching | title | matches `teaching_titles` | *drop* (`teaching`) |
| 2d | Clinical | title | matches `clinical_titles` | *drop* (`clinical`). ML roles at medtech companies are **kept**. |
| 2d' | Excluded role | title | matches `excluded_titles` (product/devops/full-stack/DSP/signal-processing/navigation/bootcamp… titles that only *mention* AI) | *drop* (`other`) |
| 2e | Anonymous employer | company | AllJobs + `anonymous_companies` (when `drop_anonymous_alljobs`) | *drop* (`anonymous`) |
| 2f | Verified? | text | ≥2 requirement lines or ≥200-char description → `extraction_ok` | *flag* only |
| 2g | Years | text | lower bound of the stated range > `years_max`, whenever a figure could be parsed (verified or not) | *drop* (`years`) |
| 2h | Agency | company | `agencies` list / `agency_patterns` | *flag* |
| 2i | Known link | link | already in `jobs.json` (any status) | enrich empty fields; Drushim `applied_date` on a `new` record → `applied` |
| 2j | Duplicate | key | normalized company\|position already known | *drop* (`duplicate`) |

Records land as `status: "new"`, `status_source: "scraper"` — or, for a
Drushim card with `applied_date`, as `status: "applied"`, `applied_via:
"manual"`, `applied_at: <date>`, with an import note. Gates 2a–2g are
skipped for those imports.

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
Boards: LinkedIn <cards seen / detail fetched / pre-filtered, window r<seconds>, 429s: n> · AllJobs <kept / hidden-employer> · Drushim <cards seen / kept> · skipped: <none | board (reason)>
ingest:  <the line ingest.py printed>
build:   <the lines build_html.py printed>
```

## Guardrails

- **Login / CAPTCHA**: pause and wait for the user. Do not retry
  automatically. If it isn't resolved, skip that board and leave its
  `state.json` entry unchanged.
- **Runtime cap**: 10 minutes total (a full run with ~100 LinkedIn details
  and two rate-limit pauses takes ~8). If exceeded, dump what you have,
  write `scrape_raw.json` with `finished: false` for the unfinished board,
  and stop.
- **HTTP 429 from LinkedIn**: pause 90 s, resume with `__liRun`; after a
  second 429 in the same run, mark the board `finished: false`.
- **Per query**: 30 LinkedIn cards (3 API pages), all Drushim pages up to 6.
- **`requests` in the Python sandbox is proxy-blocked** — all scraping goes
  through Claude in Chrome.
- **Never write `["N/A"]`; never edit `jobs.json` by hand** — `ingest.py`
  is the only writer in this shortcut.
- **If `scrape_raw.json` or `jobs.json` is write-locked**, print the error
  and stop; do not fall back to a sibling file.
