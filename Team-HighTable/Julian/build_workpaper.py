import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter

wb = openpyxl.Workbook()

# COLOR PALETTE
DARK_BLUE   = "1F3864"
MED_BLUE    = "2E75B6"
LIGHT_BLUE  = "D6E4F0"
WHITE       = "FFFFFF"
RED_FILL    = "C00000"
ORANGE_FILL = "E36C09"
YELLOW_FILL = "FFD700"
GREEN_FILL  = "70AD47"

def thin_border():
    s = Side(style='thin', color='BFBFBF')
    return Border(left=s, right=s, top=s, bottom=s)

def med_border():
    s = Side(style='medium', color='1F3864')
    return Border(left=s, right=s, top=s, bottom=s)

def style_header(cell, text, bg=DARK_BLUE, fg=WHITE, size=10, bold=True):
    cell.value = text
    cell.fill = PatternFill("solid", fgColor=bg)
    cell.font = Font(bold=bold, color=fg, size=size, name="Calibri")
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell.border = med_border()

def style_cell(cell, text="", bg=WHITE, bold=False, left=True, size=9):
    if text != "":
        cell.value = text
    cell.fill = PatternFill("solid", fgColor=bg)
    cell.font = Font(bold=bold, color="000000", size=size, name="Calibri")
    cell.alignment = Alignment(horizontal="left" if left else "center",
                                vertical="top", wrap_text=True)
    cell.border = thin_border()

def risk_fill(level):
    return {"High": RED_FILL, "Medium": ORANGE_FILL, "Low": YELLOW_FILL}.get(level, WHITE)

def risk_font_color(level):
    return WHITE if level in ("High", "Medium") else "000000"

# ===========================
# SHEET 1 - COVER PAGE
# ===========================
ws_cover = wb.active
ws_cover.title = "Cover Page"
ws_cover.sheet_view.showGridLines = False
ws_cover.column_dimensions["A"].width = 3
ws_cover.column_dimensions["B"].width = 55
ws_cover.column_dimensions["C"].width = 35

for row in range(1, 6):
    ws_cover.row_dimensions[row].height = 18
    for col in ["A","B","C"]:
        ws_cover[f"{col}{row}"].fill = PatternFill("solid", fgColor=DARK_BLUE)

ws_cover.merge_cells("A2:C5")
c = ws_cover["A2"]
c.value = "AI GOVERNANCE AUDIT WORKPAPER"
c.fill = PatternFill("solid", fgColor=DARK_BLUE)
c.font = Font(bold=True, color=WHITE, size=20, name="Calibri")
c.alignment = Alignment(horizontal="center", vertical="center")

info = [
    ("",""),
    ("Regulation:","EU AI Act – Regulation (EU) 2024/1689"),
    ("Objective:","Assess compliance with the EU Artificial Intelligence Act, evaluate adequacy of AI governance controls, and identify compliance gaps."),
    ("Scope:","All AI systems in use or under development, classified per EU AI Act risk tiers."),
    ("Audit Period:",""),
    ("Prepared by:",""),
    ("Reviewed by:",""),
    ("Date:",""),
    ("Version:","1.0"),
    ("Classification:","CONFIDENTIAL"),
    ("",""),
    ("RISK LEGEND",""),
    ("HIGH","Immediate action required – material non-compliance risk"),
    ("MEDIUM","Action required – moderate non-compliance risk"),
    ("LOW","Monitor – minor / administrative risk"),
]

start = 7
for i,(lbl,val) in enumerate(info):
    r = start + i
    ws_cover.row_dimensions[r].height = 28 if lbl in ("Objective:","Scope:") else 20
    lc = ws_cover[f"B{r}"]
    vc = ws_cover[f"C{r}"]
    if lbl == "RISK LEGEND":
        lc.value = "RISK RATING LEGEND"
        lc.font = Font(bold=True, color=DARK_BLUE, size=11, name="Calibri")
        lc.alignment = Alignment(horizontal="left", vertical="center")
    elif lbl in ("HIGH","MEDIUM","LOW"):
        lc.value = lbl
        lc.fill = PatternFill("solid", fgColor=risk_fill(lbl.capitalize()))
        lc.font = Font(bold=True, color=WHITE, size=10, name="Calibri")
        lc.alignment = Alignment(horizontal="center", vertical="center")
        lc.border = thin_border()
        vc.value = val
        vc.font = Font(size=9, name="Calibri")
        vc.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    else:
        lc.value = lbl
        lc.font = Font(bold=bool(lbl), color=DARK_BLUE, size=10, name="Calibri")
        lc.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        vc.value = val
        vc.font = Font(size=9, name="Calibri")
        vc.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        if lbl:
            lc.border = thin_border()
            vc.border = thin_border()

# ===========================
# SHEET 2 - MAIN WORKPAPER
# ===========================
ws = wb.create_sheet("AI Governance Workpaper")
ws.sheet_view.showGridLines = False
ws.freeze_panes = "A4"

col_widths = [4, 28, 40, 14, 10, 44, 16, 36, 15, 24, 15]
for i,w in enumerate(col_widths):
    ws.column_dimensions[get_column_letter(i+1)].width = w

ws.merge_cells("A1:K1")
ws.row_dimensions[1].height = 34
c = ws["A1"]
c.value = "AI GOVERNANCE AUDIT WORKPAPER  |  EU AI Act – Regulation (EU) 2024/1689"
c.fill = PatternFill("solid", fgColor=DARK_BLUE)
c.font = Font(bold=True, color=WHITE, size=13, name="Calibri")
c.alignment = Alignment(horizontal="center", vertical="center")

ws.merge_cells("A2:K2")
ws.row_dimensions[2].height = 18
c = ws["A2"]
c.value = "Audit Period: _____________  |  Prepared by: _____________  |  Reviewed by: _____________  |  Date: _____________"
c.fill = PatternFill("solid", fgColor=MED_BLUE)
c.font = Font(color=WHITE, size=9, name="Calibri")
c.alignment = Alignment(horizontal="center", vertical="center")

ws.row_dimensions[3].height = 38
hdrs = ["No.","Risk Domain","Risk Description","EU AI Act\nReference",
        "Risk\nRating","Expected Control","Control\nType",
        "Audit Testing Procedure","Work Done\n(✓/N/A)","Findings /\nObservations","Status"]
for col,h in enumerate(hdrs,1):
    style_header(ws.cell(row=3,column=col), h)

# DATA rows
data = [
    # A - Classification
    ("A. AI System Classification & Inventory",
     "Organisation fails to identify and classify all AI systems (prohibited / high-risk / limited risk / minimal risk), resulting in unmanaged regulatory exposure.",
     "Art. 6, 7;\nAnnex III","High",
     "Maintain a comprehensive AI system register classifying every AI system per EU AI Act risk tiers. Register reviewed at least annually or upon new deployments.",
     "Preventive",
     "1. Obtain the AI system register/inventory.\n2. Verify all deployed and in-development AI systems are listed.\n3. Confirm risk classification rationale is documented and approved.\n4. Cross-reference IT asset inventory, procurement records and business unit interviews.\n5. Verify periodic review dates are evidenced."),

    ("A. AI System Classification & Inventory",
     "AI systems meeting high-risk criteria under Annex III are misclassified as lower risk, bypassing mandatory compliance requirements.",
     "Art. 6(3);\nAnnex III","High",
     "Classification decisions are documented with written justification, reviewed by Legal/Compliance, and signed off by senior management. Derogation procedure exists per Art. 6(3) with EU database notification.",
     "Preventive",
     "1. Sample AI systems classified as non-high-risk.\n2. Review classification justification against Annex III criteria.\n3. Verify Legal/Compliance sign-off is on file.\n4. For Art. 6(3) derogations, confirm EU database notification.\n5. Re-assess at least two borderline cases independently."),

    # B - Prohibited
    ("B. Prohibited AI Practices",
     "Organisation develops or uses AI systems deploying subliminal or manipulative techniques that materially distort behaviour and cause significant harm.",
     "Art. 5(1)(a)","High",
     "Prohibited-use policy explicitly bans AI systems using subliminal or manipulative techniques. All new AI projects undergo prohibited-use screening before initiation.",
     "Preventive",
     "1. Obtain prohibited-use / acceptable-use policy.\n2. Confirm policy explicitly references Art. 5 prohibitions.\n3. Verify prohibited-use screening checklist is completed for all new AI projects.\n4. Sample project initiations for evidence of screening completion.\n5. Confirm employee training on prohibited practices exists."),

    ("B. Prohibited AI Practices",
     "AI systems exploit vulnerabilities of specific groups (age, disability, economic situation) causing significant harm.",
     "Art. 5(1)(b)","High",
     "Pre-deployment ethical review includes targeted assessment of whether the AI system could exploit vulnerable groups. Ethics committee sign-off is required.",
     "Preventive",
     "1. Review ethical review / pre-deployment assessment process.\n2. Confirm vulnerable-group assessment is a mandatory step.\n3. Sample two recently deployed systems and verify ethics assessments.\n4. Confirm ethics committee members are independent and qualified.\n5. Verify escalation path if vulnerabilities are identified."),

    ("B. Prohibited AI Practices",
     "Organisation uses AI-based social scoring systems leading to unjustified or disproportionate treatment of persons.",
     "Art. 5(1)(c)","High",
     "Prohibited-use policy explicitly prohibits social scoring. IT/architecture review prevents development or integration of social-scoring modules.",
     "Preventive",
     "1. Review prohibited-use policy for explicit social-scoring prohibition.\n2. Interview IT/AI leads on scoring or profiling capabilities.\n3. Inspect code repositories and vendor contracts for social-scoring functionality.\n4. Review procurement due-diligence for third-party AI."),

    ("B. Prohibited AI Practices",
     "Organisation uses real-time remote biometric identification (RBI) in publicly accessible spaces outside the narrow legal exceptions.",
     "Art. 5(1)(h),\n5(2)-(5)","High",
     "Use of real-time RBI is prohibited except where permitted. Any exceptional use requires prior judicial/administrative authorisation, EU database registration, and a completed FRIA.",
     "Preventive/\nDetective",
     "1. Confirm whether the organisation uses real-time RBI systems.\n2. If yes, verify prior judicial/administrative authorisation is documented.\n3. Verify EU database registration (Art. 49).\n4. Verify a Fundamental Rights Impact Assessment (FRIA) was completed (Art. 27).\n5. Review notifications to market surveillance and data protection authorities."),

    # C - Risk Management
    ("C. Risk Management System",
     "No formal risk management system (RMS) exists for high-risk AI systems, or the RMS is not maintained as a continuous iterative process throughout the AI lifecycle.",
     "Art. 9","High",
     "A documented RMS is established for each high-risk AI system covering: (a) risk identification & analysis, (b) risk estimation & evaluation incl. foreseeable misuse, (c) post-market monitoring inputs, (d) targeted risk mitigation measures. RMS updated regularly.",
     "Preventive",
     "1. Obtain RMS documentation for sampled high-risk AI systems.\n2. Verify the RMS covers all four Art. 9(2) steps.\n3. Confirm RMS is reviewed annually or after material changes.\n4. Verify residual risk is assessed and accepted at an appropriate level.\n5. Review testing evidence against defined metrics (Art. 9(6)).\n6. Confirm vulnerable groups (under 18 etc.) are considered per Art. 9(9)."),

    ("C. Risk Management System",
     "Risk mitigation measures are inadequate or not proportionate to actual risks, leaving residual risks unacceptably high.",
     "Art. 9(4)-(5)","High",
     "Risk mitigation follows the hierarchy: (1) eliminate/reduce by design, (2) mitigate/control, (3) inform deployers. Residual risk is formally accepted by a designated risk owner.",
     "Preventive",
     "1. Review risk mitigation hierarchy in the RMS.\n2. For sampled risks, verify mitigation measures are implemented.\n3. Confirm formal residual risk acceptance by risk owner.\n4. Assess whether feedback-loop risks for continuously learning systems are addressed."),

    # D - Data Governance
    ("D. Data & Data Governance",
     "Training, validation, and testing datasets for high-risk AI lack quality controls, contain unmitigated biases, or are not representative, leading to discriminatory or inaccurate outputs.",
     "Art. 10","High",
     "Data governance policy requires datasets to be: (a) relevant and sufficiently representative, (b) free from known biases or biases mitigated, (c) subject to documented data-preparation practices, (d) assessed for completeness gaps.",
     "Preventive",
     "1. Obtain data governance policy and data management procedures.\n2. For sampled high-risk AI systems, review dataset documentation.\n3. Verify bias detection and mitigation procedures are documented and applied.\n4. Confirm data origin, collection purpose, and processing steps are recorded.\n5. For bias-correction use of special-category data, verify Art. 10(5) conditions are met.\n6. Review evidence of data-quality assessments."),

    ("D. Data & Data Governance",
     "Special categories of personal data are processed for bias detection/correction without meeting strict legal conditions, risking data protection violations.",
     "Art. 10(5);\nGDPR Art. 9","High",
     "Processing of special-category data for bias correction is subject to documented legal basis, technical safeguards (pseudonymisation, access controls), and deletion once bias is corrected.",
     "Preventive/\nDetective",
     "1. Identify high-risk AI systems processing special-category data for bias correction.\n2. Verify documented justification that bias cannot be corrected with other data.\n3. Confirm pseudonymisation and security measures are in place.\n4. Verify data is not shared with third parties.\n5. Confirm deletion schedule once bias correction is complete.\n6. Review ROPA entries for completeness."),

    # E - Technical Docs
    ("E. Technical Documentation",
     "Technical documentation for high-risk AI systems is incomplete, outdated, or not drawn up prior to placing on market / putting into service.",
     "Art. 11;\nAnnex IV","High",
     "Technical documentation is prepared before deployment, kept up to date, and contains all Annex IV elements (system description, intended purpose, design choices, training data, test results, RMS, conformity declaration).",
     "Preventive",
     "1. For sampled high-risk AI systems, obtain technical documentation.\n2. Map documentation against Annex IV checklist.\n3. Verify documentation was finalised before go-live (date-stamped).\n4. Confirm a process exists to update documentation after material changes.\n5. Verify documentation is retained for 10 years (Art. 18).\n6. Confirm documentation is accessible to competent authorities."),

    # F - Logging
    ("F. Record-Keeping & Logging",
     "High-risk AI systems do not generate automatic logs, or logs are not retained sufficiently, preventing post-incident investigation and regulatory review.",
     "Art. 12, 19;\nArt. 26(6)","High",
     "High-risk AI systems are technically configured to automatically log relevant events. Providers and deployers retain logs for at least 6 months (or longer as required by law).",
     "Detective",
     "1. Confirm logging capability is enabled for all high-risk AI systems.\n2. Review log retention policy and verify minimum 6-month compliance.\n3. For biometric ID systems (Annex III pt. 1(a)), verify logs include: use periods, reference databases, input data, and verifier IDs (Art. 12(3)).\n4. Test log completeness by sampling records against a known operational period.\n5. Verify financial institutions maintain logs within financial governance records."),

    # G - Transparency
    ("G. Transparency & Information to Deployers",
     "Deployers of high-risk AI do not receive adequate instructions for use to understand capabilities, limitations, and oversight requirements, leading to misuse or overreliance.",
     "Art. 13","High",
     "Instructions for use accompany each high-risk AI system and include: provider identity, intended purpose, performance metrics, known limitations, human oversight measures, computational requirements, and log interpretation guidance.",
     "Preventive",
     "1. Obtain instructions for use for sampled high-risk AI systems.\n2. Verify instructions contain all Art. 13(3) elements.\n3. Confirm instructions are in an appropriate digital format.\n4. Verify deployers acknowledge receipt.\n5. Assess comprehensibility of instructions for target deployer audience."),

    ("G. Transparency & Information to Deployers",
     "Individuals are not informed that they are subject to an AI-assisted decision or that they are interacting with an AI system, violating transparency obligations.",
     "Art. 26(11);\nArt. 50","Medium",
     "Transparency notice procedure ensures natural persons are notified when high-risk AI systems assist in decisions affecting them. AI-generated content is labelled/watermarked per Art. 50.",
     "Preventive",
     "1. Review transparency notice procedure and templates.\n2. Confirm high-risk AI systems under Annex III include user notification mechanisms.\n3. For AI-generated content (Art. 50), verify machine-readable labelling or watermarking.\n4. Test notification workflows in at least one deployed system.\n5. Review complaint logs for transparency-related concerns."),

    # H - Human Oversight
    ("H. Human Oversight",
     "High-risk AI systems are deployed without effective human oversight mechanisms, increasing the risk of uncorrected erroneous outputs causing harm.",
     "Art. 14","High",
     "All high-risk AI systems are deployed with commensurate human oversight measures: ability to understand capabilities/limitations, detect anomalies, avoid automation bias, interpret outputs, override outputs, and halt the system (stop-button).",
     "Preventive",
     "1. Review human oversight design for each sampled high-risk AI system.\n2. Confirm oversight measures are proportionate to risk and autonomy level.\n3. Verify a 'stop' or interruption mechanism exists and is operable.\n4. Assess whether staff are trained to detect automation bias.\n5. For biometric ID systems (Annex III pt. 1(a)), confirm dual-verification by two qualified persons (Art. 14(5)).\n6. Review records of any system overrides or stops."),

    ("H. Human Oversight",
     "Staff assigned human oversight responsibilities lack the competence, training, and authority required to effectively oversee AI systems.",
     "Art. 14;\nArt. 26(2)","High",
     "Human oversight roles are assigned to qualified individuals with documented competencies. Training records are maintained. Responsibilities are formalised in job descriptions or policies.",
     "Preventive",
     "1. Obtain human oversight role assignments for sampled systems.\n2. Verify training records demonstrate adequate AI literacy (Art. 4).\n3. Confirm oversight responsibilities are included in job descriptions or policy.\n4. Interview a sample of oversight personnel on their system understanding."),

    # I - Accuracy
    ("I. Accuracy, Robustness & Cybersecurity",
     "High-risk AI systems do not achieve and maintain appropriate levels of accuracy and robustness throughout their lifecycle, including after deployment.",
     "Art. 15(1)-(4)","High",
     "Accuracy and robustness requirements are defined pre-deployment, tested against declared metrics. Continuously-learning systems have feedback-loop controls. Technical redundancy (backup/fail-safe) is implemented.",
     "Preventive",
     "1. Review declared accuracy metrics in instructions for use (Art. 15(3)).\n2. Verify pre-deployment test results meet declared thresholds.\n3. For continuously-learning systems, review feedback-loop mitigation controls.\n4. Assess technical redundancy and fail-safe mechanisms.\n5. Verify performance monitoring post-deployment is in place."),

    ("I. Accuracy, Robustness & Cybersecurity",
     "High-risk AI systems are vulnerable to adversarial attacks (data poisoning, model evasion, adversarial inputs) that could compromise integrity and outputs.",
     "Art. 15(5)","High",
     "Cybersecurity measures address AI-specific vulnerabilities including data poisoning, model poisoning, adversarial examples, model evasion, and confidentiality attacks, commensurate with risk.",
     "Preventive/\nDetective",
     "1. Obtain the AI cybersecurity risk assessment.\n2. Verify AI-specific threats (Art. 15(5)) are included in the threat model.\n3. Review technical controls against data poisoning, adversarial inputs, and model evasion.\n4. Confirm penetration testing / red-teaming has been performed.\n5. Verify alignment with ENISA AI cybersecurity guidance."),

    # J - QMS
    ("J. Quality Management System (QMS)",
     "Provider lacks a documented Quality Management System, resulting in inconsistent compliance with EU AI Act requirements across the AI lifecycle.",
     "Art. 17","High",
     "A QMS is documented covering: regulatory compliance strategy, design control, quality assurance, testing & validation, technical standards, data management, risk management (Art. 9), post-market monitoring (Art. 72), serious incident reporting (Art. 73), accountability framework, and resource management.",
     "Preventive",
     "1. Obtain QMS documentation.\n2. Map against all Art. 17(1)(a)-(m) elements.\n3. Verify QMS is implemented – inspect evidence of each element.\n4. Confirm QMS is proportionate to organisational size and risk profile.\n5. For financial institutions, confirm QMS is integrated into internal governance frameworks."),

    # K - Conformity
    ("K. Conformity Assessment",
     "High-risk AI systems are placed on the market or put into service without completing the required conformity assessment, or without an EU Declaration of Conformity.",
     "Art. 16(f);\nArt. 43; 47-48","High",
     "All high-risk AI systems undergo the appropriate conformity assessment (self-assessment or third-party notified body) before deployment. EU Declaration of Conformity is drawn up and CE marking affixed.",
     "Preventive",
     "1. Obtain list of high-risk AI systems placed on market or in service.\n2. Verify each has a completed conformity assessment file.\n3. Confirm EU Declarations of Conformity (Art. 47) are on file and dated pre-deployment.\n4. Verify CE marking is applied where required.\n5. For biometric systems, confirm notified body third-party assessment was used.\n6. Confirm no substantial modifications were made post-assessment without reassessment."),

    # L - Registration
    ("L. EU Database Registration",
     "High-risk AI systems are not registered in the EU AI database, preventing regulatory oversight and public accountability.",
     "Art. 49; Art. 71","High",
     "All applicable high-risk AI systems are registered in the EU database before deployment. Public authority deployers register their use. Substantial modifications are re-registered.",
     "Preventive",
     "1. Obtain list of high-risk AI systems requiring registration.\n2. Verify each is registered in the EU database.\n3. Confirm registration information matches technical documentation.\n4. For public authority deployers, verify deployer-side registration.\n5. Confirm substantial modifications are reflected in updated registrations."),

    # M - FRIA
    ("M. Fundamental Rights Impact Assessment",
     "Public bodies and certain private entities deploying applicable high-risk AI systems fail to conduct a Fundamental Rights Impact Assessment (FRIA) before deployment.",
     "Art. 27","High",
     "A FRIA is performed prior to first use of applicable high-risk AI systems, covering: process description, use frequency/period, affected groups, risks of harm, human oversight implementation, and governance/complaint mechanisms. Results notified to the market surveillance authority.",
     "Preventive",
     "1. Identify all Art. 6(2) high-risk AI deployments by public bodies or applicable private entities.\n2. Verify a completed FRIA is on file for each deployment (using AI Office template).\n3. Confirm FRIA was completed before first use (date evidence).\n4. Verify notification to the market surveillance authority.\n5. Confirm FRIA is updated if material changes occur.\n6. Review FRIA for adequacy of affected group identification and mitigation measures."),

    # N - Post-market
    ("N. Post-Market Monitoring",
     "Providers do not maintain a post-market monitoring system, resulting in undetected performance degradation or new risks emerging after deployment.",
     "Art. 72;\nArt. 17(1)(h)","High",
     "A post-market monitoring plan is documented and actively operated for each high-risk AI system. Plan covers: usage data, performance indicators, user feedback, and incident signals. Results feed back into the RMS.",
     "Detective",
     "1. Obtain the post-market monitoring plan for sampled high-risk AI systems.\n2. Verify monitoring is actively performed (review monitoring records/reports).\n3. Confirm monitoring data feeds back into the RMS (Art. 9(2)(c)).\n4. For continuously-learning systems, assess whether monitoring includes performance drift detection.\n5. Verify post-market monitoring is included in the QMS (Art. 17(1)(h))."),

    # O - Incident Reporting
    ("O. Serious Incident Reporting",
     "Serious incidents or malfunctions of high-risk AI systems are not reported to competent authorities within required timeframes, or root-cause analysis is not performed.",
     "Art. 73;\nArt. 17(1)(i);\nArt. 20","High",
     "A serious incident reporting procedure defines: what constitutes a serious incident (Art. 73), responsible parties, reporting timelines (15 days for deaths, 10 days for serious harm, 10 business days for significant malfunctions), and root-cause analysis requirements.",
     "Corrective/\nDetective",
     "1. Obtain the serious incident reporting procedure.\n2. Verify the procedure aligns with Art. 73 definitions and timelines.\n3. Review any serious incidents reported in the past 12 months.\n4. For each incident, confirm timely reporting to the market surveillance authority.\n5. Verify root-cause analysis and corrective actions were documented.\n6. Confirm corrective action feeds back into the RMS and technical documentation."),

    # P - GPAI
    ("P. General-Purpose AI Models (GPAI)",
     "Organisation provides or integrates GPAI models without meeting transparency, technical documentation, and copyright summary obligations.",
     "Art. 53; Art. 55","High",
     "GPAI model providers maintain: (a) technical documentation, (b) information packages for downstream providers, (c) copyright law compliance (training data summary). Systemic-risk models additionally require: adversarial testing, incident reporting, cybersecurity measures, and energy efficiency reporting.",
     "Preventive",
     "1. Identify all GPAI models developed or integrated by the organisation.\n2. For provider role: review technical documentation and copyright summaries.\n3. Verify downstream provider information packages are prepared and accessible.\n4. Determine if any models exceed 10^25 FLOPs threshold (systemic risk – Art. 51).\n5. If systemic risk: verify adversarial testing, serious incident notifications, cybersecurity controls, and energy reporting.\n6. Confirm participation in relevant codes of practice (Art. 56)."),

    ("P. General-Purpose AI Models (GPAI)",
     "Organisation integrates third-party GPAI models into its systems without adequate due diligence, creating unmanaged accountability and liability risk.",
     "Art. 25;\nArt. 53(2)","High",
     "A vendor/third-party AI due-diligence procedure assesses GPAI provider compliance before integration. Contractual provisions flow down EU AI Act obligations. Organisation maintains records of integrated models.",
     "Preventive",
     "1. Obtain the third-party AI procurement / due-diligence policy.\n2. Review GPAI model contracts for EU AI Act flow-down clauses.\n3. Verify due-diligence assessments are completed before integration.\n4. Confirm the organisation's liability is understood and managed when building on top of GPAI.\n5. Review records of downstream providers' compliance confirmations."),

    # Q - AI Literacy
    ("Q. AI Literacy",
     "Staff dealing with AI systems lack sufficient AI literacy, increasing the risk of misuse, over-reliance, or failure to detect system anomalies.",
     "Art. 4","Medium",
     "An AI literacy programme is established for all staff involved in operating, overseeing, or deploying AI systems. Training is role-based, documented, and refreshed regularly. Completion is tracked.",
     "Preventive",
     "1. Obtain the AI literacy / training programme documentation.\n2. Verify training covers AI risks, obligations, and oversight techniques.\n3. Confirm role-specific modules exist for high-risk AI operators.\n4. Review training completion records for in-scope staff.\n5. Assess whether training is refreshed when new systems are deployed."),

    # R - Governance
    ("R. AI Governance & Accountability",
     "No clear accountability structure exists for AI governance, leading to fragmented responsibility and compliance gaps across the organisation.",
     "Art. 17(1)(m);\nArt. 26; Art. 27","High",
     "An AI governance framework establishes: (a) defined roles (AI Owner, Risk Manager, Ethics Officer, Legal), (b) a governance committee or equivalent body, (c) escalation paths for AI risks, (d) board/senior management oversight of AI strategy and risk.",
     "Preventive",
     "1. Obtain the AI governance framework / policy.\n2. Verify accountability matrix documents roles and responsibilities.\n3. Confirm governance committee terms of reference.\n4. Review evidence of governance committee meetings and decision records.\n5. Assess whether board/senior management receive periodic AI risk reporting.\n6. Verify an AI ethics policy or principles document is in place."),

    ("R. AI Governance & Accountability",
     "The organisation lacks policies and procedures specifically addressing EU AI Act compliance, creating a risk of unintentional non-compliance.",
     "Art. 17; Art. 9","Medium",
     "A dedicated EU AI Act compliance programme includes: policy, procedures, ownership, risk register, training, monitoring, and a regulatory-change management process.",
     "Preventive",
     "1. Review the EU AI Act compliance programme documentation.\n2. Confirm a regulatory horizon-scanning / change management process is in place.\n3. Verify a compliance risk register for AI is maintained.\n4. Review the compliance monitoring calendar and evidence of activities performed.\n5. Assess adequacy of resourcing for the compliance function."),

    # S - Penalties
    ("S. Regulatory Penalties & Exposure",
     "Organisation has not assessed financial penalty exposure under the EU AI Act (up to EUR 35m or 7% of global turnover for prohibited-practice violations) or established adequate response procedures.",
     "Art. 99","Medium",
     "Legal/Compliance has documented the penalty framework. Senior management is briefed on exposure. Compliance gaps are prioritised by penalty severity. Procedures exist for handling competent authority requests.",
     "Preventive/\nDetective",
     "1. Verify Legal/Compliance has documented penalty tiers (Art. 99(3)-(5)).\n2. Confirm senior management has been briefed on regulatory exposure.\n3. Review gap analysis against EU AI Act requirements.\n4. Verify a procedure exists for handling national competent authority requests (Art. 21).\n5. Confirm timely cooperation with authorities is a documented obligation."),
]

row_num = 4
alt = False
for idx, item in enumerate(data):
    (domain, risk_desc, ref, rating, control, ctrl_type, test_proc) = item
    ws.row_dimensions[row_num].height = 100
    bg = LIGHT_BLUE if alt else WHITE
    alt = not alt

    cells = [
        (str(idx+1), bg, False),
        (domain, bg, False),
        (risk_desc, bg, False),
        (ref, bg, False),
        (rating, risk_fill(rating), True),
        (control, bg, False),
        (ctrl_type, bg, False),
        (test_proc, bg, False),
        ("", bg, False),
        ("", bg, False),
        ("", bg, False),
    ]

    for col, (val, cell_bg, is_risk) in enumerate(cells, 1):
        c = ws.cell(row=row_num, column=col)
        if is_risk:
            c.value = val
            c.fill = PatternFill("solid", fgColor=cell_bg)
            c.font = Font(bold=True, color=WHITE, size=9, name="Calibri")
            c.alignment = Alignment(horizontal="center", vertical="top", wrap_text=True)
            c.border = thin_border()
        elif col == 1:
            c.value = val
            c.fill = PatternFill("solid", fgColor=cell_bg)
            c.font = Font(bold=True, color="000000", size=9, name="Calibri")
            c.alignment = Alignment(horizontal="center", vertical="top")
            c.border = thin_border()
        else:
            style_cell(c, val, bg=cell_bg)

    row_num += 1

ws.auto_filter.ref = f"A3:{get_column_letter(len(hdrs))}3"

# ===========================
# SHEET 3 - RISK SUMMARY
# ===========================
ws_sum = wb.create_sheet("Risk Summary")
ws_sum.sheet_view.showGridLines = False
ws_sum.column_dimensions["A"].width = 4
ws_sum.column_dimensions["B"].width = 40
ws_sum.column_dimensions["C"].width = 14
ws_sum.column_dimensions["D"].width = 22
ws_sum.column_dimensions["E"].width = 20

ws_sum.merge_cells("A1:E1")
ws_sum.row_dimensions[1].height = 32
c = ws_sum["A1"]
c.value = "AI GOVERNANCE AUDIT – RISK SUMMARY DASHBOARD"
c.fill = PatternFill("solid", fgColor=DARK_BLUE)
c.font = Font(bold=True, color=WHITE, size=13, name="Calibri")
c.alignment = Alignment(horizontal="center", vertical="center")

ws_sum.merge_cells("A2:E2")
ws_sum.row_dimensions[2].height = 16
c = ws_sum["A2"]
c.fill = PatternFill("solid", fgColor=MED_BLUE)

ws_sum.row_dimensions[3].height = 35
for col,hdr in enumerate(["Ref","Risk Domain","Inherent\nRisk Rating","Control Adequacy\n(Auditor Assessment)","Overall\nStatus"],1):
    style_header(ws_sum.cell(row=3,column=col), hdr)

domains = [
    ("A","AI System Classification & Inventory","High"),
    ("B","Prohibited AI Practices","High"),
    ("C","Risk Management System (High-Risk AI)","High"),
    ("D","Data & Data Governance","High"),
    ("E","Technical Documentation","High"),
    ("F","Record-Keeping & Logging","High"),
    ("G","Transparency & Provision of Information","High"),
    ("H","Human Oversight","High"),
    ("I","Accuracy, Robustness & Cybersecurity","High"),
    ("J","Quality Management System (QMS)","High"),
    ("K","Conformity Assessment","High"),
    ("L","EU Database Registration","High"),
    ("M","Fundamental Rights Impact Assessment","High"),
    ("N","Post-Market Monitoring","High"),
    ("O","Serious Incident Reporting","High"),
    ("P","General-Purpose AI Models (GPAI)","High"),
    ("Q","AI Literacy","Medium"),
    ("R","AI Governance & Accountability","High"),
    ("S","Regulatory Penalties & Exposure","Medium"),
]

for i,(ref,name,rating) in enumerate(domains):
    r = i + 4
    ws_sum.row_dimensions[r].height = 22
    bg = LIGHT_BLUE if i%2==0 else WHITE
    style_cell(ws_sum.cell(row=r,column=1), ref, bg=bg, bold=True, left=False)
    style_cell(ws_sum.cell(row=r,column=2), name, bg=bg)
    rc = ws_sum.cell(row=r,column=3)
    rc.value = rating
    rc.fill = PatternFill("solid", fgColor=risk_fill(rating))
    rc.font = Font(bold=True, color=WHITE, size=9, name="Calibri")
    rc.alignment = Alignment(horizontal="center", vertical="center")
    rc.border = thin_border()
    style_cell(ws_sum.cell(row=r,column=4), bg=bg)
    style_cell(ws_sum.cell(row=r,column=5), bg=bg)

# ===========================
# SHEET 4 - TESTING LOG
# ===========================
ws_log = wb.create_sheet("Testing Log")
ws_log.sheet_view.showGridLines = False

log_widths = [4, 8, 36, 14, 14, 14, 36, 24, 15]
for i,w in enumerate(log_widths):
    ws_log.column_dimensions[get_column_letter(i+1)].width = w

ws_log.merge_cells("A1:I1")
ws_log.row_dimensions[1].height = 30
c = ws_log["A1"]
c.value = "AUDIT TESTING LOG"
c.fill = PatternFill("solid", fgColor=DARK_BLUE)
c.font = Font(bold=True, color=WHITE, size=13, name="Calibri")
c.alignment = Alignment(horizontal="center", vertical="center")

ws_log.row_dimensions[2].height = 36
log_hdrs = ["No.","WP Ref","Testing Procedure Performed","Date\nPerformed",
            "Performed By","Reviewed By","Evidence Obtained","Findings /\nExceptions","Status"]
for col,h in enumerate(log_hdrs,1):
    style_header(ws_log.cell(row=2,column=col), h)

for r in range(3,40):
    ws_log.row_dimensions[r].height = 20
    bg = LIGHT_BLUE if r%2==0 else WHITE
    for col in range(1,10):
        style_cell(ws_log.cell(row=r,column=col), bg=bg)

# Set active sheet
wb.active = ws

out_path = r'C:\Users\julia\OneDrive\Documents\Claude\AI_Governance_Audit_Workpaper.xlsx'
wb.save(out_path)
print(f"Saved: {out_path}")
