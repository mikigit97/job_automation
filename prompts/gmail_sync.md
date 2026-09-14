# Gmail status sync — Cowork scheduled task  (schema v2)

Save this as a Cowork scheduled task. Run Sunday–Thursday at 16:05 (right after
the afternoon `/scrape-jobs`).

---

Sync application replies from Gmail into `jobs.json`. Do not store emails
locally; store only a link to the most recent relevant thread per position, its
classification, and move the status forward when the email warrants it.

## Step 1 — Load the tracker

Read `jobs.json` at the Cowork project root — a JSON array of schema-v2
records. The fields you use:

```json
{
  "id": "...", "company": "...", "position": "...",
  "status": "new|applied|interview|offer|rejected|archived",
  "status_source": "user|gmail|auto_apply|scraper|maintain",
  "status_changed_at": "2026-09-11T10:00:00Z",
  "applied_at": "2026-09-11T10:00:00Z",
  "last_email": null
}
```

### Field ownership — the Gmail task's lane

You may write **only**: `last_email`, and — for forward moves — `status`,
`status_source` (always `"gmail"`), `status_changed_at`. Nothing else, ever
(not `applied_at`, not `notes`, not any scraper field). Save with a
field-scoped patch: read the file, change those fields on the records you
touched, write it back.

## Step 2 — Pick the candidates

Check a record when `status` is `applied` or `interview` (an outcome can
still arrive). Skip `new` (nothing sent yet), `offer`, `rejected`, `archived`.

## Step 3 — Search Gmail per candidate

One search per record. Query:

```
(from:(<company>) OR subject:("<position>") OR (from:(<ATS senders>) "<company>")) after:<applied_at minus 1 day>
```

where `<ATS senders>` is the fixed list
`comeet OR greenhouse OR lever.co OR myworkday OR smartrecruiters OR ashbyhq OR workable OR hibob OR jobvite OR icims`
— applicant-tracking systems send from their own domains, not the company's,
so a `from:(company)` search alone misses most confirmations and rejections.

- If `last_email` exists, additionally scope `after:<last_email.date>`.
- Cap at the 3 most recent threads. Retrieve: sender, subject, snippet,
  internal date, **thread id**.
- Token discipline: snippets + subject only. Fetch a body (first ~1500
  chars) only when Step 5 can't classify from the snippet.
- Company names with non-ASCII characters: search the Hebrew name and an
  obvious romanization.

## Step 4 — Pick the latest relevant thread and compare

From the results, drop threads that are clearly not about this application
(newsletters, unrelated recruiters, "talent network" digests with no
reference to the position). Take the most recent remaining thread and build

```
https://mail.google.com/mail/u/0/#inbox/<thread-id>
```

If it equals `last_email.thread_link` → nothing to do for this record.
Otherwise continue.

## Step 5 — Classify and write

Classify subject + snippet with this rubric, checking buckets in priority
order **Offer → Interview → Rejected → Auto_ack** so a rejection that also
says "thank you for applying" lands in Rejected. If no keyword matches,
classify semantically; if still ambiguous, fetch ~1500 chars of the body
once and re-classify.

**Auto_ack** — receipt confirmation, no decision
- English: `received your application`, `thank you for applying`, `thanks for applying`, `we got your submission`, `application received`, `we have received your`, `application confirmation`, `thank you for your interest`, `we appreciate your interest`, `your application has been`, `under review`, `currently reviewing`, `talent acquisition team will`
- Hebrew: `תודה על פנייתך`, `תודה רבה על פנייתך`, `קיבלנו את קורות החיים`, `קורות החיים נקלטו`, `אישור הרשמה`, `אישור קבלה`, `פנייתך התקבלה`, `תודה על התעניינותך`, `נבחן את מועמדותך`, `נבחן אותם בקפידה`

**Rejected** — explicit decline
- English: `unfortunately`, `regret to inform`, `not moving forward`, `decided to move forward with other`, `other candidates`, `not a match`, `not the right fit`, `different direction`, `position has been filled`, `no longer considering`, `wish you success`, `wish you the best`, `best of luck in your`
- Hebrew: `מצטערים`, `לצערנו`, `החלטנו שלא להמשיך`, `לא נמשיך`, `לא מתאים`, `אינך מתאים`, `מועמדים אחרים`, `המשרה אוישה`, `בהצלחה בהמשך`, `מאחלים לך הצלחה`

**Interview** — invitation to talk / next step
- English: `interview`, `phone screen`, `phone call`, `video call`, `zoom`, `google meet`, `would like to chat`, `would like to speak`, `set up a time`, `available for a call`, `schedule a call`, `next step`, `meeting invitation`, `talk further`, `move to the next stage`, `home assignment`, `take-home`
- Hebrew: `ראיון`, `ראיון טלפוני`, `שיחת היכרות`, `נשמח להיפגש`, `נשמח לדבר`, `הוזמנת לראיון`, `נקבע מועד`, `נקבע פגישה`, `זמן פנוי`, `שלב הבא`, `מבחן בית`

**Offer** — formal job offer
- English: `offer letter`, `pleased to offer`, `extending an offer`, `formal offer`, `compensation package`, `starting date`, `start date`
- Hebrew: `הצעת עבודה`, `שמחים להציע`, `הצעה רשמית`, `תנאי העסקה`, `מכתב הצעה`

**Other** — anything else. Still update `last_email`; do not touch status.

Always write `last_email`:

```json
"last_email": {
  "thread_link": "https://mail.google.com/mail/u/0/#inbox/<id>",
  "classification": "Interview",
  "date": "2026-09-14",
  "subject": "Re: your application for Data Scientist"
}
```

Then decide the status move. Map classification → target status:
`Auto_ack → applied`, `Interview → interview`, `Offer → offer`,
`Rejected → rejected`. Write the move **only if all three hold**:

1. It is forward: rank `applied (1) < rejected (2) < interview (3) < offer (4)`
   and the target rank is higher than the current `status`'s rank. Never
   downgrade — an Auto_ack arriving after an Interview keeps `interview`.
2. The email date is later than the record's `status_changed_at`. A user click
   that is newer than the email always wins.
3. The current `status` is not `archived` (you never look at those anyway).

When you move it: `status = <target>`, `status_source = "gmail"`,
`status_changed_at = <email date as ISO, e.g. "2026-09-14T00:00:00Z">`.
`applied_at` is never touched here — it was set when the user (or auto-apply)
applied.

## Step 6 — Persist and rebuild

1. Save `jobs.json` (pretty-printed, 2-space indent, UTF-8). Only
   `last_email`, and where moved `status` / `status_source` /
   `status_changed_at`, differ from what you read in Step 1.
2. Run `python build_html.py`.

## Step 7 — One-line summary

`Gmail sync: checked N · updated M last_email · moved: I→interview, O→offer, R→rejected, A→applied · X other · S skipped (newer user status)`

## Token and call discipline

- One Gmail search per record per run.
- Snippets only; bodies only when classification is ambiguous.
- No writes to files other than `jobs.json` and the rebuilt HTML.
- No emails stored locally.

## Error handling

- **Gmail connector unavailable**: print the error and exit. Do not partially
  update `jobs.json` — all-or-nothing per run.
- **Ambiguous company name** (e.g. "matrix DnA"): search the literal string;
  accept some noise. The position-in-subject clause and the user's own status
  clicks keep it from doing harm.
