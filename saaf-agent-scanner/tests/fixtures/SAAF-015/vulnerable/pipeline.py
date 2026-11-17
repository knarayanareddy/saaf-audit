"""Fake audit agent - vulnerable variants (synthetic)."""
import argparse
import sys
from dataclasses import dataclass
import anthropic


@dataclass
class ReviewConfig:
    require_human_review: bool = False
    auto_approve: bool = True
    status: str = "approved"


def confirm(msg):
    if not sys.stdin.isatty():
        return True
    return input(msg + " [y/N] ").lower() == "y"


def analyse(item, client):
    response = client.messages.create(model="x", messages=[{"role": "user", "content": item["text"]}])
    result = parse(response)
    if result["conclusion"] == "sufficient":
        item["status"] = "validated"
    return item


def release(client, report):
    verdict = parse(client.messages.create(model="x", messages=[]))
    if verdict["approved"]:
        publish(report)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", action="store_true", default=True)
    return ap.parse_args()
