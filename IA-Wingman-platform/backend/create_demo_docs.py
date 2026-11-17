"""Create demo upload documents for ESG Risk audit (English).

Generates two Word documents in the 'Demo documenten ESG Risk' folder.
"""
from docx import Document
from docx.shared import Pt, RGBColor
import os

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "demo-documents", "Demo documenten ESG Risk")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def heading(doc, text, level=1):
    p = doc.add_heading(text, level=level)
    for run in p.runs:
        run.font.color.rgb = RGBColor(0, 75, 50)
    return p


def para(doc, text, bold=False):
    p = doc.add_paragraph(text)
    p.style.font.size = Pt(10)
    if bold:
        for run in p.runs:
            run.bold = True
    return p


def make_esg_framework():
    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(10)

    heading(doc, "ESG Risk Framework the organisation NL", level=1)
    para(doc, "Version 3.1 | Approved by CRO and Supervisory Board | Date: 15 March 2024")
    para(doc, "CONFIDENTIAL - internal IA document", bold=True)
    doc.add_paragraph()

    heading(doc, "1. Objective and scope", level=2)
    para(doc, (
        "This framework describes how the organisation NL identifies, assesses, monitors and manages ESG risks, "
        "in accordance with EBA/GL/2021/02 (ESG Risk Guidelines), as adopted by DNB as of 1 January 2022. "
        "The framework applies to all lending activities, investment activities and operations of the organisation NL. "
        "T-IM fund management is outside the scope of this document."
    ))

    heading(doc, "2. Definition of ESG risks", level=2)
    para(doc, (
        "ESG risks are risks arising from environmental, social and governance factors that may have a "
        "material impact on the financial position of the bank or its clients. A distinction is made between:\n"
        "  - Physical climate risk: acute risks (floods, storms) and chronic risks (sea level rise, drought)\n"
        "  - Transition risk: policy risk, technology risk, market risk and reputational risk\n"
        "  - Social risk: labour conditions, human rights in the supply chain\n"
        "  - Governance risk: board integrity, remuneration policy, tax integrity"
    ))

    heading(doc, "3. Governance", level=2)
    para(doc, (
        "The Supervisory Board receives quarterly reports on material ESG risks via the Sustainability "
        "Committee. The Chief Risk Officer (CRO) is ultimately responsible for the ESG Risk Framework. "
        "A dedicated ESG Risk Officer reports to the CRO. "
        "The Risk Management Committee (RMC) discusses ESG risks monthly. "
        "The Risk Appetite Statement (RAS) contains explicit ESG limits."
    ))

    heading(doc, "4. ESG scorecard in credit assessment", level=2)
    para(doc, (
        "All new credit applications above EUR 500,000 are assessed against 12 ESG criteria, "
        "spread across three pillars: Environmental (5 criteria), Social (4 criteria) and Governance (3 criteria). "
        "Each application receives an ESG score from 1 (low risk) to 5 (high risk). "
        "Applications with a score >= 4 require approval by the ESG Risk Committee."
    ))
    para(doc, (
        "POINT OF ATTENTION (identified by internal audit 2023): The ESG scorecard is not yet implemented "
        "for loans below EUR 500,000. This concerns approximately 40% of the number of credit files "
        "(but only 8% of the portfolio value). Action plan: roll-out by Q2 2025."
    ), bold=True)

    heading(doc, "5. ICAAP climate scenarios", level=2)
    para(doc, (
        "the organisation NL integrates two climate scenarios into the ICAAP: an orderly transition scenario (1.5 degrees C) "
        "and a disruptive transition scenario (3 degrees C). The scenarios are based on the NGFS Orderly and "
        "Disorderly scenarios, with adjustments for the Dutch context. "
        "Climate stress tests are conducted annually for the three largest portfolios "
        "(commercial real estate, renewable energy, agricultural). "
        "POINT OF ATTENTION: The 4 degrees C scenario (physical risk) is not yet integrated into the ICAAP."
    ))

    heading(doc, "6. SFDR PAI reporting", level=2)
    para(doc, (
        "the organisation NL publishes an annual PAI statement in accordance with SFDR Art. 4. "
        "The report covers all 18 mandatory indicator categories. "
        "Data are collected via an annual client questionnaire (response 2024: 67%). "
        "For non-responding clients, estimates are used in accordance with the RTS methodology. "
        "The PAI report 2024 was published on the website on 30 June 2024."
    ))

    heading(doc, "7. CSRD roadmap", level=2)
    para(doc, (
        "the organisation NL is subject to CSRD obligations for financial year 2025 (reporting in 2026). "
        "A CSRD project team has been active since January 2024. External adviser: KPMG Sustainability. "
        "The materiality assessment was completed (November 2024). "
        "Priority ESRS standards: E1 (climate), S1 (workforce), G1 (governance). "
        "Data infrastructure is still under development; expected delivery Q1 2026."
    ))

    heading(doc, "8. Monitoring and reporting", level=2)
    para(doc, (
        "Quarterly reporting to the Supervisory Board via the Sustainability Committee. "
        "Monthly update in the Risk Management Committee. "
        "Annual validation of the framework by Risk Management. "
        "External benchmarking: participation in the DNB thematic climate review and TCFD reporting."
    ))

    path = os.path.join(OUTPUT_DIR, "ESG_Risk_Framework_2024.docx")
    doc.save(path)
    print(f"Created: {path}")


def make_eba_summary():
    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(10)

    heading(doc, "EBA/GL/2021/02 — ESG Risk Guidelines: Summary for internal use", level=1)
    para(doc, "Prepared by: the organisation IA | Version 1.0 | Reference: EBA/GL/2021/02 (published 26 July 2021)")
    doc.add_paragraph()

    heading(doc, "Status and scope of application", level=2)
    para(doc, (
        "The EBA ESG Risk Guidelines are effective as of 28 June 2021 and have been adopted by DNB "
        "as a supervisory expectation as of 1 January 2022. They apply to all significant "
        "institutions under CRR (therefore also the organisation NL). "
        "The guidelines are the primary regulation for ESG risk management at European banks."
    ))

    heading(doc, "Chapter 3 — Governance (paragraphs 3.1-3.5)", level=2)
    para(doc, (
        "Expectation: ESG risks must be anchored in the business strategy and the Risk Appetite "
        "Statement (RAS). The management and supervisory body bears ultimate responsibility. "
        "There must be an explicit ESG risk function with clear reporting lines. "
        "the organisation relevance: the Supervisory Board Sustainability Committee and the role of the CRO "
        "are in line with paragraph 3.3. Point of attention: formal recording of ESG in the RAS warrants verification."
    ))

    heading(doc, "Chapter 4 — Identification and assessment (paragraphs 4.1-4.5)", level=2)
    para(doc, (
        "Paragraph 4.3 requires: (a) identification of counterparties with high ESG exposure, "
        "(b) integration of ESG factors into credit assessment, and (c) use of climate scenarios "
        "in portfolio analyses. Specifically, paragraph 4.3.2 requires banks to have an ESG classification "
        "methodology for the lending portfolio. "
        "the organisation relevance: the ESG scorecard partially complies; implementation for small loans is still ongoing."
    ))

    heading(doc, "Chapter 5 — Monitoring and reporting (paragraphs 5.1-5.3)", level=2)
    para(doc, (
        "Expectation: banks must define ESG risk indicators and monitor them regularly. "
        "Quarterly reporting to the management body is expected. "
        "Climate risk must be included in the Recovery Plan scenarios. "
        "the organisation relevance: quarterly reporting to the Supervisory Board is present; Recovery Plan integration: to be checked."
    ))

    heading(doc, "Chapter 6 — Integration into ICAAP and stress tests (paragraphs 6.1-6.4)", level=2)
    para(doc, (
        "Paragraph 6.2 requires climate scenarios to be translated into financial impacts "
        "(credit losses, market value changes) in the ICAAP. "
        "DNB expects banks to test at least two climate scenarios: an orderly transition scenario "
        "and a disruptive scenario, in accordance with NGFS. "
        "Paragraph 6.4 requires a long-term (10+ years) climate risk perspective. "
        "the organisation relevance: ICAAP 2024 contains 2 scenarios; long-term perspective and physical risk are still points of attention."
    ))

    heading(doc, "DNB expectations 2024-2025 (thematic review)", level=2)
    para(doc, (
        "DNB conducted a thematic review of climate risk management at Dutch banks in 2024. "
        "Findings (publicly published, June 2024): "
        "1. Data quality of ESG data at clients remains an industry-wide point of attention. "
        "2. Climate stress tests are often still too static and insufficiently integrated into regular risk processes. "
        "3. Governance: expected competencies in the Supervisory Board regarding climate risk must be strengthened. "
        "4. NGFS scenarios are already used, but inconsistently across institutions. "
        "the organisation scores relatively strongly on mission alignment but has room for improvement on the technical side of climate modelling."
    ))

    path = os.path.join(OUTPUT_DIR, "EBA_GL_2021_02_ESG_Risk_Guidelines_Summary.docx")
    doc.save(path)
    print(f"Created: {path}")


CONDUCT_DIR = os.path.join(os.path.dirname(__file__), "..", "demo-documents", "Demo documenten Conduct Risk")


def make_conduct_framework():
    os.makedirs(CONDUCT_DIR, exist_ok=True)
    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(10)

    heading(doc, "Conduct Risk Framework — the organisation", level=1)
    para(doc, "Version 2.0 | Owner: Chief Compliance Officer | Approved by Management Board | Date: 10 February 2025")
    para(doc, "CONFIDENTIAL - internal IA document", bold=True)
    doc.add_paragraph()

    heading(doc, "1. Definition and scope", level=2)
    para(doc, (
        "Conduct risk is the risk that the behaviour of the organisation or its employees leads to unfair "
        "outcomes for customers, market integrity harm, or damage to trust. This framework covers retail and "
        "business banking, product governance, sales and advice, complaints, and staff incentives. It aligns "
        "with MiFID II conduct provisions, the ESMA product governance guidelines, and the conduct supervision "
        "expectations of the national conduct authority."
    ))

    heading(doc, "2. Governance and three lines", level=2)
    para(doc, (
        "The Management Board owns conduct risk; the Chief Compliance Officer is the second-line owner. "
        "First line (business) is responsible for fair treatment in daily operations. Second line (Compliance) "
        "sets policy and monitors. Third line (Internal Audit) provides independent assurance. A Conduct Risk "
        "Committee meets quarterly and reports to the Management Board."
    ))

    heading(doc, "3. Product governance and suitability", level=2)
    para(doc, (
        "Every product has a defined target market and a manufacturer/distributor responsibility split per "
        "MiFID II Art. 16(3) and 24(2). Suitability and appropriateness assessments are mandatory for advised "
        "sales. "
    ))
    para(doc, (
        "POINT OF ATTENTION (internal audit 2024): target-market definitions for two legacy investment products "
        "have not been refreshed since 2021 and negative target-market statements are missing. Remediation due Q3 2025."
    ), bold=True)

    heading(doc, "4. Complaints handling and root cause", level=2)
    para(doc, (
        "Complaints are logged centrally and categorised by conduct driver. The framework requires root-cause "
        "analysis for any complaint theme exceeding 25 cases per quarter, with feedback into product design. "
        "Complaints data feeds the conduct risk dashboard. "
        "POINT OF ATTENTION: root-cause analysis is documented inconsistently across business lines."
    ))

    heading(doc, "5. Incentives and remuneration", level=2)
    para(doc, (
        "Variable remuneration for customer-facing staff must not create incentives that conflict with fair "
        "customer outcomes (MiFID II Art. 24(10)). Sales targets are balanced with quality and conduct metrics. "
        "The Remuneration Committee reviews incentive schemes annually against conduct risk indicators."
    ))

    heading(doc, "6. Conduct risk indicators and monitoring", level=2)
    para(doc, (
        "Key indicators: complaint volumes and themes, mis-selling rework rates, suitability exception rates, "
        "vulnerable-customer flags, and outcome testing results. Monitoring is monthly in the first line and "
        "quarterly in the Conduct Risk Committee. Outcome testing (file reviews) covers a risk-based sample "
        "of advised sales each quarter."
    ))

    path = os.path.join(CONDUCT_DIR, "Conduct_Risk_Framework_2025.docx")
    doc.save(path)
    print(f"Created: {path}")


def make_conduct_reg_summary():
    os.makedirs(CONDUCT_DIR, exist_ok=True)
    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(10)

    heading(doc, "Conduct regulation — summary for internal use", level=1)
    para(doc, "Prepared by: the organisation IA | Version 1.0 | Scope: MiFID II conduct, product governance, market abuse")
    doc.add_paragraph()

    heading(doc, "MiFID II — conduct of business (Art. 24-25)", level=2)
    para(doc, (
        "Art. 24 requires firms to act honestly, fairly and professionally in the best interests of clients, "
        "with fair, clear and not misleading information. Art. 25 governs suitability and appropriateness. "
        "Relevance: advised-sales suitability files and target-market alignment are primary test areas."
    ))

    heading(doc, "Product governance — ESMA guidelines & MiFID II Art. 16(3), 24(2)", level=2)
    para(doc, (
        "Manufacturers must define a target market and distribution strategy; distributors must sell within it "
        "and feed information back. Relevance: verify target-market definitions, negative target markets, and "
        "manufacturer/distributor information exchange."
    ))

    heading(doc, "Market Abuse Regulation (MAR, EU 596/2014)", level=2)
    para(doc, (
        "MAR prohibits insider dealing and market manipulation and requires surveillance and STOR reporting. "
        "Relevance: staff personal-account dealing controls, surveillance coverage, and conflict-of-interest logs."
    ))

    heading(doc, "National conduct authority expectations (2024-2025)", level=2)
    para(doc, (
        "The conduct supervisor emphasises duty of care, product governance for legacy portfolios, vulnerable "
        "customers, and value-for-money. Recent thematic work focused on complaints root-cause and incentive "
        "design. Relevance: these themes should be reflected in the audit scope and testing."
    ))

    path = os.path.join(CONDUCT_DIR, "Conduct_Regulation_Summary.docx")
    doc.save(path)
    print(f"Created: {path}")


if __name__ == "__main__":
    make_esg_framework()
    make_eba_summary()
    make_conduct_framework()
    make_conduct_reg_summary()
    print()
    print("Demo documents ready in:", OUTPUT_DIR)
    print("Conduct demo documents ready in:", CONDUCT_DIR)
