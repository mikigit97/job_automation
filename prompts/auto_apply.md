# Cowork task: Auto-apply  (schema v2, on demand only)

Save this as a Cowork saved task named "Auto-apply". **Never schedule it.**
Run it when you have reviewed the Inbox and want the AllJobs / Drushim
postings applied to in one pass.

The task reads `jobs.json`, picks the postings that are safe to apply to
without tripping anti-bot defences, makes sure each has a fitted CV, drives
Claude in Chrome to submit the application, and records the outcome.

---

You are running the Israel junior AI / ML / DS **auto-apply** task. Use
Claude in Chrome with the accessibility tree or page-state JavaScript — never
screenshots.

## Step 0 — Load the tracker

Read `jobs.json` from the Cowork project root (schema v2).

### Field ownership — the auto-apply lane

You may write, on the records you actually submitted: `status`,
`status_source` (`"auto_apply"`), `status_changed_at`, `applied_at`,
`applied_via` (`"auto"`), and append one line to `notes`. On records you
could not submit you may only append to `notes`. Nothing else, ever. Save
with a field-scoped patch.

## Step 1 — Pick candidates

A record is a candidate iff **all** of these hold:

1. `status == "new"`.
2. `source` is exactly `AllJobs` or `Drushim`. Any other source — LinkedIn,
   big-tech pages, Manual — skip: those you apply to yourself.
3. `extraction_ok == true`. Never apply blind to a posting whose
   requirements weren't captured; it shows as *unverified* in the dashboard
   and needs a look first.
4. `link` is set.
5. `notes` does not already contain `auto-apply:` (one attempt per posting;
   retries are the user's call, via the dashboard).

Order: `fit.tier` strong → ok → weak, then newest `scraped_at`. **Max 15
per run.**

## Step 2 — Make sure a fitted CV exists

For each candidate, the file to upload is `cv/tailored/<id>.pdf`. If it does
not exist, run the `cv-tailor` skill, **Part A**, for that one record first
(it picks the closest variant, renders the PDF, and writes `cv_variant` /
`cv_tailored_at` on the record). If fitting fails — no variant covers the
role (Hard Rule 6) — append `auto-apply: no matching CV variant` to `notes`
and skip the record. Never upload `cv/base_cv.pdf` or any other generic file.

## Step 3 — Filter by destination host

If the application link redirects to any of these hosts, skip it and append
`auto-apply: skipped, <host> needs a manual application` to `notes`:

- `linkedin.com`
- `greenhouse.io`, `lever.co`, `myworkdayjobs.com`, `workday.com`,
  `ashbyhq.com`, `smartrecruiters.com`, `comeet.co`, `comeet.com`
- career subdomains at `google.com`, `meta.com`, `microsoft.com`,
  `amazon.jobs`, `apple.com`, `nvidia.com`, `intel.com`, `wix.com`,
  `monday.com`, `checkpoint.com`, `paloaltonetworks.com`, `lightricks.com`

Bot-detection risk on those is too high; the user does them by hand.

## Step 4 — Apply (per candidate)

1. Open `link` in a new tab. Wait for load.
2. Read the page state. If it contains any of `recaptcha`, `captcha`,
   `cloudflare`, `are you human`, `prove you're not a robot`, `hcaptcha`
   (case-insensitive): stop for this record, append
   `auto-apply: CAPTCHA / bot check, apply manually` to `notes`, move on.
   Do not solve or retry.
3. Find the apply form. AllJobs: a form with a file input named `cv` or
   `resume` and a textarea for a note. Drushim: a multi-step wizard with
   `first_name`, `last_name`, `email`, `phone`, plus a file input.
4. Fill it:
   - First name `Mickael`; last name — the site's saved value if present,
     otherwise from `cv/base_cv.html`.
   - Email `mickaelz@post.bgu.ac.il`; phone from `cv/base_cv.html`.
   - CV file: `cv/tailored/<id>.pdf` from Step 2 — nothing else.
5. Submit. Confirm a success state: a page containing `Thank you` / `תודה` /
   `Application received` / `פנייתך נקלטה` / `קורות החיים נשלחו`.
6. **On success**, on that record:
   `status = "applied"`, `status_source = "auto_apply"`,
   `applied_via = "auto"`, `applied_at = <now, ISO UTC>`,
   `status_changed_at = <same>`, and append
   `auto-apply: submitted <YYYY-MM-DD HH:MM> with cv_variant=<variant>` to `notes`.
7. **On any error** (timeout, unexpected page, missing form, upload failed):
   leave `status` as `new`, append `auto-apply: failed — <what went wrong>`
   to `notes`, continue with the next candidate. Never crash the run.

## Step 5 — Save and rebuild

Field-scoped read-modify-write of `jobs.json` for the records you touched,
then run `python build_html.py` so the Applied tab and the follow-up timers
pick them up.

## Step 6 — Report

```
Applied (3):
  • Picaro — Machine Learning Researcher (cv: data-scientist-ml)
Skipped, manual host (2):
  • <company> — <position> (<host>)
Skipped, CAPTCHA (1): …
Skipped, no CV variant (0): …
Failed (0): …
Not candidates (N): not new / not AllJobs-Drushim / unverified / already attempted
```

## Guardrails

- On-demand only. Do not schedule; do not run more than once a day.
- Max 15 submissions per run; stop at the first CAPTCHA on a board and skip
  the rest of that board's candidates for this run.
- Never change a status other than `new → applied`, and only on a confirmed
  success page.
- Never upload anything but `cv/tailored/<id>.pdf`.
