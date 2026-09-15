#!/usr/bin/env python3
"""
ingest.py — turn raw scraped postings into jobs.json records (schema v2).

The Chrome scraper only extracts; this script decides. It applies exactly the
same gates, parsers and dedup rules as build_html.py (it imports them), so
the scraper prompt and the build can never disagree.

Input file (default scrape_raw.json), either a list of batches or
{"batches": [...]}:

    {"batches": [
      {"source": "LinkedIn", "finished": true,
       "postings": [
         {"position": "...", "company": "...", "link": "https://...",
          "location": null, "date": "2026-09-14", "description": "...",
          "responsibilities": ["..."], "requirements": ["..."], "nice_to_have": [],
          "applied_date": null,          # "YYYY-MM-DD" when the user already applied (Gmail import, board badge)
          "note": null}                  # optional free text appended to the record's notes
       ]}
    ]}

What it does per posting:
  * link already in jobs.json  -> enrich empty scraper fields, re-verify,
                                  never touch status (except applied_date on a
                                  `new` record, which promotes it to applied)
  * gates (role family, seniority, teaching, clinical, excluded role,
    anonymous AllJobs, parsed years above years_soft_max) -> dropped, counted
  * dedup_key already known    -> dropped as duplicate — unless the posting
                                  carries applied_date and the known record is
                                  still `new`: then that record is promoted
  * otherwise                  -> appended as status=new, or as applied when
                                  applied_date is set (link may be null then —
                                  an application confirmed by email whose
                                  posting was never scraped)

Then writes jobs.json (backup first), updates state.json for finished
batches, and prints one summary line. Run `python build_html.py` afterwards.

Usage:  python ingest.py [scrape_raw.json] [--dry-run]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import build_html as bh

ROOT = Path(__file__).resolve().parent
STATE_JSON = ROOT / "state.json"
RAW_DEFAULT = ROOT / "scrape_raw.json"

_SPLIT_RX = re.compile(r"\s*(?:\n|•|·|•|\s-\s|;\s)\s*")


def _as_list(v, cap: int) -> list[str]:
    if v is None:
        return []
    if isinstance(v, str):
        parts = [p.strip(" -•·\t") for p in _SPLIT_RX.split(v)]
    else:
        parts = [str(x).strip() for x in v]
    out = [p for p in parts if len(p) >= 4 and p != "N/A"]
    return out[:cap]


def make_id(company: str, link: str, taken: set[str], fallback: str = "") -> str:
    first = (str(company or "").strip().split() or ["job"])[0].lower()
    first = re.sub(r"[^\w\-]", "", first, flags=re.UNICODE) or "job"
    h = hashlib.md5(str(link or fallback).encode("utf-8")).hexdigest()[:6]
    base = f"{first}-{h}"
    jid, n = base, 2
    while jid in taken:
        jid, n = f"{base}-{n}", n + 1
    return jid


def _promote(existing: dict, applied: str, source: str, note: str | None) -> None:
    """A `new` record the user has in fact applied to (board badge or email confirmation)."""
    existing.update({
        "status": "applied", "status_source": "gmail" if source == "Gmail" else "scraper",
        "applied_via": "manual", "applied_at": applied, "status_changed_at": applied,
        "notes": ((existing.get("notes") or "").strip() + "\n" + (note or f"imported: applied via {source} on {applied}")).strip(),
    })


def new_record(p: dict, source: str, scraped_at: str, taken: set[str]) -> dict:
    applied = p.get("applied_date")
    note = (p.get("note") or "").strip()
    rec = {
        "id": make_id(p.get("company"), p.get("link"), taken, fallback=bh.dedup_key(p.get("company"), p.get("position"))),
        "position": (p.get("position") or "").strip(),
        "company": (p.get("company") or "").strip(),
        "source": source,
        "link": p.get("link") or None,
        "scraped_at": scraped_at,
        "location": (p.get("location") or None),
        "date": (p.get("date") or None),
        "description": (str(p.get("description")).strip()[:600] if p.get("description") else None),
        "responsibilities": _as_list(p.get("responsibilities"), 4),
        "requirements": _as_list(p.get("requirements"), 6),
        "nice_to_have": _as_list(p.get("nice_to_have"), 3),
        "extraction_attempts": 1,
        "status": "applied" if applied else "new",
        "status_source": "scraper",
        "status_changed_at": applied or scraped_at,
        "applied_at": applied,
        "applied_via": "manual" if applied else None,
        "followed_up_at": None,
        "archive_reason": None,
        "last_email": None,
        "cv_variant": None,
        "cv_tailored_at": None,
        "notes": note or (f"imported: applied via {source} on {applied}" if applied else ""),
        "recruiter_phone": "",
    }
    return rec


def enrich(existing: dict, p: dict, source: str, cfg: bh.Config) -> tuple[bool, bool]:
    """Fill empty scraper fields from a fresh extraction. Returns (changed, became_verified)."""
    was_ok = bool(existing.get("extraction_ok"))
    changed = False
    for k, cap in (("responsibilities", 4), ("requirements", 6), ("nice_to_have", 3)):
        if not existing.get(k):
            v = _as_list(p.get(k), cap)
            if v:
                existing[k] = v
                changed = True
    for k in ("location", "date"):
        if not existing.get(k) and p.get(k):
            existing[k] = p[k]
            changed = True
    if not existing.get("description") and p.get("description"):
        existing["description"] = str(p["description"]).strip()[:600]
        changed = True
    if not was_ok:
        existing["extraction_attempts"] = int(existing.get("extraction_attempts") or 0) + 1
    bh.ensure_fields(existing, cfg)
    applied = p.get("applied_date")
    if applied and existing.get("status") == "new":
        _promote(existing, applied, source, (p.get("note") or "").strip() or None)
        changed = True
    return changed, (not was_ok and bool(existing.get("extraction_ok")))


def run(raw_path: Path, jobs_path: Path, state_path: Path, cfg: bh.Config, dry_run: bool = False) -> dict:
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    batches = raw.get("batches", []) if isinstance(raw, dict) else raw
    scraped_at = (raw.get("scraped_at") if isinstance(raw, dict) else None) or bh.iso(bh.now_utc())

    jobs = json.loads(jobs_path.read_text(encoding="utf-8")) if jobs_path.exists() else []
    jobs = [j for j in jobs if isinstance(j, dict)]
    for j in jobs:
        if bh.needs_migration(j):
            bh.migrate_record(j, bh.now_utc())
        bh.ensure_fields(j, cfg)
    by_link = {j.get("link"): j for j in jobs if j.get("link")}
    by_key = {j.get("dedup_key"): j for j in jobs if j.get("dedup_key")}
    keys = set(by_key)
    ids = {j.get("id") for j in jobs}

    c = {"new": {}, "imported": 0, "promoted": 0, "enriched": 0, "reverified": 0, "duplicate": 0,
         "filtered": {}, "agency": 0, "unverified": 0}

    for batch in batches:
        source = batch.get("source") or "Unknown"
        for p in batch.get("postings", []):
            if not (p.get("position") or p.get("company")):
                continue
            if not p.get("link") and not p.get("applied_date"):
                continue                      # a posting without a link is only acceptable as an applied import
            existing = by_link.get(p["link"]) if p.get("link") else None
            if existing is None and p.get("applied_date"):
                existing = by_key.get(bh.dedup_key(p.get("company"), p.get("position")))
                if existing is not None and existing.get("status") == "new":
                    _promote(existing, p["applied_date"], source, (p.get("note") or "").strip() or None)
                    if p.get("link") and not existing.get("link"):
                        existing["link"] = p["link"]; by_link[p["link"]] = existing
                    c["promoted"] += 1
                    continue
                if existing is not None:
                    continue                  # already applied/interview/...: the email adds nothing
            if existing is not None:
                was_new = existing.get("status") == "new"
                changed, verified = enrich(existing, p, source, cfg)
                c["enriched"] += int(changed)
                c["reverified"] += int(verified)
                c["promoted"] += int(was_new and existing.get("status") == "applied")
                continue
            rec = new_record(p, source, scraped_at, ids)
            bh.ensure_fields(rec, cfg)
            if rec["status"] == "new":
                keep, why = bh.is_relevant(rec, cfg)
                if not keep:
                    reason = ("family" if "outside role families" in why or "no position" in why else
                              "senior" if "senior" in why else
                              "teaching" if "teaching" in why else
                              "clinical" if "clinical" in why else
                              "anonymous" if "anonymous" in why else
                              "years" if "years" in why else "other")
                    c["filtered"][reason] = c["filtered"].get(reason, 0) + 1
                    continue
            if rec["dedup_key"] in keys:
                c["duplicate"] += 1
                continue
            jobs.append(rec)
            if rec.get("link"):
                by_link[rec["link"]] = rec
            by_key[rec["dedup_key"]] = rec
            keys.add(rec["dedup_key"])
            ids.add(rec["id"])
            if rec["status"] == "applied":
                c["imported"] += 1
            else:
                c["new"][source] = c["new"].get(source, 0) + 1
            c["agency"] += int(bool(rec.get("agency")))
            c["unverified"] += int(not rec.get("extraction_ok"))

    if not dry_run:
        bh.backup(jobs_path, "pre-ingest", cfg.backups_to_keep)
        jobs_path.write_text(json.dumps(jobs, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
        state.setdefault("sources", {})
        for batch in batches:
            if batch.get("finished"):
                state["sources"][batch.get("source") or "Unknown"] = {"last_scrape_at": scraped_at}
        state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return c


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("raw", nargs="?", type=Path, default=RAW_DEFAULT)
    ap.add_argument("--jobs", type=Path, default=bh.JOBS_JSON)
    ap.add_argument("--state", type=Path, default=STATE_JSON)
    ap.add_argument("--config", type=Path, default=bh.CONFIG_PATH)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    if not args.raw.exists():
        print(f"ERROR: {args.raw} not found.", file=sys.stderr)
        return 1
    cfg = bh.load_config(args.config)
    c = run(args.raw, args.jobs, args.state, cfg, args.dry_run)
    new_total = sum(c["new"].values())
    per = " ".join(f"{k}:{v}" for k, v in sorted(c["new"].items()))
    filt = " / ".join(f"{v} {k}" for k, v in sorted(c["filtered"].items())) or "none"
    print(f"Ingested {new_total} new ({per or '-'}) · {c['enriched']} enriched ({c['reverified']} now verified) · "
          f"{c['imported']} imported as applied · {c['promoted']} promoted new→applied · {c['duplicate']} duplicates · filtered: {filt} · "
          f"flagged: {c['agency']} agency, {c['unverified']} unverified"
          + (" · DRY RUN" if args.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
