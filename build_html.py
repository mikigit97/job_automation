#!/usr/bin/env python3
"""
build_html.py  (schema v2)
--------------------------
Reads jobs.json, keeps it healthy, and writes Job_applications.html.

What one run does, in order:
  1. migrate   - one-time upgrade of v1 records (status_manual/status_auto/
                 interested/deleted) to the v2 model (status/status_source/
                 applied_at/...). A backup goes to backups/ first.
  2. derive    - recompute per-record derived fields that depend only on the
                 posting text: years_min, dedup_key, extraction_ok, agency
                 (agency is only filled when absent; the user may override it).
  3. maintain  - status "new" records that expired, fail the relevance gates, or
                 duplicate another live posting become "archived" with a reason.
                 Nothing is ever removed from jobs.json: archived and rejected
                 records are the dedup memory that stops scrapers re-adding them.
  4. fit       - compute a fit tier (strong / ok / weak) with reasons, for sorting.
  5. purge     - delete cv/tailored/<id>.* for archived and rejected records.
  6. render    - embed the records into templates/dashboard.html.

Why rebuild instead of fetch at runtime: browsers block a file:// page from
reading local JSON via fetch(), so the data is baked in.

Run:  python build_html.py [--jobs PATH] [--out PATH] [--dry-run]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
TEMPLATE_PATH = ROOT / "templates" / "dashboard.html"
JOBS_JSON = ROOT / "jobs.json"
HTML_OUT = ROOT / "Job_applications.html"
TAILORED_DIR = ROOT / "cv" / "tailored"
BACKUP_DIR = ROOT / "backups"

STATUSES = ("new", "applied", "interview", "offer", "rejected", "archived")
STATUS_RANK = {s: i for i, s in enumerate(STATUSES)}  # higher = further along
PURGE_STATUSES = {"archived", "rejected"}
USER_FIELDS = (
    "status", "status_source", "status_changed_at", "applied_at", "applied_via",
    "followed_up_at", "archive_reason", "notes", "recruiter_phone", "agency",
)
LIST_FIELDS = ("responsibilities", "requirements", "nice_to_have")


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def _rx(fragments: list[str], flags: int = re.I) -> re.Pattern:
    """Join regex fragments with | into one case-insensitive pattern."""
    if not fragments:
        return re.compile(r"(?!x)x")  # never matches
    return re.compile("(?:" + "|".join(fragments) + ")", flags)


class Config:
    def __init__(self, raw: dict):
        self.raw = raw
        self.years_max: int = int(raw.get("years_max", 3))
        self.expiry_days: int = int(raw.get("expiry_days", 21))
        self.followup_days: int = int(raw.get("followup_days", 7))
        self.backups_to_keep: int = int(raw.get("backups_to_keep", 20))
        self.drop_anonymous_alljobs: bool = bool(raw.get("drop_anonymous_alljobs", True))
        fam = raw.get("role_families", {})
        self.families: dict[str, re.Pattern] = {k: _rx(v) for k, v in fam.items()}
        self.junior = _rx(raw.get("junior_titles", []))
        self.seniority = _rx(raw.get("seniority_titles", []))
        self.teaching = _rx(raw.get("teaching_titles", []))
        self.clinical = _rx(raw.get("clinical_titles", []))
        self.excluded = _rx(raw.get("excluded_titles", []))
        self.anonymous = [s.lower() for s in raw.get("anonymous_companies", [])]
        self.agencies = [s.lower() for s in raw.get("agencies", [])]
        self.agency_patterns = _rx(raw.get("agency_patterns", []))
        self.variants: list[str] = list(raw.get("variants", []))

    def public(self) -> dict:
        """The subset the dashboard needs at runtime."""
        return {
            "years_max": self.years_max,
            "expiry_days": self.expiry_days,
            "followup_days": self.followup_days,
            "variants": self.variants,
        }


def load_config(path: Path = CONFIG_PATH) -> Config:
    with open(path, encoding="utf-8") as f:
        return Config(json.load(f))


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------

def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def iso(t: dt.datetime) -> str:
    return t.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_ts(s) -> dt.datetime | None:
    """Parse an ISO timestamp or YYYY-MM-DD; return None when unparseable."""
    if not s:
        return None
    s = str(s).strip()
    try:
        if len(s) == 10:
            return dt.datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=dt.timezone.utc)
        t = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=dt.timezone.utc)
    return t


def age_days(s, now: dt.datetime) -> float | None:
    t = parse_ts(s)
    return None if t is None else (now - t).total_seconds() / 86400.0


# ---------------------------------------------------------------------------
# Text-derived fields
# ---------------------------------------------------------------------------

def _text_blob(job: dict) -> str:
    parts: list[str] = []
    for k in LIST_FIELDS:
        v = job.get(k)
        if isinstance(v, list):
            parts.extend(str(x) for x in v)
    if job.get("description"):
        parts.append(str(job["description"]))
    return " ".join(parts)


# "3 years", "3+ years", "3-5 years", "3 to 5 yrs"  -> group 1 = lower bound
_YEARS_EN = re.compile(
    r"(\d{1,2})\s*(?:\+|-|–|to)?\s*(?:\d{1,2})?\s*\+?\s*(?:years?|yrs?)\b", re.I)
# "3 שנות ניסיון", "לפחות 5 שנים", "2-3 שנים"
_YEARS_HE = re.compile(r"(\d{1,2})\s*(?:\+|-|–)?\s*(?:\d{1,2})?\s*\+?\s*שנ(?:ה|ים|ות)\b")
_EXP_CONTEXT = re.compile(r"experience|exp\.|ניסיון|נסיון", re.I)
_CONTEXT_WINDOW = 60


def years_min(job: dict) -> int | None:
    """Lower bound of the years-of-experience requirement, or None.

    A number only counts when the word "experience" / "ניסיון" appears within
    60 characters of it, so "founded 4 years ago" is not read as a requirement.
    "שנתיים" (= two years) is handled as a bare word.
    """
    text = _text_blob(job)
    if not text:
        return None
    found: list[int] = []
    for rx in (_YEARS_EN, _YEARS_HE):
        for m in rx.finditer(text):
            lo, hi = max(0, m.start() - _CONTEXT_WINDOW), m.end() + _CONTEXT_WINDOW
            if _EXP_CONTEXT.search(text[lo:hi]):
                try:
                    found.append(int(m.group(1)))
                except ValueError:
                    pass
    for m in re.finditer(r"שנתיים", text):
        lo, hi = max(0, m.start() - _CONTEXT_WINDOW), m.end() + _CONTEXT_WINDOW
        if _EXP_CONTEXT.search(text[lo:hi]):
            found.append(2)
    return min(found) if found else None


_LEGAL_RX = re.compile(
    r"\b(?:ltd\.?|inc\.?|llc|gmbh|corp\.?|co\.?)\b|בע\"?מ|בע״מ", re.I)
_GENDER_RX = re.compile(
    r"\((?:m/f|f/m|w/m|m/w|m/f/d|h/f)\)|\b(?:m/f|f/m)\b|דרוש/ה|דרושה|דרושים|דרושות|דרוש|/ת\b|/ה\b|/ית\b|/ות\b", re.I)
_PUNCT_RX = re.compile(r"[^\w\s]", re.UNICODE)
_WS_RX = re.compile(r"\s+")


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", str(s or "")).lower()
    s = _GENDER_RX.sub(" ", s)
    s = _LEGAL_RX.sub(" ", s)
    s = _PUNCT_RX.sub(" ", s)
    return _WS_RX.sub(" ", s).strip()


def dedup_key(company, position) -> str:
    return f"{_norm(company)}|{_norm(position)}"


def is_agency(company, cfg: Config) -> bool:
    c = _norm(company)
    if not c:
        return False
    padded = f" {c} "
    for a in cfg.agencies:
        if f" {_norm(a)} " in padded:
            return True
    return bool(cfg.agency_patterns.search(c))


def is_anonymous(company, cfg: Config) -> bool:
    c = _norm(company)
    return any(_norm(a) in c for a in cfg.anonymous) if c else False


def extraction_ok(job: dict) -> bool:
    req = job.get("requirements") or []
    desc = job.get("description") or ""
    return len(req) >= 2 or len(str(desc)) >= 200


def classify_title(position, cfg: Config) -> str | None:
    """Role family ('ai' first, then 'ds'), or None when the title matches neither."""
    pos = str(position or "")
    for fam, rx in cfg.families.items():
        if rx.search(pos):
            return fam
    return None


def is_relevant(job: dict, cfg: Config) -> tuple[bool, str]:
    """Return (keep, reason). Applied to status=new records only."""
    pos = (job.get("position") or "").strip()
    if not pos:
        return False, "no position title"
    if classify_title(pos, cfg) is None:
        return False, f"title outside role families: {pos!r}"
    if cfg.seniority.search(pos):
        return False, "senior/lead title"
    if cfg.teaching.search(pos):
        return False, "teaching/mentoring title"
    if cfg.clinical.search(pos):
        return False, "clinical title"
    if cfg.excluded.search(pos):
        return False, "excluded role (not AI/ML/DS)"
    if (cfg.drop_anonymous_alljobs and (job.get("source") or "").lower() == "alljobs"
            and is_anonymous(job.get("company"), cfg)):
        return False, "anonymous AllJobs company"
    ym = job.get("years_min")
    if ym is not None and ym > cfg.years_max:
        # Gate on any parsed figure: a years line is evidence even when the rest
        # of the extraction is thin (e.g. Drushim's structured "ניסיון" field).
        return False, f"requires {ym}+ years"
    return True, ""


def compute_fit(job: dict, cfg: Config) -> dict:
    """Sorting aid only. strong / ok / weak plus the reasons behind it."""
    pos = job.get("position") or ""
    fam = classify_title(pos, cfg)
    junior = bool(cfg.junior.search(pos))
    ym = job.get("years_min")
    agency = bool(job.get("agency"))
    ok = bool(job.get("extraction_ok"))
    reasons: list[str] = []
    if fam:
        reasons.append(fam)
    if junior:
        reasons.append("junior")
    if ym is not None:
        reasons.append(f"{ym}y")
    if agency:
        reasons.append("agency")
    if not ok:
        reasons.append("unverified")
    if not ok or agency or (ym is not None and ym >= cfg.years_max):
        tier = "weak"
    elif fam and (junior or (ym is not None and ym <= 2)):
        tier = "strong"
    else:
        tier = "ok"
    return {"tier": tier, "reasons": reasons}


# ---------------------------------------------------------------------------
# Migration v1 -> v2
# ---------------------------------------------------------------------------

_V1_STATUS = {
    "new": ("new", None),
    "manual review": ("new", None),
    "auto-applied": ("applied", "auto"),
    "applied": ("applied", "manual"),
    "interview": ("interview", None),
    "offer": ("offer", None),
    "rejected": ("rejected", None),
    "archived": ("archived", None),
}
_V1_EMAIL = {"auto_ack": "applied", "interview": "interview", "offer": "offer", "rejected": "rejected"}


def _clean_list(v) -> list:
    if not isinstance(v, list):
        return []
    out = [str(x).strip() for x in v if x is not None and str(x).strip()]
    return [] if out == ["N/A"] else [x for x in out if x != "N/A"]


def needs_migration(job: dict) -> bool:
    return job.get("status") not in STATUSES


def migrate_record(job: dict, now: dt.datetime) -> dict:
    """Upgrade one v1 record in place. Returns a small report dict."""
    manual = (job.pop("status_manual", None) or "").strip().lower()
    auto = (job.pop("status_auto", None) or "").strip().lower()
    interested = job.pop("interested", None)
    deleted = bool(job.pop("deleted", False))
    email = job.get("last_email") or {}
    cls = (email.get("classification") or "").strip().lower()
    email_date = email.get("date")

    if manual in _V1_STATUS:
        status, via = _V1_STATUS[manual]
        source = "user"
    elif auto in _V1_STATUS:
        status, via = _V1_STATUS[auto]
        source = "gmail"
    elif cls in _V1_EMAIL:
        status, via = _V1_EMAIL[cls], ("manual" if _V1_EMAIL[cls] == "applied" else None)
        source = "gmail"
    else:
        status, via, source = "new", None, "scraper"

    reason = None
    if deleted or (interested == "no" and status == "new"):
        status, via, source, reason = "archived", None, "user", "skipped"
    if status == "archived" and reason is None:
        reason = "skipped"

    changed_at = email_date if source == "gmail" and email_date else (job.get("scraped_at") or iso(now))
    applied_at = None
    note_add = ""
    if status in ("applied", "interview", "offer"):
        applied_at = email_date or job.get("scraped_at") or iso(now)
        note_add = "[migration] applied_at backfilled"

    job["status"] = status
    job["status_source"] = source
    job["status_changed_at"] = changed_at
    job["applied_at"] = applied_at
    job["applied_via"] = via if status in ("applied", "interview", "offer") else None
    job["followed_up_at"] = None
    job["archive_reason"] = reason
    if note_add:
        notes = (job.get("notes") or "").strip()
        job["notes"] = f"{notes}\n{note_add}".strip() if notes else note_add
    job.setdefault("cv_variant", None)
    job.setdefault("cv_tailored_at", None)
    job.setdefault("extraction_attempts", 1 if (job.get("source") or "").lower() != "manual" else 0)
    return {"status": status, "from_deleted": deleted}


def ensure_fields(job: dict, cfg: Config) -> None:
    """Defaults + recomputed derived fields; idempotent."""
    for k in LIST_FIELDS:
        job[k] = _clean_list(job.get(k))
    for k in ("location", "date", "description", "last_email", "applied_at", "applied_via",
              "followed_up_at", "archive_reason", "cv_variant", "cv_tailored_at"):
        job.setdefault(k, None)
    for k in ("notes", "recruiter_phone"):
        if job.get(k) is None:
            job[k] = ""
    job.setdefault("extraction_attempts", 0)
    job.setdefault("status_source", "scraper")
    job.setdefault("status_changed_at", job.get("scraped_at"))
    job["extraction_ok"] = extraction_ok(job)
    job["years_min"] = years_min(job)
    job["dedup_key"] = dedup_key(job.get("company"), job.get("position"))
    if "agency" not in job or job["agency"] is None:
        job["agency"] = is_agency(job.get("company"), cfg)


# ---------------------------------------------------------------------------
# Maintenance
# ---------------------------------------------------------------------------

def _archive(job: dict, reason: str, now: dt.datetime) -> None:
    job["status"] = "archived"
    job["status_source"] = "maintain"
    job["status_changed_at"] = iso(now)
    job["archive_reason"] = reason


def auto_maintain(jobs: list[dict], cfg: Config, now: dt.datetime | None = None) -> dict:
    """Archive expired / irrelevant / duplicate *new* records. Never deletes.

    Records whose id starts with ``manual-`` are exempt from expiry, relevance
    and dedup — the user added them deliberately.
    """
    now = now or now_utc()
    report = {"expired": [], "irrelevant": [], "duplicate": []}
    for j in jobs:
        if j.get("status") != "new" or str(j.get("id", "")).startswith("manual-"):
            continue
        age = age_days(j.get("scraped_at"), now)
        if age is not None and age > cfg.expiry_days:
            _archive(j, "expired", now)
            report["expired"].append(j["id"])
            continue
        keep, why = is_relevant(j, cfg)
        if not keep:
            _archive(j, "irrelevant", now)
            j["notes"] = ((j.get("notes") or "").strip() + f"\n[maintain] {why}").strip()
            report["irrelevant"].append(j["id"])

    # Secondary dedup: same normalized company|position among live records.
    groups: dict[str, list[dict]] = {}
    for j in jobs:
        if j.get("status") in PURGE_STATUSES or str(j.get("id", "")).startswith("manual-"):
            continue
        groups.setdefault(j.get("dedup_key") or "", []).append(j)
    for key, members in groups.items():
        if not key or len(members) < 2:
            continue
        # Keep the record furthest along; ties -> earliest scraped.
        members.sort(key=lambda r: (-STATUS_RANK.get(r.get("status"), 0), r.get("scraped_at") or ""))
        keeper = members[0]
        for dup in members[1:]:
            if dup.get("status") == "new":
                _archive(dup, "duplicate", now)
                dup["notes"] = ((dup.get("notes") or "").strip() + f"\n[maintain] duplicate of {keeper['id']}").strip()
                report["duplicate"].append(dup["id"])
    return report


def purge_tailored(jobs: list[dict], tailored_dir: Path = TAILORED_DIR, dry_run: bool = False) -> list[str]:
    """Delete cv/tailored/<id>.* for archived and rejected records.

    Files are matched on the job id prefix, so hand-named files in that folder
    (e.g. "Mickael Zeitoun - CV.pdf") are never touched. cv/variants/ is never
    touched by anything in this script.
    """
    removed: list[str] = []
    if not tailored_dir.is_dir():
        return removed
    for j in jobs:
        if j.get("status") not in PURGE_STATUSES:
            continue
        jid = str(j.get("id") or "").strip()
        if not jid:
            continue
        for path in sorted(tailored_dir.glob(f"{jid}.*")):
            if path.is_file():
                if not dry_run:
                    path.unlink()
                removed.append(path.name)
    return removed


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def backup(src: Path, tag: str, keep: int, backup_dir: Path = BACKUP_DIR) -> Path | None:
    if not src.exists():
        return None
    backup_dir.mkdir(exist_ok=True)
    ts = now_utc().strftime("%Y%m%dT%H%M%SZ")
    dst = backup_dir / f"{src.name}.{tag}-{ts}"
    dst.write_bytes(src.read_bytes())
    # Prune: keep the newest N backups of this file.
    olds = sorted(backup_dir.glob(f"{src.name}.*"), key=lambda p: p.stat().st_mtime, reverse=True)
    for p in olds[keep:]:
        try:
            p.unlink()
        except OSError:
            pass
    return dst


def derived_for_embed(job: dict, tailored_dir: Path = TAILORED_DIR) -> dict:
    """Build-time-only fields (underscore = not persisted to jobs.json)."""
    jid = str(job.get("id") or "")
    pdf = tailored_dir / f"{jid}.pdf"
    html = tailored_dir / f"{jid}.html"
    return {
        "_cv_pdf": f"cv/tailored/{jid}.pdf" if jid and pdf.is_file() else None,
        "_cv_html": f"cv/tailored/{jid}.html" if jid and html.is_file() else None,
    }


def render(jobs: list[dict], cfg: Config, template_path: Path = TEMPLATE_PATH) -> str:
    template = template_path.read_text(encoding="utf-8")
    embedded = [{**j, **derived_for_embed(j)} for j in jobs]
    build_time = dt.datetime.now().strftime("%Y-%m-%d %H:%M")

    def js(obj) -> str:
        return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")

    return (template
            .replace("__JOBS_JSON__", js(embedded))
            .replace("__CONFIG_JSON__", js(cfg.public()))
            .replace("__BUILD_TIME__", build_time))


def process(jobs: list[dict], cfg: Config, now: dt.datetime | None = None) -> dict:
    """Migrate + derive + maintain + fit, in place. Returns a report."""
    now = now or now_utc()
    report: dict = {"migrated": 0, "migrated_to": {}, "maintain": {}, "tiers": {}}
    for j in jobs:
        if not isinstance(j, dict):
            continue
        if needs_migration(j):
            r = migrate_record(j, now)
            report["migrated"] += 1
            report["migrated_to"][r["status"]] = report["migrated_to"].get(r["status"], 0) + 1
        ensure_fields(j, cfg)
    report["maintain"] = auto_maintain(jobs, cfg, now)
    for j in jobs:
        if isinstance(j, dict):
            j["fit"] = compute_fit(j, cfg)
            if j.get("status") == "new":
                report["tiers"][j["fit"]["tier"]] = report["tiers"].get(j["fit"]["tier"], 0) + 1
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--jobs", type=Path, default=JOBS_JSON)
    ap.add_argument("--out", type=Path, default=HTML_OUT)
    ap.add_argument("--config", type=Path, default=CONFIG_PATH)
    ap.add_argument("--template", type=Path, default=TEMPLATE_PATH)
    ap.add_argument("--dry-run", action="store_true", help="report, but write nothing")
    args = ap.parse_args(argv)

    if not args.jobs.exists():
        print(f"ERROR: {args.jobs} not found.", file=sys.stderr)
        return 1
    cfg = load_config(args.config)
    raw = args.jobs.read_text(encoding="utf-8")
    jobs = json.loads(raw)
    if not isinstance(jobs, list):
        print("ERROR: jobs.json must be a JSON array.", file=sys.stderr)
        return 1
    jobs = [j for j in jobs if isinstance(j, dict)]
    before = json.dumps(jobs, ensure_ascii=False, sort_keys=True)

    report = process(jobs, cfg)
    after = json.dumps(jobs, ensure_ascii=False, sort_keys=True)
    changed = before != after

    if report["migrated"]:
        print(f"Migration: {report['migrated']} record(s) upgraded to schema v2 -> "
              + ", ".join(f"{k}: {v}" for k, v in sorted(report["migrated_to"].items())))
    m = report["maintain"]
    touched = sum(len(v) for v in m.values())
    if touched:
        print("Maintenance: archived " + ", ".join(f"{len(v)} {k}" for k, v in m.items() if v))
    else:
        print("Maintenance: nothing to archive.")
    live = sum(1 for j in jobs if j.get("status") not in PURGE_STATUSES)
    counts = {s: sum(1 for j in jobs if j.get("status") == s) for s in STATUSES}
    print("Status: " + ", ".join(f"{s} {n}" for s, n in counts.items()) + f"  (live {live}, total {len(jobs)})")
    if report["tiers"]:
        print("Inbox fit: " + ", ".join(f"{k} {v}" for k, v in sorted(report["tiers"].items())))

    if args.dry_run:
        print("Dry run: no files written.")
        return 0

    if changed:
        tag = "pre-v2" if report["migrated"] else "pre-maintain"
        b = backup(args.jobs, tag, cfg.backups_to_keep)
        args.jobs.write_text(json.dumps(jobs, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Wrote {args.jobs.name}" + (f" (backup: backups/{b.name})" if b else ""))

    removed = purge_tailored(jobs)
    if removed:
        print(f"Removed {len(removed)} tailored CV file(s) for archived/rejected postings:")
        for name in removed:
            print(f"  - cv/tailored/{name}")

    html = render(jobs, cfg, args.template)
    args.out.write_text(html, encoding="utf-8")
    print(f"Wrote {args.out.name} ({len(html):,} chars, {live} live jobs)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
