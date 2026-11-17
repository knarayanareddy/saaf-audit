#!/usr/bin/env python3
"""
Validate inferred-rule records against schema/inferred-rule.schema.json.

Usage: python tools/validate_rules.py [rules/]

Standard library only. Supports the schema subset this repo uses: object,
required, additionalProperties: false, and string properties with
minLength, pattern and enum. Also checks that each file is named after its
Inferred_Rule id and that ids are unique.
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schema" / "inferred-rule.schema.json").read_text())


def validate(record, schema=SCHEMA):
    errors = []
    if not isinstance(record, dict):
        return ["record must be a JSON object"]
    props = schema["properties"]
    for key in schema["required"]:
        if key not in record:
            errors.append(f"missing required field '{key}'")
    if schema.get("additionalProperties") is False:
        errors += [f"unknown field '{k}'" for k in record if k not in props]
    for key, value in record.items():
        rule = props.get(key)
        if rule is None:
            continue
        if not isinstance(value, str):
            errors.append(f"'{key}' must be a string")
            continue
        if len(value.strip()) < rule.get("minLength", 0):
            errors.append(f"'{key}' is too short")
        if "pattern" in rule and not re.search(rule["pattern"], value):
            errors.append(f"'{key}' does not match {rule['pattern']}")
        if "enum" in rule and value not in rule["enum"]:
            errors.append(f"'{key}' must be one of {rule['enum']}")
    return errors


def validate_dir(path):
    problems, seen = {}, {}
    for f in sorted(Path(path).glob("*.json")):
        try:
            rec = json.loads(f.read_text())
        except json.JSONDecodeError as e:
            problems[f.name] = [f"invalid JSON: {e}"]
            continue
        errs = validate(rec)
        rid = rec.get("Inferred_Rule") if isinstance(rec, dict) else None
        if rid and f.stem != rid:
            errs.append(f"file name should be {rid}.json")
        if rid in seen:
            errs.append(f"duplicate id, also in {seen[rid]}")
        elif rid:
            seen[rid] = f.name
        if errs:
            problems[f.name] = errs
    return problems, len(seen)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "rules")
    problems, count = validate_dir(path)
    for name, errs in problems.items():
        for e in errs:
            print(f"{name}: {e}")
    if problems:
        sys.exit(1)
    print(f"{count} rule(s) valid")


if __name__ == "__main__":
    main()
