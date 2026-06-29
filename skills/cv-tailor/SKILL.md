---
name: cv-tailor
description: Use this skill when the user asks to tailor, customize, or adapt their CV/resume to a specific job posting, or when processing rows marked "V" in the job_automation tracker. Triggers include "tailor the CV", "tailor CVs for interested jobs", "adapt my resume to this job", "rebuild CV for <company>", or any request that pairs a base CV with a job requirements file. The workflow uses an HTML template plus a structured experience bank.
---

# CV Tailoring Rules (HTML template + experience bank)

## Inputs

| Input | Default path | Purpose |
|---|---|---|
| Template | `cv/base_cv.html` | Visual template — fonts, layout, colors, section order. Never replace the structure. |
| Experience bank | `cv/experience_bank/` | Content pool. Every `.md` inside is a candidate for inclusion. |
| Job requirements | `positions/<id>/requirements.md` | What the target role asks for. |
| Output | `cv/tailored/<position_id>.html` | Tailored HTML. Opens in Chrome, prints to PDF via the existing button. |

## Hard rules

1. **Only use content that exists in `experience_bank/`.** Never invent skills, projects, dates, or employers. If the job asks for X and no bank entry covers X, leave it out.
2. **Preserve the HTML template's structure and styling.** Keep the exact Tailwind classes, colors (`blue-900`, `gray-700`, etc.), section headers, two-column layout, and the `window.print()` button. Only swap text content inside sections.
3. **Output is a new file at `cv/tailored/<position_id>.html`.** Never overwrite `base_cv.html`.
4. **Fit on one printed A4 page.** The template is designed for one page with `zoom: 0.81`. If content overflows, drop `priority: 3` entries first, then `priority: 2`.

## Tailoring steps (in order)

### Step 1 — Parse the job requirements

Extract from `requirements.md`:
- `must_have`: hard requirements (years experience, specific tools, degree)
- `nice_to_have`: preferred qualifications
- `keywords`: the exact terminology the posting uses

### Step 2 — Index the experience bank (token-efficient)

Do NOT load every file. Instead:

```bash
grep -rn "^tags:" cv/experience_bank/
```

This returns one line per file with its tags. From this, rank each file by tag-overlap with the job's `keywords` + `must_have`. Fully load the top-scoring files plus all `priority: 1` files.

Rough budget: load ~8–12 files per tailor run, not all of them.

### Step 3 — Select content per section

| Section | Selection rule |
|---|---|
| Header subtitle | Retune to the target role family (e.g., "AI Engineer \| Data Science M.Sc. Student") while keeping factual accuracy. |
| Professional Summary | Rewrite the 2–3 line summary. Name the target role. Reference top 3 matched `must_have` items. Use the posting's keywords where they describe real experience. |
| Technical Skills | For each `skills/*.md`, output its "Skills cluster" line. Promote skills that match `keywords` to the front. Drop unmatched clusters if space-constrained. |
| Research Experience | Pick 2–4 entries from `research/`, ranked by tag-overlap. Default to **Medium** variation; switch to **Short** if space-constrained. |
| Experience | Pick from `work/`, newest first. Default to **Medium** variation. Always include `priority: 1`. |
| Education | Include both degree entries. |
| Military Service | Always include if space permits. |
| Volunteering | Include if space permits. Drop first when trimming. |
| Languages | Copy verbatim from the template. |
| Contact | Copy verbatim from the template. |

### Step 4 — Rewrite phrasing to match the posting

Where a bank entry's **Medium** variation describes the same work the posting names differently, rewrite to use the posting's terminology. Examples:
- Bank: "recommendation systems" + posting uses "recsys pipelines" → "recsys pipelines"
- Bank: "autoencoder-based reconstruction" + posting uses "unsupervised anomaly detection" → "unsupervised anomaly detection with autoencoders"

Do not rewrite where meaning would shift. Do not introduce a tool or framework not in the bank entry.

### Step 5 — Generate the tailored HTML

Start from `base_cv.html`. Load it as a string. Replace only the text content inside these anchors (identified by surrounding class/heading text, since the template has no IDs):

- Header subtitle: `<p class="text-lg text-blue-900 font-medium">...</p>`
- Each section body: the `<div>` that follows each `<h2>` heading

Keep all `<h2>` headings, SVG icons, wrappers, and Tailwind classes intact.

Recommended implementation: use Python with BeautifulSoup for safe HTML editing. Pseudocode:

```python
from bs4 import BeautifulSoup
soup = BeautifulSoup(open('cv/base_cv.html'), 'html.parser')

# Locate section by its <h2> text, then edit the sibling content div.
# Example: replace Professional Summary paragraph text.
for h2 in soup.find_all('h2'):
    if h2.get_text(strip=True) == 'PROFESSIONAL SUMMARY':
        p = h2.find_next('p')
        p.string = new_summary_text
    # ... repeat per section
```

For sections with multiple entries (Research Experience, Experience), rebuild the inner children matching the existing child structure (a `<div>` per entry with an `<h3>` title, optional date `<p>`, and a description `<p>`).

Save to `cv/tailored/<position_id>.html`.

### Step 6 — Log the changes

Append to `positions/<position_id>/notes.md`:

```
## CV tailored <ISO-date>
- Matched must_have: [list]
- Bank entries included: [list of filenames]
- Keyword rewrites applied: [before → after]
- Output: cv/tailored/<position_id>.html
```

### Step 7 — Self-audit before declaring done

Before returning:
1. Every concrete claim in the output maps to a bank entry. Grep the output for any claim, confirm it exists in `experience_bank/`.
2. The HTML is valid (BeautifulSoup round-trips cleanly; `<html>`, `<body>`, and the `print-container` div are all present).
3. The `window.print()` button is preserved.
4. No placeholder text (`TODO`, `lorem`, `{{...}}`) remains.

If any check fails, fix before finishing.

## What not to do

- Do not change fonts, colors, layout, or the print button.
- Do not add a cover-letter section.
- Do not translate content. Keep language matching the posting. If the bank only has English versions, keep English regardless.
- Do not duplicate entries across sections (a research project goes in Research, not also in Experience).

## Token-efficiency pattern (summary)

1. One `grep` to index all frontmatter tags (~1K tokens).
2. Score files, load top ~10 matches (~6K tokens).
3. Load `base_cv.html` once (~4K tokens).
4. Load `requirements.md` once (~2K tokens).
5. Produce tailored HTML (~6K output tokens).

Total per tailor run: ~20K tokens.
