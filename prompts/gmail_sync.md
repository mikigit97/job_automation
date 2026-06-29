# Gmail status sync — Cowork scheduled task

Save this as a Cowork scheduled task. Run Sunday–Thursday at 16:05 (right after
the afternoon scrape, which runs both `/scrape-jobs` and `/scrape-bigtech` at 16:00).

---

Sync job application statuses from Gmail into `jobs.json`. Do not store emails
locally; store only a link to the most recent email thread per position, the
classification, and a derived status.

## Step 1 — Load the tracker

Read `jobs.json` at the Cowork project root. It is a JSON array of position
objects. Each position has at least:

```json
{
  "id": "<folder-name-or-scraper-id>",
  "company": "<company name>",
  "link": "<listing url>",
  "last_email": null,
  "status_auto": null
}
```

`last_email` (if present) is an object: `{ thread_link, classification, date, subject }`.
`status_auto` (if present) is one of: `Applied`, `Interview`, `Offer`, `Rejected`.

### Field ownership — the Gmail task's lane

`jobs.json` is shared with the scraper and the HTML tracker. Stay in your
lane:

- You may write: `last_email`, `status_auto`. That's it.
- Leave untouched: everything else on the entry (`position`, `company`,
  `link`, `scraped_at`, `location`, `date`, `responsibilities`,
  `requirements`, `nice_to_have`, `status_manual`, `interested`, `notes`).

When you save, do a field-scoped patch — not a wholesale replacement of the
entry.

## Step 2 — Pick the candidates to check

Skip any position where:
- `deleted` is `true` (the user soft-deleted it from the HTML tracker — no
  reason to chase email status for a hidden row), or
- `status_auto` is `Rejected` or `Offer` — no reason to keep polling once
  the outcome is final.

Check every other position.

## Step 3 — Search Gmail per position

For each candidate, call the Gmail connector with:

- Query: `from:(<company>) OR from:(<company-domain-guess>)`
- If `last_email` exists, scope to `after:<last_email.date>` to limit work.
- Cap at the 3 most recent threads per company.
- Retrieve: sender, subject, snippet, internal date, **thread id**.

Token discipline: snippets + subject only. No full bodies unless Step 5
cannot classify from the snippet alone.

If the company name contains non-ASCII characters, search by its Hebrew name
and by an obvious romanization.

## Step 4 — Pick the latest email and compare to what's in the JSON

From the Gmail results for this position, pick the single most recent thread.
Build its thread link:

```
https://mail.google.com/mail/u/0/#inbox/<thread-id>
```

**Compare to `jobs.json[i].last_email.thread_link`:**

- If they match exactly → skip this position. Nothing to do.
- Otherwise → continue to Step 5.

## Step 5 — Classify the new email and update the JSON

Classify the snippet (+ subject) using this rubric. Match keywords
case-insensitively. Check buckets in priority order **Offer → Interview →
Rejected → Auto_ack** so a rejection mentioning "thank you for applying"
still lands in Rejected. If none of the keywords match, classify
semantically — read the snippet and pick the bucket whose meaning fits
best. If still ambiguous, fetch the first ~1500 characters of the thread
body once and re-classify.

**Auto_ack** — application receipt confirmation, no decision yet
- English: `received your application`, `thank you for applying`, `thanks for applying`, `we got your submission`, `application received`, `we have received your`, `application confirmation`, `thank you for your interest`, `we appreciate your interest`, `your application has been`, `under review`, `currently reviewing`, `talent acquisition team will`
- Hebrew: `תודה על פנייתך`, `תודה רבה על פנייתך`, `קיבלנו את קורות החיים`, `קורות החיים נקלטו`, `אישור הרשמה`, `אישור קבלה`, `פנייתך התקבלה`, `תודה על התעניינותך`, `נבחן את מועמדותך`, `נבחן אותם בקפידה`

**Rejected** — explicit decline
- English: `unfortunately`, `regret to inform`, `not moving forward`, `decided to move forward with other`, `other candidates`, `not a match`, `not the right fit`, `different direction`, `position has been filled`, `no longer considering`, `wish you success`, `wish you the best`, `best of luck in your`
- Hebrew: `מצטערים`, `לצערנו`, `החלטנו שלא להמשיך`, `לא נמשיך`, `לא מתאים`, `אינך מתאים`, `מועמדים אחרים`, `המשרה אוישה`, `בהצלחה בהמשך`, `מאחלים לך הצלחה`

**Interview** — invitation to talk / next step beyond auto-ack
- English: `interview`, `phone screen`, `phone call`, `video call`, `zoom`, `google meet`, `would like to chat`, `would like to speak`, `set up a time`, `available for a call`, `schedule a call`, `next step`, `meeting invitation`, `talk further`, `move to the next stage`
- Hebrew: `ראיון`, `ראיון טלפוני`, `שיחת היכרות`, `נשמח להיפגש`, `נשמח לדבר`, `הוזמנת לראיון`, `נקבע מועד`, `נקבע פגישה`, `זמן פנוי`, `שלב הבא`

**Offer** — formal job offer
- English: `offer letter`, `pleased to offer`, `extending an offer`, `formal offer`, `compensation package`, `starting date`, `start date`
- Hebrew: `הצעת עבודה`, `שמחים להציע`, `הצעה רשמית`, `תנאי העסקה`, `מכתב הצעה`

**Other** — anything else; still update `last_email`, but leave `status_auto` unchanged.

Map classification → `status_auto`:

| Classification | status_auto |
|---|---|
| Auto_ack | Applied |
| Interview | Interview |
| Offer | Offer |
| Rejected | Rejected |
| Other | (unchanged) |

**Never downgrade.** If the current `status_auto` is `Interview` and the new
classification is `Auto_ack`, keep `Interview`. Priority order high-to-low:
`Offer > Interview > Rejected > Applied > (empty)`.

Write the updated object back into `jobs.json[i]`:

```json
{
  "last_email": {
    "thread_link": "https://mail.google.com/mail/u/0/#inbox/<id>",
    "classification": "Interview",
    "date": "2026-04-22",
    "subject": "Re: your application for Data Scientist"
  },
  "status_auto": "Interview"
}
```

## Step 6 — Persist and rebuild

After processing all positions:

1. Save `jobs.json` (pretty-printed, UTF-8, one entry per array slot). Only
   `last_email` and `status_auto` on the entries you changed should differ
   from the version you read at Step 1.
2. Run `python build_html.py` to rebuild `Job_applications.html` so the changes
   show up in the tracker.

## Step 7 — Print a one-line summary

`Gmail sync: checked N positions, updated M with new emails. Classifications: A Auto_ack / I Interview / O Offer / R Rejected / X Other.`

## Token and call discipline

- One Gmail search per position per run (not per thread).
- Snippets only; no full bodies unless classification is ambiguous.
- No writes to files other than `jobs.json` and the rebuilt HTML.
- No emails stored locally.

## Error handling

- **Gmail connector unavailable**: print the error and exit non-zero. Do not
  partially update `jobs.json` — it's all-or-nothing per run to keep the file
  consistent.
- **A position's company name is ambiguous** (e.g., "matrix DnA"): search
  the literal string as-is; accept that a few threads may be noisy. Your
  manual status override in the HTML always wins.
