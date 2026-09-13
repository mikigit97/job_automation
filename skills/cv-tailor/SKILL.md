---
name: cv-tailor
description: Use this skill when the user asks to tailor, customize, or fit their CV/resume to a specific job posting, or to build/update one of the CV variants. Triggers include "tailor the CV", "fit a CV for <company>", "adapt my resume to this job", "rebuild the AI engineer variant", or any request that pairs a CV with a job posting or a role archetype. The workflow keeps a small set of durable CV variants and fits the closest one to each posting.
---

# CV Tailoring Rules (variants + per-job fit)

There are two distinct jobs this skill can do. Work out which one is being asked
for before starting:

- **Fit a CV to a posting** (the common case, run per job). Cheap: pick the
  closest existing variant and adapt it. Does not touch `experience_bank/` or
  rebuild sections from scratch.
- **Build or update a variant** (rare, run only per "Maintaining the variants"
  below). Expensive: the full bank-scan-and-select process. Only three variants
  exist; do not create a fourth for a single job.

## Inputs

| Input | Path | Purpose |
|---|---|---|
| Variants | `cv/variants/{ai-llm-engineer,data-scientist-ml,software-engineer-ml}.html` | Three durable base CVs, one per role archetype. Maintained separately, not rebuilt per job. |
| Experience bank | `cv/experience_bank/` | Content pool. Only read when building or updating a variant. |
| Job requirements | the job's record in `jobs.json` | What the target role asks for: the `position`, `requirements`, `responsibilities`, `nice_to_have` and `description` fields of the entry whose `id` matches. |
| Output (HTML) | `cv/tailored/<id>.html` | Fitted HTML, copied and adapted from the chosen variant. Opens in Chrome, prints to PDF via the existing button. |
| Output (PDF) | `cv/tailored/<id>.pdf` | Rendered + verified A4 PDF. This is the deliverable to actually send. |
| Output (log) | `cv/tailored/<id>.notes.md` | Which variant was used and what was reworded, for later audit. |
| Renderer | `cv/render_pdf.py` | Converts the HTML to a verified one-page A4 PDF. Always use it; never hand-roll the render. |

`cv/tailored/<id>.*` files are disposable: `build_html.py` deletes them
automatically when the matching posting's `status` becomes `archived` or
`rejected`. `cv/variants/*` and `cv/experience_bank/*` are never touched by
that cleanup.

**Record the fit on the job.** After Step 5 succeeds, patch two fields on the
matching `jobs.json` record (field-scoped read-modify-write; touch nothing
else): `cv_variant` = the variant name used (e.g. `data-scientist-ml`) and
`cv_tailored_at` = ISO timestamp. Then run `python build_html.py` so the
dashboard shows the `CV: <variant> ↗` link on that row.

## Hard rules

1. **Only use content that exists in `experience_bank/`.** Never invent skills, projects, dates, or employers. This binds both when fitting (you're only rewording, never adding a new claim) and when building a variant.
2. **Preserve the HTML template's structure and styling.** Keep the exact Tailwind classes, colors (`blue-900`, `gray-700`, etc.), section headers, two-column layout, and the `window.print()` button. Only swap text content inside sections.
3. **Fitting writes a new file at `cv/tailored/<id>.html`.** Never overwrite a variant in `cv/variants/` or `cv/base_cv.html` as a side effect of fitting one job.
4. **Fit on one printed A4 page.** If content overflows after rewording, revert the reword rather than trimming sections — a fit run does not drop bank entries; that's a variant-level decision.
5. **Never declare done from the HTML alone.** Always render the PDF and visually inspect it (Step 5 / Step 8). The HTML can look fine yet render wrong.
6. **If none of the three variants fits the posting's core ask** (e.g. a computer vision, robotics, or embedded-systems role — nothing in `cv/variants/` leads with that, and the bank has no entries to support it), stop and tell the user instead of force-fitting an unrelated variant.

---

## Part A — Fit a CV to a posting (the common case)

### Step 1 — Pick the closest variant

Read the job's `position`, `requirements`, `responsibilities`, `description`
from `jobs.json`. If `extraction_ok` is `false` the posting text was not
captured: pick the variant from the title alone and say so in the notes file
(the dashboard already flags the row as unverified). Score against the three archetypes:

| Variant | Leads with |
|---|---|
| `ai-llm-engineer` | LLM, GenAI, NLP, fine-tuning, agents |
| `data-scientist-ml` | time-series, forecasting, anomaly detection, recsys, general ML research |
| `software-engineer-ml` | systems/software engineering, concurrency, algorithms, SQL/backend, "SDE" titles |

Pick the variant with the strongest keyword overlap. If it's a close call,
default to `data-scientist-ml` — it's the broadest fit for his M.Sc.

### Step 2 — Copy and reword (do not rebuild)

Copy the chosen variant's HTML verbatim to `cv/tailored/<id>.html`. Then make
only these adjustments, each grounded in content the variant already contains:

- **Header subtitle** — only change it if the posting's actual title differs
  materially from the variant's default (e.g. the posting is literally titled
  "Data Scientist" but the closest-matching variant is `ai-llm-engineer`, whose
  subtitle says "AI Engineer"). Swap the subtitle text only; nothing else.
- **Professional Summary** — reword using the posting's own terminology where
  it describes something the summary already claims (e.g. variant says
  "recommendation systems", posting says "recsys pipelines" → adopt the
  posting's term). Do not add a claim the variant doesn't already make.
- **Skills cluster order** — you may reorder terms *within* a cluster line to
  lead with what the posting asks for, if those terms are already in that
  line. Do not add or remove skills.

Do **not**:
- Re-select which Research/Experience entries appear. The variant's set
  stands. If a posting would genuinely need a different entry than any
  variant offers, that's a signal to consider a new variant (see Part B), not
  a one-off rebuild.
- Touch `cv/experience_bank/` at all during a fit run.

### Step 3 — Log the fit

Append to `cv/tailored/<id>.notes.md`:

```
## CV fitted <ISO-date>
- Variant used: cv/variants/<variant>.html
- Subtitle: unchanged | changed to "<text>"
- Summary reword: [before -> after], or "none"
- Skills reorder: [cluster: before -> after], or "none"
- Output: cv/tailored/<id>.html
- jobs.json patched: cv_variant=<variant>, cv_tailored_at=<ISO-date>
```

### Step 4 — Self-audit

1. Every claim in the output still maps to a bank entry (it should, since it
   came from a variant that was already audited).
2. The HTML is valid (BeautifulSoup round-trips cleanly; `<html>`, `<body>`,
   and the `print-container` div are all present).
3. The `window.print()` button is preserved.
4. No placeholder text (`TODO`, `lorem`, `{{...}}`) remains.
5. No em or en dashes (`—` `–`) were introduced by the reword. Use a plain
   hyphen (`-`) or restructure the sentence.

### Step 5 — Render the PDF and VISUALLY verify it (mandatory)

The template relies on CSS `zoom: 0.81`, which the renderer (WeasyPrint) does
NOT support — rendered naively, the container stays ~259mm wide and the right
edge gets clipped. `cv/render_pdf.py` handles this: forces a true 210mm
container, supplies the template's Tailwind classes as static CSS, bakes in
page margins, and auto-scales to fit one A4 page.

First-time setup in a fresh sandbox (renderer deps are not preinstalled):

```bash
pip install weasyprint pymupdf --break-system-packages -q
```

Render:

```bash
python3 cv/render_pdf.py cv/tailored/<id>.html
# -> writes cv/tailored/<id>.pdf and <id>.preview.png, prints the scale used
```

Then **open the generated `.preview.png` with the Read tool and look at it.**
Confirm all three:

1. **No right-edge clipping** — the rightmost words of the right column are
   fully visible.
2. **Exactly one page** — `render_pdf.py` prints `pages=1`.
3. **Bottom section has breathing room** — the last section is not crammed
   against the bottom edge.

If any check fails, undo the reword that caused it (Step 2 is small edits to
an already-verified document; it should rarely overflow) and re-render. Only
the verified `.pdf` is the deliverable to send; the `.preview.png` is a check
artifact and may be deleted afterward.

---

## Part B — Maintaining the variants (rare)

Rebuild or add a variant only when:

- The experience bank gains a new entry substantial enough to change what an
  archetype should lead with, or
- Two or more postings in a row reveal an archetype the current three don't
  cover well (e.g. several computer-vision or robotics roles arrive). A
  single job is never a reason to add a fourth variant.

Building a variant is the old full-tailoring process, run once against
`cv/base_cv.html` and `cv/experience_bank/` rather than per job:

1. Index the bank: `grep -rn "^tags:" cv/experience_bank/`. Rank files by
   tag-overlap with the archetype's theme; load the top ~10 plus all
   `priority: 1` files.
2. Rewrite, from `cv/base_cv.html`: header subtitle, Professional Summary
   (2-3 lines naming the archetype), each Technical Skills cluster (promote
   matching families to the front, using each bank file's "Skills cluster"
   line), 2-4 Research Experience entries (Medium variation, ranked by
   tag-overlap), and 1-2 Experience entries (`priority: 1` always included).
   Keep Education, Military Service, Languages, and Contact as in the
   template. Drop Volunteering first if space is tight.
3. Save to `cv/variants/<archetype-name>.html`. Never overwrite
   `cv/base_cv.html`.
4. Run the full Step 4 self-audit and Step 5 render-and-inspect from Part A
   against the new variant file.

## What not to do

- Do not change fonts, colors, layout, or the print button.
- Do not add a cover-letter section.
- Do not translate content. Keep language matching the posting. If the bank only has English versions, keep English regardless.
- Do not duplicate entries across sections (a research project goes in Research, not also in Experience).
- Do not use em or en dashes (`—` `–`) anywhere in the output — they read as AI-generated. Use a plain hyphen (`-`) or restructure the sentence (e.g. a comma or "like"). This applies even if a bank entry contains them; convert on the way in.
- Mickael has graduated. Refer to the M.Sc. as completed ("Data Science M.Sc.", Education status "Graduated"), never "student" or "current".
- Do not re-select Research/Experience entries during a per-job fit (Part A). That's variant-level work (Part B).

## Token-efficiency note

Fitting (Part A) reuses an already-built, already-audited document instead of
re-scanning the bank, so it costs roughly the job record plus one variant
HTML plus the render pass — a few thousand tokens, well under the ~20K a full
rebuild used to cost. Reserve Part B's bank-scan-and-select process for
variant maintenance, not routine applications.
