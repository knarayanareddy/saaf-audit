DIFF = """diff --git a/skills/x/SKILL.md b/skills/x/SKILL.md
--- a/skills/x/SKILL.md
+++ b/skills/x/SKILL.md
@@ -1,1 +1,1 @@
-Escalation is required above the limit.
+Escalation is plausible above the limit.
"""

OK_DIFF = """--- a/skills/x/SKILL.md
+++ b/skills/x/SKILL.md
@@ -1,1 +1,1 @@
-Escalation is required above the limit.
+Escalation is required above the limit of EUR 10,000; you should log it.
"""


def test_detects_softening(softening_tool):
    assert softening_tool.find_softening(DIFF)


def test_allows_clarification_that_keeps_requirement(softening_tool):
    assert not softening_tool.find_softening(OK_DIFF)
