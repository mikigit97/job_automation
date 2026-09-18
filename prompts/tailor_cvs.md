# Cowork task: Fit CVs to open postings

Save as a Cowork saved task. Run on demand ("Fit CVs" / "Tailor CVs").

---

Fit a CV to every live posting in `jobs.json` that doesn't have one yet.

**Step 1 - Build the work list.**

Read `jobs.json` (a JSON array of job records, schema v2). A job needs a CV
when all of these hold:
- `status` is `new` or `applied` (never `archived`, `rejected`, `offer`, or
  `interview` - those either don't need a CV or already sent one), and
- `cv_variant` is null AND `cv/tailored/<id>.pdf` does not exist.

Order the list: `applied` first (a CV is overdue), then Inbox rows by fit
tier `strong`, `ok`, `weak`. Rows with `years_min` above `years_max` (they
show `4y` / `5y` on the dashboard) go through the skill's **Step 0 coverage
check** first; the ones it rejects are archived with `archive_reason: "fit"`
and listed in the summary instead of getting a CV.

`jobs.json` is the only store. Everything the fit step needs is on the job
record itself: `position`, `company`, `requirements`, `responsibilities`,
`nice_to_have`, `description`, `extraction_ok`.

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
via `cv/render_pdf.py`, logs to `cv/tailored/<id>.notes.md`, and patches
`cv_variant` + `cv_tailored_at` onto the job record.

Because fitting reuses an already-verified document instead of rebuilding
from the experience bank, this is cheap - there's no need to batch or ask
before running the full work list.

**If a posting's core ask isn't covered by any of the three variants** (e.g.
computer vision, robotics - the skill's Hard Rule 6), skip that job, note it
in the summary below, and do not force a mismatched variant onto it.

**If `extraction_ok` is false** (requirements weren't captured), still fit
from the title alone and say so in the notes file. The dashboard already
marks the row as unverified; the user can paste requirements via Edit and
re-run.

Do not change `status`, `applied_at`, or any other field beyond `cv_variant`
and `cv_tailored_at` — with one exception: the Step 0 coverage check may
archive a 4–5-year posting (`status`, `archive_reason: "fit"`,
`status_source: "fit"`, `status_changed_at`, a `notes` line). Nothing else.

**Step 3 - Rebuild the dashboard.**

Run `python build_html.py` once at the end so the `CV: <variant> ↗` links
appear on the rows. Then commit:

```
git -c user.name=mikigit97 -c user.email=mickaelz@post.bgu.ac.il add -A && git -c user.name=mikigit97 -c user.email=mickaelz@post.bgu.ac.il commit -m "fit-cvs: <fitted N, archived J>"
```

**Step 4 - Summary.**

Print:
```
Fitted N CVs:
- <id> (<company> - <position>): used <variant>, reworded [summary / subtitle / neither]
...
Skipped M (already have a CV).
Could not fit K (no matching variant): <id> (<company> - <position>), ...
Archived J (4-5y posting, requirements not covered): <id> (<company> - <position>): uncovered <line>; ...
```

**If `cv/variants/` is missing or empty**, stop and tell me - the variants
need to be built first (see the skill's Part B).

**Renderer dependencies.** `cv/render_pdf.py` needs `weasyprint` and
`pymupdf`. They may not be installed where this task runs; if the import
fails, install them first: `pip install weasyprint pymupdf --break-system-packages -q`.

## Lifecycle note

Fitted CVs in `cv/tailored/` are disposable outputs, not archives. When a
posting's `status` becomes `archived` or `rejected`, `build_html.py` deletes
the matching `cv/tailored/<id>.*` files on its next run. `cv/variants/` is
never touched by that cleanup - it changes only through the skill's Part B
(maintaining the variants), not as a side effect of fitting jobs.
