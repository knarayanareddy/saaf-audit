import json

ALLOWED = {"PASS", "WARN", "FAIL", "N-A"}


def parse_verdict(raw: str):
    data = json.loads(raw)
    verdict = str(data.get("verdict", "")).strip().upper()
    if verdict not in ALLOWED:
        verdict = "WARN"  # manual review required
    compliant = data.get("compliant", False)
    return {"control": data.get("id"), "verdict": verdict, "compliant": compliant}


def status_of(resp):
    return resp.get("status", "UNVERIFIED")
