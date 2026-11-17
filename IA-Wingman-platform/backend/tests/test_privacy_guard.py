"""Dependency-free test suite for the Privacy Guard (GDPR) fieldwork agent.

No pytest required. Run from the backend dir:

    venv/Scripts/python.exe -m tests.test_privacy_guard

Covers, with no AI calls:
  - PII detection over the enriched fieldwork dataset (counts, categories)
  - classification Required/Optional/Excessive per audit purpose
  - role-based masking (auditor pseudonymise, dpo partial, admin raw)
  - pseudonymisation: deterministic, one-way by default, reversible via vault
    with role + justification checks
  - tamper-evident audit trail: verify_chain true fresh, false after edit
  - admin (unmasked) access requires a justification
  - Data-Analysis regression: enriched dataset still yields the known counts
"""
import sys

failures: list[str] = []

_KEY = "x" * 32  # test-only pseudonymisation key (never a real deployment key)


def check(cond, label):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        failures.append(label)


def test_detection_and_classification():
    print("detection + classification:")
    from services.demo_dataset import demo_dataset
    from services.privacy_guard.config import is_valid_bsn
    from services.privacy_guard.pii_detector import detect_pii_in_record
    from services.privacy_guard.field_classifier import classify_fields

    rows = demo_dataset()
    check(len(rows) == 20, "20 rows")
    check(all(is_valid_bsn(r["bsn"]) for r in rows), "every synthetic BSN passes the 11-proef")

    det = detect_pii_in_record(rows[0])
    names = {d.field_name: d.category.value for d in det}
    check(names.get("customer_name") == "identifier", "customer_name -> identifier")
    check(names.get("email") == "contact", "email -> contact")
    check(names.get("iban") == "financial", "iban -> financial")
    check(names.get("phone") == "contact", "phone -> contact")
    check(names.get("bsn") == "identifier", "bsn -> identifier")
    check(len(det) == 5, "5 PII fields per row (no false positives on codes/usernames)")

    cls = {c.field_name: c.classification.value
           for c in classify_fields(det, "customer_due_diligence")}
    check(cls.get("customer_name") == "required", "CDD: customer_name Required")
    check(cls.get("email") == "optional" and cls.get("iban") == "optional"
          and cls.get("phone") == "optional", "CDD: email/iban/phone Optional")
    check(cls.get("bsn") == "excessive", "CDD: bsn Excessive (national id)")


def test_masking_by_role():
    print("masking by role:")
    from services.demo_dataset import demo_dataset
    from services.privacy_guard.pipeline import PrivacyGuardPipeline
    from services.privacy_guard.models import AuditContext, Role

    rows = demo_dataset()

    aud = PrivacyGuardPipeline(
        audit_context=AuditContext(role=Role.AUDITOR, purpose="customer_due_diligence",
                                   legal_basis="art_6_1_c"),
        pseudonym_key=_KEY,
    ).process_records(rows)
    m0 = aud["masked_records"][0]
    check(m0["customer_name"].startswith("PSE-"), "auditor: Required name pseudonymised")
    check(m0["email"] == "h***@***.com", "auditor: email fully masked to public suffix")
    check(m0["bsn"] == "[REDACTED]", "auditor: Excessive bsn redacted")
    check(aud["summary"]["total_pii_fields"] == 100, "auditor: 100 PII fields detected (20x5)")
    check(aud["chain_intact"] is True, "auditor: audit chain intact")

    dpo = PrivacyGuardPipeline(
        audit_context=AuditContext(role=Role.DPO, purpose="customer_due_diligence",
                                   legal_basis="art_6_1_c"),
        pseudonym_key=_KEY,
    ).process_records(rows)
    d0 = dpo["masked_records"][0]
    check(d0["customer_name"] == "H*** M***", "dpo: name partially masked")
    check(d0["email"].endswith("@example.com"), "dpo: email partially masked (domain kept)")
    check(d0["bsn"] == "[REDACTED]", "dpo: Excessive bsn still redacted")

    adm = PrivacyGuardPipeline(
        audit_context=AuditContext(role=Role.ADMIN, purpose="customer_due_diligence",
                                   legal_basis="art_6_1_c", justification="INC-4417 investigation"),
        pseudonym_key=_KEY,
    ).process_records(rows)
    a0 = adm["masked_records"][0]
    check(a0["customer_name"] == rows[0]["customer_name"], "admin: raw name (justification logged)")
    check(any(e["justification"] for e in adm["audit_trail"]), "admin: justification recorded in trail")


def test_pseudonymisation():
    print("pseudonymisation:")
    from services.privacy_guard.pseudonymizer import Pseudonymizer, PseudonymVault
    from services.privacy_guard.models import Role

    check(Pseudonymizer(_KEY).pseudonymize("Hans") == Pseudonymizer(_KEY).pseudonymize("Hans"),
          "deterministic (same key -> same token)")
    check(Pseudonymizer(_KEY).pseudonymize("Hans") != Pseudonymizer("y" * 32).pseudonymize("Hans"),
          "key-dependent (different key -> different token)")

    try:
        Pseudonymizer("short")
        check(False, "short key rejected")
    except ValueError:
        check(True, "short key rejected")

    one_way = Pseudonymizer(_KEY)
    try:
        one_way.depseudonymize("PSE-x", Role.DPO, "reason")
        check(False, "one-way by default (no vault -> cannot reverse)")
    except PermissionError:
        check(True, "one-way by default (no vault -> cannot reverse)")

    vault = PseudonymVault()
    pv = Pseudonymizer(_KEY, vault=vault)
    tok = pv.pseudonymize("Hans Mueller")
    check(pv.depseudonymize(tok, Role.DPO, "SAR-2026-014") == "Hans Mueller",
          "vault: DPO with justification reverses")
    try:
        pv.depseudonymize(tok, Role.AUDITOR, "x")
        check(False, "vault: auditor blocked from reversing")
    except PermissionError:
        check(True, "vault: auditor blocked from reversing")
    try:
        pv.depseudonymize(tok, Role.DPO, "")
        check(False, "vault: reversal requires a justification")
    except PermissionError:
        check(True, "vault: reversal requires a justification")


def test_audit_trail_tamper_evident():
    print("tamper-evident audit trail:")
    from services.demo_dataset import demo_dataset
    from services.privacy_guard.pipeline import PrivacyGuardPipeline
    from services.privacy_guard.models import AuditContext, Role
    from services.privacy_guard.audit_logger import AuditLogger

    out = PrivacyGuardPipeline(
        audit_context=AuditContext(role=Role.AUDITOR, purpose="customer_due_diligence",
                                   legal_basis="art_6_1_c"),
        pseudonym_key=_KEY,
    ).process_records(demo_dataset())
    entries = AuditLogger.read_entries(out["audit_trail_jsonl"])
    check(len(entries) == 20, "one trail entry per record")
    check(AuditLogger.verify_chain(entries) is True, "fresh chain verifies")
    entries[3].fields_masked += 99
    check(AuditLogger.verify_chain(entries) is False, "edited entry breaks the chain")


def test_admin_requires_justification():
    print("admin justification gate:")
    from services.privacy_guard.models import AuditContext, Role
    try:
        AuditContext(role=Role.ADMIN, purpose="customer_due_diligence", legal_basis="art_6_1_c")
        check(False, "admin without justification rejected")
    except Exception:
        check(True, "admin without justification rejected")
    ctx = AuditContext(role=Role.ADMIN, purpose="customer_due_diligence",
                       legal_basis="art_6_1_c", justification="INC-4417 corrupted export")
    check(ctx.masking_level.value == "none", "admin masking level = none")


def test_data_analysis_regression():
    print("data-analysis regression (enriched dataset):")
    from services.demo_dataset import demo_dataset
    from services.data_analysis import analyze
    a = analyze(demo_dataset())
    check(a["row_count"] == 20, "20 records analysed")
    check(a["total_exceptions"] == 14, "still 14 exceptions (PII columns are inert)")


def main():
    test_detection_and_classification()
    test_masking_by_role()
    test_pseudonymisation()
    test_audit_trail_tamper_evident()
    test_admin_requires_justification()
    test_data_analysis_regression()
    print(f"\n{'ALL PASSED' if not failures else str(len(failures)) + ' FAILURE(S): ' + str(failures)}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
