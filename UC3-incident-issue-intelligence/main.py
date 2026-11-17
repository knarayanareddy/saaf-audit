# Incident & Issue Intelligence Agent
#
# This agent transforms raw incident data into structured audit risk intelligence.
# This file contains the high-level workflow outline.
# Per step, the detailed Code and AI notes live in a separate Python module.


# 1. Set audit context
# Goal:
# Build the analysis context before any incident data is processed.
import workflow_steps.step_1_set_audit_context


# 2. Request, check, clean, and anonymize data
# Goal:
# Retrieve the minimum required incident data and make it safe and usable.
import workflow_steps.step_2_request_check_clean_anonymize_data


# 3. Select relevant incidents
# Goal:
# Reduce the full incident population to the subset relevant for the audit scope.
import workflow_steps.step_3_select_relevant_incidents


# 4. Classify and reconcile
# Goal:
# Assign each relevant incident to a risk/control taxonomy with defensible output.
import workflow_steps.step_4_classify_and_reconcile


# 5. Find patterns and root causes
# Goal:
# Move from single incidents to structural themes and recurring weaknesses.
import workflow_steps.step_5_find_patterns_and_root_causes


# 6. Assess materiality and priority
# Goal:
# Decide what deserves audit attention first.
import workflow_steps.step_6_assess_materiality_and_priority


# 7. Produce report with limitations
# Goal:
# Generate a usable Incident Intelligence Report without leaking sensitive data.
import workflow_steps.step_7_produce_report_with_limitations
