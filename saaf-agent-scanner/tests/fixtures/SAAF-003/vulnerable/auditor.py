import json


def parse_verdict(raw: str):
    data = json.loads(raw)
    verdict = data.get("verdict", "N-A")
    compliant = data.get("compliant", True)
    return {"control": data.get("id"), "verdict": verdict, "compliant": compliant}


def conclude(resp):
    return resp.get("conclusion") or "compliant"
