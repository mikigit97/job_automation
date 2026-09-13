"""Unit tests for build_html.py's gates, parsers and migration.

Run from the project root:  python tests/test_gates.py
Uses only the standard library (unittest), no pytest needed.
"""
import datetime as dt
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import build_html as bh  # noqa: E402

CFG = bh.load_config(ROOT / "config.json")
NOW = dt.datetime(2026, 9, 13, 12, 0, tzinfo=dt.timezone.utc)


def job(**kw):
    base = {"id": "acme-000001", "position": "Data Scientist", "company": "Acme", "source": "LinkedIn",
            "link": "https://x/1", "scraped_at": "2026-09-10T00:00:00Z", "description": None,
            "requirements": ["Python", "SQL"], "responsibilities": [], "nice_to_have": []}
    base.update(kw)
    return base


class TitleFamilies(unittest.TestCase):
    def test_ai_family(self):
        for t in ["AI Engineer", "Generative AI Engineer", "LLM Engineer", "NLP Engineer", "Applied AI Engineer",
                  "מומחה/ית AI ואוטומציה", "מהנדס בינה מלאכותית"]:
            self.assertEqual(bh.classify_title(t, CFG), "ai", t)

    def test_ds_family(self):
        for t in ["Data Scientist", "Machine Learning Engineer", "ML Engineer", "Deep Learning Researcher",
                  "Algorithm Developer", "Computer Vision Engineer", "Applied Scientist", "Research Engineer",
                  "מדען נתונים", "מהנדס למידת מכונה", "מפתח/ת אלגוריתמים"]:
            self.assertEqual(bh.classify_title(t, CFG), "ds", t)

    def test_outside_families(self):
        for t in ["Software Engineer", "Backend Developer", "Data Engineer", "Data Analyst", "Product Manager",
                  "Full Stack Developer", "HTML Developer", "DevOps Engineer"]:
            self.assertIsNone(bh.classify_title(t, CFG), t)


class RelevanceGate(unittest.TestCase):
    def keep(self, **kw):
        j = job(**kw)
        bh.ensure_fields(j, CFG)
        return bh.is_relevant(j, CFG)

    def test_plain_junior_titles_pass(self):
        self.assertTrue(self.keep(position="Junior Data Scientist")[0])
        self.assertTrue(self.keep(position="AI Engineer")[0])
        self.assertTrue(self.keep(position="Data Scientist מנוסה במודלי Machine Learning")[0])

    def test_senior_titles_fail(self):
        for t in ["Senior Data Scientist", "Sr. ML Engineer", "Lead AI Engineer", "Principal Data Scientist",
                  "Staff Machine Learning Engineer", "Head of AI", "Data Science Manager", "Data Scientist בכיר",
                  "ראש צוות למידת מכונה", "מוביל/ת צוות אלגוריתמים", "Tech Lead - AI"]:
            keep, why = self.keep(position=t)
            self.assertFalse(keep, t)
            self.assertIn("senior", why)

    def test_leading_company_is_not_seniority(self):
        # "לחברה מובילה" = "for a leading company" - a company adjective, not a team-lead title.
        keep, _ = self.keep(position="לחברה מובילה דרוש /ה data Scientist לתפקיד משמעותי")
        self.assertTrue(keep)

    def test_teaching_titles_fail(self):
        for t in ["דרושים מנחי.ות פרויקט data Science בתכנית מגשימים AI",
                  "רכז /ת הדרכה לשנת י\"ב בתכנית מגשימים AI- משרה חלקית",
                  "AI Instructor", "Machine Learning Mentor", "Data Science Lecturer"]:
            keep, why = self.keep(position=t)
            self.assertFalse(keep, t)
            self.assertIn("teaching", why)

    def test_ml_training_is_not_teaching(self):
        self.assertTrue(self.keep(position="ML Engineer - model training pipelines")[0])

    def test_clinical_titles_fail_but_medtech_ml_passes(self):
        self.assertFalse(self.keep(position="Clinical Trial Coordinator - AI")[0])
        self.assertFalse(self.keep(position="Nurse - AI Data Scientist")[0])
        self.assertTrue(self.keep(position="Data Scientist", company="Aidoc Medical", description="medical imaging AI " * 20)[0])
        self.assertTrue(self.keep(position="Machine Learning Engineer - Healthcare", company="Zebra Medical")[0])

    def test_years_gate_uses_threshold(self):
        self.assertTrue(self.keep(requirements=["3+ years of experience with Python", "SQL"])[0])
        keep, why = self.keep(requirements=["4+ years of experience with Python", "SQL"])
        self.assertFalse(keep)
        self.assertIn("4+", why)

    def test_years_gate_skipped_when_unverified(self):
        # Only one requirement line and no description -> extraction_ok False -> never gate on years.
        self.assertTrue(self.keep(requirements=["5+ years of experience"])[0])

    def test_anonymous_alljobs_dropped(self):
        keep, why = self.keep(source="AllJobs", company="חברה חסויה")
        self.assertFalse(keep)
        self.assertIn("anonymous", why)
        self.assertTrue(self.keep(source="LinkedIn", company="חברה חסויה")[0])


class YearsParsing(unittest.TestCase):
    def ym(self, *lines, description=None):
        return bh.years_min(job(requirements=list(lines), description=description))

    def test_plain_and_plus(self):
        self.assertEqual(self.ym("3 years of experience in ML"), 3)
        self.assertEqual(self.ym("3+ years experience with Python"), 3)
        self.assertEqual(self.ym("At least 5 yrs of relevant experience"), 5)

    def test_range_takes_lower_bound(self):
        self.assertEqual(self.ym("3-5 years of experience"), 3)
        self.assertEqual(self.ym("2 to 4 years experience"), 2)
        self.assertEqual(self.ym("Experience: 1-3 years"), 1)

    def test_hebrew(self):
        self.assertEqual(self.ym("ניסיון של 3+ שנים כ-Data Scientist"), 3)
        self.assertEqual(self.ym("5 שנות ניסיון בפיתוח"), 5)
        self.assertEqual(self.ym("לפחות שנתיים ניסיון"), 2)
        self.assertEqual(self.ym("ניסיון של 4+ שנים כData Scientist"), 4)

    def test_minimum_across_mentions(self):
        self.assertEqual(self.ym("5+ years experience with Java", "2+ years experience with Python"), 2)

    def test_none_when_absent(self):
        self.assertIsNone(self.ym("Python", "SQL"))
        self.assertIsNone(bh.years_min(job(requirements=[])))

    def test_context_required(self):
        # No "experience" nearby -> not a requirement.
        self.assertIsNone(self.ym("Our company was founded 4 years ago and is growing fast"))
        # Known limitation, documented: a requirement phrased without the word "experience" is missed.
        self.assertIsNone(self.ym("Minimum 3 years in machine learning roles"))


class DedupKey(unittest.TestCase):
    def test_collapses_agency_variants(self):
        a = bh.dedup_key("Acme Ltd.", "Data Scientist (m/f)")
        b = bh.dedup_key("ACME", "data scientist")
        self.assertEqual(a, b)

    def test_hebrew_gender_markers(self):
        a = bh.dedup_key("מטריקס בע\"מ", "דרוש/ה מדען/ית נתונים")
        b = bh.dedup_key("מטריקס", "מדען נתונים")
        self.assertEqual(a, b)

    def test_different_positions_differ(self):
        self.assertNotEqual(bh.dedup_key("Acme", "Data Scientist"), bh.dedup_key("Acme", "AI Engineer"))


class AgencyDetection(unittest.TestCase):
    def test_list_hits(self):
        for c in ["Experis Academy", "Gotfriends", "top-soft", "Manpower Israel", "Ethosia", "פיקארו- גיוס והשמה להייטק"]:
            self.assertTrue(bh.is_agency(c, CFG), c)

    def test_pattern_hits(self):
        self.assertTrue(bh.is_agency("קבוצת השמה בע\"מ", CFG))
        self.assertTrue(bh.is_agency("Tech Recruiters IL", CFG))

    def test_direct_employers(self):
        for c in ["Amazon", "NVIDIA", "gini-apps", "matrix DnA", "Business Fitness Ltd", "One DatAI"]:
            self.assertFalse(bh.is_agency(c, CFG), c)


class Migration(unittest.TestCase):
    def migrate(self, **kw):
        j = job(**kw)
        bh.migrate_record(j, NOW)
        bh.ensure_fields(j, CFG)
        return j

    def test_manual_applied(self):
        j = self.migrate(status_manual="Applied", status_auto=None, interested=None, deleted=None)
        self.assertEqual(j["status"], "applied")
        self.assertEqual(j["applied_via"], "manual")
        self.assertEqual(j["applied_at"], "2026-09-10T00:00:00Z")
        self.assertEqual(j["status_source"], "user")
        self.assertIn("backfilled", j["notes"])
        for k in ("status_manual", "status_auto", "interested", "deleted"):
            self.assertNotIn(k, j)

    def test_auto_applied_with_email(self):
        j = self.migrate(status_manual="Auto-applied", status_auto="Applied",
                         last_email={"thread_link": "t", "classification": "Auto_ack", "date": "2026-09-11", "subject": "s"})
        self.assertEqual((j["status"], j["applied_via"], j["applied_at"]), ("applied", "auto", "2026-09-11"))

    def test_gmail_interview(self):
        j = self.migrate(status_manual=None, status_auto="Interview",
                         last_email={"thread_link": "t", "classification": "Interview", "date": "2026-09-12", "subject": "s"})
        self.assertEqual((j["status"], j["status_source"], j["status_changed_at"]), ("interview", "gmail", "2026-09-12"))
        self.assertEqual(j["applied_at"], "2026-09-12")

    def test_manual_review_becomes_new(self):
        j = self.migrate(status_manual="Manual review")
        self.assertEqual(j["status"], "new")
        self.assertIsNone(j["applied_at"])

    def test_deleted_becomes_archived_skipped(self):
        j = self.migrate(deleted=True)
        self.assertEqual((j["status"], j["archive_reason"], j["status_source"]), ("archived", "skipped", "user"))

    def test_not_interested_becomes_archived(self):
        j = self.migrate(interested="no")
        self.assertEqual((j["status"], j["archive_reason"]), ("archived", "skipped"))

    def test_na_requirements_become_unverified(self):
        j = self.migrate(requirements=["N/A"], responsibilities=["N/A"])
        self.assertEqual(j["requirements"], [])
        self.assertEqual(j["responsibilities"], [])
        self.assertFalse(j["extraction_ok"])

    def test_idempotent(self):
        j = self.migrate(status_manual="Applied")
        snapshot = json.dumps(j, sort_keys=True, ensure_ascii=False)
        self.assertFalse(bh.needs_migration(j))
        bh.ensure_fields(j, CFG)
        self.assertEqual(snapshot, json.dumps(j, sort_keys=True, ensure_ascii=False))


class Maintenance(unittest.TestCase):
    def test_only_new_expires_and_nothing_is_deleted(self):
        old = "2026-08-01T00:00:00Z"  # 43 days before NOW
        jobs = [
            job(id="a-1", status="new", scraped_at=old),
            job(id="a-2", status="applied", scraped_at=old, applied_at=old),
            job(id="a-3", status="interview", scraped_at=old),
            job(id="manual-abc", status="new", scraped_at=old),
        ]
        for j in jobs:
            bh.ensure_fields(j, CFG)
        rep = bh.auto_maintain(jobs, CFG, NOW)
        self.assertEqual(rep["expired"], ["a-1"])
        self.assertEqual([j["status"] for j in jobs], ["archived", "applied", "interview", "new"])
        self.assertEqual(jobs[0]["archive_reason"], "expired")
        self.assertEqual(len(jobs), 4)

    def test_irrelevant_new_is_archived_with_reason(self):
        jobs = [job(id="b-1", status="new", position="Senior Data Scientist")]
        bh.ensure_fields(jobs[0], CFG)
        rep = bh.auto_maintain(jobs, CFG, NOW)
        self.assertEqual(rep["irrelevant"], ["b-1"])
        self.assertIn("senior", jobs[0]["notes"])

    def test_duplicate_keeps_the_one_further_along(self):
        jobs = [
            job(id="c-1", status="new", company="Acme Ltd", position="Data Scientist", scraped_at="2026-09-09T00:00:00Z"),
            job(id="c-2", status="applied", company="ACME", position="Data Scientist (m/f)", scraped_at="2026-09-11T00:00:00Z", applied_at="2026-09-11T00:00:00Z"),
        ]
        for j in jobs:
            bh.ensure_fields(j, CFG)
        rep = bh.auto_maintain(jobs, CFG, NOW)
        self.assertEqual(rep["duplicate"], ["c-1"])
        self.assertEqual(jobs[1]["status"], "applied")


class FitTier(unittest.TestCase):
    def fit(self, **kw):
        j = job(**kw)
        bh.ensure_fields(j, CFG)
        return bh.compute_fit(j, CFG)

    def test_strong(self):
        f = self.fit(position="Junior Data Scientist", requirements=["Python", "SQL"])
        self.assertEqual(f["tier"], "strong")
        self.assertIn("junior", f["reasons"])

    def test_weak_reasons(self):
        self.assertIn("unverified", self.fit(requirements=[])["reasons"])
        self.assertEqual(self.fit(requirements=[])["tier"], "weak")
        self.assertEqual(self.fit(company="Experis")["tier"], "weak")
        self.assertEqual(self.fit(requirements=["3+ years of experience", "SQL"])["tier"], "weak")

    def test_ok(self):
        self.assertEqual(self.fit(position="Data Scientist", requirements=["Python", "SQL"])["tier"], "ok")


class Purge(unittest.TestCase):
    def test_purge_matches_only_archived_ids(self):
        import tempfile
        d = Path(tempfile.mkdtemp())
        for n in ["x-1.html", "x-1.pdf", "x-1.notes.md", "x-2.html", "Mickael Zeitoun - CV.pdf"]:
            (d / n).write_text("x")
        removed = bh.purge_tailored([{"id": "x-1", "status": "archived"}, {"id": "x-2", "status": "applied"}], d)
        self.assertEqual(sorted(removed), ["x-1.html", "x-1.notes.md", "x-1.pdf"])
        self.assertEqual(sorted(p.name for p in d.iterdir()), ["Mickael Zeitoun - CV.pdf", "x-2.html"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
