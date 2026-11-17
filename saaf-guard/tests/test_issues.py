import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from saaf_guard.issues import MARKER, build_body  # noqa: E402


class IssueTests(unittest.TestCase):
    F = [{"title": "NaN passes as MATCH", "repo": "r", "risk_rating": "High", "observation": "matcher.py:180",
          "recommendation": "within_tolerance()", "verified": "yes", "location": "matcher.py:180", "cause": "failopen"},
         {"title": "Open CORS", "repo": "r", "risk_rating": "Medium", "observation": "x", "recommendation": "y",
          "verified": "no", "cause": "open"}]

    def test_body_heeft_marker_checklist_en_ernst(self):
        title, body = build_body("r", self.F, "2026-11-10")
        self.assertIn(MARKER, body)
        self.assertIn("1 High, 1 Medium", title)
        self.assertEqual(body.count("- [ ] "), 2)
        self.assertLess(body.index("High"), body.index("Medium"))  # ernstigste eerst
        self.assertIn("not verified", body)

    def test_weigert_sleutelwaarden(self):
        bad = [dict(self.F[0], observation="key sk-ant-abcdefghijklmnopqrstu")]
        with self.assertRaises(ValueError):
            build_body("r", bad, "2026-11-10")


if __name__ == "__main__":
    unittest.main()
