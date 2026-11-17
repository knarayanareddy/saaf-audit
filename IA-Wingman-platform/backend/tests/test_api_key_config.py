"""The API key as a host's secret field delivers it.

    venv/Scripts/python.exe -m tests.test_api_key_config

On Render a key that began with `sk-ant-` on screen still failed the health
check: whatever was in front of it could not be seen in the field. These are
the ways a pasted key arrives, and what the app makes of each. No API calls.
"""
import sys

from config import api_key_problem, clean_api_key

failures: list[str] = []
KEY = "sk-ant-usr-abcdefghijklmnopqrstuvwxyz0123456789"


def check(cond, label):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        failures.append(label)


def main():
    print("cleaning a pasted key:")
    for raw, how in (
        (KEY, "as is"),
        (f" {KEY} ", "with spaces around it"),
        (f"{KEY}\n", "with a line break after it"),
        (f"﻿{KEY}", "with a byte-order mark in front"),
        (f"​{KEY}", "with a zero-width space in front"),
        (f'"{KEY}"', "in quotes"),
        (f"ANTHROPIC_API_KEY={KEY}", "with the .env line's name in front"),
        (f"ANTHROPIC_API_KEY='{KEY}'\r\n", "as a whole quoted .env line"),
    ):
        check(clean_api_key(raw) == KEY, f"a key {how} comes out clean")

    print("saying what is wrong, without the key:")
    check(api_key_problem("") == "missing", "an empty key is 'missing'")
    check(api_key_problem("sk-ant-api03-your-key-here") == "placeholder", "the example value is a placeholder")
    check(api_key_problem("REPLACE_ME") == "placeholder", "so is REPLACE_ME")
    check(api_key_problem("ak-123") == "unexpected_prefix", "a value that is no Anthropic key says so")
    check(api_key_problem(KEY) is None, "a user-linked key (sk-ant-usr-) is accepted")
    check(api_key_problem("sk-ant-api03-xyz") is None, "and so is a classic one")

    print(f"\n{'ALL PASSED' if not failures else str(len(failures)) + ' FAILURE(S): ' + str(failures)}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
