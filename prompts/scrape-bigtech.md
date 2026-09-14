# Chrome shortcut: /scrape-bigtech  (schema v2)

Save this as a Claude in Chrome shortcut. Schedule it **Sunday at 16:00,
weekly**. Junior openings at these companies are rare and usually ask for
3–5+ years, so one pass a week catches everything worth catching. This
shortcut scrapes the Israel careers pages for NVIDIA, Google, Apple, and
Amazon and appends new postings to the same `jobs.json` the main
`/scrape-jobs` shortcut writes to.

The data model (schema v2), helpers, gates, dedup rules, and write-then-rebuild
sequence are **identical to `scrape.md`** — read that file's Step 0, 0.5, 2,
3, 4, 5 and apply them here. This file only documents the four extra boards
and their URL / extraction patterns.

---

You are running the Israel DS / AI-engineer big-tech scraper. Follow the steps
below exactly. Use the accessibility tree or page-state JavaScript, never
screenshots.

## Step 0 — Load the tracker, config and state

Same as `scrape.md` Step 0: read `config.json`, `jobs.json` (schema v2) and
`state.json`; build `existing_by_link` (every record, any status) and
`existing_keys` (every `dedup_key`). Define the Step 0.5 helpers
(`yearsMin`, `dedupKey`, `extractionOk`, `isAgency`). Stay in the scraper
lane: never touch `status`, `applied_at`, `notes`, `last_email`, or any
other user/Gmail/fit field.

## Step 1 — Boards

Each board below is a single public careers page — no login, no CAPTCHA.
Open each in its own tab and run the extraction snippet.

Search terms per board: `data scientist`, `AI engineer`, `machine learning`.
Run the URL once per term; dedupe by `link` at the end.

### Board 4 — NVIDIA

Platform: Eightfold AI. Israel filter is a numeric country id passed as
`location_country`. `country=Israel` is ignored.

```
https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite?locations=ab40a7b5fd2510012d9ea47ad4110000
https://jobs.nvidia.com/careers?query=<q>&location_country=103644278890604&pid=&sort_by=relevance
```

The `jobs.nvidia.com` host is the Eightfold front-end and renders faster.
Wait ~4 seconds for results, then:

```javascript
function extractNvidia() {
  const cards = document.querySelectorAll('a[href*="/careers/job/"]');
  const out = [];
  const seen = new Set();
  for (const a of cards) {
    const m = a.href.match(/\/careers\/job\/(\d+)/);
    if (!m) continue;
    const id = m[1];
    if (seen.has(id)) continue;
    seen.add(id);
    // Card container sits a few levels up; walk until we find the li/div
    // with both a position title and a location row.
    let card = a;
    for (let i = 0; i < 6 && card; i++) {
      if (card.tagName === 'LI' || card.getAttribute('data-test-id')) break;
      card = card.parentElement;
    }
    const text = (card || a).innerText.split('\n').map(s => s.trim()).filter(Boolean);
    out.push({
      id,
      link: `https://jobs.nvidia.com/careers/job/${id}`,
      title: text[0] || a.innerText.trim(),
      location: text.find(l => /israel|yokneam|tel aviv|herzl|raan|haifa/i.test(l)) || null,
      lines: text,
    });
  }
  return out;
}
extractNvidia();
```

Build each record with `source = "NVIDIA"` and `company = "NVIDIA"`. Description
sections come from the job-detail page (`/careers/job/<id>`) under the
`Responsibilities` / `What we need to see` / `Ways to stand out` headers.
**Open the detail page** — without it the record is unverified
(`requirements: []`, `extraction_ok: false`) and the years gate can't run,
which for big tech means most postings would slip into the Inbox unfiltered.

### Board 5 — Google

Platform: custom. Israel filter is a readable string.

```
https://www.google.com/about/careers/applications/jobs/results/?location=Israel&q=<q>
```

Wait ~3 seconds after load. Google paginates via infinite scroll; scroll to
bottom twice before extracting.

```javascript
function extractGoogle() {
  const out = [];
  const seen = new Set();
  // Each card has an h3 with the title and an anchor to /jobs/results/<id>-<slug>/
  for (const h3 of document.querySelectorAll('h3')) {
    const card = h3.closest('li') || h3.parentElement.parentElement;
    if (!card) continue;
    const a = card.querySelector('a[href*="/jobs/results/"]');
    if (!a) continue;
    const m = a.href.match(/\/jobs\/results\/(\d+)-/);
    if (!m) continue;
    const id = m[1];
    if (seen.has(id)) continue;
    seen.add(id);
    const text = card.innerText.split('\n').map(s => s.trim()).filter(Boolean);
    out.push({
      id,
      link: a.href.split('?')[0],   // canonical = the /jobs/results/<id>-<slug>/ path
      title: h3.innerText.trim(),
      location: text.find(l => /israel|tel aviv|haifa/i.test(l)) || null,
      lines: text,
    });
  }
  return out;
}
extractGoogle();
```

Build each record with `source = "Google"` and `company = "Google"`.
Responsibilities and requirements sit on the job-detail page under
`Minimum qualifications`, `Preferred qualifications`, and `Responsibilities`.
As with NVIDIA, skip the detail fetch on the first pass if time is tight.

### Board 6 — Apple

Platform: custom. Israel filter is a location slug.

```
https://jobs.apple.com/en-us/search?location=israel-ISR&search=<q>
```

Wait ~3 seconds. Apple's cards live in a table-like structure.

```javascript
function extractApple() {
  const out = [];
  const seen = new Set();
  for (const a of document.querySelectorAll('a[href*="/details/"]')) {
    const m = a.href.match(/\/details\/(\d+)/);
    if (!m) continue;
    const id = m[1];
    if (seen.has(id)) continue;
    seen.add(id);
    const row = a.closest('tr') || a.closest('li') || a.parentElement.parentElement;
    const text = row.innerText.split('\n').map(s => s.trim()).filter(Boolean);
    out.push({
      id,
      link: `https://jobs.apple.com/en-us/details/${id}`,
      title: a.innerText.trim(),
      location: text.find(l => /israel|herzl|haifa|tel aviv/i.test(l)) || null,
      lines: text,
    });
  }
  return out;
}
extractApple();
```

Build each record with `source = "Apple"` and `company = "Apple"`. Detail page
sections: `Description`, `Minimum Qualifications`, `Preferred Qualifications`.

### Board 7 — Amazon

Platform: custom. Israel filter uses two redundant keys.

```
https://www.amazon.jobs/en/search?base_query=<q>&loc_query=Israel&country=ISR
```

Wait ~3 seconds.

```javascript
function extractAmazon() {
  const out = [];
  const seen = new Set();
  for (const a of document.querySelectorAll('a[href*="/en/jobs/"]')) {
    const m = a.href.match(/\/en\/jobs\/(\d+)/);
    if (!m) continue;
    const id = m[1];
    if (seen.has(id)) continue;
    seen.add(id);
    const tile = a.closest('.job-tile') || a.closest('li') || a.parentElement.parentElement;
    const text = tile.innerText.split('\n').map(s => s.trim()).filter(Boolean);
    out.push({
      id,
      link: `https://www.amazon.jobs/en/jobs/${id}`,
      title: text[0] || a.innerText.trim(),
      location: text.find(l => /israel|tel aviv|haifa/i.test(l)) || null,
      lines: text,
    });
  }
  return out;
}
extractAmazon();
```

Build each record with `source = "Amazon"` and `company = "Amazon"`. Detail
page sections: `DESCRIPTION`, `BASIC QUALIFICATIONS`, `PREFERRED QUALIFICATIONS`.

## Step 2 — Gates

Apply `scrape.md` Step 2 gates 2a–2j exactly. Notes for these boards:

- 2e (anonymous employer) never applies — there are no anonymous postings.
- 2d is **clinical titles only**. Google Health / Apple Health ML roles are
  kept; a "Clinical Research Coordinator" is dropped.
- 2g (years): big-tech postings bury the years in "Minimum qualifications" /
  "Basic qualifications" — make sure that section is in the text you pass
  to `yearsMin()`. Expect most postings to fail this gate; that is the
  point of the gate, not a bug.
- 2h: none of these four are agencies (`agency: false`).

## Step 3 — Build each job record

Same schema-v2 record as `scrape.md` Step 3 (`status: "new"`,
`status_source: "scraper"`, `extraction_ok`, `years_min`, `agency: false`,
`dedup_key`, empty arrays never `["N/A"]`), including the `description`
field — the prose lead-in before "Responsibilities" / "Minimum
qualifications" on the detail page. NVIDIA tags it with no header (it's just
the first paragraph); Google labels it implicitly under the role title; Apple
has a literal "Description" header; Amazon has "DESCRIPTION". Cap at ~600 chars.

The only differences vs the main scraper are the `source` / `company` values
and the canonical link templates:

| Source | `company` | Template |
|---|---|---|
| NVIDIA | `NVIDIA` | `https://jobs.nvidia.com/careers/job/<ID>` |
| Google | `Google` | `https://www.google.com/about/careers/applications/jobs/results/<ID>-<slug>/` |
| Apple | `Apple` | `https://jobs.apple.com/en-us/details/<ID>` |
| Amazon | `Amazon` | `https://www.amazon.jobs/en/jobs/<ID>` |

`id` is still `<lowercase-first-word-of-company>-<6-char-md5-of-link>` — so
NVIDIA entries start with `nvidia-`, Google with `google-`, and so on.

## Step 4 — Dedup against `jobs.json`

Same rules as `scrape.md` Step 4: `link` already known → enrich empty
scraper fields only (never a status); `dedup_key` already known → drop as
duplicate. The `/scrape-jobs` run may already hold the same posting via
LinkedIn — the `dedup_key` check is what catches that.

## Step 5 — Write `jobs.json`, `state.json` and rebuild

Same as `scrape.md` Step 5. In `state.json` set `sources.NVIDIA`,
`sources.Google`, `sources.Apple`, `sources.Amazon` → `last_scrape_at` for
each board you finished. Then run `python build_html.py`.

## Step 6 — Summary line

```
Big-tech: N new (NV:a GO:b AP:c AM:d) · E enriched · D duplicates · filtered: f_f family / f_s senior / f_t teaching / f_c clinical / f_y years · u unverified · build: <build_html.py summary>
```

## Guardrails

- **No login expected.** All four boards are public. If any of them starts
  asking for a login, pause and surface it — something changed.
- **Runtime cap**: 5 minutes total across all four boards.
- **Same empty result 3 runs in a row**: surface the URL and extraction
  snippet to the user so they can inspect — the DOM may have shifted.
- **Detail-page fetches are not optional here.** A listing card alone gives
  an unverified record, and unverified records skip the years gate. If time
  runs out, stop adding postings rather than adding unverified ones; the
  next run's Step 1b re-verify pass (from `scrape.md`) covers the rest.
