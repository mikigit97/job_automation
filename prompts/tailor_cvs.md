# Cowork task: Fit CVs to open postings

Save as a Cowork saved task. Run on demand ("Fit CVs" / "Tailor CVs").

---

Fit a CV to every job posting in `jobs.json` that doesn't have one yet.

**Step 1 - Build the work list.**

Read `jobs.json` (a JSON array of job records). A job needs a CV when:
- `cv/tailored/<id>.html` does not exist, and
- the job is not already out of the running (`status_manual` or `status_auto`
  is not `Rejected`).

There is no spreadsheet and no `positions/` folder. `jobs.json` is the only
store. Everything the fit step needs is on the job record itself.

If nothing matches, print `No pending CVs to fit.` and stop.

**Step 2 - For each job in the work list, apply the `cv-tailor` skill** (it
autoloads - do not inline its rules here). Use **Part A - Fit a CV to a
posting**, not Part B: this is the per-job path, and it works from
`cv/variants/` and `jobs.json` directly. It does not touch
`cv/experience_bank/`.

The skill picks the closest of the three durable variants
(`cv/variants/ai-llm-engineer.html`, `data-scientist-ml.html`,
`software-engineer-ml.html`), copies it to `cv/tailored/<id>.html`, rewords
only the header subtitle and Professional Summary where the posting's own
terms already match something the variant claims, renders `cv/tailored/<id>.pdf`
via `cv/render_pdf.py`, and logs to `cv/tailored/<id>.notes.md`.

Because fitting reuses an already-verified document instead of rebuilding
from the experience bank, this is cheap - there's no need to batch or ask
before running the full work list, unlike a from-scratch tailor run would be.

**If a posting's core ask isn't covered by any of the three variants** (e.g.
computer vision, robotics - the skill's Hard Rule 6), skip that job, note it
in the summary below, and do not force a mismatched variant onto it.

Do not write a `Tailored_CV_file` field or change `status_manual`. The
presence of `cv/tailored/<id>.html` is the record that a CV exists - that is
what Step 1 checks, and what `build_html.py` cleans up when a posting drops
out of the tracker.

**Step 3 - Summary.**

Print:
```
Fitted N CVs:
- <id> (<company> - <position>): used <variant>, reworded [summary / subtitle / neither]
...
Skipped M (already have a CV).
Could not fit K (no matching variant): <id> (<company> - <position>), ...
```

**If `cv/variants/` is missing or empty**, stop and tell me - the variants
need to be built first (see the skill's Part B).

## Lifecycle note

Fitted CVs in `cv/tailored/` are disposable outputs, not archives. When a
posting is rejected or ages out of the tracker, `build_html.py` deletes the
matching `cv/tailored/<id>.*` files on its next run. `cv/variants/` is never
touched by that cleanup - it changes only through the skill's Part B
(maintaining the variants), not as a side effect of fitting jobs.
