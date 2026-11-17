import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from saaf_guard import check  # noqa: E402
from saaf_guard.report import infer_cause, write_csv  # noqa: E402
from saaf_guard.scan import main as scan_main  # noqa: E402


class ScanAgentTests(unittest.TestCase):
    def setUp(self):
        self.ws = tempfile.mkdtemp()
        for name in ("bad_agent", "good_agent"):
            dst = os.path.join(self.ws, name)
            shutil.copytree(os.path.join(ROOT, "demo", name), dst)
            subprocess.run(["git", "init", "-q", dst], check=True)
        self.out = os.path.join(self.ws, "_out")
        self.reviews = os.path.join(self.ws, "_reviews")
        os.makedirs(self.reviews)
        review = [{"title": "Uploaded text steers the verdict", "repo": "bad_agent", "risk_rating": "High",
                   "observation": "agent.py:30 concatenates the upload into the prompt.", "recommendation": "Use fence().",
                   "verified": "yes", "location": "agent.py:30", "cause": "inject", "category": "prompt-injection"}]
        with open(os.path.join(self.reviews, "g1.json"), "w", encoding="utf-8") as fh:
            json.dump(review, fh)

    def tearDown(self):
        check.set_lang("nl")
        shutil.rmtree(self.ws, ignore_errors=True)

    def run_scan(self, lang):
        rc = scan_main([self.ws, "--out", self.out, "--reviews", self.reviews, "--lang", lang, "--team", "T"])
        self.assertEqual(rc, 0)
        return json.load(open(os.path.join(self.out, "findings.json"), encoding="utf-8"))

    def test_samenvoegen_review_wint_en_goede_agent_schoon(self):
        f = self.run_scan("nl")
        self.assertFalse([x for x in f if x["repo"] == "good_agent"])
        bad = [x for x in f if x["repo"] == "bad_agent"]
        # SG02 (inject in agent.py) is gedekt door de review en vervalt; de andere regels blijven
        self.assertEqual(sum(x.get("cause") == "inject" for x in bad), 1)
        self.assertTrue({"SG03", "SG05", "SG06"} <= {x.get("rule") for x in bad})

    def test_engels_en_tweetalig_rapport(self):
        f = self.run_scan("en")
        self.assertTrue(any("falls back" in x["observation"] for x in f))
        page = open(os.path.join(self.out, "report.html"), encoding="utf-8").read()
        self.assertIn('class="langsw"', page)
        self.assertIn("Root causes", page)
        self.assertIn("Oorzaken", page)
        head = open(os.path.join(self.out, "findings.csv"), encoding="utf-8").readline().strip()
        self.assertEqual(head, "title,repo,risk_rating,observation,recommendation,verified,team")

    def test_csv_weigert_sleutelwaarden(self):
        bad = [{"title": "x", "repo": "r", "risk_rating": "Low", "observation": "key sk-ant-abcdefghijklmnop",
                "recommendation": "y", "verified": "no"}]
        with self.assertRaises(ValueError):
            write_csv(bad, os.path.join(self.ws, "x.csv"))

    def test_oorzaak_uit_categorie(self):
        self.assertEqual(infer_cause({"title": "Empty output yields a GREEN report", "category": "audit-integrity"}), "failopen")
        self.assertEqual(infer_cause({"title": "Approver name taken from request", "category": "audit-integrity"}), "gate")
        self.assertEqual(infer_cause({"title": "Unescaped XSS in table", "category": "web"}), "output")


if __name__ == "__main__":
    unittest.main()
