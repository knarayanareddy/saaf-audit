#!/usr/bin/env python3
"""Tests for generate_dashboard.py: PDCA parsing, sector/repo resolution and progress roll-ups.

Run from the repo root: python3 tools/scripts/test_generate_dashboard.py
Uses only the standard library and the plan files in plans/ (no network, synthetic data only).
"""

import datetime
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import generate_dashboard as gd  # noqa: E402

PDCA_TABLE = """## {num}. PDCA{suffix}

| Phase | Status | Notes |
|---|---|---|
| **Plan** | {plan} | x |
| **Do** | {do} | x |
| **Check** | {check} | x |
| **Act** | {act} | x |
"""


def pdca_text(plan="Complete", do="Not started", check="Not started", act="Not started",
              num=11, suffix=" Positioning"):
    return PDCA_TABLE.format(num=num, suffix=suffix, plan=plan, do=do, check=check, act=act)


class ClassifyPdcaStatus(unittest.TestCase):
    def test_variants(self):
        cases = {
            "Complete": "complete",
            "✅ Complete": "complete",
            "Complete (MVP)": "complete",
            "In progress": "in_progress",
            "Not started": "not_started",
            "Pending": "not_started",
            "Not complete": "not_started",
            "Incomplete": "not_started",
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(gd.classify_pdca_status(text), expected)


class ParsePdca(unittest.TestCase):
    def test_any_section_number(self):
        # frank-heldens uses "## 12. PDCA"; it used to be read as all not_started.
        pdca = gd.parse_pdca(pdca_text(num=12, suffix="", plan="✅ Complete"))
        self.assertEqual(pdca["plan"], "complete")

    def test_mixed_statuses(self):
        pdca = gd.parse_pdca(pdca_text(do="In progress", check="Complete (MVP)", act="Pending"))
        self.assertEqual(pdca, {"plan": "complete", "do": "in_progress", "check": "complete", "act": "not_started"})

    def test_has_pdca(self):
        self.assertTrue(gd.has_pdca(pdca_text()))
        self.assertFalse(gd.has_pdca("# A plan\n\n## 10. Open questions\n\n- none\n"))
        # A PDCA heading without all four phases is not a usable table.
        self.assertFalse(gd.has_pdca("## 11. PDCA\n\n| **Plan** | Complete | x |\n"))


class Sectors(unittest.TestCase):
    VOCAB = ["General", "Banking", "Insurance", "Payments/Fintech", "Public sector", "Healthcare", "Other"]
    CFG = {
        "vocabulary": VOCAB,
        "default": "General",
        "organisation_rules": {"Mollie": ["Payments/Fintech"]},
        "assignments": {"mapped-plan": ["Banking"]},
    }

    def test_normalise(self):
        self.assertEqual(gd.normalise_sectors("banking, Insurance", self.VOCAB), ["Banking", "Insurance"])
        self.assertEqual(gd.normalise_sectors("Payments/Fintech", self.VOCAB), ["Payments/Fintech"])
        self.assertEqual(gd.normalise_sectors("Aviation", self.VOCAB), ["Other"])
        self.assertEqual(gd.normalise_sectors("Banking, banking", self.VOCAB), ["Banking"])

    def test_unfilled_template_placeholder_is_ignored(self):
        self.assertIsNone(gd.normalise_sectors("_Comma-separated, optional: General, Banking_", self.VOCAB))
        self.assertIsNone(gd.normalise_sectors("General / Banking / Insurance", self.VOCAB))
        self.assertIsNone(gd.normalise_sectors("", self.VOCAB))

    def test_precedence(self):
        own = gd.resolve_sectors("mapped-plan", {"sector": "Healthcare"}, "Mollie", self.CFG)
        self.assertEqual(own, {"sectors": ["Healthcare"], "sector_source": "plan"})
        mapped = gd.resolve_sectors("mapped-plan", {}, "Mollie", self.CFG)
        self.assertEqual(mapped, {"sectors": ["Banking"], "sector_source": "mapping"})
        org = gd.resolve_sectors("other", {}, "Mollie", self.CFG)
        self.assertEqual(org, {"sectors": ["Payments/Fintech"], "sector_source": "organisation"})
        default = gd.resolve_sectors("other", {}, "Anonymous", self.CFG)
        self.assertEqual(default, {"sectors": ["General"], "sector_source": "default"})


class Repos(unittest.TestCase):
    CFG = {"ignore_repos": ["SAAF-Project", "TipsAndTricks"], "assignments": {"no-repo": None, "ext": "someone/tool", "own": "Agent-X"}}

    def test_mapping_wins(self):
        self.assertIsNone(gd.resolve_repo("no-repo", {}, "github.com/SAAF-Project/Foo", self.CFG))
        ext = gd.resolve_repo("ext", {}, "", self.CFG)
        self.assertEqual(ext["url"], "https://github.com/someone/tool")
        self.assertEqual(gd.resolve_repo("own", {}, "", self.CFG)["url"], "https://github.com/SAAF-Project/Agent-X")

    def test_metadata_then_text(self):
        meta = {"repository": "https://github.com/SAAF-Project/Compliance-Report-Generator"}
        self.assertEqual(gd.resolve_repo("p", meta, "", self.CFG)["source"], "plan-metadata")
        text = "see github.com/SAAF-Project/SAAF-Project and github.com/SAAF-Project/Foo.git, github.com/SAAF-Project/Foo/blob/x"
        repo = gd.resolve_repo("p", {}, text, self.CFG)
        self.assertEqual((repo["name"], repo["source"]), ("Foo", "text-link"))

    def test_ignored_and_external_links_are_not_detected(self):
        text = "github.com/SAAF-Project/SAAF-Project github.com/SAAF-Project/TipsAndTricks github.com/other/Thing"
        self.assertIsNone(gd.resolve_repo("p", {}, text, self.CFG))


class RepoStatus(unittest.TestCase):
    REPO = {"name": "r"}
    CODE = [{"path": "tools/x"}]

    def test_statuses(self):
        self.assertEqual(gd.repo_status(self.REPO, [], [], False), "dedicated")
        self.assertEqual(gd.repo_status(self.REPO, [{"name": "old"}], [], False), "duplicate")
        self.assertEqual(gd.repo_status(self.REPO, [], self.CODE, False), "duplicate")
        self.assertEqual(gd.repo_status(None, [], self.CODE, False), "main-repo")
        self.assertEqual(gd.repo_status(None, [], [], False), "missing")
        self.assertEqual(gd.repo_status(None, [], [], True), "not-needed")
        # An existing repo or main-repo code always beats "not needed".
        self.assertEqual(gd.repo_status(self.REPO, [], [], True), "dedicated")

    def test_not_needed(self):
        cfg = {"no_repo_needed": {"strategy-plan": "x"}}
        self.assertTrue(gd.repo_not_needed("Reference", "a", cfg))
        self.assertTrue(gd.repo_not_needed("Framework", "a", cfg))
        self.assertTrue(gd.repo_not_needed("Workflow", "strategy-plan", cfg))
        self.assertFalse(gd.repo_not_needed("Agent", "a", cfg))

    def test_primary_and_duplicates_from_object_assignment(self):
        cfg = {"assignments": {"p": {"primary": "New-Repo", "duplicates": ["old_repo", "x/other"], "note": "n"}}}
        self.assertEqual(gd.resolve_repo("p", {}, "", cfg)["name"], "New-Repo")
        alternatives = gd.resolve_repo_alternatives("p", cfg)
        self.assertEqual([a["url"] for a in alternatives],
                         ["https://github.com/SAAF-Project/old_repo", "https://github.com/x/other"])
        self.assertEqual(gd.resolve_repo_alternatives("unmapped", cfg), [])
        self.assertEqual(gd.repo_note("p", cfg, "main note"), "n main note")

    def test_main_repo_code_must_exist_and_skips_nested_and_ignored(self):
        cfg = {"main_repo_code": {"p": {"paths": ["tools/scripts/track-5", "tools/does-not-exist"], "note": "n"}},
               "main_repo_ignore_prefixes": ["tools/scripts/test_data"]}
        text = ("tools/scripts/track-5/README.md tools/scripts/test_data/ad_export.csv "
                "tools/scripts/never-built.py tools/scripts/generate_dashboard.py")
        result = gd.resolve_main_repo_code("p", text, cfg)
        self.assertEqual([c["path"] for c in result["code"]],
                         ["tools/scripts/track-5", "tools/scripts/generate_dashboard.py"])
        self.assertEqual(result["code"][0]["source"], "mapping")
        self.assertEqual(result["code"][1]["source"], "plan-text")


class Rollup(unittest.TestCase):
    @staticmethod
    def record(pdca, known=True, repo=None):
        return {"pdca": pdca, "pdca_known": known, "progress": gd.plan_progress(pdca), "repo": repo,
                "repo_status": "dedicated" if repo else "missing"}

    def test_plan_progress_weights(self):
        pdca = {"plan": "complete", "do": "in_progress", "check": "not_started", "act": "not_started"}
        self.assertEqual(gd.plan_progress(pdca), 0.375)

    def test_unknown_plans_are_counted_but_not_averaged(self):
        done = {"plan": "complete", "do": "complete", "check": "complete", "act": "complete"}
        none = {"plan": "not_started", "do": "not_started", "check": "not_started", "act": "not_started"}
        result = gd.rollup([self.record(done), self.record(none, known=False, repo={"name": "r"})])
        self.assertEqual(result["plan_count"], 2)
        self.assertEqual(result["plans_unknown"], 1)
        self.assertEqual(result["progress"], 1.0)
        self.assertEqual(result["repo_count"], 1)
        self.assertEqual(result["repo_status"], {"missing": 1, "dedicated": 1})

    def test_empty(self):
        self.assertIsNone(gd.rollup([])["progress"])


def pdca_of(plan="complete", do="not_started", check="not_started", act="not_started"):
    return {"plan": plan, "do": do, "check": check, "act": act}


class KindsAndStages(unittest.TestCase):
    def test_kind_from_the_free_text_type(self):
        cases = {
            "Agent": "agent", "Workflow": "workflow", "Skill": "skill", "Reference": "document",
            "Framework + Reference": "document", "Framework + Workflow": "workflow",
            "Workflow (infrastructure for all Agents)": "workflow", "TBD": "unspecified", "": "unspecified",
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(gd.plan_kind(text), expected)

    def test_stages_follow_the_pdca_table(self):
        self.assertEqual(gd.stage_of("workflow", pdca_of("in_progress"), True, "missing"), 0)  # Draft plan
        self.assertEqual(gd.stage_of("workflow", pdca_of("complete"), True, "missing"), 1)  # Final plan
        self.assertEqual(gd.stage_of("workflow", pdca_of(do="in_progress"), True, "missing"), 2)  # Building
        self.assertEqual(gd.stage_of("workflow", pdca_of(do="complete"), True, "missing"), 3)  # Ready
        self.assertEqual(gd.stage_of("workflow", pdca_of(do="complete", check="in_progress"), True, "missing"), 4)  # Tested
        self.assertEqual(gd.stage_of("workflow", pdca_of(do="complete", check="complete", act="in_progress"), True, "missing"), 5)  # Improving

    def test_no_pdca_table_stays_in_draft_plan(self):
        self.assertEqual(gd.stage_of("agent", pdca_of(do="complete"), False, "dedicated"), 0)

    def test_an_agent_needs_a_repo_to_leave_the_plan_stages(self):
        building = pdca_of(do="in_progress")
        self.assertEqual(gd.stage_of("agent", building, True, "missing"), 1)  # held at Final plan
        self.assertEqual(gd.stage_of("agent", pdca_of("in_progress", do="in_progress"), True, "missing"), 0)
        for status in ("dedicated", "duplicate", "main-repo"):
            self.assertEqual(gd.stage_of("agent", building, True, status), 2, status)
        # other kinds are not held back by a missing repo
        for kind in ("workflow", "skill", "document", "unspecified"):
            self.assertEqual(gd.stage_of(kind, building, True, "missing"), 2, kind)


class Alerts(unittest.TestCase):
    TODAY = datetime.date(2026, 10, 8)

    def rec(self, **over):
        base = {
            "kind": "agent", "pdca": pdca_of(), "pdca_known": True, "stage": 1, "status": "Presented",
            "repo": None, "repo_alternatives": [], "main_repo_code": [], "repo_status": "missing",
            "track_source": "workstreams", "track": 1, "track_reason": "", "updated": "2026-10-01",
        }
        base.update(over)
        return base

    def ids(self, **over):
        return [a["id"] for a in gd.plan_alerts(self.rec(**over), self.TODAY)]

    def test_catalog_is_consistent(self):
        ids = [a["id"] for a in gd.ALERT_CATALOG]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue({a["severity"] for a in gd.ALERT_CATALOG} <= {"error", "warning", "info"})

    def test_a_clean_plan_has_no_alerts(self):
        self.assertEqual(self.ids(), [])

    def test_claims_building_without_a_repo_is_an_agent_alert(self):
        building = pdca_of(do="in_progress")
        self.assertIn("claims-building-no-repo", self.ids(pdca=building))
        self.assertNotIn("claims-building-no-repo", self.ids(pdca=building, repo_status="dedicated", repo={"name": "r"}))
        self.assertNotIn("claims-building-no-repo", self.ids(pdca=building, kind="workflow"))

    def test_pdca_missing_and_out_of_sync(self):
        self.assertIn("pdca-missing", self.ids(pdca_known=False))
        self.assertIn("pdca-out-of-sync", self.ids(pdca=pdca_of("not_started", do="complete")))
        self.assertIn("pdca-out-of-sync", self.ids(pdca=pdca_of(check="complete")))  # Check done, Do not started
        self.assertNotIn("pdca-out-of-sync", self.ids(pdca=pdca_of(do="complete", check="in_progress")))

    def test_duplicate_repos_and_code_in_the_main_repo(self):
        # code in the main repo is shown in the Repo Annex, but is not an alert of its own
        repo = {"name": "primary"}
        dup = self.ids(repo=repo, repo_alternatives=[{"name": "old"}], repo_status="duplicate")
        self.assertIn("duplicate-repos", dup)
        copy = self.ids(repo=repo, main_repo_code=[{"path": "tools/x"}], repo_status="duplicate")
        self.assertIn("duplicate-repos", copy)
        self.assertNotIn("code-in-main-repo", copy)
        only_main = self.ids(main_repo_code=[{"path": "tools/x"}], repo_status="main-repo")
        self.assertNotIn("code-in-main-repo", only_main)
        self.assertNotIn("code-in-main-repo", [a["id"] for a in gd.ALERT_CATALOG])
        self.assertNotIn("duplicate-repos", only_main)

    def test_repo_but_do_not_started(self):
        self.assertIn("repo-not-started", self.ids(repo={"name": "r"}, repo_status="dedicated"))
        self.assertNotIn("repo-not-started", self.ids(repo={"name": "r"}, repo_status="dedicated", pdca=pdca_of(do="in_progress")))

    def test_repo_shared_between_plans(self):
        def rec(slug, repo):
            return {"slug": slug, "repo": {"name": repo} if repo else None, "alerts": [{"id": "status-draft", "severity": "info", "message": ""}]}
        plans = [rec("a", "Same-Repo"), rec("b", "same-repo"), rec("c", "other"), rec("d", None)]
        gd.add_shared_repo_alerts(plans)
        shared = {r["slug"]: [a["id"] for a in r["alerts"]] for r in plans}
        self.assertEqual(shared["a"], ["repo-shared", "status-draft"])  # catalog order kept
        self.assertEqual(shared["b"], ["repo-shared", "status-draft"])
        self.assertEqual(shared["c"], ["status-draft"])
        self.assertEqual(shared["d"], ["status-draft"])
        self.assertIn("b", plans[0]["alerts"][0]["message"])

    def test_status_draft_only_when_the_plan_is_complete(self):
        self.assertIn("status-draft", self.ids(status="Draft"))
        self.assertNotIn("status-draft", self.ids(status="Draft", pdca=pdca_of("in_progress")))
        self.assertNotIn("status-draft", self.ids(status="Finalised"))
        severity = next(a["severity"] for a in gd.ALERT_CATALOG if a["id"] == "status-draft")
        self.assertEqual(severity, "info")  # 56 of 66 plans: a piece tag would carry no information

    def test_stale_pdca_needs_a_known_age(self):
        working = pdca_of(do="in_progress")
        kwargs = dict(pdca=working, kind="workflow")
        self.assertIn("pdca-stale", self.ids(updated="2026-04-17", **kwargs))
        self.assertNotIn("pdca-stale", self.ids(updated="2026-09-01", **kwargs))
        self.assertNotIn("pdca-stale", self.ids(updated=None, **kwargs))  # shallow clone: no false alarm
        self.assertNotIn("pdca-stale", self.ids(updated="2026-04-17", pdca=pdca_of(do="complete"), kind="workflow"))

    def test_proposed_track(self):
        self.assertIn("proposed-track", self.ids(track_source="proposed", track_reason="Agent infrastructure"))
        rec = self.rec(track_source="proposed", track=5, track_reason="Compliance harness for AI usage")
        msg = [a for a in gd.plan_alerts(rec, track_names={5: "AI Governance"}) if a["id"] == "proposed-track"][0]["message"]
        self.assertIn("AI Governance", msg)
        self.assertIn("Compliance harness for AI usage", msg)
        self.assertIn("Not a problem with the plan", msg)


class RealPlans(unittest.TestCase):
    """Invariants over the generated hierarchy built from the actual plan files."""

    @classmethod
    def setUpClass(cls):
        cls.progress = json.loads((gd.OUT_DIR / "progress.json").read_text())
        cls.plans_json = json.loads((gd.OUT_DIR / "plans.json").read_text())

    def test_every_plan_is_in_exactly_one_part(self):
        slugs = [s for part in self.progress["parts"] for s in part["plans"]]
        self.assertEqual(len(slugs), len(set(slugs)))
        self.assertEqual(set(slugs), {p["slug"] for p in self.plans_json})

    def test_part_counts_add_up_to_project(self):
        self.assertEqual(sum(p["plan_count"] for p in self.progress["parts"]), self.progress["project"]["plan_count"])
        self.assertEqual(self.progress["project"]["plan_count"], len(self.plans_json))

    def test_phase_counts_match_known_plans(self):
        project = self.progress["project"]
        known = project["plan_count"] - project["plans_unknown"]
        self.assertEqual(sum(project["phases"].values()), known * 4)

    def test_quarry_holds_only_plans_without_track_or_proposal(self):
        quarry = next(p for p in self.progress["parts"] if p["id"] == "quarry")
        proposals = json.loads((gd.META_DIR / "track-proposals.json").read_text())["proposals"]
        untracked = {p["slug"] for p in self.plans_json if p["track"] is None and p["slug"] not in proposals}
        self.assertEqual(set(quarry["plans"]), untracked)

    def test_workstream_tracks_win_over_proposals(self):
        by_slug = {p["slug"]: p for p in self.progress["plans"]}
        for plan in self.plans_json:
            record = by_slug[plan["slug"]]
            if plan["track"] is not None:
                self.assertEqual((record["track"], record["track_source"]), (plan["track"], "workstreams"))
            elif record["track"] is not None:
                self.assertEqual(record["track_source"], "proposed")
                self.assertTrue(record["track_reason"], plan["slug"])

    def test_proposals_only_name_real_plans_and_tracks(self):
        proposals = json.loads((gd.META_DIR / "track-proposals.json").read_text())["proposals"]
        slugs = {p["slug"] for p in self.plans_json}
        self.assertTrue(set(proposals) <= slugs, set(proposals) - slugs)
        self.assertTrue({v["track"] for v in proposals.values()} <= {0, 1, 2, 3, 4, 5})

    def test_annex_matches_repo_status(self):
        expected = {p["slug"] for p in self.progress["plans"] if p["repo_status"] in ("duplicate", "main-repo")}
        self.assertEqual({i["plan"] for i in self.progress["annex"]["items"]}, expected)
        self.assertTrue(self.progress["annex"]["guidance"]["duplicate"]["steps"])
        self.assertTrue(self.progress["annex"]["guidance"]["main-repo"]["steps"])

    def test_main_repo_code_exists_on_disk(self):
        for plan in self.progress["plans"]:
            for code in plan["main_repo_code"]:
                self.assertTrue((gd.ROOT / code["path"]).exists(), code["path"])

    def test_primary_repo_is_never_also_listed_as_duplicate(self):
        for plan in self.progress["plans"]:
            if plan["repo"]:
                self.assertNotIn(plan["repo"]["name"], [a["name"] for a in plan["repo_alternatives"]])

    def test_known_parser_fixes(self):
        by_slug = {p["slug"]: p for p in self.progress["plans"]}
        self.assertEqual(by_slug["frank-heldens-llm-finding-fact-check-agent"]["pdca"]["plan"], "complete")
        self.assertFalse(by_slug["table-9-execution-plan"]["pdca_known"])

    def test_sectors_are_in_vocabulary(self):
        vocab = set(self.progress["sector_vocabulary"])
        for plan in self.progress["plans"]:
            self.assertTrue(plan["sectors"])
            self.assertTrue(set(plan["sectors"]) <= vocab, plan["slug"])

    def test_every_plan_has_a_kind_a_stage_and_valid_alerts(self):
        catalog = {a["id"]: a["severity"] for a in self.progress["alert_catalog"]}
        self.assertEqual(self.progress["schema_version"], 2)
        self.assertEqual([s["id"] for s in self.progress["stages"]], list(range(6)))
        for plan in self.progress["plans"]:
            self.assertIn(plan["kind"], self.progress["kinds"], plan["slug"])
            self.assertEqual(self.progress["stages"][plan["stage"]]["key"], plan["stage_key"], plan["slug"])
            for alert in plan["alerts"]:
                self.assertEqual(catalog[alert["id"]], alert["severity"], plan["slug"])

    def test_agents_without_a_repo_never_pass_the_plan_stages(self):
        for plan in self.progress["plans"]:
            if plan["kind"] == "agent" and plan["repo_status"] not in ("dedicated", "duplicate", "main-repo"):
                self.assertLessEqual(plan["stage"], 1, plan["slug"])

    def test_a_plan_without_a_pdca_table_is_a_draft_plan_with_an_alert(self):
        for plan in self.progress["plans"]:
            if not plan["pdca_known"]:
                self.assertEqual(plan["stage"], 0, plan["slug"])
                self.assertIn("pdca-missing", [a["id"] for a in plan["alerts"]], plan["slug"])


if __name__ == "__main__":
    unittest.main()
