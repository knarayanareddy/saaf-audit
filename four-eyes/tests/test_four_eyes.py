"""Tests for Four Eyes. Run: python -m unittest discover -s tests -v"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from four_eyes import (  # noqa: E402
    ApprovalInvalid,
    ApprovalRejected,
    Gate,
    GateMisconfigured,
    short_code,
    verify_log,
)
from four_eyes.testkit import FourEyesBypassTests  # noqa: E402

KEY = b"unit-test-key-0123456789"


class Clock:
    def __init__(self, now: float = 1_000_000.0):
        self.now = now

    def __call__(self) -> float:
        return self.now


# ---------------------------------------------------------------------------
# A tiny reference agent: drafts a report, releases it only through the gate.
# The test kit runs against it exactly as it would against a real SAAF agent.
# ---------------------------------------------------------------------------


class ReferenceAgent:
    def __init__(self):
        self.published: list[str] = []

    def draft(self) -> dict:
        return {"report": "Finding F-01: access reviews are not performed. Rating: High."}

    def publish(self, gate: Gate, state: dict, approval) -> str:
        gate.require("final_report", state["report"], approval)
        self.published.append(state["report"])
        return state["report"]


class TestKitOnReferenceAgent(FourEyesBypassTests, unittest.TestCase):
    STEP = "final_report"

    def prepare(self, gate):
        self.agent = ReferenceAgent()
        return self.agent.draft()

    def artefact(self, state):
        return state["report"]

    def tamper(self, state):
        return {"report": state["report"].replace("High", "Low")}

    def release(self, gate, state, approval):
        return self.agent.publish(gate, state, approval)


# ---------------------------------------------------------------------------
# The gate itself
# ---------------------------------------------------------------------------


class GateBasics(unittest.TestCase):
    def test_fails_closed_without_a_key(self):
        with self.assertRaises(GateMisconfigured):
            Gate(lambda: "a", key_env="FOUR_EYES_KEY_THAT_IS_NOT_SET")
        with self.assertRaises(GateMisconfigured):
            Gate(lambda: "a", key="short")

    def test_phrase_names_the_content(self):
        gate = Gate(lambda: "a", key=KEY)
        self.assertEqual(gate.confirmation_phrase("x"), f"APPROVE {short_code('x')}")
        self.assertNotEqual(gate.confirmation_phrase("x"), gate.confirmation_phrase("y"))

    def test_strict_four_eyes_rejects_self_approval(self):
        gate = Gate(lambda: "Robin", key=KEY)
        with self.assertRaises(ApprovalRejected):
            gate.approve("final", "x", gate.confirmation_phrase("x"), prepared_by="robin")
        approval = gate.approve("final", "x", gate.confirmation_phrase("x"), prepared_by="Sam")
        self.assertEqual(approval.approver, "Robin")

    def test_approval_expires(self):
        clock = Clock()
        gate = Gate(lambda: "a", key=KEY, clock=clock, max_age_seconds=60)
        approval = gate.approve("final", "x", gate.confirmation_phrase("x"))
        clock.now += 61
        with self.assertRaises(ApprovalInvalid):
            gate.require("final", "x", approval)

    def test_approval_for_another_step_is_refused(self):
        gate = Gate(lambda: "a", key=KEY)
        approval = gate.approve("draft", "x", gate.confirmation_phrase("x"))
        with self.assertRaises(ApprovalInvalid):
            gate.require("final", "x", approval)

    def test_approval_survives_a_round_trip_through_json(self):
        gate = Gate(lambda: "a", key=KEY)
        approval = gate.approve("final", "x", gate.confirmation_phrase("x"))
        travelled = json.loads(json.dumps(approval.to_dict()))
        gate.require("final", "x", travelled)

    def test_verify_checks_without_using_the_approval_up(self):
        gate = Gate(lambda: "a", key=KEY)
        approval = gate.approve("final", "x", gate.confirmation_phrase("x"))
        gate.verify("final", "x", approval)
        gate.verify("final", "x", approval)
        with self.assertRaises(ApprovalInvalid):
            gate.verify("final", "changed", approval)
        gate.require("final", "x", approval)
        with self.assertRaises(ApprovalInvalid):
            gate.verify("final", "x", approval)  # used up by require

    def test_garbage_approval_is_refused(self):
        gate = Gate(lambda: "a", key=KEY)
        for junk in ({}, {"step": "final"}, {"approved_at": "yesterday"}, "APPROVED"):
            with self.subTest(junk=junk), self.assertRaises(ApprovalInvalid):
                gate.require("final", "x", junk)


class Log(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "four-eyes-log.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def _run_session(self):
        gate = Gate(lambda: "reviewer", key=KEY, log_path=self.path)
        with self.assertRaises(ApprovalRejected):
            gate.approve("final", "x", "yes approve all")
        approval = gate.approve("final", "x", gate.confirmation_phrase("x"))
        gate.require("final", "x", approval)
        with self.assertRaises(ApprovalInvalid):
            gate.require("final", "x", approval)
        return approval

    def test_log_verifies_and_counts_events(self):
        self._run_session()
        ok, notes = verify_log(self.path, key=KEY)
        self.assertTrue(ok, notes)
        self.assertIn("1 approved", notes[0])
        self.assertIn("1 blocked", notes[0])
        self.assertIn("1 released", notes[0])
        self.assertIn("1 rejected", notes[0])

    def test_edited_log_line_is_detected(self):
        self._run_session()
        lines = self.path.read_text(encoding="utf-8").splitlines()
        entry = json.loads(lines[1])
        entry["approver"] = "someone else"
        lines[1] = json.dumps(entry, sort_keys=True)
        self.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        ok, notes = verify_log(self.path, key=KEY)
        self.assertFalse(ok)
        self.assertTrue(any("line 2" in n for n in notes))

    def test_removed_log_line_is_detected(self):
        self._run_session()
        lines = self.path.read_text(encoding="utf-8").splitlines()
        del lines[0]
        self.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        ok, _ = verify_log(self.path, key=KEY)
        self.assertFalse(ok)

    def test_a_damaged_log_fails_closed_and_is_reported(self):
        self._run_session()
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write('["not", "an", "entry"]\n{not json\n')
        with self.assertRaises(GateMisconfigured):
            Gate(lambda: "reviewer", key=KEY, log_path=self.path)
        ok, notes = verify_log(self.path, key=KEY)
        self.assertFalse(ok)
        self.assertTrue(any("not a log entry" in n for n in notes))
        self.assertTrue(any("not valid JSON" in n for n in notes))

    def test_used_approvals_stay_used_after_a_restart(self):
        approval = self._run_session()
        restarted = Gate(lambda: "reviewer", key=KEY, log_path=self.path)
        with self.assertRaises(ApprovalInvalid):
            restarted.require("final", "x", approval)
        ok, notes = verify_log(self.path, key=KEY)
        self.assertTrue(ok, notes)


if __name__ == "__main__":
    unittest.main()
