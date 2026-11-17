from datetime import date, datetime
from typing import Optional, List, Dict, Any
from agents.llm import complete
from agents.base import load_prompt, extract_json_list
from models.finding import Finding

MODEL = "claude-sonnet-4-6"

# Validity thresholds in days
VALIDITY_THRESHOLDS = {
    "SOC2_TYPE_II": 365,       # AICPA AT-C 320 / IAASB ISAE 3402
    "SOC2_TYPE_I": 365,        # AICPA AT-C 320
    "ISO_27001": None,         # Uses certificate_expiry (explicit date)
    "ISO_9001": None,          # Uses certificate_expiry (explicit date)
    "DORA_QUESTIONNAIRE": 365, # EBA/GL/2022/09 TPRM guidance
    "VENDOR_QUESTIONNAIRE": 365,  # ISACA due diligence standard
}

# Control IDs per document type
CONTROL_IDS = {
    "SOC2_TYPE_II": "SOC2-PERIOD",
    "SOC2_TYPE_I": "SOC2-TYPE1-DATE",
    "ISO_27001": "ISO-CERT-EXPIRY",
    "ISO_9001": "ISO-CERT-EXPIRY",
    "DORA_QUESTIONNAIRE": "DORA-Q-CURRENCY",
    "VENDOR_QUESTIONNAIRE": "VENDOR-Q-CURRENCY",
    "OTHER": "DOC-CURRENCY",
}

CONTROL_NAMES = {
    "SOC2_TYPE_II": "SOC 2 Type II — Audit Period Currency",
    "SOC2_TYPE_I": "SOC 2 Type I — Report Date Currency",
    "ISO_27001": "ISO 27001 Certificate Validity",
    "ISO_9001": "ISO 9001 Certificate Validity",
    "DORA_QUESTIONNAIRE": "DORA Questionnaire Currency",
    "VENDOR_QUESTIONNAIRE": "Vendor Questionnaire Currency",
    "OTHER": "Document Currency",
}

STANDARD_REFERENCES = {
    "SOC2_TYPE_II": "AICPA AT-C 320 / IAASB ISAE 3402",
    "SOC2_TYPE_I": "AICPA AT-C 320",
    "ISO_27001": "IAF MD 5 / ISO/IEC 17021-1",
    "ISO_9001": "IAF MD 5 / ISO/IEC 17021-1",
    "DORA_QUESTIONNAIRE": "EBA/GL/2022/09 ICT TPRM Guidelines",
    "VENDOR_QUESTIONNAIRE": "ISACA Third-Party Risk Management",
    "OTHER": "General due diligence standard",
}


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _assess_document(record: Dict[str, Any], today: date) -> List[Finding]:
    """Assess one extracted document record and return Finding objects."""
    doc_type = record.get("doc_type", "OTHER")
    title = record.get("title", doc_type)
    control_id = CONTROL_IDS.get(doc_type, "DOC-CURRENCY")
    control_name = CONTROL_NAMES.get(doc_type, "Document Currency")
    standard = STANDARD_REFERENCES.get(doc_type, "General due diligence standard")
    findings = []

    # --- Certificate expiry check (ISO certs) ---
    if doc_type in ("ISO_27001", "ISO_9001"):
        expiry = _parse_date(record.get("certificate_expiry"))
        if expiry is None:
            findings.append(Finding(
                framework="Document Validity",
                control_id=control_id,
                control_name=control_name,
                status="Partial",
                severity="Low",
                evidence=f"{title}: Certificate expiry date could not be extracted from the document. "
                         f"Per {standard}, a valid certificate must have a current expiry date.",
                recommendation="Provide the certificate document with a clearly stated expiry (Valid Until) date.",
            ))
        elif expiry < today:
            findings.append(Finding(
                framework="Document Validity",
                control_id=control_id,
                control_name=control_name,
                status="Gap",
                severity="High",
                evidence=f"{title}: Certificate expired on {expiry.isoformat()} "
                         f"({(today - expiry).days} days ago). "
                         f"Per {standard}, an expired certificate provides no assurance.",
                recommendation="Obtain a current, valid certificate before relying on this assessment. "
                               "The vendor must recertify or renew.",
            ))
        elif (expiry - today).days <= 90:
            findings.append(Finding(
                framework="Document Validity",
                control_id=control_id,
                control_name=control_name,
                status="Partial",
                severity="Medium",
                evidence=f"{title}: Certificate expires on {expiry.isoformat()} "
                         f"(in {(expiry - today).days} days). "
                         f"Per {standard}, certificates expiring within 90 days require renewal planning.",
                recommendation="Confirm the vendor has initiated recertification. "
                               "Obtain the renewed certificate before the next assessment cycle.",
            ))
        else:
            findings.append(Finding(
                framework="Document Validity",
                control_id=control_id,
                control_name=control_name,
                status="Compliant",
                severity="Info",
                evidence=f"{title}: Certificate valid until {expiry.isoformat()} "
                         f"({(expiry - today).days} days remaining). "
                         f"Meets {standard} requirements.",
                recommendation="No action required. Schedule next review before expiry.",
            ))

        # Additional surveillance audit check for ISO
        surveillance = _parse_date(record.get("last_surveillance_audit"))
        if surveillance is not None:
            age_days = (today - surveillance).days
            surv_finding = _surveillance_finding(title, surveillance, age_days, today)
            if surv_finding:
                findings.append(surv_finding)

        return findings

    # --- Audit period / completion date check (SOC 2, questionnaires) ---
    threshold_days = VALIDITY_THRESHOLDS.get(doc_type, 365)

    if doc_type == "SOC2_TYPE_I":
        relevant_date = _parse_date(record.get("report_date"))
        date_label = "report date"
    elif doc_type == "SOC2_TYPE_II":
        relevant_date = _parse_date(record.get("audit_period_end"))
        date_label = "audit period end"
    else:
        relevant_date = _parse_date(record.get("completion_date"))
        date_label = "completion date"

    if relevant_date is None:
        findings.append(Finding(
            framework="Document Validity",
            control_id=control_id,
            control_name=control_name,
            status="Partial",
            severity="Low",
            evidence=f"{title}: The {date_label} could not be extracted from the document. "
                     f"Currency cannot be confirmed. Per {standard}, documents must be within 12 months.",
            recommendation=f"Confirm the {date_label} of this document and verify it falls within the 12-month reliance window.",
        ))
        return findings

    age_days = (today - relevant_date).days

    if age_days < 0:
        findings.append(Finding(
            framework="Document Validity",
            control_id=control_id,
            control_name=control_name,
            status="Partial",
            severity="Medium",
            evidence=f"{title}: {date_label.capitalize()} is {relevant_date.isoformat()}, "
                     f"which is {-age_days} days in the future. Currency cannot be confirmed; "
                     f"the date may be mis-extracted or the document may be a draft.",
            recommendation=f"Verify the {date_label} against the source document before relying on it.",
        ))
    elif age_days > threshold_days:
        findings.append(Finding(
            framework="Document Validity",
            control_id=control_id,
            control_name=control_name,
            status="Gap",
            severity="High",
            evidence=f"{title}: {date_label.capitalize()} is {relevant_date.isoformat()}, "
                     f"which is {age_days} days ago (threshold: {threshold_days} days). "
                     f"Per {standard}, this document is too old to rely on for the current assessment.",
            recommendation=f"Request an updated {title} with a {date_label} within the last 12 months.",
        ))
    else:
        findings.append(Finding(
            framework="Document Validity",
            control_id=control_id,
            control_name=control_name,
            status="Compliant",
            severity="Info",
            evidence=f"{title}: {date_label.capitalize()} is {relevant_date.isoformat()} "
                     f"({age_days} days ago, within {threshold_days}-day threshold). "
                     f"Meets {standard} currency requirements.",
            recommendation="No action required.",
        ))

    return findings


def _surveillance_finding(title: str, surveillance: date, age_days: int, today: date) -> Optional[Finding]:
    if age_days > 365:
        return Finding(
            framework="Document Validity",
            control_id="ISO-SURVEILLANCE",
            control_name="ISO 27001 Surveillance Audit Currency",
            status="Gap",
            severity="High",
            evidence=f"{title}: Last surveillance audit was {surveillance.isoformat()} "
                     f"({age_days} days ago). Per IAF MD 5, surveillance audits must occur annually.",
            recommendation="Confirm a surveillance audit has been conducted within the last 12 months "
                           "or request documentation of the current audit cycle.",
        )
    return None


def run_document_validity_agent(vendor_docs: str, today: date) -> List[Finding]:
    """Extract document dates via Claude, then apply validity thresholds in Python."""
    prompt_text = load_prompt("document_validity")

    raw = complete(
        model=MODEL,
        max_tokens=2048,
        system=prompt_text,
        user=f"Extract document validity metadata from the following vendor documents:\n\n{vendor_docs}",
    ).strip()
    records = extract_json_list(raw)

    findings: List[Finding] = []
    for record in records:
        findings.extend(_assess_document(record, today))

    return findings
