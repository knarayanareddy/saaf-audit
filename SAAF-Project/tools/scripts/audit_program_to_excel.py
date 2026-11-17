"""
audit_program_to_excel.py — Generate a formatted Excel workbook from the
NovaPay Customer Onboarding Audit Program.

Usage:
    python3 tools/scripts/audit_program_to_excel.py <output-path>

Output:
    Excel workbook with 4 sheets:
      1. Risk Register (Policy-Stated)
      2. AI-Inferred Risks
      3. Control Register
      4. Audit Work Program (with ToD and ToE)

Part of the SAAF analyze-policy skill pipeline.
"""

import sys
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import (
    PatternFill, Font, Alignment, Border, Side, GradientFill
)
from openpyxl.utils import get_column_letter

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------
DARK_BLUE   = "1F3864"   # header background
MID_BLUE    = "2E5FA3"   # section sub-header
LIGHT_BLUE  = "D6E4F0"   # alternate row
AMBER       = "F4B942"   # attention / gap rows
GREEN       = "D9F0D3"   # control present
RED_LIGHT   = "FCE4E4"   # no control / gap
YELLOW_PALE = "FFFDE7"   # inferred risk rows
WHITE       = "FFFFFF"
FONT_WHITE  = "FFFFFF"
FONT_DARK   = "1A1A1A"

# ---------------------------------------------------------------------------
# Style helpers
# ---------------------------------------------------------------------------

def header_font(bold=True, color=FONT_WHITE, size=10):
    return Font(name="Calibri", bold=bold, color=color, size=size)

def body_font(bold=False, color=FONT_DARK, size=9):
    return Font(name="Calibri", bold=bold, color=color, size=size)

def fill(hex_color):
    return PatternFill("solid", fgColor=hex_color)

def wrap_align(horizontal="left", vertical="top"):
    return Alignment(wrap_text=True, horizontal=horizontal, vertical=vertical)

def thin_border():
    side = Side(style="thin", color="CCCCCC")
    return Border(left=side, right=side, top=side, bottom=side)

def apply_header_row(ws, row_num, values, col_widths=None):
    for col, val in enumerate(values, 1):
        cell = ws.cell(row=row_num, column=col, value=val)
        cell.fill = fill(DARK_BLUE)
        cell.font = header_font()
        cell.alignment = wrap_align("center", "center")
        cell.border = thin_border()
    if col_widths:
        for col, width in enumerate(col_widths, 1):
            ws.column_dimensions[get_column_letter(col)].width = width

def apply_body_row(ws, row_num, values, row_fill=WHITE, bold_col=None):
    for col, val in enumerate(values, 1):
        cell = ws.cell(row=row_num, column=col, value=val)
        cell.fill = fill(row_fill)
        cell.font = body_font(bold=(col == bold_col))
        cell.alignment = wrap_align()
        cell.border = thin_border()

def freeze_and_filter(ws, freeze_row=2):
    ws.freeze_panes = ws.cell(row=freeze_row, column=1)
    ws.auto_filter.ref = ws.dimensions

# ---------------------------------------------------------------------------
# Sheet 1: Policy-Stated Risk Register
# ---------------------------------------------------------------------------

POLICY_RISKS = [
    ("RS-01", "Money laundering through payment services",
     "Compliance / Financial Crime", "All onboarding and ongoing monitoring", "Sec. 1"),
    ("RS-02", "Terrorist financing via payment channels",
     "Compliance / Financial Crime", "All onboarding and ongoing monitoring", "Sec. 1"),
    ("RS-03", "Sanctions violations — transacting with sanctioned parties",
     "Compliance / Legal", "Screening (Sec. 12.1), ongoing monitoring", "Sec. 12.1"),
    ("RS-04", "PEP-related bribery and corruption risk",
     "Compliance / Reputational", "PEP screening, EDD (Sec. 12.2, 9.3)", "Sec. 12.2"),
    ("RS-05", "Identity fraud / impersonation at customer onboarding",
     "Operational / Fraud", "CIP (Sec. 8), CDD (Sec. 9)", "Sec. 8, 9"),
    ("RS-06", "Complex / opaque ownership structures obscuring beneficial ownership",
     "Compliance / Financial Crime", "UBO identification (Sec. 10)", "Sec. 10"),
    ("RS-07", "Cross-border remittance to high-risk or sanctioned jurisdictions",
     "Compliance / Financial Crime", "Transaction monitoring TM-03, TM-08", "Sec. 13.1"),
    ("RS-08", "Structuring / smurfing (deliberate transaction splitting)",
     "Compliance / Fraud", "Transaction monitoring TM-04", "Sec. 13.1"),
    ("RS-09", "Rapid fund layering (in-and-out movement)",
     "Compliance / Financial Crime", "Transaction monitoring TM-05", "Sec. 13.1"),
    ("RS-10", "Unusual transaction volume deviation from expected customer profile",
     "Operational", "Transaction monitoring TM-06", "Sec. 13.1"),
    ("RS-11", "Identity fraud specific to non-face-to-face onboarding",
     "Operational / Fraud", "Non-face-to-face channel (Sec. 9.5)", "Sec. 9.5"),
    ("RS-12", "Third-party / agent non-compliance with AML/CTF obligations",
     "Third Party", "Agent onboarding (Sec. 11)", "Sec. 11"),
    ("RS-13", "Adverse media indicating financial crime or reputational harm",
     "Reputational / Compliance", "Adverse media screening (Sec. 12.3)", "Sec. 12.3"),
]

def build_risk_register(wb):
    ws = wb.create_sheet("Risk Register (Policy-Stated)")
    ws.sheet_view.showGridLines = False

    # Title
    ws.merge_cells("A1:E1")
    title = ws["A1"]
    title.value = "POLICY-STATED RISK REGISTER  |  NP-POL-AML-001 v3.2  |  Customer Onboarding Audit 2026"
    title.fill = fill(DARK_BLUE)
    title.font = header_font(size=11)
    title.alignment = wrap_align("center", "center")
    ws.row_dimensions[1].height = 22

    headers = ["Risk ID", "Risk Description", "Category", "Process / Activity Affected", "Policy Source"]
    widths   = [10, 55, 28, 45, 14]
    apply_header_row(ws, 2, headers, widths)
    ws.row_dimensions[2].height = 18

    for i, row in enumerate(POLICY_RISKS, 3):
        row_fill = LIGHT_BLUE if i % 2 == 0 else WHITE
        apply_body_row(ws, i, row, row_fill=row_fill, bold_col=1)
        ws.row_dimensions[i].height = 30

    freeze_and_filter(ws, freeze_row=3)

# ---------------------------------------------------------------------------
# Sheet 2: AI-Inferred Risks
# ---------------------------------------------------------------------------

INFERRED_RISKS = [
    ("RI-01", "EWRA staleness or non-completion",
     "EWRA is referenced as NP-EWRA-[Year] with no specific year. If not completed annually, risk scoring model calibration is not validated against current business risk.",
     "Risk scoring (Sec. 6.2, 7.1)", "Compliance / Operational"),
    ("RI-02", "Risk scoring model calibration drift",
     "7-factor weights and score thresholds are fixed in Appendix A. No process is described for recalibrating factor weights or thresholds when the business profile or regulatory environment changes.",
     "Risk scoring (Sec. 7.1, Appendix A)", "Operational / Model"),
    ("RI-03", "Key person dependency — MLRO",
     "The MLRO is sole authority for SAR filing, high-risk approvals, EDD sign-off, and regulatory reporting. No succession plan or extended absence procedure exists beyond naming the Deputy MLRO.",
     "SAR filing, EDD, regulatory reporting", "People / Operational"),
    ("RI-04", "Alert fatigue from high false-positive screening rates",
     "KPI target for screening false positives is ≤15% but no minimum floor is set. Sustained high false-positive rates may cause analysts to dismiss alerts less carefully, masking genuine matches.",
     "Sanctions/PEP/Adverse Media screening (Sec. 12)", "Operational / Fraud"),
    ("RI-05", "Jurisdictional compliance gap (unresolved placeholders)",
     "Multiple placeholder fields for national regulations, sanctions lists, and FIU names are unresolved. In jurisdictions where these are not completed, NovaPay may operate without adequate local controls.",
     "Regulatory framework (Sec. 4), Screening (Sec. 12.1), SAR (Sec. 14.2)", "Compliance / Legal"),
    ("RI-06", "System outage affecting CDD completeness",
     "Section 18.3 escalates screening system outages to MLRO and NCA, but no fallback manual screening procedure is defined. A prolonged outage could result in onboarding without required screening.",
     "Screening (Sec. 12), GRC Platform", "Technology / Operational"),
    ("RI-07", "Self-reported UBO data inaccuracy",
     "UBO declarations are signed by the customer's authorised representative. No independent verification of declared ownership percentages against authoritative registries for standard-risk cases.",
     "UBO identification (Sec. 10)", "Compliance / Data Quality"),
    ("RI-08", "Training effectiveness — critical knowledge gaps",
     "Minimum pass score is 80%, meaning an employee may miss 20% of assessed content and still be deemed compliant. In AML/CTF contexts, specific procedural errors (e.g., tipping-off prohibition) carry criminal liability.",
     "Training (Sec. 17)", "People / Compliance"),
    ("RI-09", "Cooling-off period evasion through related parties",
     "Declined or terminated customers may reapply through related entities (same UBOs, new legal entity) after fewer than 12 months. No requirement exists to cross-reference the Involuntary Exit Register against UBOs of new applicants.",
     "Customer exit / Re-application (Sec. 16.3)", "Fraud / Compliance"),
    ("RI-10", "No proactive dormant account remediation",
     "TM-07 monitors reactivation of dormant accounts (≥180 days inactive), but no proactive process is described for periodically reviewing or closing accounts showing no sign of reactivation.",
     "Transaction monitoring (Sec. 13.1 TM-07)", "Operational / Financial Crime"),
    ("RI-11", "Insufficient EDD granularity for Non-Profit Organizations",
     "NPOs in high-risk jurisdictions are a mandatory EDD category (Sec. 9.4) but no NPO-specific verification steps are defined (e.g., assessment of funding sources, charitable purpose, beneficiary countries). FATF specifically identifies NPOs as high-risk.",
     "EDD (Sec. 9.4)", "Compliance / Financial Crime"),
    ("RI-12", "Agent network oversight insufficiency",
     "Annual compliance attestation is the primary ongoing control for agents. For high-volume or rapidly expanding agent networks, this may be insufficient to detect emerging compliance failures in a timely manner.",
     "Third-party / Agent onboarding (Sec. 11)", "Third Party / Compliance"),
]

def build_inferred_risks(wb):
    ws = wb.create_sheet("AI-Inferred Risks")
    ws.sheet_view.showGridLines = False

    ws.merge_cells("A1:E1")
    title = ws["A1"]
    title.value = "AI-INFERRED RISKS  |  NP-POL-AML-001 v3.2  |  Require auditor validation before inclusion in scope"
    title.fill = fill(MID_BLUE)
    title.font = header_font(size=11)
    title.alignment = wrap_align("center", "center")
    ws.row_dimensions[1].height = 22

    headers = ["Risk ID", "Risk Description", "Rationale", "Process / Activity Affected", "Category"]
    widths   = [10, 40, 65, 45, 28]
    apply_header_row(ws, 2, headers, widths)
    ws.row_dimensions[2].height = 18

    for i, row in enumerate(INFERRED_RISKS, 3):
        apply_body_row(ws, i, row, row_fill=YELLOW_PALE, bold_col=1)
        ws.row_dimensions[i].height = 48

    freeze_and_filter(ws, freeze_row=3)

# ---------------------------------------------------------------------------
# Sheet 3: Control Register
# ---------------------------------------------------------------------------

CONTROLS = [
    # (ID, Description, Type, Nature, Process, Risks Mitigated, Threshold/SLA, Testability, Source, has_gap)
    ("C-01 (AML-CIP-01)", "Customer identity collected and verified before relationship established",
     "Preventive", "Manual + System", "Customer Identification", "RS-05, RS-11",
     "100% completion required", "High", "Sec. 8, 9.1, App. E", False),
    ("C-02 (AML-CIP-02)", "Verification method matched to customer risk level and channel",
     "Preventive", "Manual", "Customer Identification", "RS-05, RS-11",
     "Per verification method table (Sec. 8.4)", "High", "Sec. 8.4, 9.5, App. E", False),
    ("C-03 (AML-CDD-03)", "Risk score assigned using approved 7-factor weighted model",
     "Detective", "Manual + System", "Risk Scoring", "RI-01, RI-02",
     "100% population; all 7 factors documented", "High", "Sec. 7.1, App. E", False),
    ("C-04 (AML-CDD-04)", "CDD approved by appropriate authority per risk band",
     "Preventive", "Manual", "CDD Approval", "RS-01, RS-02",
     "Per approval matrix Sec. 7.2", "High", "Sec. 7.2, 9.1, App. E", False),
    ("C-05 (AML-UBO-05)", "UBOs identified and verified for all legal entities",
     "Preventive", "Manual + System", "UBO Identification", "RS-06, RI-07",
     "100% of legal entity onboardings", "High", "Sec. 10, App. E", False),
    ("C-06 (AML-UBO-06)", "Multi-layered ownership structures documented to UBO level with MLRO approval",
     "Preventive", "Manual", "UBO Identification", "RS-06, RI-07, RI-09",
     "MLRO approval required for 3+ layer structures", "High", "Sec. 10.3, App. E", False),
    ("C-07 (AML-SCR-07)", "Sanctions screening at onboarding and within 24h of list updates",
     "Preventive", "Automated + Manual", "Screening", "RS-03",
     "Within 24 hours of list publication", "High", "Sec. 12.1, App. E", False),
    ("C-08 (AML-SCR-08)", "Potential sanctions matches resolved within 4 business hours",
     "Detective", "Manual", "Screening", "RS-03",
     "4 business hours", "High", "Sec. 12.1, App. E", False),
    ("C-09 (AML-PEP-09)", "PEP screening at onboarding and each periodic review",
     "Preventive", "Automated", "Screening / Periodic Review", "RS-04",
     "100% coverage at each review cycle", "High", "Sec. 12.2, App. E", False),
    ("C-10 (AML-PEP-10)", "EDD and MLRO approval for all confirmed PEP relationships",
     "Preventive", "Manual", "EDD", "RS-04",
     "MLRO approval mandatory", "High", "Sec. 9.3, 12.2, App. E", False),
    ("C-11 (AML-MON-11)", "Transaction monitoring — 8 scenarios calibrated and operational",
     "Detective", "Automated", "Ongoing Monitoring", "RS-07, RS-08, RS-09, RS-10",
     "8 scenarios per Sec. 13.1; semi-annual calibration review", "High", "Sec. 13.1, App. E", False),
    ("C-12 (AML-REV-12)", "Periodic reviews completed on or before due date",
     "Detective", "Manual + System", "Periodic Review", "RS-01–RS-04, RS-13",
     "≥90% on time; GRC reminder 60 days prior", "High", "Sec. 13.2, 7.2, App. E", False),
    ("C-13 (AML-SAR-13)", "Internal SAR assessed by MLRO within 24 hours",
     "Detective / Corrective", "Manual", "SAR Reporting", "RS-01, RS-02",
     "24 hours from receipt", "High", "Sec. 14.1, App. E", False),
    ("C-14 (AML-SAR-14)", "External SARs filed within statutory deadline",
     "Corrective", "Manual", "SAR Reporting", "RS-01, RS-02",
     "Statutory deadline [jurisdiction-specific — placeholder]", "High", "Sec. 14.2, App. E", False),
    ("C-15 (AML-REC-15)", "CDD records retained minimum 5 years post-relationship",
     "Directive", "Automated + Manual", "Record Keeping", "RS-01, RS-02",
     "5 years; retrieval within 3 business days", "High", "Sec. 15, App. E", False),
    ("C-16 (AML-EXC-16)", "Exceptions approved per delegation matrix",
     "Preventive", "Manual", "Exception Management", "All",
     "100% per matrix Sec. 18.2", "High", "Sec. 18.2, App. E", False),
    ("C-17 (AML-TRN-17)", "Annual AML/CTF training completed by all in-scope staff",
     "Directive", "Manual + System", "Training", "RI-08",
     "≥98% completion; 80% pass score", "High", "Sec. 17, App. E", False),
    ("C-18 (AML-QA-18)", "Second-line QA: 100% EDD file review quarterly",
     "Detective", "Manual", "Quality Assurance", "All EDD controls",
     "100% quarterly; 5% random sample all CDD files", "High", "Sec. 19.2, App. E", False),
    ("C-19", "Screening system outage — escalation to MLRO and NCA",
     "Corrective", "Manual", "Screening", "RI-06",
     "MLRO within 4 hours; NCA if >24 hours", "Medium", "Sec. 18.3", False),
    ("C-20", "Annual compliance attestation from third-party agents",
     "Detective", "Manual", "Agent Oversight", "RS-12, RI-12",
     "Annual; periodic compliance review for material relationships", "Medium", "Sec. 11.2", False),
    ("C-21", "EWRA conducted annually and Board-approved",
     "Directive", "Manual", "Risk Framework Governance", "RI-01, RI-02",
     "Annual; Board approval required", "Medium", "Sec. 6.2", False),
    ("C-22", "First-line QA: 10% random CDD file sample monthly",
     "Detective", "Manual", "Quality Assurance", "All CDD controls",
     "10% monthly; deficiencies remediated within 5 days", "High", "Sec. 19.1", False),
    # Gaps — risks with no control
    ("[No control]", "Risk scoring model recalibration — RI-02",
     "—", "—", "Risk Scoring", "RI-02",
     "—", "—", "Gap identified by AI analysis", True),
    ("[No control]", "MLRO succession and continuity — RI-03",
     "—", "—", "Governance", "RI-03",
     "—", "—", "Gap identified by AI analysis", True),
    ("[No control]", "Cooling-off period evasion cross-check — RI-09",
     "—", "—", "Customer Exit / Re-application", "RI-09",
     "—", "—", "Gap identified by AI analysis", True),
    ("[No control]", "Proactive dormant account remediation — RI-10",
     "—", "—", "Ongoing Monitoring", "RI-10",
     "—", "—", "Gap identified by AI analysis", True),
    ("[No control]", "NPO-specific EDD verification steps — RI-11",
     "—", "—", "EDD", "RI-11",
     "—", "—", "Gap identified by AI analysis", True),
]

def build_control_register(wb):
    ws = wb.create_sheet("Control Register")
    ws.sheet_view.showGridLines = False

    ws.merge_cells("A1:J1")
    title = ws["A1"]
    title.value = "CONTROL REGISTER  |  NP-POL-AML-001 v3.2  |  22 controls identified (18 from Appendix E + 4 by AI)  |  5 control gaps flagged"
    title.fill = fill(DARK_BLUE)
    title.font = header_font(size=11)
    title.alignment = wrap_align("center", "center")
    ws.row_dimensions[1].height = 22

    headers = ["Control ID", "Control Description", "Type", "Nature", "Process", "Risks Mitigated", "Threshold / SLA", "Testability", "Source", "Gap?"]
    widths   = [16, 55, 22, 20, 30, 25, 40, 12, 20, 8]
    apply_header_row(ws, 2, headers, widths)
    ws.row_dimensions[2].height = 18

    for i, row in enumerate(CONTROLS, 3):
        is_gap = row[-1]
        data = row[:-1]
        row_fill = RED_LIGHT if is_gap else (LIGHT_BLUE if i % 2 == 0 else WHITE)
        apply_body_row(ws, i, list(data) + ["YES" if is_gap else ""], row_fill=row_fill, bold_col=1)
        ws.row_dimensions[i].height = 36 if is_gap else 30

    freeze_and_filter(ws, freeze_row=3)

# ---------------------------------------------------------------------------
# Sheet 4: Audit Work Program
# ---------------------------------------------------------------------------

WORK_PROGRAM = [
    # (WP#, Process, Activity, Risk(s), Control(s), ToD, ToE)
    ("WP-01", "Customer Identification", "Identity data collection — natural persons",
     "RS-05 Identity fraud", "C-01",
     "Review Section 8.1 and 9.1. Confirm all mandatory data fields are listed and that verification is required before onboarding is completed. Confirm GRC platform is configured to enforce mandatory fields before file can be approved.",
     "Select a sample of 30 natural person onboarding files from the past 12 months. For each: verify all mandatory fields (name, DOB, nationality, address, TIN) are present and supported by verified documents dated before relationship establishment. Calculate the exception rate."),

    ("WP-02", "Customer Identification", "Identity data collection — legal entities",
     "RS-05, RS-06", "C-01",
     "Review Section 8.2 against a legal entity onboarding checklist. Confirm all 11 mandatory data elements are required in the GRC platform before approval can be granted.",
     "Select a sample of 25 legal entity onboarding files. For each: verify all 11 mandatory data elements are present with supporting documentation. Note any missing fields and calculate the deficiency rate."),

    ("WP-03", "Customer Identification", "Verification method selection — including non-face-to-face",
     "RS-05, RS-11 Non-face-to-face fraud", "C-02",
     "Review Section 8.4 verification methods table. Confirm the GRC platform or onboarding procedure requires documentation of the verification method used. Confirm controls prevent use of lower-assurance methods for higher-risk customers or non-face-to-face channels.",
     "From the WP-01 sample: for each file, confirm the verification method recorded matches the method permitted for the customer's risk level per Section 8.4. For non-face-to-face files specifically, confirm that the three additional measures in Section 9.5 (two independent sources, first payment check, IP geolocation) are each documented."),

    ("WP-04", "Risk Scoring", "7-factor risk model application",
     "RI-01 EWRA staleness, RI-02 Model drift", "C-03",
     "Review Section 7.1 and Appendix A. Confirm all 7 factors are defined with score criteria (1–5) and weights totalling 100%. Verify the GRC platform enforces all 7 factors before a score is generated and that no factor can be left blank.",
     "From the combined WP-01/WP-02 sample: for each file, independently re-calculate the expected risk score using Section 7.1 weights and Appendix A criteria. Compare to the score recorded in the CDD file. Investigate all discrepancies greater than 0.25 weighted points. Report the recalculation error rate."),

    ("WP-05", "Risk Scoring", "Approval authority per risk band",
     "RS-01, RS-02 Unauthorised approval", "C-04",
     "Review Section 7.2 approval matrix. Confirm the GRC platform workflow routes approvals to the correct role for each risk band and does not permit self-approval or bypass by a lower-authority role.",
     "From the combined WP-01/WP-02 sample: for each file, confirm the approval was granted by the role specified in Section 7.2 for the assigned risk band. Flag any files approved by a role with lower authority than required. Calculate the non-compliance rate."),

    ("WP-06", "Risk Scoring", "Automatic high-risk trigger assessment",
     "RS-03, RS-04, RS-06 Trigger override missed", "C-03, C-04",
     "Review Section 7.3 list of 8 automatic high-risk triggers. Confirm the GRC platform or onboarding checklist requires mandatory documentation of trigger assessment for each customer, and that the system automatically elevates risk to High when a trigger is present.",
     "Identify all customers onboarded as Medium-Low or Medium in the past 12 months. Select a sample of 20. For each CDD file: confirm all 8 triggers were assessed and none were present (or, if present, that risk was elevated to High). Flag any files where trigger assessment is not documented."),

    ("WP-07", "UBO Identification", "UBO identification and verification — standard cases",
     "RS-06 Complex ownership, RI-07 UBO data inaccuracy", "C-05",
     "Review Sections 10.1 and 10.2. Confirm the policy requires UBO declaration plus cross-check against a national commercial register or equivalent registry. Assess whether the GRC platform records UBO data separately from entity data, with its own verification status field.",
     "From the WP-02 legal entity sample: for each file, confirm a signed UBO declaration is present and that the declared UBO(s) match the commercial register extract on file. Assess whether the ownership chain is documented to the natural person level. Report the rate of files with incomplete or unverified UBO data."),

    ("WP-08", "UBO Identification", "Multi-layered / complex ownership structures",
     "RS-06, RI-07, RI-09 Evasion via related entities", "C-06",
     "Review Section 10.3 table. Confirm the GRC platform captures the ownership structure type (simple / multi-layer / listed company stop) and that structures with 3 or more layers are automatically routed to MLRO for review and approval.",
     "Identify all customers with a recorded ownership structure of 3 or more layers. For each: verify a full chain diagram is on file, independent verification is documented for each ownership layer, and MLRO approval is recorded in the GRC workflow. Report any files with incomplete chain documentation or missing MLRO approval."),

    ("WP-09", "Screening", "Sanctions screening — onboarding and ongoing re-screening",
     "RS-03 Sanctions violations", "C-07",
     "Review Section 12.1 and the screening infrastructure table. Confirm the screening provider contract specifies daily batch updates and real-time API capability. Confirm the procedure requires all existing customers to be re-screened within 24 hours of a sanctions list publication.",
     "Obtain the dates of all FATF and EU sanctions list updates in the past 12 months. For each update date, query the screening system log to confirm all existing customers were re-screened within 24 hours. Select 3 update dates and verify no gap in re-screening coverage exceeds the SLA. Document the maximum observed delay."),

    ("WP-10", "Screening", "Sanctions potential match adjudication",
     "RS-03 Match resolution delay", "C-08",
     "Review Section 12.1 escalation procedure. Confirm GRC/screening system captures timestamps for both alert generation and analyst resolution decision. Confirm the 4-business-hour SLA is defined in the system or procedure.",
     "Pull all potential sanctions match alerts generated in the past 12 months. For each alert, measure the elapsed time from alert generation to a documented resolution decision (clear or escalate). Calculate the percentage resolved within 4 business hours. Report the non-compliance rate and investigate outliers."),

    ("WP-11", "Screening", "PEP screening — onboarding and at each periodic review",
     "RS-04 PEP corruption risk", "C-09",
     "Review Section 12.2. Confirm PEP screening is a mandatory step in the onboarding GRC workflow. Confirm periodic review checklists explicitly require PEP re-screening at each review cycle, regardless of risk band.",
     "From the WP-01/02 onboarding sample: confirm PEP screening was conducted and the result (match or clear) is recorded for each file. Separately, from all completed periodic reviews in the past 12 months: confirm PEP re-screening is documented in each review file. Report the rate of missing screening records."),

    ("WP-12", "EDD", "Enhanced Due Diligence — confirmed PEP relationships",
     "RS-04, RI-03 MLRO key person", "C-10",
     "Review Sections 9.3 and 12.2. Confirm MLRO approval is a mandatory GRC workflow step for PEP-flagged customers and that the workflow cannot be completed without MLRO sign-off. Confirm the EDD checklist includes all required PEP-specific elements.",
     "Identify all customers flagged as PEP or Related and Close Associate (RCA) in the GRC platform. For each: verify the EDD file contains source of funds documentation, source of wealth documentation, certified identification documents, a dated adverse media search result, and a recorded MLRO approval decision. Report any missing elements."),

    ("WP-13", "Ongoing Monitoring", "Transaction monitoring — scenario calibration and coverage",
     "RS-07, RS-08, RS-09, RS-10 TM coverage gaps", "C-11",
     "Review Section 13.1 scenario table. Confirm the TM system has all 8 scenarios configured with the specified thresholds. Confirm semi-annual calibration review is documented, including sign-off by the Compliance team.",
     "For each of the 8 TM scenarios: prepare synthetic transaction data that meets the scenario threshold (e.g., a single transaction of EUR 15,001 for TM-01) and confirm the system generates an alert within the expected timeframe. Request and review the most recent semi-annual calibration report. Confirm all 8 scenarios were reviewed and threshold appropriateness assessed."),

    ("WP-14", "Ongoing Monitoring", "Periodic review timeliness by risk band",
     "RS-01–RS-04, RS-13 Overdue reviews", "C-12",
     "Review Section 13.2 and GRC platform reminder configuration. Confirm automated reminders are set 60 days prior to each review due date and that overdue reviews trigger escalation per Section 18.3. NOTE: Resolve the inconsistency between Sections 7.2 (6 months) and 13.2 (9 months) for High-risk customers before designing the test — audit testing against the wrong frequency will produce incorrect conclusions.",
     "Query the GRC platform for all periodic reviews that became due in the past 12 months. Calculate the percentage completed by the due date (KPI: ≥90%). For all overdue reviews: confirm the escalation procedure was followed. Stratify results by risk band (Low / Medium / High) and identify whether any risk band systematically underperforms."),

    ("WP-15", "SAR Reporting", "Internal SAR assessment timeliness",
     "RS-01, RS-02, RI-03 MLRO key person dependency", "C-13",
     "Review Section 14.1. Confirm the SAR form (NP-FORM-AML-001) captures the employee submission timestamp. Confirm the MLRO assessment decision is time-stamped in the SAR register and that the 24-hour clock starts from submission, not from MLRO receipt.",
     "Review all internal SAR submissions recorded in the SAR register for the past 12 months. For each submission: measure the elapsed time from employee submission to MLRO assessment decision (accept / reject / request further information). Confirm 100% of submissions were assessed within 24 hours. Identify any submissions assessed by the Deputy MLRO and confirm this was due to documented MLRO unavailability."),

    ("WP-16", "SAR Reporting", "External SAR filing within statutory deadline",
     "RS-01, RS-02 Delayed SAR filing", "C-14",
     "Review Section 14.2. NOTE: The statutory filing deadline is a placeholder field — obtain the applicable jurisdiction-specific deadline from the relevant FIU regulations before proceeding with test design. Confirm the SAR register captures the date of each external filing.",
     "Cross-reference the SAR register external filing dates against the applicable statutory deadline for each jurisdiction. Confirm 100% of external SARs were filed on time. For each SAR, assess whether the elapsed time between internal assessment approval and external filing is proportionate. Flag any cases showing unexplained delay between MLRO decision and filing."),

    ("WP-17", "Record Keeping", "CDD record retention — minimum 5-year post-relationship",
     "RS-01, RS-02 Record availability", "C-15",
     "Review Section 15 retention schedule. Confirm the GRC platform has automated deletion schedules configured for each record category. Confirm the DPO has reviewed the deletion schedule against GDPR requirements (lawful basis for retention beyond the relationship). Confirm records can be retrieved within 3 business days.",
     "Select a sample of 20 customer relationships terminated in the past 24 months. For each: confirm CDD records are still accessible in the GRC system and that the scheduled deletion date is no earlier than 5 years after the relationship end date. Test retrieval time for 5 files to confirm the 3-business-day SLA. Review the GRC automated deletion schedule configuration."),

    ("WP-18", "Exception Management", "Exception approvals per delegation matrix",
     "All risks — bypass of controls", "C-16",
     "Review Section 18.2 delegation matrix. Confirm the GRC exception register captures: exception type, date requested, requestor role, approver role, approval date, and expiry date. Confirm the matrix specifies the minimum approval authority for each exception type.",
     "Pull all exceptions recorded in the GRC exception register for the past 12 months. For each exception: verify the approver's role matches or exceeds the minimum authority required per the Section 18.2 matrix. Identify any self-approved exceptions (requestor = approver), exceptions without a documented expiry date, or exceptions approved below the required authority level. Report the non-compliance rate."),

    ("WP-19", "Training", "AML/CTF training completion rate and pass scores",
     "RI-08 Training knowledge gaps", "C-17",
     "Review Section 17. Confirm the LMS captures completion date and pass score per employee. Confirm the non-completion escalation process is triggered at 14 calendar days. Confirm the 80% pass score threshold is enforced by the LMS (failed employees must retake).",
     "Query the LMS for the most recent annual AML/CTF training cycle. Calculate: (a) completion rate by role (KPI: ≥98%); (b) first-attempt pass rate overall; (c) number of employees who completed training with a score between 80% and 89% (i.e., passed but missed up to 20% of content). Confirm the escalation process was followed for all non-completers. Assess training content to determine whether high-risk procedural topics (tipping-off, SAR reporting, PEP EDD requirements) are assessed with dedicated questions."),

    ("WP-20", "Quality Assurance", "Second-line QA — EDD file completeness review",
     "All EDD controls — QA oversight", "C-18",
     "Review Section 19.2. Confirm the second-line QA scope, sampling methodology (100% EDD files + 5% random all-file sample), frequency (quarterly), and reporting chain (Compliance Manager → MLRO) are documented in a QA procedure.",
     "Request QA reports for each quarter of the past 12 months (4 reports). For each report: verify it confirms 100% of EDD files opened in that quarter were reviewed; record the deficiency rate; confirm all identified deficiencies were formally reported, tracked to remediation, and closed within the defined remediation window. Assess whether the QA deficiency rate has trended upward or downward over the 12-month period."),

    ("WP-21", "Governance", "EWRA — annual completion and Board approval",
     "RI-01 EWRA staleness, RI-02 Model drift", "C-21",
     "Review Section 6.2. Confirm the EWRA is referenced with a specific version number and year (not a placeholder). Confirm Board approval is a documented requirement and that Board minutes evidence approval.",
     "Request the most recent EWRA (NP-EWRA-[Year]). Verify: (a) it is dated within the past 12 months; (b) it covers all four risk factor categories (Sec. 6.3: customer, product/channel, geography, delivery channel); (c) Board approval is evidenced by meeting minutes. Additionally, confirm that the risk scoring model weights in Appendix A were reviewed against the EWRA findings and that any recalibration decisions are documented."),

    ("WP-22", "Third Party / Agents", "Annual compliance attestation from appointed agents",
     "RS-12, RI-12 Agent compliance gap", "C-20",
     "Review Section 11.2. Confirm the attestation content and process are defined in NP-PROC-OB-003 (not available for review — flag as gap). Confirm the GRC system maintains a register of all appointed agents with attestation due dates.",
     "Request the full list of all currently appointed agents from the GRC system. For each active agent: confirm a signed compliance attestation is on file dated within the past 12 months. For agents flagged as 'material relationships' in Section 11.2: confirm a periodic compliance review (beyond just attestation) was conducted. Report the percentage of agents with current attestations and investigate any gaps."),

    ("WP-23", "Risk Scoring", "[Gap] Risk scoring model recalibration governance",
     "RI-02 Model calibration drift", "[No control identified — gap]",
     "Auditor to assess whether a model governance framework exists outside this policy (e.g., a Model Risk Policy or Model Validation procedure). Confirm whether the 7-factor risk scoring model is subject to periodic validation and recalibration requirements.",
     "Inquire with the Compliance team and/or Risk team whether the 7-factor risk scoring model weights and band thresholds have been reviewed or recalibrated since the policy's last major revision. Obtain any documentation of model validation reviews, back-testing results, or calibration change logs. If no model governance process exists, document as a control gap for management response."),

    ("WP-24", "Governance", "[Gap] MLRO succession and continuity planning",
     "RI-03 Key person dependency — MLRO", "[No control identified — gap]",
     "Auditor to assess whether an MLRO succession plan or extended absence procedure exists outside this policy (e.g., in an HR continuity plan or a Compliance function governance document).",
     "Inquire whether a documented MLRO succession plan exists, including: (a) the trigger conditions for activating Deputy MLRO authority; (b) confirmation that the Deputy MLRO has all system access rights required to fulfil MLRO functions; (c) the NCA notification procedure if the MLRO is absent for an extended period. If no formal plan exists, document as a governance gap requiring management response."),
]

def build_work_program(wb):
    ws = wb.create_sheet("Audit Work Program")
    ws.sheet_view.showGridLines = False

    ws.merge_cells("A1:G1")
    title = ws["A1"]
    title.value = "AUDIT WORK PROGRAM  |  NP-POL-AML-001 v3.2  |  Customer Onboarding Audit 2026  |  All ToD/ToE are AI-suggested — require auditor refinement"
    title.fill = fill(DARK_BLUE)
    title.font = header_font(size=11)
    title.alignment = wrap_align("center", "center")
    ws.row_dimensions[1].height = 22

    headers = ["#", "Process", "Activity (Sub-Process)", "Risk(s)", "Control(s)", "Test of Design (ToD)", "Test of Operating Effectiveness (ToE)"]
    widths   = [8, 22, 30, 25, 16, 55, 60]
    apply_header_row(ws, 2, headers, widths)
    ws.row_dimensions[2].height = 18

    for i, row in enumerate(WORK_PROGRAM, 3):
        is_gap = "[No control" in row[4]
        row_fill = AMBER if is_gap else (LIGHT_BLUE if i % 2 == 0 else WHITE)
        apply_body_row(ws, i, list(row), row_fill=row_fill, bold_col=1)
        ws.row_dimensions[i].height = 90

    freeze_and_filter(ws, freeze_row=3)

# ---------------------------------------------------------------------------
# Sheet 5: Legend / Instructions
# ---------------------------------------------------------------------------

def build_legend(wb):
    ws = wb.create_sheet("Legend & Instructions")
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 70

    ws.merge_cells("A1:B1")
    title = ws["A1"]
    title.value = "LEGEND & INSTRUCTIONS"
    title.fill = fill(DARK_BLUE)
    title.font = header_font(size=12)
    title.alignment = wrap_align("center", "center")
    ws.row_dimensions[1].height = 24

    entries = [
        ("", ""),
        ("DOCUMENT", ""),
        ("Title", "Audit Program & Risk-Control Matrix — NP-POL-AML-001 v3.2"),
        ("Engagement", "Customer Onboarding Audit 2026"),
        ("Source policy", "NovaPay Customer Onboarding Policy (NP-POL-AML-001 v3.2, effective 2025-09-01)"),
        ("Analysis date", "2026-04-21"),
        ("Produced by", "Claude Code / SAAF analyze-policy skill (GIAS 13.2)"),
        ("Status", "AI-generated draft — requires auditor review and sign-off before use in formal workpapers"),
        ("", ""),
        ("SHEETS", ""),
        ("Risk Register (Policy-Stated)", "RS-01 to RS-13: risks explicitly identified in the policy text. Source quotes provided."),
        ("AI-Inferred Risks", "RI-01 to RI-12: risks identified by AI analysis of the described processes. Require auditor validation before inclusion in scope."),
        ("Control Register", "C-01 to C-22: controls extracted from the policy. Bottom rows (highlighted red) are control gaps — risks with no mitigating control."),
        ("Audit Work Program", "WP-01 to WP-24: one row per testable control or gap. Rows highlighted amber are gaps with no existing control."),
        ("", ""),
        ("COLOUR CODE", ""),
        ("Dark blue header", "Column headers and sheet titles"),
        ("Light blue row", "Alternate body rows for readability"),
        ("Yellow row", "AI-inferred risks — require auditor validation"),
        ("Red row", "Control gap — no mitigating control identified"),
        ("Amber row", "Audit program row for a gap (no control)"),
        ("", ""),
        ("RISK ID PREFIXES", ""),
        ("RS-xx", "Policy-stated risk — extracted directly from the policy text"),
        ("RI-xx", "AI-inferred risk — identified by reasoning about the process; not stated in policy"),
        ("", ""),
        ("CONTROL TYPES", ""),
        ("Preventive", "Designed to prevent the risk from occurring"),
        ("Detective", "Designed to identify when the risk has materialised"),
        ("Corrective", "Designed to remedy or recover from a risk event"),
        ("Directive", "Policy or mandate requiring a specific action"),
        ("", ""),
        ("TEST TYPES", ""),
        ("ToD (Test of Design)", "Verify the control is adequately designed — if followed, it would mitigate the risk"),
        ("ToE (Test of Operating Effectiveness)", "Verify the control actually operates as intended in practice"),
        ("", ""),
        ("IMPORTANT LIMITATIONS", ""),
        ("Policy-only analysis", "This analysis is based solely on the policy document. It does not incorporate information from prior audits, regulatory correspondence, management interviews, or operational data."),
        ("AI-inferred risks", "RI-xx risks are starting points for professional discussion, not audit conclusions. Each requires engagement supervisor validation."),
        ("AI-suggested ratings", "All [AI-suggested] risk ratings require auditor validation and sign-off before use in formal workpapers."),
        ("Placeholders", "The source policy contains 13 unresolved [placeholder] fields. These affect the enforceability of jurisdiction-specific requirements."),
        ("Two critical inconsistencies", "Section 7.2 vs 13.2 (high-risk review: 6 vs 9 months) and Section 9.6 vs 16.1 (CDD deadline: 30 vs 21 days) must be resolved before audit testing commences."),
    ]

    for i, (label, value) in enumerate(entries, 2):
        is_section = value == "" and label != ""
        label_cell = ws.cell(row=i, column=1, value=label)
        value_cell = ws.cell(row=i, column=2, value=value)

        if is_section:
            for cell in [label_cell, value_cell]:
                cell.fill = fill(MID_BLUE)
                cell.font = header_font(size=10)
                cell.alignment = wrap_align("left", "center")
                ws.row_dimensions[i].height = 18
        else:
            label_cell.font = body_font(bold=True)
            label_cell.fill = fill(LIGHT_BLUE)
            label_cell.alignment = wrap_align("left", "top")
            value_cell.font = body_font()
            value_cell.fill = fill(WHITE)
            value_cell.alignment = wrap_align("left", "top")
            ws.row_dimensions[i].height = 36 if len(value) > 80 else 18

        for cell in [label_cell, value_cell]:
            cell.border = thin_border()

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    if len(sys.argv) < 2:
        print(f"Usage: python3 {Path(__file__).name} <output-path>", file=sys.stderr)
        return 1

    output_path = Path(sys.argv[1]).resolve()

    wb = Workbook()
    wb.remove(wb.active)  # remove default empty sheet

    build_legend(wb)
    build_risk_register(wb)
    build_inferred_risks(wb)
    build_control_register(wb)
    build_work_program(wb)

    wb.save(str(output_path))
    print(f"Workbook saved: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
