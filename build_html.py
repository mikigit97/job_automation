#!/usr/bin/env python3
"""
build_html.py
-------------
Reads jobs.json and writes Job_applications.html — a single-file
interactive tracker.

Why rebuild instead of fetch at runtime? Browsers block a file:// HTML
page from reading local JSON via fetch(), so we bake the data in.

Before rendering, runs an auto-maintenance pass on jobs.json that:
  * drops any entry whose status (auto or manual) is "Rejected"
  * drops any entry scraped more than 14 days ago
  * drops any entry whose position title is not a data-science role
    or that requires more than 2 years of experience

Run:  python build_html.py
"""
from __future__ import annotations
import datetime as _dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent
JOBS_JSON = ROOT / "jobs.json"
HTML_OUT = ROOT / "Job_applications.html"
MOBILE_HTML_OUT = ROOT / "Job_applications_mobile.html"

# Fields the mobile artifact's JS actually reads. Anything else (description,
# responsibilities, requirements, recruiter_phone, …) is stripped to keep the
# embedded JOBS array small.
MOBILE_FIELDS = [
    "id", "position", "company", "source", "link",
    "scraped_at", "date", "location",
    "last_email", "status_auto", "status_manual", "interested",
    "notes", "deleted",
]


def rebuild_mobile_html(kept: list) -> None:
    """Rewrite the embedded `const JOBS = [...]` array and `Snapshot:` line
    in Job_applications_mobile.html. No-op if the file doesn't exist — the
    mobile artifact is hand-authored, this function only refreshes its data."""
    if not MOBILE_HTML_OUT.exists():
        return
    slim = [{k: j.get(k) for k in MOBILE_FIELDS} for j in kept]
    src = MOBILE_HTML_OUT.read_text(encoding="utf-8")
    new_jobs = "const JOBS = " + json.dumps(slim, ensure_ascii=False) + ";"
    src2, n1 = re.subn(r"const JOBS = \[.*?\];", new_jobs, src,
                       count=1, flags=re.DOTALL)
    snap = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    src3, n2 = re.subn(r"Snapshot: [\d\-: ]+",
                       f"Snapshot: {snap}", src2, count=1)
    if n1 != 1:
        print(f"Mobile rebuild: JOBS array not found ({n1} matches); skipped.")
        return
    MOBILE_HTML_OUT.write_text(src3, encoding="utf-8")
    print(f"Wrote {MOBILE_HTML_OUT} ({len(src3):,} chars, {len(slim)} jobs)")

# ---------------------------------------------------------------------------
# Relevance filter — keep only DS-flavoured roles requiring <=2 years.
# ---------------------------------------------------------------------------

DS_TITLE_RE = re.compile(
    r"(?ix)"
    r"(?:"
    r"  data\s*scien"
    r"| machine\s*learn"
    r"| (?:^|[^a-z])ML(?:[\s/\-]|$)"
    r"| (?:^|[^a-z])AI(?:[\s/\-]|$)"
    r"| deep\s*learn"
    r"| applied\s*scien"
    r"| research\s*(?:scien|engineer)"
    r"| (?:^|[^a-z])NLP(?:[\s/\-]|$)"
    r"| computer\s*vision"
    r"| (?:^|[^a-z])LLM"
    r"| gen[\s\-]?ai"
    r"| generative\s*ai"
    r"| MLOps"
    r"| algorithm\s*(?:eng|dev|research)"
    r"| מדען\s*נתונים"
    r"| למידת\s*מכונה"
    r"| בינה\s*מלאכותית"
    r"| אלגוריתמ"
    r")",
)

SENIOR_TITLE_RE = re.compile(
    r"(?i)\b(?:senior|sr\.?|lead|principal|staff|manager|director|head\s+of|architect|vp)\b"
    r"|בכיר|מנהל|ראש\s*צוות",
)

_YEARS_NUM_RE = re.compile(r"(\d+)\s*\+?\s*(?:years?|yrs?)\b", re.IGNORECASE)
_YEARS_HEB_RE = re.compile(r"(\d+)\s*שנ")


def years_required(job: dict) -> int | None:
    """Lowest years-of-experience requirement mentioned in the posting.

    Returns ``None`` when nothing year-shaped is mentioned.
    """
    parts: list[str] = []
    if isinstance(job.get("requirements"), list):
        parts.extend(str(x) for x in job["requirements"])
    if isinstance(job.get("responsibilities"), list):
        parts.extend(str(x) for x in job["responsibilities"])
    if job.get("description"):
        parts.append(str(job["description"]))
    if not parts:
        return None
    text = " ".join(parts)
    found: list[int] = []
    for m in _YEARS_NUM_RE.finditer(text):
        try:
            found.append(int(m.group(1)))
        except ValueError:
            pass
    for m in _YEARS_HEB_RE.finditer(text):
        try:
            found.append(int(m.group(1)))
        except ValueError:
            pass
    if "שנתיים" in text:
        found.append(2)
    if not found:
        return None
    return min(found)


def is_relevant(job: dict) -> tuple[bool, str]:
    """Return ``(keep, reason)``. ``reason`` is empty when ``keep`` is True."""
    pos = (job.get("position") or "").strip()
    if not pos:
        return False, "no position title"
    if not DS_TITLE_RE.search(pos):
        return False, f"non-DS title: {pos!r}"
    if SENIOR_TITLE_RE.search(pos):
        return False, "senior/lead role"
    yrs = years_required(job)
    if yrs is not None and yrs > 2:
        return False, f"requires {yrs}+ years"
    return True, ""


# ---------------------------------------------------------------------------
# Auto-maintenance pass — runs at build time, mutates jobs.json on disk.
# ---------------------------------------------------------------------------

MAX_AGE_DAYS = 14


def _scraped_age_days(job: dict, now: _dt.datetime) -> float | None:
    s = job.get("scraped_at")
    if not s:
        return None
    try:
        t = _dt.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=_dt.timezone.utc)
    return (now - t).total_seconds() / 86400.0


def auto_maintain(jobs: list[dict]) -> tuple[list[dict], list[dict]]:
    """Return ``(kept, dropped)``.

    Drop order (first match wins):
      * rejected     — status_auto or status_manual is "Rejected"
      * stale        — scraped_at older than ``MAX_AGE_DAYS``
      * irrelevant   — title not DS, senior role, or >2y experience

    Rows whose ``id`` starts with ``manual-`` are exempt from staleness and
    relevance — the user added them deliberately.
    """
    now = _dt.datetime.now(_dt.timezone.utc)
    kept: list[dict] = []
    dropped: list[dict] = []
    for j in jobs:
        if not isinstance(j, dict):
            continue
        status_m = (j.get("status_manual") or "").strip().lower()
        status_a = (j.get("status_auto") or "").strip().lower()
        if status_m == "rejected" or status_a == "rejected":
            dropped.append({**j, "_drop_reason": "rejected"})
            continue
        manual = str(j.get("id", "")).startswith("manual-")
        if not manual:
            age = _scraped_age_days(j, now)
            if age is not None and age > MAX_AGE_DAYS:
                dropped.append({**j, "_drop_reason": f"stale ({age:.0f}d)"})
                continue
            keep, why = is_relevant(j)
            if not keep:
                dropped.append({**j, "_drop_reason": f"irrelevant: {why}"})
                continue
        kept.append(j)
    return kept, dropped


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Job Applications Tracker</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
  :root {
    --bg: #0b0f15;
    --surface: #161c25;
    --surface-2: #1f2733;
    --border: #2d3745;
    --border-soft: #232b36;
    --text: #e6edf3;
    --text-dim: #8b96a3;
    --accent: #4a9eff;
    --accent-dim: #2a5a99;
    --green: #3fb950;
    --yellow: #d29922;
    --red: #f85149;
    --purple: #a371f7;
    --orange: #f78166;
    --shadow: 0 1px 0 rgba(255,255,255,0.03) inset, 0 6px 18px rgba(0,0,0,0.35);
  }
  body {
    background:
      radial-gradient(1100px 600px at 90% -10%, rgba(74,158,255,0.07), transparent 60%),
      radial-gradient(900px 500px at -10% 110%, rgba(163,113,247,0.06), transparent 60%),
      var(--bg);
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.5;
    padding: 20px;
  }
  header {
    max-width: 1400px;
    margin: 0 auto 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 12px;
  }
  h1 { font-size: 22px; font-weight: 600; }
  .stats { display: flex; gap: 16px; font-size: 13px; color: var(--text-dim); }
  .stats b { color: var(--text); }
  .controls {
    max-width: 1400px;
    margin: 0 auto 16px;
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    align-items: center;
  }
  .controls input, .controls select, .controls button {
    background: var(--surface);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
    font-family: inherit;
  }
  .controls input { flex: 1; min-width: 240px; }
  .controls input:focus, .controls select:focus { outline: none; border-color: var(--accent); }
  .controls button { cursor: pointer; transition: background 0.15s; }
  .controls button:hover { background: var(--surface-2); }
  .controls button.primary { background: var(--accent-dim); border-color: var(--accent); }
  .controls button.primary:hover { background: var(--accent); }
  .view-toggle {
    display: flex;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 6px;
    overflow: hidden;
  }
  .view-toggle button { border: none; border-radius: 0; background: transparent; }
  .view-toggle button.active { background: var(--accent-dim); }
  .grid {
    max-width: 1400px;
    margin: 0 auto;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
    gap: 14px;
  }
  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 14px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    transition: border-color 0.15s;
    position: relative;
  }
  .card.interested { border-color: var(--green); }
  .card.not-interested { opacity: 0.55; }
  .card-head { display: flex; justify-content: space-between; gap: 10px; align-items: flex-start; }
  .card-title { font-weight: 600; font-size: 15px; }
  .card-company { color: var(--text-dim); font-size: 13px; margin-top: 2px; }
  .badge {
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 10px;
    background: var(--surface-2);
    color: var(--text-dim);
    border: 1px solid var(--border);
    white-space: nowrap;
  }
  .badge.linkedin { border-color: #0a66c2; color: #4a9eff; }
  .badge.drushim { border-color: var(--orange); color: var(--orange); }
  .badge.alljobs { border-color: var(--purple); color: var(--purple); }
  .badge.comeet { border-color: var(--green); color: var(--green); }
  .meta { display: flex; flex-wrap: wrap; gap: 6px; font-size: 12px; color: var(--text-dim); }
  .email-info {
    font-size: 12px;
    background: var(--surface-2);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 5px 8px;
    display: flex;
    gap: 6px;
    align-items: center;
    flex-wrap: wrap;
  }
  .email-info a { color: var(--accent); text-decoration: none; }
  .email-info a:hover { text-decoration: underline; }
  .email-info.interview { border-color: var(--purple); }
  .email-info.offer { border-color: var(--green); }
  .email-info.rejected { border-color: var(--red); }
  .row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
  .row label { font-size: 12px; color: var(--text-dim); }
  select.status {
    background: var(--surface-2);
    border: 1px solid var(--border);
    color: var(--text);
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
    font-family: inherit;
  }
  select.status.new { border-color: var(--accent); }
  select.status.auto-applied { border-color: var(--yellow); border-style: dashed; }
  select.status.applied { border-color: var(--yellow); }
  select.status.manual-review { border-color: var(--orange); }
  select.status.interview { border-color: var(--purple); }
  select.status.offer { border-color: var(--green); }
  select.status.rejected { border-color: var(--red); }
  select.status.archived { border-color: var(--text-dim); }
  .status-mode {
    font-size: 10px;
    padding: 1px 5px;
    border-radius: 3px;
    color: var(--text-dim);
    background: var(--surface-2);
    border: 1px solid var(--border);
    text-transform: uppercase;
    letter-spacing: 0.4px;
  }
  .status-mode.manual { color: var(--yellow); border-color: var(--yellow); }
  .status-mode.auto { color: var(--accent); border-color: var(--accent); }
  .interest { display: flex; gap: 4px; }
  .interest button {
    background: var(--surface-2);
    border: 1px solid var(--border);
    color: var(--text-dim);
    border-radius: 4px;
    padding: 3px 10px;
    font-size: 12px;
    cursor: pointer;
    font-family: inherit;
  }
  .interest button.yes.active { background: var(--green); color: #000; border-color: var(--green); }
  .interest button.no.active { background: var(--red); color: #fff; border-color: var(--red); }
  .link-btn {
    font-size: 12px;
    color: var(--accent);
    text-decoration: none;
    padding: 3px 8px;
    border: 1px solid var(--accent-dim);
    border-radius: 4px;
  }
  .link-btn:hover { background: var(--accent-dim); }
  .delete-btn {
    font-size: 11px;
    color: var(--red);
    background: transparent;
    border: 1px solid var(--red);
    border-radius: 4px;
    padding: 3px 8px;
    cursor: pointer;
    font-family: inherit;
    margin-left: auto;
  }
  .delete-btn:hover { background: var(--red); color: #fff; }
  .restore-btn {
    font-size: 11px;
    color: var(--accent);
    background: transparent;
    border: 1px solid var(--accent);
    border-radius: 4px;
    padding: 3px 8px;
    cursor: pointer;
    font-family: inherit;
    margin-left: auto;
  }
  .restore-btn:hover { background: var(--accent); color: #fff; }
  .card.deleted, tr.deleted { opacity: 0.55; }
  .card.deleted .card-title, tr.deleted td:nth-child(2) { text-decoration: line-through; }
  .deleted-badge {
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--red);
    border: 1px solid var(--red);
    border-radius: 3px;
    padding: 1px 5px;
    margin-left: 6px;
    vertical-align: middle;
  }
  textarea.notes {
    width: 100%;
    background: var(--surface-2);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 6px 8px;
    font-size: 12px;
    font-family: inherit;
    resize: vertical;
    min-height: 32px;
  }
  details.details {
    font-size: 12px;
    color: var(--text-dim);
    border-top: 1px solid var(--border);
    padding-top: 8px;
  }
  details.details summary {
    cursor: pointer;
    color: var(--accent);
    font-weight: 500;
    user-select: none;
  }
  details.details summary:hover { color: #6eb0ff; }
  details.details h4 {
    margin-top: 10px;
    font-size: 12px;
    color: var(--text);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  details.details ul { margin-top: 4px; padding-left: 18px; }
  details.details li { margin-top: 3px; }
  table.table-view {
    width: 100%;
    max-width: 1400px;
    margin: 0 auto;
    border-collapse: collapse;
    font-size: 13px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    overflow: hidden;
  }
  table.table-view th, table.table-view td {
    padding: 8px 10px;
    text-align: left;
    border-bottom: 1px solid var(--border);
  }
  table.table-view th {
    background: var(--surface-2);
    font-weight: 600;
    color: var(--text-dim);
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  table.table-view tr:last-child td { border-bottom: none; }
  table.table-view tr:hover { background: var(--surface-2); }
  table.table-view select.status { padding: 3px 6px; }
  .file-status {
    font-size: 12px;
    padding: 4px 10px;
    border-radius: 4px;
    border: 1px solid var(--border);
    background: var(--surface);
  }
  .file-status.not-linked { color: var(--text-dim); }
  .file-status.linked { color: var(--green); border-color: var(--green); }
  .file-status.saving { color: var(--yellow); border-color: var(--yellow); }
  .file-status.error { color: var(--red); border-color: var(--red); }
  .file-status.unsupported { color: var(--orange); border-color: var(--orange); }
  .hidden { display: none !important; }
  .empty {
    max-width: 1400px;
    margin: 40px auto;
    text-align: center;
    color: var(--text-dim);
    font-size: 14px;
  }
  .build-time {
    font-size: 11px;
    color: var(--text-dim);
    margin-left: 8px;
  }
  .edit-btn {
    font-size: 11px;
    color: var(--accent);
    background: transparent;
    border: 1px solid var(--accent-dim);
    border-radius: 4px;
    padding: 3px 8px;
    cursor: pointer;
    font-family: inherit;
  }
  .edit-btn:hover { background: var(--accent-dim); color: #fff; }
  .phone-line { font-size: 12px; color: var(--text-dim); }
  .phone-line a { color: var(--accent); text-decoration: none; }
  .phone-line a:hover { text-decoration: underline; }
  .overridden { border-color: var(--yellow) !important; }
  .modal-backdrop {
    position: fixed; inset: 0;
    background: rgba(0,0,0,0.6);
    display: none;
    align-items: flex-start;
    justify-content: center;
    z-index: 1000;
    padding: 40px 16px;
    overflow-y: auto;
  }
  .modal-backdrop.open { display: flex; }
  .modal {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 18px;
    max-width: 680px;
    width: 100%;
    max-height: calc(100vh - 80px);
    overflow-y: auto;
  }
  .modal h2 { font-size: 16px; margin-bottom: 12px; color: var(--text); }
  .modal .field { margin-bottom: 12px; }
  .modal label {
    display: block;
    font-size: 11px;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.4px;
    margin-bottom: 4px;
  }
  .modal input, .modal textarea, .modal select {
    width: 100%;
    background: var(--surface-2);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 6px 8px;
    font-size: 13px;
    font-family: inherit;
  }
  .modal textarea { resize: vertical; min-height: 60px; }
  .modal input:focus, .modal textarea:focus, .modal select:focus {
    outline: none; border-color: var(--accent);
  }
  .modal .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
  .modal .actions {
    display: flex; gap: 8px; justify-content: flex-end; margin-top: 16px;
  }
  .modal .actions button {
    background: var(--surface-2);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 7px 14px;
    font-size: 13px;
    cursor: pointer;
    font-family: inherit;
  }
  .modal .actions button.primary {
    background: var(--accent-dim);
    border-color: var(--accent);
  }
  .modal .actions button.primary:hover { background: var(--accent); }
  .modal .hint { font-size: 11px; color: var(--text-dim); margin-top: 4px; }
  .modal .danger {
    margin-right: auto;
    color: var(--red) !important;
    border-color: var(--red) !important;
  }
  .modal .danger:hover { background: var(--red); color: #fff !important; }

  /* --- Chart card (applications over time) ---------------------------- */
  .chart-card {
    max-width: 1400px;
    margin: 0 auto 18px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 14px 16px 6px;
    box-shadow: var(--shadow);
  }
  .chart-head {
    display: flex; justify-content: space-between; align-items: center;
    flex-wrap: wrap; gap: 10px; margin-bottom: 6px;
  }
  .chart-head h2 {
    font-size: 14px; font-weight: 600; color: var(--text-dim);
    text-transform: uppercase; letter-spacing: 0.6px;
  }
  .chart-head .legend {
    font-size: 12px; color: var(--text-dim);
  }
  .chart-head .legend b { color: var(--text); }
  .chart-wrap { position: relative; height: 220px; }
  .bucket-toggle {
    display: inline-flex;
    background: var(--surface-2);
    border: 1px solid var(--border);
    border-radius: 6px;
    overflow: hidden;
  }
  .bucket-toggle button {
    background: transparent; border: none; color: var(--text-dim);
    padding: 5px 12px; font-size: 12px; cursor: pointer; font-family: inherit;
    letter-spacing: 0.4px;
  }
  .bucket-toggle button.active { background: var(--accent-dim); color: #fff; }

  /* --- Date-range filter --------------------------------------------- */
  .date-range {
    display: inline-flex; align-items: center; gap: 6px;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 6px; padding: 4px 8px;
  }
  .date-range label {
    font-size: 11px; color: var(--text-dim); text-transform: uppercase;
    letter-spacing: 0.4px;
  }
  .date-range input[type="date"] {
    background: transparent; border: none; color: var(--text);
    font-size: 12px; padding: 2px 0; font-family: inherit; width: 130px;
  }
  .date-range input[type="date"]::-webkit-calendar-picker-indicator {
    filter: invert(0.7);
  }
  .date-range button.clear {
    background: transparent; border: none; color: var(--text-dim);
    cursor: pointer; font-size: 14px; padding: 0 4px; line-height: 1;
  }
  .date-range button.clear:hover { color: var(--red); }

  /* --- Bulk-action toolbar (select-all + delete-selected) ------------ */
  .bulk-bar {
    max-width: 1400px; margin: 0 auto 10px;
    display: flex; align-items: center; gap: 12px;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 6px; padding: 6px 12px;
    font-size: 13px; color: var(--text-dim);
  }
  .bulk-bar.has-selection {
    border-color: var(--accent); background: rgba(74,158,255,0.06);
  }
  .bulk-bar input[type="checkbox"] {
    width: 16px; height: 16px; accent-color: var(--accent); cursor: pointer;
  }
  .bulk-bar button {
    background: var(--surface-2); border: 1px solid var(--border);
    color: var(--text); padding: 5px 12px; border-radius: 4px;
    font-size: 12px; cursor: pointer; font-family: inherit;
  }
  .bulk-bar button:disabled { opacity: 0.4; cursor: not-allowed; }
  .bulk-bar button.danger { color: var(--red); border-color: var(--red); }
  .bulk-bar button.danger:hover:not(:disabled) { background: var(--red); color: #fff; }
  .bulk-bar .count b { color: var(--text); }

  /* --- Per-row select checkbox -------------------------------------- */
  .row-check {
    position: absolute; top: 10px; left: 10px;
    width: 16px; height: 16px; accent-color: var(--accent); cursor: pointer;
    z-index: 2;
  }
  .card.has-check { padding-left: 32px; }
  .card.selected { outline: 2px solid var(--accent); }
  tr.selected td { background: rgba(74,158,255,0.08); }
  table.table-view th.check-col, table.table-view td.check-col { width: 30px; }

  /* Polish: cards lift on hover, header weight, better card title */
  .card { box-shadow: var(--shadow); transition: border-color 0.15s, transform 0.15s; }
  .card:hover { border-color: var(--border); transform: translateY(-1px); }
  .card-title { line-height: 1.3; }
  h1 { font-weight: 700; letter-spacing: -0.2px; }
  .stats { font-size: 12px; }

  @media (max-width: 720px) {
    body { padding: 12px; }
    .controls input { min-width: 100%; }
    .grid { grid-template-columns: 1fr; }
    .chart-wrap { height: 180px; }
  }
</style>
</head>
<body>

<header>
  <div>
    <h1>Job Applications <span class="build-time">built __BUILD_TIME__</span></h1>
    <div class="stats" id="stats"></div>
  </div>
  <div class="controls">
    <div class="view-toggle">
      <button id="view-cards" class="active">Cards</button>
      <button id="view-table">Table</button>
    </div>
    <button id="add-btn" class="primary">+ New job</button>
    <button id="link-btn" class="primary">Link folder…</button>
    <button id="import-btn">Import JSON</button>
    <button id="export-btn">Export JSON</button>
    <button id="reset-btn">Reset state</button>
    <input type="file" id="import-input" accept=".json,application/json" style="display:none">
  </div>
</header>
<div class="controls" style="max-width:1400px;margin:-6px auto 10px;">
  <span id="file-status" class="file-status not-linked">Not linked — edits save only to this browser. Click "Link folder…" to persist into jobs.json.</span>
</div>

<div class="chart-card">
  <div class="chart-head">
    <h2>Applications over time</h2>
    <div class="bucket-toggle" role="tablist" aria-label="Bucket size">
      <button data-bucket="day" class="active">Day</button>
      <button data-bucket="week">Week</button>
      <button data-bucket="month">Month</button>
    </div>
    <div class="legend">total in range: <b id="chart-total">0</b></div>
  </div>
  <div class="chart-wrap"><canvas id="apply-chart"></canvas></div>
</div>

<div class="controls">
  <input id="search" placeholder="Search company, position, location, requirements…">
  <select id="filter-source">
    <option value="">All sources</option>
  </select>
  <select id="filter-status">
    <option value="">All statuses</option>
    <option value="New">New</option>
    <option value="Auto-applied">Auto-applied</option>
    <option value="Applied">Applied</option>
    <option value="Manual review">Manual review</option>
    <option value="Interview">Interview</option>
    <option value="Offer">Offer</option>
    <option value="Rejected">Rejected</option>
    <option value="Archived">Archived</option>
  </select>
  <select id="filter-interest">
    <option value="">All</option>
    <option value="yes">Interested</option>
    <option value="no">Not interested</option>
    <option value="unset">No decision</option>
  </select>
  <select id="filter-deleted" title="Show deleted jobs">
    <option value="active" selected>Active only</option>
    <option value="deleted">Deleted only</option>
    <option value="all">Active + deleted</option>
  </select>
  <select id="sort">
    <option value="date-desc">Newest first</option>
    <option value="date-asc">Oldest first</option>
    <option value="scraped-desc">Recently scraped</option>
    <option value="company">Company A-Z</option>
    <option value="status">Status</option>
  </select>
  <div class="date-range" title="Filter by scrape date">
    <label for="date-from">From</label>
    <input id="date-from" type="date">
    <label for="date-to">To</label>
    <input id="date-to" type="date">
    <button class="clear" id="date-clear" title="Clear date range">×</button>
  </div>
</div>

<div class="bulk-bar" id="bulk-bar">
  <input type="checkbox" id="select-all" title="Select all visible jobs">
  <label for="select-all" style="cursor:pointer">Select all visible</label>
  <span class="count">Selected: <b id="select-count">0</b></span>
  <button id="delete-selected" class="danger" disabled>Delete selected</button>
  <button id="clear-selection" disabled>Clear</button>
</div>

<div id="grid" class="grid"></div>
<table id="table" class="table-view hidden">
  <thead>
    <tr>
      <th class="check-col"></th>
      <th>Company</th><th>Position</th><th>Location</th><th>Source</th>
      <th>Status</th><th>Last email</th><th>Interest</th><th>Link</th><th>Notes</th><th></th>
    </tr>
  </thead>
  <tbody></tbody>
</table>
<div id="empty" class="empty hidden">No jobs match your filters.</div>

<div id="modal-backdrop" class="modal-backdrop">
  <div class="modal" role="dialog" aria-modal="true">
    <h2 id="modal-title">Edit job</h2>
    <div class="grid-2">
      <div class="field"><label>Position</label><input id="m-position" type="text"></div>
      <div class="field"><label>Company</label><input id="m-company" type="text"></div>
    </div>
    <div class="grid-2">
      <div class="field"><label>Source</label><input id="m-source" type="text" placeholder="LinkedIn / AllJobs / Drushim / Manual / …"></div>
      <div class="field"><label>Location</label><input id="m-location" type="text"></div>
    </div>
    <div class="field"><label>Link</label><input id="m-link" type="url" placeholder="https://…"></div>
    <div class="field"><label>Recruiter phone number</label><input id="m-phone" type="tel" placeholder="e.g. +972 50-123-4567"></div>
    <div class="field"><label>Description (free-form prose)</label><textarea id="m-description" rows="4"></textarea></div>
    <div class="field"><label>Requirements (one per line)</label><textarea id="m-requirements" rows="5"></textarea></div>
    <div class="field"><label>Responsibilities (one per line)</label><textarea id="m-responsibilities" rows="3"></textarea></div>
    <div class="field"><label>Nice to have (one per line)</label><textarea id="m-nice" rows="2"></textarea></div>
    <div class="field"><label>Notes</label><textarea id="m-notes" rows="2"></textarea></div>
    <div class="hint" id="m-hint"></div>
    <div class="actions">
      <button id="m-delete" class="danger">Delete</button>
      <button id="m-cancel">Cancel</button>
      <button id="m-save" class="primary">Save</button>
    </div>
  </div>
</div>

<script>
const JOBS = __JOBS_JSON__;
const STORAGE_KEY = 'job_tracker_state_v2';
const STATUS_OPTS = ['New','Auto-applied','Applied','Manual review','Interview','Offer','Rejected','Archived'];

// Slug for CSS class — replaces whitespace with hyphens so multi-word
// values like "Manual review" don't split into two class tokens.
function statusClass(s) { return (s || '').toLowerCase().replace(/\s+/g, '-'); }

// Map Gmail-classification terms to our status dropdown values.
const EMAIL_TO_STATUS = {
  Auto_ack: 'Applied',
  Applied: 'Applied',
  Interview: 'Interview',
  Offer: 'Offer',
  Rejected: 'Rejected',
};

// Everything lives in a single jobs.json. Each JOBS[i] carries:
//   scraper-owned:  id, position, company, source, link, scraped_at, location, date,
//                   description, responsibilities, requirements, nice_to_have
//   Gmail-owned:    last_email, status_auto
//   user-owned:     status_manual, interested, notes, recruiter_phone
//
// In addition, the user can override scraper-owned fields per entry from the
// Edit dialog. Those overrides land in state[id].overrides = { ... } and are
// also written to jobs.json on save. The scraper will not overwrite a
// non-empty field, so user edits survive future scraper runs.
//
// `state` is an in-memory view of user-owned fields + overrides, keyed by id.
// Persisted into jobs.json via field-scoped read-modify-write — scraper and
// Gmail writes on untouched fields are preserved.
const SCRAPER_OVERRIDABLE = [
  'position','company','source','link','location','date',
  'description','responsibilities','requirements','nice_to_have'
];
let state = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
// Migrate v1 state if found (keys: status, interested, notes)
const v1 = JSON.parse(localStorage.getItem('job_tracker_state_v1') || 'null');
if (v1 && Object.keys(state).length === 0) {
  for (const [id, s] of Object.entries(v1)) {
    state[id] = {
      status_manual: s.status && s.status !== 'New' ? s.status : null,
      interested: s.interested ?? null,
      notes: s.notes || '',
      recruiter_phone: '',
      overrides: {},
    };
  }
}
function hydrateFromDisk(arr) {
  for (const j of arr) {
    if (!j?.id || state[j.id]) continue;
    const hasUser = j.status_manual != null || j.interested != null
                 || (j.notes && j.notes !== '') || (j.recruiter_phone && j.recruiter_phone !== '');
    if (hasUser) {
      state[j.id] = {
        status_manual: j.status_manual ?? null,
        interested: j.interested ?? null,
        notes: j.notes || '',
        recruiter_phone: j.recruiter_phone || '',
        overrides: {},
      };
    }
  }
}
hydrateFromDisk(JOBS);
let saveState = () => localStorage.setItem(STORAGE_KEY, JSON.stringify(state));

// Bulk selection set — ids currently checked. Lives in-memory only.
const selectedIds = new Set();
// Bucket size for the applications-over-time chart.
let chartBucket = 'day';
// Currently visible ids after applyFilters() — used by select-all and chart.
let visibleIds = [];

function getS(id) {
  if (!state[id]) state[id] = {
    status_manual: null, interested: null, notes: '',
    recruiter_phone: '', overrides: {},
  };
  if (!state[id].overrides) state[id].overrides = {};
  if (state[id].recruiter_phone == null) state[id].recruiter_phone = '';
  return state[id];
}
function getJ(id) {
  return JOBS.find(j => j.id === id);
}
// Returns the merged, user-effective view of a job: scraper fields with any
// user overrides applied, plus user-owned fields like recruiter_phone.
function effectiveJob(id) {
  const j = getJ(id) || {};
  const s = state[id] || {};
  return { ...j, ...(s.overrides || {}), recruiter_phone: s.recruiter_phone || '' };
}
// Has the user overridden this scraper-owned field?
function isOverridden(id, field) {
  return Object.prototype.hasOwnProperty.call(state[id]?.overrides || {}, field);
}

function effectiveStatus(id) {
  const s = getS(id);
  if (s.status_manual) return s.status_manual;
  const j = getJ(id);
  if (j?.status_auto) return j.status_auto;
  const cls = j?.last_email?.classification;
  if (cls && EMAIL_TO_STATUS[cls]) return EMAIL_TO_STATUS[cls];
  return 'New';
}
function statusMode(id) {
  const s = getS(id);
  if (s.status_manual) return 'manual';
  const j = getJ(id);
  if (j?.status_auto || j?.last_email?.classification) return 'auto';
  return 'default';
}

const $ = (id) => document.getElementById(id);
const grid = $('grid');
const tbody = $('table').querySelector('tbody');

const sources = [...new Set(JOBS.map(j => j.source).filter(Boolean))].sort();
for (const s of sources) {
  const o = document.createElement('option');
  o.value = s; o.textContent = s;
  $('filter-source').appendChild(o);
}

function escapeHtml(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function shortDate(iso) {
  if (!iso) return '';
  // Accept YYYY-MM-DD or full ISO; return YYYY-MM-DD
  return String(iso).slice(0, 10);
}

function statusSelectHtml(id) {
  const eff = effectiveStatus(id);
  const mode = statusMode(id);
  const opts = [
    (() => {
      const em = getJ(id)?.last_email;
      const cls = em?.classification || null;
      let label;
      if (mode === 'auto' && cls) {
        // Gmail-derived: show classification + status
        label = `— Gmail (${cls}) → ${eff} —`;
      } else if (mode === 'auto') {
        // status_auto present without classification (rare)
        label = `— Auto: ${eff} —`;
      } else {
        // No email yet — be explicit instead of "Auto (from email)"
        label = '— No email yet —';
      }
      return `<option value="__auto" ${mode==='auto'?'selected':''}>${label}</option>`;
    })(),
    ...STATUS_OPTS.map(o => `<option value="${o}" ${o===eff && mode!=='auto'?'selected':''}>${o}</option>`)
  ];
  return `
    <select class="status ${statusClass(eff)}" data-field="status">
      ${opts.join('')}
    </select>
    <span class="status-mode ${mode}" title="${
      mode==='manual' ? 'You set this manually' :
      mode==='auto' ? 'Derived from last email' : 'Default (no email, no manual)'}">${
      mode==='manual' ? 'manual' : mode==='auto' ? 'auto' : '—'}</span>
  `;
}

function emailInfoHtml(id) {
  const e = getJ(id)?.last_email;
  if (!e) return '';
  const cls = (e.classification || '').toLowerCase();
  return `
    <div class="email-info ${cls}">
      <span>📧 <b>${escapeHtml(e.classification || '?')}</b></span>
      ${e.date ? `<span>· ${escapeHtml(shortDate(e.date))}</span>` : ''}
      ${e.subject ? `<span style="color:var(--text-dim);overflow:hidden;text-overflow:ellipsis;max-width:180px;white-space:nowrap" title="${escapeHtml(e.subject)}">${escapeHtml(e.subject)}</span>` : ''}
      ${e.thread_link ? `<a href="${escapeHtml(e.thread_link)}" target="_blank" rel="noopener">Open thread ↗</a>` : ''}
    </div>`;
}

function cardHtml(jobBase) {
  const id = jobBase.id;
  const s = getS(id);
  const job = effectiveJob(id);
  const interestClass = s.interested === 'yes' ? 'interested' : s.interested === 'no' ? 'not-interested' : '';
  const sourceClass = (job.source || '').toLowerCase().replace(/\s+/g,'-');
  const phone = (job.recruiter_phone || '').trim();
  const deletedClass = job.deleted ? 'deleted' : '';
  const deletedBadge = job.deleted ? '<span class="deleted-badge">deleted</span>' : '';
  const actionBtn = job.deleted
    ? '<button class="restore-btn" data-action="restore" title="Restore this position">Restore</button>'
    : '<button class="delete-btn" data-action="delete" title="Delete this position from jobs.json">Delete</button>';
  const selected = selectedIds.has(id) ? 'selected' : '';
  const checked = selectedIds.has(id) ? 'checked' : '';
  return `
    <div class="card has-check ${interestClass} ${deletedClass} ${selected}" data-id="${id}">
      <input type="checkbox" class="row-check" data-rowcheck="${id}" ${checked} title="Select for bulk actions">
      <div class="card-head">
        <div>
          <div class="card-title">${escapeHtml(job.position || '(no position)')}${deletedBadge}</div>
          <div class="card-company">${escapeHtml(job.company || '(no company)')}</div>
        </div>
        <span class="badge ${sourceClass}">${escapeHtml(job.source || '—')}</span>
      </div>
      <div class="meta">
        ${job.location ? `<span>📍 ${escapeHtml(job.location)}</span>` : ''}
        ${job.date ? `<span>• posted ${escapeHtml(shortDate(job.date))}</span>` : ''}
        ${job.scraped_at ? `<span>• added ${escapeHtml(shortDate(job.scraped_at))}</span>` : ''}
      </div>
      ${phone ? `<div class="phone-line">📞 <a href="tel:${escapeHtml(phone)}">${escapeHtml(phone)}</a></div>` : ''}
      ${emailInfoHtml(id)}
      <div class="row">
        <label>Status:</label>
        ${statusSelectHtml(id)}
        <div class="interest">
          <button class="yes ${s.interested==='yes'?'active':''}" data-interest="yes">👍</button>
          <button class="no ${s.interested==='no'?'active':''}" data-interest="no">👎</button>
        </div>
        ${job.link ? `<a class="link-btn" href="${escapeHtml(job.link)}" target="_blank" rel="noopener">Open ↗</a>` : ''}
        <button class="edit-btn" data-action="edit" title="Edit fields">Edit</button>
        ${actionBtn}
      </div>
      <textarea class="notes" data-field="notes" placeholder="Notes…">${escapeHtml(s.notes)}</textarea>
      <details class="details">
        <summary>Show description, requirements & responsibilities</summary>
        ${job.description ? `<h4>Description</h4><p style="margin-top:4px;white-space:pre-wrap">${escapeHtml(job.description)}</p>` : ''}
        ${job.responsibilities?.length ? `<h4>Responsibilities</h4><ul>${job.responsibilities.map(r=>`<li>${escapeHtml(r)}</li>`).join('')}</ul>` : ''}
        ${job.requirements?.length ? `<h4>Requirements</h4><ul>${job.requirements.map(r=>`<li>${escapeHtml(r)}</li>`).join('')}</ul>` : ''}
        ${job.nice_to_have?.length ? `<h4>Nice to have</h4><ul>${job.nice_to_have.map(r=>`<li>${escapeHtml(r)}</li>`).join('')}</ul>` : ''}
      </details>
    </div>`;
}

function rowHtml(jobBase) {
  const id = jobBase.id;
  const s = getS(id);
  const job = effectiveJob(id);
  const e = job.last_email;
  const sourceClass = (job.source || '').toLowerCase().replace(/\s+/g,'-');
  const deletedClass = job.deleted ? 'deleted' : '';
  const actionBtn = job.deleted
    ? '<button class="restore-btn" data-action="restore">Restore</button>'
    : '<button class="delete-btn" data-action="delete">Delete</button>';
  const selected = selectedIds.has(id) ? 'selected' : '';
  const checked = selectedIds.has(id) ? 'checked' : '';
  return `
    <tr class="${deletedClass} ${selected}" data-id="${id}">
      <td class="check-col"><input type="checkbox" data-rowcheck="${id}" ${checked}></td>
      <td>${escapeHtml(job.company || '')}</td>
      <td>${escapeHtml(job.position || '')}</td>
      <td>${escapeHtml(job.location || '')}</td>
      <td><span class="badge ${sourceClass}">${escapeHtml(job.source || '—')}</span></td>
      <td>${statusSelectHtml(id)}</td>
      <td>${e ? `<a href="${escapeHtml(e.thread_link||'#')}" target="_blank" rel="noopener" title="${escapeHtml(e.subject||'')}">${escapeHtml(e.classification)} · ${escapeHtml(shortDate(e.date))}</a>` : '—'}</td>
      <td>
        <div class="interest">
          <button class="yes ${s.interested==='yes'?'active':''}" data-interest="yes">👍</button>
          <button class="no ${s.interested==='no'?'active':''}" data-interest="no">👎</button>
        </div>
      </td>
      <td>${job.link ? `<a class="link-btn" href="${escapeHtml(job.link)}" target="_blank" rel="noopener">↗</a>` : ''}</td>
      <td><textarea class="notes" data-field="notes" rows="1" placeholder="Notes…">${escapeHtml(s.notes)}</textarea></td>
      <td><button class="edit-btn" data-action="edit">Edit</button> ${actionBtn}</td>
    </tr>`;
}

function applyFilters() {
  const q = $('search').value.trim().toLowerCase();
  const src = $('filter-source').value;
  const stat = $('filter-status').value;
  const interest = $('filter-interest').value;
  const sort = $('sort').value;
  const dateFrom = $('date-from').value;  // YYYY-MM-DD or ''
  const dateTo   = $('date-to').value;

  function jobYmd(j) {
    // Prefer the posting date if known; fall back to scrape date.
    return (j.date || j.scraped_at || '').slice(0, 10);
  }

  const delMode = $('filter-deleted').value;
  let list = JOBS.map(j => effectiveJob(j.id)).filter(j => {
    const s = getS(j.id);
    if (delMode === 'active' && j.deleted) return false;
    if (delMode === 'deleted' && !j.deleted) return false;
    // delMode === 'all' → no filtering on deleted
    if (src && j.source !== src) return false;
    if (stat && effectiveStatus(j.id) !== stat) return false;
    if (interest === 'yes' && s.interested !== 'yes') return false;
    if (interest === 'no' && s.interested !== 'no') return false;
    if (interest === 'unset' && s.interested !== null) return false;
    const ymd = jobYmd(j);
    if (dateFrom && ymd && ymd < dateFrom) return false;
    if (dateTo   && ymd && ymd > dateTo)   return false;
    if (dateFrom && !ymd) return false;   // unknown date with active filter → hide
    if (dateTo   && !ymd) return false;
    if (q) {
      const hay = [j.company, j.position, j.location, j.source, j.recruiter_phone, j.description,
        ...(j.responsibilities||[]), ...(j.requirements||[]), ...(j.nice_to_have||[]),
        s.notes].join(' ').toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });

  list.sort((a,b) => {
    if (sort === 'date-desc') return (b.date||'').localeCompare(a.date||'');
    if (sort === 'date-asc') return (a.date||'').localeCompare(b.date||'');
    if (sort === 'scraped-desc') return (b.scraped_at||'').localeCompare(a.scraped_at||'');
    if (sort === 'company') return (a.company||'').localeCompare(b.company||'');
    if (sort === 'status') return effectiveStatus(a.id).localeCompare(effectiveStatus(b.id));
    return 0;
  });

  // Refresh source dropdown options from effective sources (keeps user-set ones).
  const cur = $('filter-source').value;
  const fresh = [...new Set(JOBS.map(j => effectiveJob(j.id).source).filter(Boolean))].sort();
  const dd = $('filter-source');
  dd.innerHTML = '<option value="">All sources</option>' +
    fresh.map(s => `<option value="${escapeHtml(s)}" ${s===cur?'selected':''}>${escapeHtml(s)}</option>`).join('');

  grid.innerHTML = list.map(cardHtml).join('');
  tbody.innerHTML = list.map(rowHtml).join('');
  $('empty').classList.toggle('hidden', list.length > 0);
  visibleIds = list.map(j => j.id);
  // Prune selectedIds to only ids that are still visible — invisible
  // selections would be confusing for the "delete selected" action.
  for (const id of [...selectedIds]) if (!visibleIds.includes(id)) selectedIds.delete(id);
  refreshBulkBar();
  updateStats();
  drawChart();
}

function updateStats() {
  const live = JOBS.filter(j => !j.deleted);
  const total = live.length;
  const c = { New:0, Applied:0, Interview:0, Offer:0, Rejected:0, Archived:0 };
  let yes = 0, no = 0;
  for (const j of live) {
    const s = getS(j.id);
    const eff = effectiveStatus(j.id);
    if (c[eff] !== undefined) c[eff]++;
    if (s.interested === 'yes') yes++;
    if (s.interested === 'no') no++;
  }
  $('stats').innerHTML = `
    <span><b>${total}</b> total</span>
    <span><b>${c.New}</b> new</span>
    <span><b>${c.Applied}</b> applied</span>
    <span><b>${c.Interview}</b> interviewing</span>
    <span><b>${c.Offer}</b> offer</span>
    <span>👍 <b>${yes}</b> · 👎 <b>${no}</b></span>
  `;
}

// ---------- Bulk selection ----------
function refreshBulkBar() {
  const n = selectedIds.size;
  $('select-count').textContent = String(n);
  $('delete-selected').disabled = (n === 0);
  $('clear-selection').disabled = (n === 0);
  $('bulk-bar').classList.toggle('has-selection', n > 0);
  // Sync the master checkbox without firing 'change'.
  const master = $('select-all');
  const allChecked = visibleIds.length > 0 && visibleIds.every(id => selectedIds.has(id));
  master.checked = allChecked;
  master.indeterminate = !allChecked && n > 0;
}

$('select-all').addEventListener('change', e => {
  if (e.target.checked) for (const id of visibleIds) selectedIds.add(id);
  else selectedIds.clear();
  applyFilters();
});
$('clear-selection').addEventListener('click', () => {
  selectedIds.clear();
  applyFilters();
});
$('delete-selected').addEventListener('click', async () => {
  if (selectedIds.size === 0) return;
  const ids = [...selectedIds];
  const labels = ids.slice(0, 8)
    .map(id => { const j = JOBS.find(x => x.id === id); return j ? `• ${j.company} — ${j.position}` : `• ${id}`; })
    .join('\n');
  const more = ids.length > 8 ? `\n…and ${ids.length - 8} more` : '';
  if (!confirm(`Delete ${ids.length} selected job${ids.length === 1 ? '' : 's'}?\n\n${labels}${more}\n\nMarks each as deleted in jobs.json so the scraper won't re-add them.`)) return;
  for (const id of ids) await deletePosition(id, { skipConfirm: true });
  selectedIds.clear();
  applyFilters();
});

// ---------- Applications-over-time chart ----------
let chartInstance = null;
function applicationDates() {
  // An "application event" = job whose effective status moved past New.
  // We bucket by the most informative timestamp available, preferring
  // last_email.date (when the application was acknowledged/responded to),
  // then scraped_at, then date.
  const out = [];
  for (const j of JOBS) {
    if (j.deleted) continue;
    const eff = effectiveStatus(j.id);
    if (eff === 'New') continue;
    const when = j.last_email?.date || j.scraped_at || j.date;
    if (!when) continue;
    out.push(String(when).slice(0, 10));  // YYYY-MM-DD
  }
  return out;
}
function bucketKey(ymd, bucket) {
  if (bucket === 'day')   return ymd;
  if (bucket === 'week') {
    // ISO week start (Monday). Reasonable for Israeli work week too.
    const d = new Date(ymd + 'T00:00:00Z');
    const day = d.getUTCDay() || 7;  // Sun=0 → 7
    d.setUTCDate(d.getUTCDate() - (day - 1));
    return d.toISOString().slice(0, 10);
  }
  if (bucket === 'month') return ymd.slice(0, 7);  // YYYY-MM
  return ymd;
}
function buildSeries(bucket) {
  const dates = applicationDates();
  if (dates.length === 0) return { labels: [], data: [], total: 0 };
  const counts = new Map();
  for (const d of dates) {
    const k = bucketKey(d, bucket);
    counts.set(k, (counts.get(k) || 0) + 1);
  }
  // Fill missing buckets between earliest and latest so the chart line
  // doesn't lie about a gap.
  const sortedKeys = [...counts.keys()].sort();
  const labels = [];
  const data = [];
  let cur = sortedKeys[0];
  const last = sortedKeys[sortedKeys.length - 1];
  const safety = 1200;
  let i = 0;
  while (cur <= last && i < safety) {
    labels.push(cur);
    data.push(counts.get(cur) || 0);
    cur = nextBucket(cur, bucket);
    i++;
  }
  return { labels, data, total: dates.length };
}
function nextBucket(key, bucket) {
  if (bucket === 'day') {
    const d = new Date(key + 'T00:00:00Z');
    d.setUTCDate(d.getUTCDate() + 1);
    return d.toISOString().slice(0, 10);
  }
  if (bucket === 'week') {
    const d = new Date(key + 'T00:00:00Z');
    d.setUTCDate(d.getUTCDate() + 7);
    return d.toISOString().slice(0, 10);
  }
  if (bucket === 'month') {
    const [y, m] = key.split('-').map(Number);
    const d = new Date(Date.UTC(y, m - 1 + 1, 1));
    return d.toISOString().slice(0, 7);
  }
  return key;
}
function drawChart() {
  if (typeof Chart === 'undefined') return;  // Chart.js failed to load
  const { labels, data, total } = buildSeries(chartBucket);
  $('chart-total').textContent = String(total);
  const ctx = $('apply-chart').getContext('2d');
  if (chartInstance) chartInstance.destroy();
  chartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: `Applications / ${chartBucket}`,
        data,
        backgroundColor: 'rgba(74,158,255,0.45)',
        borderColor: 'rgba(74,158,255,1)',
        borderWidth: 1,
        borderRadius: 3,
      }],
    },
    options: {
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { mode: 'index', intersect: false },
      },
      scales: {
        x: { ticks: { color: '#8b96a3', maxRotation: 0, autoSkip: true }, grid: { color: '#232b36' } },
        y: { beginAtZero: true, ticks: { color: '#8b96a3', precision: 0 }, grid: { color: '#232b36' } },
      },
    },
  });
}
document.querySelectorAll('.bucket-toggle button').forEach(b => {
  b.addEventListener('click', () => {
    document.querySelectorAll('.bucket-toggle button').forEach(x => x.classList.remove('active'));
    b.classList.add('active');
    chartBucket = b.dataset.bucket;
    drawChart();
  });
});

// ---------- Date-range filter ----------
['date-from', 'date-to'].forEach(id => $(id).addEventListener('input', applyFilters));
$('date-clear').addEventListener('click', () => {
  $('date-from').value = ''; $('date-to').value = ''; applyFilters();
});

// ---------- Event delegation ----------
document.body.addEventListener('change', e => {
  // Row-level checkbox toggle (cards + table both use data-rowcheck).
  if (e.target.matches('[data-rowcheck]')) {
    const id = e.target.dataset.rowcheck;
    if (e.target.checked) selectedIds.add(id);
    else selectedIds.delete(id);
    // Update visual selected class without a full re-render.
    const row = e.target.closest('[data-id]');
    if (row) row.classList.toggle('selected', e.target.checked);
    refreshBulkBar();
    return;
  }
  const id = e.target.closest('[data-id]')?.dataset.id;
  if (!id) return;
  const field = e.target.dataset.field;
  if (field === 'status') {
    const v = e.target.value;
    if (v === '__auto') getS(id).status_manual = null;
    else getS(id).status_manual = v;
    saveState();
    applyFilters();
  } else if (field === 'notes') {
    getS(id).notes = e.target.value;
    saveState();
  }
});
document.body.addEventListener('input', e => {
  if (e.target.dataset.field === 'notes') {
    const id = e.target.closest('[data-id]')?.dataset.id;
    if (id) { getS(id).notes = e.target.value; saveState(); }
  }
});
document.body.addEventListener('click', e => {
  const card = e.target.closest('[data-id]');
  if (!card) return;
  const id = card.dataset.id;
  const iBtn = e.target.closest('[data-interest]');
  if (iBtn) {
    const v = iBtn.dataset.interest;
    const s = getS(id);
    s.interested = s.interested === v ? null : v;
    saveState();
    applyFilters();
    return;
  }
  if (e.target.closest('[data-action="delete"]')) {
    deletePosition(id);
    return;
  }
  if (e.target.closest('[data-action="restore"]')) {
    restorePosition(id);
    return;
  }
  if (e.target.closest('[data-action="edit"]')) {
    openEditModal(id);
  }
});

['search','filter-source','filter-status','filter-interest','filter-deleted','sort'].forEach(id =>
  $(id).addEventListener('input', applyFilters));

$('view-cards').addEventListener('click', () => {
  $('view-cards').classList.add('active');
  $('view-table').classList.remove('active');
  grid.classList.remove('hidden');
  $('table').classList.add('hidden');
});
$('view-table').addEventListener('click', () => {
  $('view-table').classList.add('active');
  $('view-cards').classList.remove('active');
  grid.classList.add('hidden');
  $('table').classList.remove('hidden');
});

// ---------- Folder-backed persistence (File System Access API) ----------
//
// We cache only the dirHandle (the folder). Every save/load re-acquires a
// fresh file handle via dirHandle.getFileHandle('jobs.json'). Caching the
// file handle across writes tripped Chrome's stale-state guard: after one
// write, a second write via the same cached handle errored with
// "state had changed since it was read from disk". Re-acquiring sidesteps
// that, and also handles the case where OneDrive or another process
// touches the file in the background.
const FSA_SUPPORTED = 'showDirectoryPicker' in window;
let dirHandle = null;
let saveTimer = null;

async function getJobsHandle({ createIfMissing = false } = {}) {
  if (!dirHandle) return null;
  return await dirHandle.getFileHandle('jobs.json', { create: createIfMissing });
}

function idbOpen() {
  return new Promise((resolve, reject) => {
    const r = indexedDB.open('job_tracker_fs', 2);
    r.onupgradeneeded = (e) => {
      const db = r.result;
      if (!db.objectStoreNames.contains('handles')) db.createObjectStore('handles');
    };
    r.onsuccess = () => resolve(r.result);
    r.onerror = () => reject(r.error);
  });
}
async function idbGet(key) {
  const db = await idbOpen();
  return new Promise((resolve) => {
    const tx = db.transaction('handles', 'readonly');
    const rq = tx.objectStore('handles').get(key);
    rq.onsuccess = () => { resolve(rq.result || null); db.close(); };
    rq.onerror = () => { resolve(null); db.close(); };
  });
}
async function idbPut(key, val) {
  const db = await idbOpen();
  return new Promise((resolve) => {
    const tx = db.transaction('handles', 'readwrite');
    tx.objectStore('handles').put(val, key);
    tx.oncomplete = () => { resolve(); db.close(); };
  });
}
async function idbDel(key) {
  const db = await idbOpen();
  return new Promise((resolve) => {
    const tx = db.transaction('handles', 'readwrite');
    tx.objectStore('handles').delete(key);
    tx.oncomplete = () => { resolve(); db.close(); };
  });
}
async function verifyPermission(handle, write = true) {
  const opts = { mode: write ? 'readwrite' : 'read' };
  if ((await handle.queryPermission(opts)) === 'granted') return true;
  if ((await handle.requestPermission(opts)) === 'granted') return true;
  return false;
}
function setFileStatus(kind, msg) {
  const el = $('file-status');
  el.className = 'file-status ' + kind;
  el.textContent = msg;
}

async function readFileJson(handle) {
  const file = await handle.getFile();
  if (file.size === 0) return null;
  return JSON.parse(await file.text());
}

// Atomic-ish write. createWritable() truncates the target file on open, so a
// closed-window mid-write leaves the target empty/truncated. Instead we write
// the full payload to jobs.json.tmp first, then atomically swap it onto
// jobs.json via FileSystemFileHandle.move() (Chromium-supported). If move()
// is unavailable, fall back to a buffered copy: write to .tmp, read it back
// into memory once it's known-good, then write that to the real handle. The
// fallback isn't truly atomic, but it ensures we only truncate the real file
// AFTER we hold a complete copy of the payload.
async function writeFileJson(handle, data) {
  const payload = JSON.stringify(data, null, 2) + '\n';
  if (!dirHandle) {
    // No dir handle (shouldn't normally happen here) — direct write fallback.
    const w = await handle.createWritable();
    await w.write(payload);
    await w.close();
    return;
  }
  const tmpHandle = await dirHandle.getFileHandle('jobs.json.tmp', { create: true });
  const w = await tmpHandle.createWritable();
  await w.write(payload);
  await w.close();
  if (typeof tmpHandle.move === 'function') {
    try {
      await tmpHandle.move('jobs.json');  // atomic rename, overwrites target
      return;
    } catch (e) {
      // Fall through to buffered copy if move() is rejected (e.g. perms).
      console.warn('move() failed, falling back to buffered copy:', e);
    }
  }
  // Fallback: re-read the tmp file to make sure it's intact, then copy to real.
  const tmpFile = await tmpHandle.getFile();
  const bytes = await tmpFile.arrayBuffer();
  const w2 = await handle.createWritable();
  await w2.write(bytes);
  await w2.close();
  // Best-effort cleanup of the tmp file.
  try { await dirHandle.removeEntry('jobs.json.tmp'); } catch (_) {}
}

// Read jobs.json from disk, rebuild in-memory JOBS + state from what's there.
async function loadFromJobsFile() {
  const handle = await getJobsHandle();
  if (!handle) return;
  try {
    const data = await readFileJson(handle);
    if (!Array.isArray(data)) return;
    JOBS.length = 0;
    for (const j of data) JOBS.push(j);
    // Re-hydrate user state from the fresh array. Local edits that weren't
    // yet flushed to disk stay (we only overwrite an id's state if the disk
    // copy has non-default user fields). recruiter_phone is user-owned so we
    // pick it up too. Overrides aren't reconstructed — once written, the
    // scraper field on disk IS the user's value.
    for (const j of JOBS) {
      if (!j?.id) continue;
      const hasUser = j.status_manual != null || j.interested != null
                   || (j.notes && j.notes !== '') || (j.recruiter_phone && j.recruiter_phone !== '');
      if (hasUser) {
        state[j.id] = {
          status_manual: j.status_manual ?? null,
          interested: j.interested ?? null,
          notes: j.notes || '',
          recruiter_phone: j.recruiter_phone || '',
          overrides: state[j.id]?.overrides || {},
        };
      }
    }
    saveState();
    applyFilters();
  } catch (e) {
    console.warn('Could not parse jobs.json; keeping in-memory data.', e);
  }
}

// Field-scoped write: read jobs.json, patch user fields per id in state, write back.
// Scraper and Gmail fields on every entry are preserved. A fresh file handle
// is opened each call to avoid stale-state errors after external writes.
function scheduleFileSave() {
  if (!dirHandle) return;
  setFileStatus('saving', 'Saving to jobs.json…');
  clearTimeout(saveTimer);
  saveTimer = setTimeout(async () => {
    try {
      const handle = await getJobsHandle();
      const disk = await readFileJson(handle);
      if (!Array.isArray(disk)) throw new Error('jobs.json on disk is not an array');
      const byId = new Map(disk.map(j => [j.id, j]));
      for (const [id, s] of Object.entries(state)) {
        let row = byId.get(id);
        if (!row) {
          // New manually-added entry (or one that vanished from disk). Take
          // its scraper-fields snapshot from the in-memory JOBS array.
          const jm = getJ(id);
          if (!jm) continue;
          row = { ...jm };
          disk.push(row);
          byId.set(id, row);
        }
        row.status_manual    = s.status_manual ?? null;
        row.interested       = s.interested    ?? null;
        row.notes            = s.notes || '';
        row.recruiter_phone  = s.recruiter_phone || '';
        // User overrides on scraper-owned fields.
        for (const key of SCRAPER_OVERRIDABLE) {
          if (Object.prototype.hasOwnProperty.call(s.overrides || {}, key)) {
            row[key] = s.overrides[key];
          }
        }
      }
      await writeFileJson(handle, disk);
      setFileStatus('linked', `Linked: ${dirHandle.name}/jobs.json · saved ✓`);
    } catch (e) {
      console.error(e);
      setFileStatus('error', `Save failed: ${e.message}. Edits still in browser storage.`);
    }
  }, 400);
}

async function linkToFolder() {
  if (!FSA_SUPPORTED) {
    alert('Your browser does not support folder access (needs Chrome or Edge). Use Import/Export JSON instead.');
    return;
  }
  try {
    const dir = await window.showDirectoryPicker({ mode: 'readwrite' });
    if (!(await verifyPermission(dir, true))) {
      alert('Write permission required to save edits and delete positions.');
      return;
    }
    dirHandle = dir;
    // Check jobs.json exists before committing
    try { await getJobsHandle(); }
    catch (e) {
      dirHandle = null;
      alert(`"${dir.name}/" has no jobs.json. Pick the folder that contains your tracker.`);
      return;
    }
    const loadIt = confirm(
      `Link "${dir.name}/jobs.json"?\n\n` +
      `OK = Load its contents into this tracker (replaces in-memory data).\n` +
      `Cancel = Keep the embedded snapshot and overwrite the file with any edits you make.`
    );
    if (loadIt) await loadFromJobsFile();
    else scheduleFileSave();
    await idbPut('dir', dir);
    setFileStatus('linked', `Linked: ${dir.name}/jobs.json ✓`);
    applyFilters();
  } catch (e) {
    if (e.name === 'AbortError') return;
    console.error(e);
    setFileStatus('error', `Link failed: ${e.message}`);
  }
}

async function tryReconnectOnStartup() {
  if (!FSA_SUPPORTED) {
    setFileStatus('unsupported', 'Folder auto-save needs Chrome or Edge. Using browser storage + Import/Export only.');
    return;
  }
  const dir = await idbGet('dir');
  if (!dir) return;
  const opts = { mode: 'readwrite' };
  if ((await dir.queryPermission(opts)) === 'granted') {
    try {
      dirHandle = dir;
      await getJobsHandle();  // throws if jobs.json missing
      await loadFromJobsFile();
      setFileStatus('linked', `Linked: ${dir.name}/jobs.json ✓`);
    } catch (e) {
      dirHandle = null;
      setFileStatus('error', `Previously linked to ${dir.name}/ but jobs.json is missing or unreadable.`);
    }
  } else {
    setFileStatus('not-linked', `Previously linked to ${dir.name}/ — click "Reconnect" to resume.`);
    $('link-btn').textContent = `Reconnect: ${dir.name}/`;
    $('link-btn').onclick = async () => {
      if (await verifyPermission(dir, true)) {
        try {
          dirHandle = dir;
          await getJobsHandle();
          await loadFromJobsFile();
          setFileStatus('linked', `Linked: ${dir.name}/jobs.json ✓`);
          $('link-btn').textContent = 'Link folder…';
          $('link-btn').onclick = linkToFolder;
          applyFilters();
        } catch (e) {
          dirHandle = null;
          setFileStatus('error', `Reconnect failed: ${e.message}`);
        }
      } else {
        await idbDel('dir');
        $('link-btn').textContent = 'Link folder…';
        $('link-btn').onclick = linkToFolder;
        linkToFolder();
      }
    };
  }
}

$('link-btn').addEventListener('click', linkToFolder);

async function deletePosition(id, opts = {}) {
  const { skipConfirm = false } = opts;
  const job = JOBS.find(j => j.id === id);
  const label = job ? `${job.company} — ${job.position}` : id;
  const inHtmlOnly = !dirHandle;
  if (!skipConfirm) {
    const msg = inHtmlOnly
      ? `Hide "${label}" from this view?\n\nNOT linked to a folder, so the jobs.json entry will NOT be marked deleted on disk. ` +
        `Next page reload brings it back. Click "Link folder…" first if you want the change to persist.`
      : `Hide "${label}" from the tracker?\n\nThis marks the entry as deleted in ${dirHandle.name}/jobs.json so the scraper won't re-add it. The row stays in the file (set "deleted": false to restore).`;
    if (!confirm(msg)) return;
  }

  if (dirHandle) {
    try {
      // 1) Soft-delete in jobs.json — flip the `deleted` flag instead of
      //    removing the row. The scraper still sees the link in
      //    `existing_links` and skips it on the next run, so deleted jobs
      //    don't reappear. Fresh handle each call.
      const handle = await getJobsHandle();
      if (handle) {
        const current = await readFileJson(handle) || [];
        if (Array.isArray(current)) {
          const idx = current.findIndex(j => j.id === id);
          if (idx >= 0) {
            current[idx] = { ...current[idx], deleted: true };
            await writeFileJson(handle, current);
          }
        }
      }
      // 2) Drop local state for this id, and cancel any pending save (the
      //    debounced save would otherwise re-add user fields for an id
      //    we just hid — harmless but wasteful).
      delete state[id];
      clearTimeout(saveTimer);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (e) {
      console.error(e);
      alert(`Delete failed on disk: ${e.message}\n\nThe tracker view was not changed.`);
      return;
    }
  }
  // 3) Mark deleted in in-memory JOBS (don't splice — keep it for dedup
  //    awareness if anything later touches the array).
  const idx = JOBS.findIndex(j => j.id === id);
  if (idx >= 0) JOBS[idx].deleted = true;
  applyFilters();
}

async function restorePosition(id) {
  const job = JOBS.find(j => j.id === id);
  const label = job ? `${job.company} — ${job.position}` : id;
  if (!confirm(`Restore "${label}"?\n\nThis flips "deleted" back to false in jobs.json so it shows up in the active view again. The scraper continues to dedup against its link.`)) return;

  if (dirHandle) {
    try {
      const handle = await getJobsHandle();
      if (handle) {
        const current = await readFileJson(handle) || [];
        if (Array.isArray(current)) {
          const idx = current.findIndex(j => j.id === id);
          if (idx >= 0) {
            // Drop the flag entirely (cleaner than setting false).
            const { deleted, ...rest } = current[idx];
            current[idx] = rest;
            await writeFileJson(handle, current);
          }
        }
      }
    } catch (e) {
      console.error(e);
      alert(`Restore failed on disk: ${e.message}\n\nThe tracker view was not changed.`);
      return;
    }
  }
  const idx = JOBS.findIndex(j => j.id === id);
  if (idx >= 0) delete JOBS[idx].deleted;
  applyFilters();
}

// ---------- Import / Export / Reset ----------
// Export = current JOBS array with user fields merged on. That's the real jobs.json shape.
function mergedJobs() {
  return JOBS.map(j => {
    const s = state[j.id];
    const merged = {
      ...j,
      ...(s?.overrides || {}),
      status_manual:   s?.status_manual   ?? j.status_manual   ?? null,
      interested:      s?.interested      ?? j.interested      ?? null,
      notes:           s?.notes           ?? j.notes           ?? '',
      recruiter_phone: s?.recruiter_phone ?? j.recruiter_phone ?? '',
    };
    return merged;
  });
}

$('import-btn').addEventListener('click', () => $('import-input').click());
$('import-input').addEventListener('change', async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  try {
    const data = JSON.parse(await file.text());
    if (Array.isArray(data)) {
      // Full jobs.json import: replace JOBS and re-hydrate state from user fields.
      JOBS.length = 0;
      for (const j of data) JOBS.push(j);
      state = {};
      for (const j of JOBS) {
        if (!j?.id) continue;
        const hasUser = j.status_manual != null || j.interested != null
                     || (j.notes && j.notes !== '') || (j.recruiter_phone && j.recruiter_phone !== '');
        if (hasUser) {
          state[j.id] = {
            status_manual: j.status_manual ?? null,
            interested: j.interested ?? null,
            notes: j.notes || '',
            recruiter_phone: j.recruiter_phone || '',
            overrides: {},
          };
        }
      }
    } else if (data && typeof data === 'object') {
      // Legacy state-map: { <id>: { status_manual, interested, notes } }
      state = data;
      for (const id of Object.keys(state)) {
        if (!state[id].overrides) state[id].overrides = {};
        if (state[id].recruiter_phone == null) state[id].recruiter_phone = '';
      }
    } else {
      throw new Error('Unrecognized JSON shape');
    }
    saveState();
    applyFilters();
    alert(`Imported ${file.name}.`);
    if (dirHandle) scheduleFileSave();
  } catch (err) {
    alert('Import failed: ' + err.message);
  }
  e.target.value = '';
});

$('export-btn').addEventListener('click', () => {
  const blob = new Blob([JSON.stringify(mergedJobs(), null, 2) + '\n'], {type:'application/json'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = 'jobs.json';
  a.click(); URL.revokeObjectURL(url);
});

$('reset-btn').addEventListener('click', async () => {
  if (!confirm('Reset all status, interest, and notes back to defaults? This cannot be undone. (Does not delete any positions.)')) return;
  state = {};
  saveState();
  // On disk: null out user fields on every entry of jobs.json.
  if (dirHandle) {
    try {
      const handle = await getJobsHandle();
      const disk = await readFileJson(handle);
      if (Array.isArray(disk)) {
        for (const row of disk) {
          row.status_manual = null;
          row.interested    = null;
          row.notes         = '';
        }
        await writeFileJson(handle, disk);
      }
    } catch (e) {
      console.error(e);
      alert(`Reset on disk failed: ${e.message}. Browser state was cleared.`);
    }
  }
  applyFilters();
});

// Auto-save hook
const _saveState = saveState;
saveState = function() { _saveState(); scheduleFileSave(); };

// ---------- Edit / Add modal ----------
let editingId = null;  // null while modal closed; '<id>' for an existing job; '__new' for a fresh entry

function openEditModal(id) {
  editingId = id;
  const job = effectiveJob(id);
  const s = getS(id);
  $('modal-title').textContent = `Edit: ${job.position || job.company || id}`;
  $('m-position').value = job.position || '';
  $('m-company').value = job.company || '';
  $('m-source').value = job.source || '';
  $('m-location').value = job.location || '';
  $('m-link').value = job.link || '';
  $('m-phone').value = s.recruiter_phone || '';
  $('m-description').value = job.description || '';
  $('m-requirements').value = (job.requirements || []).join('\n');
  $('m-responsibilities').value = (job.responsibilities || []).join('\n');
  $('m-nice').value = (job.nice_to_have || []).join('\n');
  $('m-notes').value = s.notes || '';
  $('m-hint').textContent = 'Edits to scraper-owned fields are saved as user overrides. Future scraper runs will not overwrite a non-empty field.';
  $('m-delete').classList.remove('hidden');
  $('modal-backdrop').classList.add('open');
  $('m-position').focus();
}

function openAddJobModal() {
  editingId = '__new';
  $('modal-title').textContent = 'New job';
  for (const k of ['m-position','m-company','m-source','m-location','m-link','m-phone',
                   'm-description','m-requirements','m-responsibilities','m-nice','m-notes']) {
    $(k).value = '';
  }
  $('m-source').value = 'Manual';
  $('m-hint').textContent = 'Creates a new entry in jobs.json with id "manual-<random>".';
  $('m-delete').classList.add('hidden');
  $('modal-backdrop').classList.add('open');
  $('m-position').focus();
}

function closeModal() {
  editingId = null;
  $('modal-backdrop').classList.remove('open');
}

function linesToArr(s) {
  return s.split('\n').map(l => l.trim()).filter(Boolean);
}

function randomManualId() {
  const hex = '0123456789abcdef';
  let r = '';
  for (let i = 0; i < 6; i++) r += hex[Math.floor(Math.random()*16)];
  return `manual-${r}`;
}

function saveModal() {
  if (!editingId) return;
  const vals = {
    position: $('m-position').value.trim(),
    company:  $('m-company').value.trim(),
    source:   $('m-source').value.trim(),
    location: $('m-location').value.trim(),
    link:     $('m-link').value.trim(),
    description: $('m-description').value.trim(),
    requirements:    linesToArr($('m-requirements').value),
    responsibilities: linesToArr($('m-responsibilities').value),
    nice_to_have:    linesToArr($('m-nice').value),
  };
  const phone = $('m-phone').value.trim();
  const notes = $('m-notes').value;

  if (editingId === '__new') {
    if (!vals.company && !vals.position) {
      alert('Please fill at least Position or Company.');
      return;
    }
    let id;
    do { id = randomManualId(); } while (getJ(id));
    const newJob = {
      id,
      position: vals.position || '(unspecified)',
      company:  vals.company  || '(unspecified)',
      source:   vals.source   || 'Manual',
      link:     vals.link     || null,
      scraped_at: new Date().toISOString(),
      location: vals.location || null,
      date:     new Date().toISOString().slice(0,10),
      description: vals.description || null,
      responsibilities: vals.responsibilities,
      requirements:     vals.requirements,
      nice_to_have:     vals.nice_to_have,
      last_email: null,
      status_auto: null,
      status_manual: 'New',
      interested: null,
      notes,
      recruiter_phone: phone,
    };
    JOBS.push(newJob);
    state[id] = {
      status_manual: 'New', interested: null, notes,
      recruiter_phone: phone, overrides: {},
    };
  } else {
    const id = editingId;
    const orig = getJ(id) || {};
    const s = getS(id);
    s.notes = notes;
    s.recruiter_phone = phone;
    // Diff each scraper field against the disk/JOBS value. Record only true
    // changes as overrides — keeps the patch minimal.
    s.overrides = s.overrides || {};
    function diff(field, val) {
      const cur = orig[field];
      const a = JSON.stringify(Array.isArray(val) ? val : (val ?? null));
      const b = JSON.stringify(Array.isArray(cur) ? cur : (cur ?? null));
      if (a === b) {
        // user reset back to scraper's value: drop override if any
        delete s.overrides[field];
      } else {
        s.overrides[field] = val;
      }
    }
    diff('position', vals.position || null);
    diff('company',  vals.company  || null);
    diff('source',   vals.source   || null);
    diff('location', vals.location || null);
    diff('link',     vals.link     || null);
    diff('description', vals.description || null);
    diff('requirements',     vals.requirements);
    diff('responsibilities', vals.responsibilities);
    diff('nice_to_have',     vals.nice_to_have);
  }
  saveState();
  applyFilters();
  closeModal();
}

function deleteFromModal() {
  if (!editingId || editingId === '__new') return;
  const id = editingId;
  closeModal();
  deletePosition(id);
}

$('add-btn').addEventListener('click', openAddJobModal);
$('m-cancel').addEventListener('click', closeModal);
$('m-save').addEventListener('click', saveModal);
$('m-delete').addEventListener('click', deleteFromModal);
$('modal-backdrop').addEventListener('click', (e) => {
  if (e.target.id === 'modal-backdrop') closeModal();
});
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && editingId) closeModal();
});

tryReconnectOnStartup();
applyFilters();
</script>

</body>
</html>
"""


def main() -> int:
    if not JOBS_JSON.exists():
        print(f"ERROR: {JOBS_JSON} not found.", file=sys.stderr)
        return 1

    from collections import Counter

    raw = JOBS_JSON.read_text(encoding="utf-8")
    jobs = json.loads(raw)
    kept, dropped = auto_maintain(jobs)

    if dropped:
        ts = _dt.datetime.utcnow().strftime("%Y%m%dT%H%M%S")
        backup = JOBS_JSON.parent / f"jobs.json.bak-pre-clean-{ts}"
        backup.write_text(raw, encoding="utf-8")
        JOBS_JSON.write_text(
            json.dumps(kept, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"Auto-maintenance: kept {len(kept)}, dropped {len(dropped)}.")
        reasons = Counter(
            d.get("_drop_reason", "?").split(":")[0].split(" ")[0]
            for d in dropped
        )
        for r, n in reasons.most_common():
            print(f"  - {r}: {n}")
        print(f"Backup written: {backup.name}")
    else:
        print("Auto-maintenance: nothing to drop.")

    build_time = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    html = HTML_TEMPLATE.replace(
        "__JOBS_JSON__", json.dumps(kept, ensure_ascii=False)
    ).replace(
        "__BUILD_TIME__", build_time
    )
    HTML_OUT.write_text(html, encoding="utf-8")
    print(f"Wrote {HTML_OUT} ({len(html):,} chars, {len(kept)} jobs)")
    rebuild_mobile_html(kept)
    return 0


if __name__ == "__main__":
    sys.exit(main())
: {backup.name}")
    else:
        print("Auto-maintenance: nothing to drop.")

    build_time = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    html = HTML_TEMPLATE.replace(
        "__JOBS_JSON__", json.dumps(kept, ensure_ascii=False)
    ).replace(
        "__BUILD_TIME__", build_time
    )
    HTML_OUT.write_text(html, encoding="utf-8")
    print(f"Wrote {HTML_OUT} ({len(html):,} chars, {len(kept)} jobs)")
    rebuild_mobile_html(kept)
    return 0


if __name__ == "__main__":
    sys.exit(main())
