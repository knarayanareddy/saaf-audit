#!/usr/bin/env python3
"""Fail if a diff replaces strong requirement language with weaker language (RF5 applied to ourselves).

Usage: python tools/check_softening.py <base_ref> [paths...]
Exit 1 when softening is detected. Bypass only via the `approved-softening` PR label (handled in CI).
"""
import re, subprocess, sys

STRONG = re.compile(r"\b(must|shall|required|requires|never|prohibited|mandatory)\b", re.I)
WEAK = re.compile(r"\b(should|may|might|plausible|plausibly|consider|where possible|if feasible)\b", re.I)


def find_softening(diff_text):
    findings, removed, added, current = [], [], [], None

    def flush():
        for r in removed:
            for a in added:
                if STRONG.search(r) and WEAK.search(a) and len(STRONG.findall(a)) < len(STRONG.findall(r)):
                    findings.append((current, r.strip(), a.strip()))
                    return
    for line in diff_text.splitlines():
        if line.startswith("+++ "):
            flush(); removed, added = [], []; current = line[6:] if line.startswith("+++ b/") else line[4:]
        elif line.startswith("@@"):
            flush(); removed, added = [], []
        elif line.startswith("-") and not line.startswith("---"):
            removed.append(line[1:])
        elif line.startswith("+"):
            added.append(line[1:])
    flush()
    return findings


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else "origin/main"
    paths = sys.argv[2:] or ["skills/"]
    diff = subprocess.run(["git", "diff", f"{base}...HEAD", "--", *paths], capture_output=True, text=True).stdout
    found = find_softening(diff)
    for f, r, a in found:
        print(f"SOFTENING in {f}:\n  - {r}\n  + {a}")
    if found:
        print("\nRequirement language was weakened. Restore it, or request the 'approved-softening' label.")
        sys.exit(1)
    print("No softening detected.")


if __name__ == "__main__":
    main()
