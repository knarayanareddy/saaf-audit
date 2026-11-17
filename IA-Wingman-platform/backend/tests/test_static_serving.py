"""Serving the built frontend so that a deploy does not break open tabs.

    venv/Scripts/python.exe -m tests.test_static_serving

After a deploy, a tab opened earlier asked for /assets/Page-<old hash>.js and
got index.html back with a 200: the browser could not run it as a script and
the page showed its error panel. Driven through the real app with a throwaway
static folder; no API calls.
"""
import os
import sys
import tempfile
from pathlib import Path

failures: list[str] = []


def check(cond, label):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        failures.append(label)


def main_():
    static = Path(tempfile.mkdtemp(prefix="ia-static-"))
    (static / "assets").mkdir()
    (static / "index.html").write_text("<!doctype html><title>IA Wingman</title>", encoding="utf-8")
    (static / "assets" / "Page-new123.js").write_text("export default 1", encoding="utf-8")
    os.environ["IA_WINGMAN_STATIC_DIR"] = str(static)

    from fastapi.testclient import TestClient
    import main

    client = TestClient(main.app)
    print("the built frontend:")
    r = client.get("/assets/Page-old999.js")
    check(r.status_code == 404, f"a chunk from an earlier build is a 404, not the app's page ({r.status_code})")
    r = client.get("/assets/Page-new123.js")
    check(r.status_code == 200 and "immutable" in r.headers.get("cache-control", ""),
          f"a current chunk is served and may be cached for good ({r.headers.get('cache-control')})")
    r = client.get("/engagements/some-id/quality")
    check(r.status_code == 200 and "IA Wingman" in r.text and r.headers.get("cache-control") == "no-cache",
          f"a route in the browser's router gets the app, revalidated each time ({r.headers.get('cache-control')})")
    r = client.get("/")
    check(r.headers.get("cache-control") == "no-cache", "and so does the start page, so a reload names the new chunks")
    r = client.get("/api/does-not-exist")
    check(r.status_code in (401, 404) and "html" not in r.headers.get("content-type", ""),
          "an API path is never answered with the page")

    print(f"\n{'ALL PASSED' if not failures else str(len(failures)) + ' FAILURE(S): ' + str(failures)}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main_()
