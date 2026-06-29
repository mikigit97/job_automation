# Cowork task: Tailor CVs for V rows

Save as a Cowork saved task. Run on demand ("Tailor CVs for Vs").

---

Generate tailored CVs for all positions I marked with V.

**Step 1 — Read the tracker.**
Open `Job_applications.xlsx` (sheet `גיליון1`). Collect all rows where:
- `Interested` == `V`
- `Tailored_CV_file` is empty

If none match, print `No pending CVs to tailor.` and stop.

**Step 2 — For each matching row:**
1. Read `positions/<Position_id>/requirements.md`
2. Apply the `cv-tailor` skill (it autoloads — do not inline its rules here). The skill reads `cv/base_cv.html` as the visual template and `cv/experience_bank/` as the content pool.
3. Save output to `cv/tailored/<Position_id>.html`
4. Update the row:
   - `Tailored_CV_file` = `cv/tailored/<Position_id>.html`
   - `Status` = `CV_ready`
5. The cv-tailor skill handles the log entry to `positions/<Position_id>/notes.md`.

**Step 3 — Summary.**
Print:
```
Tailored N CVs:
- <Position_id>: matched [top 3 must_have], included [N bank entries]
...
Open each .html in Chrome and click "Download as PDF" to produce the printable version.
```

**If `cv/base_cv.html` is missing**, stop and tell me.
**If `cv/experience_bank/` is empty or has no matching tags**, still produce the CV using whatever bank entries exist — do not invent content.
