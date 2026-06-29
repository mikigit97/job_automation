# Cowork task: /auto-apply

Save this as a Cowork saved task. Schedule it Sun–Thu at 09:00. Trigger manually
from the tracker HTML's "⚡ Auto-apply now" button or from the mobile artifact.

The task reads `jobs.json`, decides which entries are safe to apply to without
tripping anti-bot defences, drives Claude in Chrome to fill each application,
and writes the outcome back into `jobs.json`.

---

You are running the Israel DS / AI-engineer **auto-apply** task. Use Claude in
Chrome with the accessibility tree or page-state JavaScript — never screenshots.

## Step 0 — Load the tracker

Read `jobs.json` from the Cowork project root.

## Step 1 — Pick candidates

A row is a candidate iff **all** of these hold:

1. `deleted` is falsy.
2. `status_manual` is null/empty AND `status_auto` is null/empty.
   (Anything already "Applied", "Interview", "Offer", "Rejected" is left alone.)
3. `interested !== 'no'`.
4. `link` is set.
5. **Source whitelist**: `source` is exactly `AllJobs` or `Drushim`. Any other
   source — LinkedIn, Comeet, big-tech career pages, manual entries — skip.
6. **Title gate**: `position` matches one of:
   `data scientist`, `machine learning`, ` ML ` / ` ML/`, ` AI `, `deep learning`,
   `applied scientist`, `research scientist`, `research engineer`, `NLP`,
   `computer vision`, `LLM`, `gen ai`, `MLOps`, `algorithm engineer`,
   `algorithm developer`, plus the Hebrew equivalents
   (`מדען נתונים`, `למידת מכונה`, `בינה מלאכותית`, `אלגוריתמ`).
   Skip any title containing `senior`, `sr.`, `lead`, `principal`, `staff`,
   `manager`, `director`, `head of`, `architect`, `vp` (and `בכיר`, `מנהל`,
   `ראש צוות`).
7. **Years gate**: scan `requirements` + `responsibilities` + `description`
   for digit-followed-by-`year(s)`, `yr(s)`, `שנה`/`שנים`/`שנות`, plus the bare
   word `שנתיים` (=2). If the lowest number found exceeds 2, skip.

If a `last_email.classification === 'Auto_ack'` exists for the row, treat it
as "already applied" and skip.

## Step 2 — Filter by destination host

If the application link redirects to one of these hosts, skip and write
`status_manual = "Manual review"` with a note explaining why:

- `linkedin.com` (any subpath)
- `greenhouse.io`, `boards.greenhouse.io`
- `lever.co`, `jobs.lever.co`
- `myworkdayjobs.com`, `workday.com`
- `ashbyhq.com`, `jobs.ashbyhq.com`
- `smartrecruiters.com`
- `comeet.co`, `comeet.com`
- Career subdomains at: `google.com`, `meta.com`, `careers.fb.com`,
  `microsoft.com`, `amazon.jobs`, `apple.com`, `nvidia.com`, `intel.com`,
  `wix.com`, `monday.com`, `checkpoint.com`, `paloaltonetworks.com`,
  `lightricks.com`

For these the bot-detection risk is too high; you do them manually.

## Step 3 — Apply (per candidate, max 15 per run)

For each remaining candidate, in order of `scraped_at` newest first:

1. Open `link` in a new tab. Wait for load.
2. Read the page-state JSON via the JS tool. If the page contains any of
   these strings (case-insensitive), STOP applying for this row, mark
   `status_manual = "Manual review"`, set `notes` to
   `"auto-apply: CAPTCHA / bot check detected"`, and move to the next candidate:
   - `recaptcha`
   - `captcha`
   - `cloudflare`
   - `are you human`
   - `prove you're not a robot`
   - `hcaptcha`
3. Find the apply form. On AllJobs this is typically a form with a
   file-input named `cv` or `resume` and a textarea for a cover note. On
   Drushim it's a multi-step wizard with fields `first_name`, `last_name`,
   `email`, `phone`, plus a file input.
4. Fill the form using these values:
   - First name: `Mickael`
   - Last name: leave the user's saved value on the site (they've applied
     before, the form remembers) OR look it up in `cv/base_cv.html`.
   - Email: `mickaelz@post.bgu.ac.il`
   - Phone: look up in `cv/base_cv.html`
   - CV file: upload the first that exists, in this order:
       1. `cv/tailored/<id>.pdf` — per-job tailored CV inside the project.
       2. `cv/base_cv.pdf` — fallback inside the project.
       3. `C:\Users\user\OneDrive\Documents\עבודה\Mickael Zeitoun - CV.pdf`
          — the user's canonical CV on Windows. The Chrome `file_upload`
          tool accepts a Windows path even though it's outside the Cowork
          mount; it goes through the OS file picker. Note the Hebrew
          folder name `עבודה`. Use the exact path verbatim — do NOT
          URL-encode or transliterate it.
     If none of the three exist, mark `status_manual = "Manual review"`
     with note `"auto-apply: no CV file"` and skip this row.
5. Submit the form. Confirm a success state — typically a page with the
   word "Thank you" / "תודה" / "Application received" / "פנייתך נקלטה".
6. On success, write the row's `status_manual = "Applied"` and append to
   `notes` a line like `auto-applied 2026-05-23 09:14`.
7. On any error (timeout, unexpected page, missing form, network failure),
   mark `status_manual = "Manual review"` with a note describing what
   went wrong. Do not crash the whole task — continue to the next candidate.

## Step 4 — Save

Do a field-scoped read-modify-write of `jobs.json`. Only touch
`status_manual` and `notes` for the candidates you processed.

## Step 5 — Report

Print a one-line-per-candidate summary:

    Applied (3):
      • Picaro — Machine Learning Researcher
      • ...
    Skipped (host) (2):
      • <company> — <position> (LinkedIn)
    Manual review (1):
      • <company> — <position> (CAPTCHA)
    Untouched (4): not-DS / senior / >2y / etc.
