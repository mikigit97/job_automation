# Chrome shortcut: /scrape-jobs

Save this as a Claude in Chrome shortcut. Schedule it Sunday–Thursday at 08:00
and 16:00. The shortcut scrapes three Israeli job boards and appends new
postings directly to `jobs.json` at the Cowork project root. There is no
`positions/` folder, no xlsx, no intermediate markdown.

The four big-company careers pages (NVIDIA, Google, Apple, Amazon) live in
a separate shortcut, `/scrape-bigtech`, scheduled once a day at 16:00. See
`scrape-bigtech.md`.

---

You are running the Israel DS / AI-engineer job scraper. Follow the steps
below exactly. Use the accessibility tree or page-state JavaScript, never
screenshots.

## Step 0 — Load the existing tracker

Read `jobs.json` from the Cowork project root. It is a JSON array of objects
with at least these keys:

```json
{
  "id": "<company-first-word>-<6-char-hash-of-link>",
  "position": "...",
  "company": "...",
  "source": "LinkedIn|AllJobs|Drushim",
  "link": "https://...",
  "scraped_at": "2026-04-22T15:58:39Z",
  "location": null,
  "date": null,
  "description": null,
  "responsibilities": [],
  "requirements": [],
  "nice_to_have": [],
  "last_email": null,
  "status_auto": null,
  "status_manual": null,
  "interested": null,
  "notes": "",
  "recruiter_phone": ""
}
```

`description` is the free-form prose section that sits at the top of most
postings — "About the role", "About the company", or just an unlabeled lead
paragraph before "Responsibilities". It's separate from the bulleted
responsibilities/requirements/nice-to-have arrays. When the scraper can't
find a distinct description block, leave it as `null`.

Keep in memory:
- `existing_links` — set of every `link` currently in the file.
- `existing_by_link` — map from link to the full object. When you see the
  same link again, you will enrich the existing entry rather than duplicate it.

### Field ownership — the scraper's lane

`jobs.json` is the single store for every writer. Stay in your lane:

| Field | Owned by | Scraper may touch? |
|---|---|---|
| `id`, `position`, `company`, `source`, `link`, `scraped_at`, `location`, `date`, `description`, `responsibilities`, `requirements`, `nice_to_have` | Scraper | Yes (only fills empty/null) |
| `last_email`, `status_auto` | Gmail sync task | No |
| `status_manual`, `interested`, `notes`, `recruiter_phone` | User (via the HTML tracker) | No |

The user can also override any scraper-owned field from the HTML's Edit
dialog. A non-empty value in any of those fields means the user has touched
it, so the scraper must not overwrite it on dedup-enrich.

When you re-see an existing posting, enrich only the scraper-owned fields.
Leave all other fields exactly as you found them.

## Step 0.5 — Relevance gate (skip-on-write)

A scraped posting is added to `jobs.json` ONLY if it passes all three gates
below. Discard everything else without writing — the user does not want
irrelevant titles in the tracker.

### Title gate

The `position` string must match one of these (case-insensitive). English:
`data scien*`, `machine learning`, ` ML ` / ` ML/`, ` AI `, `deep learning`,
`applied scien*`, `research scien*`, `research engineer`, `NLP`,
`computer vision`, `LLM`, `gen ai`, `MLOps`, `algorithm engineer`,
`algorithm developer`. Hebrew: `מדען נתונים`, `למידת מכונה`,
`בינה מלאכותית`, `אלגוריתמ`.

### Seniority gate

Discard if the title contains any of: `senior`, `sr.`, `lead`, `principal`,
`staff`, `manager`, `director`, `head of`, `architect`, `vp` (English) or
`בכיר`, `מנהל`, `ראש צוות` (Hebrew). These imply >2 years of experience.

### Experience gate

Scan `requirements`, `responsibilities`, and `description` for digit-followed-by-
`year(s)`, `yr(s)`, `שנה`/`שנים`/`שנות`. Also count the bare word `שנתיים`
(= 2 years). If the **lowest** number found is >2, discard. If no
years-of-experience signal is present, keep (treat as junior-friendly).

Build `build_html.py` runs the same gate as a safety net — anything that
slips through gets hard-deleted on the next rebuild — but you should drop
irrelevant rows here so the user never sees them in the tracker.

## Step 1 — Boards

Open each board URL below in its own tab.

### Board 1 — LinkedIn

```
https://www.linkedin.com/jobs/search/?keywords=%22data%20scientist%22%20OR%20%22AI%20engineer%22&location=Israel&f_TPR=r86400
```

- `f_TPR=r86400` filters to the last 24 hours.
- Requires login; the session cookie persists across runs.
- Job cards: `listitem` elements in the search results list; each has
  `a[href*="/jobs/view/"]`.

LinkedIn is a single-page app. Visiting `/jobs/view/<ID>/` directly does
**not** render the `#job-details` description panel. The panel only loads on
the search results page when a job is selected via the `currentJobId` query
parameter. To get each job's description:

```
https://www.linkedin.com/jobs/search/?keywords=...&location=Israel&f_TPR=r86400&currentJobId=<ID>
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
poster-requirements sweep before accepting the record. A record with
`requirements: ["N/A"]` should only be written after BOTH the search-view
extractor and the standalone-view fallback came back empty.

If a card has `disabled` on `a.job-card-container__link` or is a "Promoted"
card, `#job-details` often will not render. Before giving up with `N/A`,
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
record, then continue. Only write `requirements: ["N/A"]` if BOTH paths
return empty.

**"Requirements added by the job poster" — capture separately.** LinkedIn
renders a structured poster-added requirements block (commute, onsite,
years-of-experience by skill — e.g., "5+ years of work experience with
Python"). On collapsed posts and on some templates this block lives outside
`#job-details`, so `extractLinkedIn()` misses it and the card lands in
`jobs.json` with `requirements: ["N/A"]`, bypassing the experience gate.
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
Step 2d gate catches it.

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
const APPLIED_RE = /שלחת\s*קו["׳']ח\s*ב/;
window.__DJ_APPLIED = new Set();
for (const el of document.querySelectorAll('*')) {
  const ownText = [...el.childNodes]
    .filter(n => n.nodeType === 3)
    .map(n => n.textContent)
    .join(' ');
  if (!APPLIED_RE.test(ownText)) continue;
  // From the badge text node, walk up until an ancestor contains a
  // /job/<id>/ link — that link belongs to the card that owns the badge.
  let node = el;
  for (let i = 0; i < 12 && node; i++) {
    const a = node.querySelector?.('a[href*="/job/"]');
    if (a) {
      const m = a.href.match(/\/job\/(\d+)\//);
      if (m) { window.__DJ_APPLIED.add(m[1]); break; }
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
  resp:     stripHtml(j.JobContent.Description || '').slice(0, 200),
  req:      stripHtml(j.JobContent.Requirements || '').slice(0, 200),
  applied:  window.__DJ_APPLIED.has(String(j.JobInfo.JobCode)),
}));
// If output gets truncated, stash window.__DJS = JSON.stringify(window.__DJ)
// and read it in slices: window.__DJS.slice(0, 3600), .slice(3600, 7200), ...
```

## Step 2 — Filter out postings you won't apply to

Apply these three rejection rules to every extracted posting *before* building
the record. If any rule matches, drop the posting entirely — do not write it
to `jobs.json`, do not count it as "enriched", do not surface it in the
summary. The goal is a tracker that only contains postings worth reviewing.

### 2a. Seniority filter

Reject if the position title matches any of these (case-insensitive, word
boundaries):

- English: `senior`, `sr\.?`, `lead`, `principal`, `staff`, `head of`,
  `director`, `vp`, `chief`
- Hebrew: `בכיר`, `בכירה`, `ראש צוות`, `מוביל`, `מובילה`, `מנהל.?ת?` when
  paired with a seniority signal (e.g., `מנהל.ת קבוצה`, `מנהל.ת מחלקה`)

Do *not* reject entry/mid titles like "Data Scientist", "ML Engineer",
"Junior Data Scientist", "Associate AI Engineer".

### 2b. AllJobs VIP-only filter

Reject if `source == "AllJobs"` and the company name equals `חברה חסויה`
(exactly, after trimming whitespace). These are postings where AllJobs hides
the company name unless you're a VIP subscriber. Without VIP access the
posting is useless — you can't research the company before applying — so
they don't belong in the tracker. Partial matches like `NLP — חברה חסויה`
also count.

### 2c. Medical/healthcare filter

Reject if any of these signals appear in the company name, position title,
or the concatenated responsibilities + requirements text:

- English: `medical`, `medicine`, `clinical`, `clinic`, `hospital`,
  `pharma`, `pharmaceutical`, `biotech`, `biomed`, `healthcare`,
  `health-tech`, `health tech`, `patient`, `diagnostic`, `genomic`,
  `oncology`, `radiology`
- Hebrew: `רפואי`, `רפואה`, `תרופות`, `פארמה`, `בריאות`, `בית חולים`,
  `מרפאה`, `קופת חולים`, `ביו-רפואי`, `ביוטכנולוגיה`

A DS role at a medical device or digital health company is out of scope.
Generic insurance ("ביטוח") by itself is *not* a trigger.

### 2d. Experience-threshold filter

Reject if any 4+-years-of-experience signal appears in the posting's
requirements, responsibilities, OR description. Scanning all three fields
(not just requirements) is the safety net for cards where one extractor
section came back empty — e.g., a LinkedIn post whose `#job-details` panel
didn't render, leaving `requirements: ["N/A"]` while the years-of-experience
line sits in the description block or in the poster-added requirements
block.

```javascript
function demandsTooMuchExperience(job) {
  const text = [
    ...(job.requirements || []),
    ...(job.responsibilities || []),
    job.description || '',
  ].join(' ').toLowerCase();
  // English: "4 years", "4+ years", "at least 4 years", "minimum 5 yrs", "4-7 years"
  const en = /\b(4|5|6|7|8|9|1\d)\s*\+?\s*(?:-\s*\d+\s*)?(?:years?|yrs?)\b/;
  // Hebrew: "4 שנות ניסיון", "לפחות 5 שנים", "4+ שנים"
  const he = /(?:לפחות\s*)?(\d+)\s*\+?\s*(?:שנות|שנים)\b/;
  if (en.test(text)) return true;
  const m = text.match(he);
  if (m && parseInt(m[1], 10) >= 4) return true;
  return false;
}
```

Nice-to-haves don't count — only hard requirements. If the posting only says
"3+ years" or "2-3 years", keep it.

### 2f. Drushim "CV already sent" filter

Reject if `source == "Drushim"` and the card's `applied` flag is true. This
flag is set by the DOM-side check in Step 1 — Drushim renders
`שלחת קו"ח ב - DD-MM-YYYY` on cards whose CV the logged-in user has
already submitted. Re-applying clutters the tracker and risks duplicate
applications, so drop them entirely.

### 2e. What to log

Track counters per reason (`seniority`, `vip`, `medical`, `experience`,
`already_applied`) so the summary at the end reports them. Do not write
dropped postings anywhere.

## Step 3 — Build each job record

For every *surviving* job (one that passed all three filters), build an
object with exactly these fields:

| Field | Value |
|---|---|
| `id` | `<lowercase-first-word-of-company>-<6-char-md5-of-link>` |
| `position` | Position title |
| `company` | Company display name |
| `source` | `LinkedIn` / `AllJobs` / `Drushim` |
| `link` | Canonical URL — see template below per source |
| `scraped_at` | ISO-8601 UTC timestamp of this run |
| `location` | City (nullable; leave `null` if the board didn't show one) |
| `date` | Posting date as `YYYY-MM-DD` (nullable) |
| `description` | Free-form prose lead-in (string, ≤600 chars; `null` if no distinct description block) |
| `responsibilities` | Array of strings (4 max; `["N/A"]` if extraction failed) |
| `requirements` | Array of strings (4 max; `["N/A"]` if extraction failed) |
| `nice_to_have` | Array of strings (2 max; `[]` if none) |
| `last_email` | `null` |
| `status_auto` | `null` |
| `status_manual` | `null` |
| `interested` | `null` |
| `notes` | `""` |
| `recruiter_phone` | `""` |

Canonical `link` templates per source — always build the URL yourself from
the extracted id, never trust the DOM anchor's `href`:

| Source | Template |
|---|---|
| LinkedIn | `https://www.linkedin.com/jobs/view/<ID>/` |
| AllJobs | `https://www.alljobs.co.il/Search/UploadSingle.aspx?JobID=<ID>` |
| Drushim | `https://www.drushim.co.il/job/<JobCode>/<hash-lowercase>/` |

The AllJobs rule matters: the result page's anchors point at
`ViewJob.aspx`, which errors out on direct load. `UploadSingle.aspx` is the
one that actually renders the posting.

Notes on `id`:
- Hebrew first words are preserved as-is (`הראל-836bc4`, `דיאלוג-0184c0`).
- On rare collisions across boards, append `-2`, `-3`, etc.

## Step 4 — Dedup against `jobs.json`

For each built job:

- **If `job.link` is in `existing_links`**: do not append. If the existing
  entry has `deleted: true` (the user soft-deleted it from the HTML
  tracker), leave it untouched — do not enrich, do not flip the flag back.
  Otherwise, enrich the existing entry only for fields that are currently
  null or empty — `location`, `date`, `description`, `responsibilities`,
  `requirements`, `nice_to_have`. Never touch `last_email`, `status_auto`,
  `status_manual`, `interested`, `notes`, `recruiter_phone`, or the
  original `scraped_at`. Treat `responsibilities: ["N/A"]` as empty for
  the purpose of enrichment. A non-empty existing value is the user's
  edit (or a previous scrape) and must be left alone.
- **Otherwise**: append the new object to the array.

## Step 5 — Write `jobs.json` and rebuild

All-or-nothing per run — hold the updated array in memory, then overwrite the
file once at the end:

1. Write `jobs.json` pretty-printed (2-space indent, UTF-8, `ensure_ascii=false`).
2. Run `python build_html.py` to regenerate `Job_applications.html` with the
   updated data embedded inline. As of 2026-05-23, the same script also
   refreshes the embedded `const JOBS = [...]` array and `Snapshot:`
   timestamp in `Job_applications_mobile.html` (no-op if that file doesn't
   exist). You do not need to invoke a separate mobile-rebuild step.

Do not write any other files.

## Step 6 — Summary line

Print one line at the end:

```
Scraped N new positions across LinkedIn / AllJobs / Drushim (E enriched, D duplicates, F filtered: f_s senior / f_v VIP / f_m medical / f_e 4+yrs / f_a already-applied). HTML rebuilt.
```

## Guardrails

- **Login / CAPTCHA**: pause and wait for the user. Do not retry automatically.
- **Runtime cap**: 5 minutes total. If exceeded, write whatever you already
  collected and stop.
- **Same listing seen 10 times in a row**: move to the next board.
- **`requests` in the Python sandbox is proxy-blocked** — do not try to fetch
  boards from Python. All scraping goes through Claude in Chrome.
- **File writes are unlocked files only.** If `jobs.json` happens to be
  write-locked, print the error, do not retry, do not fall back to a dated
  sibling file.
