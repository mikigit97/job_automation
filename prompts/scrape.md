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

1. `config.json` — only for the optional title pre-filter (Step 2):
   `role_families` (`ai`, `ds`), `seniority_titles`, `teaching_titles`.
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

Open each board URL below in its own tab.

### Board 1 — LinkedIn

Run **each** of these keyword queries as its own search (build the URL with
`encodeURIComponent(q)`), newest first, and process at most **25 cards per
query**:

| # | `keywords` |
|---|---|
| 1 | `"data scientist"` |
| 2 | `"machine learning engineer" OR "ML engineer"` |
| 3 | `"AI engineer"` |
| 4 | `"NLP engineer" OR "LLM engineer"` |
| 5 | `"algorithm developer" OR "algorithm engineer"` |
| 6 | `מדען נתונים OR למידת מכונה OR מהנדס אלגוריתמים` |

```
https://www.linkedin.com/jobs/search/?keywords=<encoded q>&location=Israel&f_TPR=r<WINDOW_SECONDS>
```

- `f_TPR=r<seconds>` is the time window. Compute `WINDOW_SECONDS` from
  `state.json` (Step 0): seconds since `sources.LinkedIn.last_scrape_at`,
  rounded up to the hour, **minimum 21600 (6h), maximum 604800 (7d)**. No
  entry yet → 604800. This is what makes a day with Chrome closed
  recoverable.
- Do **not** add `f_E` (experience-level). Israeli postings are tagged
  inconsistently; the gates in Step 2 do that job.
- The same job will appear under several queries — dedup by job id in
  memory before opening any detail view.
- Requires login; the session cookie persists across runs.
- Job cards: `listitem` elements in the search results list; each has
  `a[href*="/jobs/view/"]`.

LinkedIn is a single-page app. Visiting `/jobs/view/<ID>/` directly does
**not** render the `#job-details` description panel. The panel only loads on
the search results page when a job is selected via the `currentJobId` query
parameter. To get each job's description:

```
https://www.linkedin.com/jobs/search/?keywords=<encoded q>&location=Israel&f_TPR=r<WINDOW_SECONDS>&currentJobId=<ID>
```

Navigate to that URL, wait ~5 seconds, then run:

```javascript
function extractLinkedIn() {
  const el = document.querySelector('#job-details');
  if (!el) return null;
  const text = el.innerText;
  const sections = { desc: [], resp: [], req: [], nice: [] };
  // 'desc' captures the lead-in prose before any explicit Responsibilities/
  // Requirements header. 'about the role' / 'about the company' is treated
  // as description, not responsibilities.
  let cur = 'desc';
  for (const line of text.split('\n').map(l => l.trim()).filter(Boolean)) {
    const ll = line.toLowerCase();
    if (ll.includes('about the role') || ll.includes('about the company') || ll.includes('about the job') || ll.includes('company description') || ll.includes('job description')) { cur = 'desc'; continue; }
    if (ll.includes('responsibilities') || ll.includes('what you will do') || ll.includes('what you’ll do')) { cur = 'resp'; continue; }
    if (ll.includes('qualifications') || ll.includes('requirements') || ll.includes('you will need') || ll.includes('what you bring')) { cur = 'req'; continue; }
    if (ll.includes('additional information') || ll.includes('nice to have') || ll.includes('bonus') || ll.includes('preferred')) { cur = 'nice'; continue; }
    if (line.length < 10) continue;
    sections[cur].push(line);
  }
  return {
    description: sections.desc.join(' ').slice(0, 800) || null,
    resp: sections.resp,
    req:  sections.req,
    nice: sections.nice,
  };
}
extractLinkedIn();
```

To enumerate visible IDs without navigating each one first:

```javascript
const cards = document.querySelectorAll('a[href*="/jobs/view/"]');
[...new Set([...cards].map(a => a.href.match(/\/jobs\/view\/(\d+)/)?.[1]).filter(Boolean))];
```

The container div's CSS classes include random hash strings — only rely on
the `#job-details` id.

**Empty-payload guard — required before writing a LinkedIn record.** If
`extractLinkedIn()` returns `null`, OR if it returns an object whose
`description`, `resp`, and `req` are all empty, treat the extraction as
failed and run the standalone-view fallback (below) plus the
poster-requirements sweep before accepting the record. A record is written
with `requirements: []` and `extraction_ok: false` only after BOTH the
search-view extractor and the standalone-view fallback came back empty.

If a card has `disabled` on `a.job-card-container__link` or is a "Promoted"
card, `#job-details` often will not render. Before giving up (unverified),
try the **standalone-view fallback** described below.

**Standalone-view fallback (when `#job-details` is missing).** A direct
`https://www.linkedin.com/jobs/view/<ID>/` open does not populate
`#job-details`, but it does render the "About the job" section into the
page body within a few seconds of scroll. The body needs both a wait and a
scroll — otherwise it shows only skeleton placeholders. Use this whenever
`extractLinkedIn()` returns `null` or empty arrays:

```javascript
// Run AFTER: navigate /jobs/view/<ID>/, wait ~6s, scroll body 5+ ticks, wait ~3s.
function extractLinkedInStandalone() {
  var full = document.body.innerText;
  var idx = full.toLowerCase().indexOf('about the job');
  if (idx < 0) return null;
  var endMarkers = ['Set alert', 'See more jobs', 'People you may know',
                    'Job search smarter', '\nAbout\n', 'Accessibility',
                    'Talent Solutions', 'Show more', 'Show less'];
  var endIdx = full.length;
  for (var m of endMarkers) {
    var i = full.indexOf(m, idx + 10);
    if (i > 0 && i < endIdx) endIdx = i;
  }
  var body = full.slice(idx, endIdx).trim();
  var sec = { desc: [], resp: [], req: [], nice: [] };
  var cur = 'desc';
  for (var line of body.split('\n').map(l => l.trim()).filter(Boolean)) {
    var ll = line.toLowerCase();
    if (/^about the (?:job|role|company)/.test(ll) || ll === 'company description' || ll === 'job description') { cur = 'desc'; continue; }
    if (/(responsibilities|what you will do|what you'll do|what you’ll do|the role)/.test(ll) && line.length < 60) { cur = 'resp'; continue; }
    if (/(qualifications|requirements|you will need|what you bring|must have)/.test(ll) && line.length < 60) { cur = 'req'; continue; }
    if (/(nice to have|bonus|preferred|additional information|advantage)/.test(ll) && line.length < 60) { cur = 'nice'; continue; }
    if (line.length < 5) continue;
    sec[cur].push(line);
  }
  return {
    description: sec.desc.join(' ').slice(0, 800) || null,
    resp: sec.resp.slice(0, 8),
    req:  sec.req.slice(0, 8),
    nice: sec.nice.slice(0, 4),
  };
}
```

Merge the standalone result and the poster-requirements sweep into the
record, then continue. Only leave the record unverified (`requirements: []`,
`extraction_ok: false`) if BOTH paths return empty.

**"Requirements added by the job poster" — capture separately.** LinkedIn
renders a structured poster-added requirements block (commute, onsite,
years-of-experience by skill — e.g., "5+ years of work experience with
Python"). On collapsed posts and on some templates this block lives outside
`#job-details`, so `extractLinkedIn()` misses it and the card would land in
`jobs.json` unverified, bypassing the years gate.
Sweep the whole page for it and merge into the requirements array before
running the Step 2 filters:

```javascript
function extractLinkedInPosterRequirements() {
  const out = [];
  for (const el of document.querySelectorAll('h2,h3,h4,span,strong,div')) {
    const t = (el.innerText || '').trim();
    if (!/^requirements added by the job poster$/i.test(t)) continue;
    const block = el.closest('section, div');
    if (!block) continue;
    for (const line of (block.innerText || '').split('\n').map(l => l.trim()).filter(Boolean)) {
      if (/^requirements added by the job poster$/i.test(line)) continue;
      if (line.length < 4) continue;
      out.push(line);
    }
  }
  // Dedup while preserving order.
  return [...new Set(out)];
}
// After calling extractLinkedIn():
//   const posterReqs = extractLinkedInPosterRequirements();
//   sections.req = [...(sections.req || []), ...posterReqs];
```

NBN Connect's Computer Vision Engineer post (2026-05-23) is the canonical
failure case — `#job-details` returned nothing, but the poster block listed
`5+ years of work experience with Python`. With the sweep above the
Step 2g years gate catches it.

### Board 2 — AllJobs

```
https://www.alljobs.co.il/SearchResultsGuest.aspx?page=1&position=1733&type=&city=&region=
```

- Position code `1733` = Data Scientist. Codes `49` and `52` still work for
  older DS / AI/ML buckets.
- Guest access works, but logging in is better — anonymous ("חברה דיסקרטית")
  listings resolve to their real company names once you're signed in. The
  session cookie persists across runs.
- **Homepage cookie required** even when logged in: visit
  `https://www.alljobs.co.il/` first. Without that, the search URL returns
  `/ErrorUnderConstruction.html`.

**Link template — do not use the DOM href.** AllJobs result cards link to
`/Search/ViewJob.aspx?JobID=<id>`, which errors out ("page not found") when
opened directly. The working canonical URL is
`/Search/UploadSingle.aspx?JobID=<id>`. Extract the `JobID` from the card
and rebuild the link yourself; never store the raw `ViewJob.aspx` URL. This
also collapses near-duplicates when the same job appears with different
query params across result pages.

The search results page loads the full card text for every job, so you do not
need to open individual job pages.

**Card discovery — walk up to the Location row, not a fixed depth.** The
naive pattern `a.parentElement.parentElement.parentElement` fails because
each card exposes several anchors with `JobID=` (the title link, the
quick-apply button, a share button), and they sit at different depths.
A depth-3 walk from the wrong anchor lands on a sibling card, producing a
systematic position↔JobID mismatch — on the previous real run this hit 16
of 18 postings. Use the "Location:" / "מיקום המשרה:" row as a content
anchor instead, then walk *up* until an ancestor's text contains it. That
ancestor is the true card.

```javascript
const LOC_RE = /(?:^|\n)\s*(?:Location:|מיקום המשרה:)/;

function findCard(anchor) {
  let node = anchor.parentElement;
  for (let i = 0; i < 10 && node && node !== document.body; i++) {
    if (LOC_RE.test(node.innerText || '')) return node;
    node = node.parentElement;
  }
  return null;
}

function positionAndCompany(lines) {
  // The Location row is a stable anchor; position sits two lines above it,
  // company one line above. Fall back to the first two lines if missing.
  const i = lines.findIndex(l => /^(?:Location:|מיקום המשרה:)/.test(l));
  if (i >= 2) return { position: lines[i - 2], company: lines[i - 1] };
  return { position: lines[0] || 'N/A', company: lines[1] || 'N/A' };
}

window.__allJobsData = {};
for (const a of document.querySelectorAll('a[href*="JobID="]')) {
  const id = new URL(a.href).searchParams.get('JobID');
  if (!id || window.__allJobsData[id]) continue;   // first anchor per id wins
  const card = findCard(a);
  if (!card) continue;
  const lines = card.innerText.split('\n').map(l => l.trim()).filter(l => l.length > 2);
  const { position, company } = positionAndCompany(lines);
  window.__allJobsData[id] = {
    link: `https://www.alljobs.co.il/Search/UploadSingle.aspx?JobID=${id}`,
    position,
    company,
    lines,
  };
}
Object.keys(window.__allJobsData).length + ' jobs stored';
```

**Sanity check before writing.** Print `[id, position, company]` for every
entry. If any `position` starts with `Location:`, is a bare date, equals the
string `חברה חסויה`, or is shorter than 4 chars, the card walk fell through
— log the failing JobID and skip it instead of writing garbage to
`jobs.json`.

Parse sections per card (compact format to avoid output truncation). Call
this with `window.__allJobsData[id].lines` — the first thing it does is
skip the metadata block above the Location row (position, company, posting
date) so those never leak into `responsibilities`:

```javascript
function parseSections(texts) {
  // Skip metadata: everything before and including the Location row.
  const startIdx = texts.findIndex(l => /^(?:Location:|מיקום המשרה:)/.test(l));
  const body = startIdx >= 0 ? texts.slice(startIdx + 1) : texts;

  const desc = [], resp = [], req = [], nice = [];
  // 'cur' starts at 'd' (description) — the lead-in prose before any
  // explicit "Responsibilities" / "Requirements" header gets captured into
  // description rather than mis-bucketed.
  let cur = 'd';
  const RA = ['תחומי אחריות', 'responsibilities', 'אנחנו מגייסים', 'תפקיד כולל', 'design,', 'develop'];
  const QA = ['דרישות', 'requirements', 'ניסיון מקצועי', 'חובה:', 'must have'];
  const NA = ['יתרון', 'nice to have', 'bonus', 'preferred'];
  const SKIP = ['מיקום', 'location:', 'סוג משרה', 'job type', 'היום', 'לפני',
                'המשרה מיועדת', 'לעוד משרות', 'חברת השמה'];
  for (const line of body) {
    const ll = line.toLowerCase();
    if (RA.some(k => ll.includes(k))) { cur = 'r'; continue; }
    if (QA.some(k => ll.includes(k))) { cur = 'q'; continue; }
    if (NA.some(k => ll.includes(k))) { cur = 'n'; continue; }
    if (SKIP.some(k => ll.includes(k)) || line.length < 8) continue;
    if      (cur === 'r') resp.push(line);
    else if (cur === 'q') req.push(line);
    else if (cur === 'n') nice.push(line);
    else                  desc.push(line);
  }
  return {
    description: desc.join(' ').slice(0, 600) || null,
    resp: resp.slice(0, 4),
    req:  req.slice(0, 4),
    nice: nice.slice(0, 2),
  };
}
```

### Board 3 — Drushim

```
https://www.drushim.co.il/jobs/subcat/488-511-512-702-703/?experience=1-2&ssaen=3
```

This is the saved filter for algorithm-developer / DS / ML roles at the
1–2 years experience level. Breakdown:
- `subcat/488-511-512-702-703/` — the five sub-categories that cover
  algorithm developer, data scientist, ML, and adjacent roles.
- `experience=1-2` — caps to junior listings.
- `ssaen=3` — the match-mode that pairs with this filter URL. (Note: it's
  `ssaen=3` here, not `ssaen=1` from the keyword-search variant — don't
  swap them.)

**Sanity-check the filter loaded.** Before extracting, confirm the active
filter chips rendered. The chip container is at this XPath:

```
/html/body/div[1]/div[2]/div/div/div[3]/div[1]/div[3]/div/div/div/div/div/div[2]/div/div[2]/div/div/div[2]/div[2]
```

Run a quick check in the page:

```javascript
const node = document.evaluate(
  '/html/body/div[1]/div[2]/div/div/div[3]/div[1]/div[3]/div/div/div/div/div/div[2]/div/div[2]/div/div/div[2]/div[2]',
  document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null
).singleNodeValue;
node ? node.innerText : 'FILTER CHIPS NOT FOUND';
```

If that returns `'FILTER CHIPS NOT FOUND'` or empty text, the filter URL
didn't apply (Drushim sometimes redirects on cold sessions) — reload the
URL once, then bail on this board if it fails again.

Drushim ships a Nuxt fetch cache that already has every visible job as
structured JSON, so per-card navigation is unnecessary. (On individual
job-page URLs `https://www.drushim.co.il/job/<id>/<hash>/` the same
payload lives at `window.__NUXT__.data[0].jobData` — use that path if you
ever need to re-scrape a single posting.)

```javascript
const keys = Object.keys(window.__NUXT__.fetch);
let jobs = [];
for (const k of keys) {
  const d = window.__NUXT__.fetch[k];
  if (d && d.searchRes && Array.isArray(d.searchRes)) { jobs = d.searchRes; break; }
}
// Each entry:
//   jobs[i].JobInfo.JobCode              → numeric id
//   jobs[i].JobInfo.Hash                 → url hash
//   jobs[i].JobInfo.Date                 → ISO date
//   jobs[i].Company.CompanyDisplayName   → company
//   jobs[i].JobContent.Name              → position title
//   jobs[i].JobContent.AboutCompany      → HTML description (when present)
//   jobs[i].JobContent.JobDescription    → HTML description (alt key on some payloads)
//   jobs[i].JobContent.Description       → HTML responsibilities
//   jobs[i].JobContent.Requirements      → HTML requirements
//   jobs[i].JobContent.Zones[0].CityName → location
// URL: 'https://www.drushim.co.il/job/' + JobCode + '/' + Hash.toLowerCase() + '/'
```

Compact extraction (Hebrew text is dense; trim early to stay under tool
output caps):

```javascript
function stripHtml(s) {
  return (s || '').replace(/<[^>]+>/g, ' ').replace(/&nbsp;/g, ' ').replace(/\s+/g, ' ').trim();
}

// Build a JobCode → "already applied" map from the rendered DOM. Drushim
// shows "שלחת קו"ח ב - DD-MM-YYYY" on cards whose CV the logged-in user
// already submitted. That state lives in the DOM, not in the Nuxt JSON
// cache (which is shared/anonymous and reports every job as unapplied).
//
// Walk OUTWARD from each badge span — never inward from the job link.
// The naive direction (walk up from each job link, check ancestor.innerText
// for the marker) over-matches: once the ancestor expands to the whole
// results list, every card under it inherits all the badges and gets
// flagged. Validated 2026-04-26: that direction marked 25/25 as applied
// when only 17 actually were. The inverse direction lands on the correct
// 17.
const APPLIED_RE = /שלחת\s*קו["׳']ח\s*ב\s*-?\s*(\d{2})-(\d{2})-(\d{4})/;
window.__DJ_APPLIED = new Map();   // JobCode -> "YYYY-MM-DD" the CV was sent
for (const el of document.querySelectorAll('*')) {
  const ownText = [...el.childNodes]
    .filter(n => n.nodeType === 3)
    .map(n => n.textContent)
    .join(' ');
  const dm = ownText.match(APPLIED_RE);
  if (!dm) continue;
  const appliedDate = `${dm[3]}-${dm[2]}-${dm[1]}`;
  // From the badge text node, walk up until an ancestor contains a
  // /job/<id>/ link — that link belongs to the card that owns the badge.
  let node = el;
  for (let i = 0; i < 12 && node; i++) {
    const a = node.querySelector?.('a[href*="/job/"]');
    if (a) {
      const m = a.href.match(/\/job\/(\d+)\//);
      if (m) { window.__DJ_APPLIED.set(m[1], appliedDate); break; }
    }
    node = node.parentElement;
  }
}

window.__DJ = jobs.map(j => ({
  id:       j.JobInfo.JobCode,
  hash:     j.JobInfo.Hash,
  title:    j.JobContent.Name || j.JobContent.FullName || '',
  company:  j.Company.CompanyDisplayName || j.Company.NameInHebrew || '',
  location: j.JobContent.Zones?.[0]?.CityName || '',
  date:     (j.JobInfo.Date || '').slice(0, 10),
  desc:     stripHtml(j.JobContent.AboutCompany || j.JobContent.JobDescription || '').slice(0, 600) || null,
  resp:     stripHtml(j.JobContent.Description || '').slice(0, 500),
  req:      stripHtml(j.JobContent.Requirements || '').slice(0, 600),
  applied:  window.__DJ_APPLIED.get(String(j.JobInfo.JobCode)) || null,   // date string or null
}));
// Split resp/req into lines on sentence/bullet boundaries (". ", " - ", "•", "·")
// so they become arrays; keep at most 6 requirement lines and 4 responsibilities.
// If output gets truncated, stash window.__DJS = JSON.stringify(window.__DJ)
// and read it in slices: window.__DJS.slice(0, 3600), .slice(3600, 7200), ...
```


## Step 1b — Re-verify unverified postings (before scraping new ones)

For each record in `to_verify` (Step 0), open its `link` and run the same
extractor you would use for its `source` (LinkedIn: search-view with
`currentJobId`, then the standalone fallback and the poster-requirements
sweep; AllJobs: the card parser on the results page or the
`UploadSingle.aspx` page; Drushim: `window.__NUXT__.data[0].jobData`).
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
| 2e | Anonymous employer | company | AllJobs + `anonymous_companies` (when `drop_anonymous_alljobs`) | *drop* (`anonymous`) |
| 2f | Verified? | text | ≥2 requirement lines or ≥200-char description → `extraction_ok` | *flag* only |
| 2g | Years | text | only if verified: lower bound of the stated range > `years_max` | *drop* (`years`) |
| 2h | Agency | company | `agencies` list / `agency_patterns` | *flag* |
| 2i | Known link | link | already in `jobs.json` (any status) | enrich empty fields; Drushim `applied_date` on a `new` record → `applied` |
| 2j | Duplicate | key | normalized company\|position already known | *drop* (`duplicate`) |

Records land as `status: "new"`, `status_source: "scraper"` — or, for a
Drushim card with `applied_date`, as `status: "applied"`, `applied_via:
"manual"`, `applied_at: <date>`, with an import note. Gates 2a–2g are
skipped for those imports.

**Use 2a–2c yourself as a pre-filter** to save time: don't open the detail
view of a LinkedIn card whose *title* is clearly outside the AI/DS families,
or says senior/lead/manager, or is a teaching role. `ingest.py` would drop it
anyway. Never pre-filter on years or on anything you'd need the detail page
for.

## Step 3 — After the two commands

`ingest.py` prints one line (new / enriched / imported / duplicates /
filtered by reason / agency / unverified). `build_html.py` prints the
migration, maintenance and fit-tier summary. Put both in your report. Do not
write any other files; do not edit `jobs.json` directly.

## Step 4 — Summary

```
Boards: LinkedIn <n cards seen, window r<seconds>> · AllJobs <n> · Drushim <n> · skipped: <none | board (reason)>
ingest:  <the line ingest.py printed>
build:   <the lines build_html.py printed>
```

## Guardrails

- **Login / CAPTCHA**: pause and wait for the user. Do not retry
  automatically. If it isn't resolved, skip that board and leave its
  `state.json` entry unchanged.
- **Runtime cap**: 6 minutes total. If exceeded, write whatever you already
  collected (Step 5) and stop.
- **Per query**: at most 25 LinkedIn cards; **same listing seen 10 times in a
  row**: move on.
- **`requests` in the Python sandbox is proxy-blocked** — all scraping goes
  through Claude in Chrome.
- **Never write `["N/A"]`; never edit `jobs.json` by hand** — `ingest.py`
  is the only writer in this shortcut.
- **If `scrape_raw.json` or `jobs.json` is write-locked**, print the error
  and stop; do not fall back to a sibling file.
