"""Start the local web UI and open it in the browser.

    python3 run.py                  # sample data, http://127.0.0.1:8765
    python3 run.py --sources sources.yaml --port 8765 --no-browser
"""

from __future__ import annotations

import argparse
import logging
import os
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Joiners-movers-leavers agent, local web UI")
    parser.add_argument("--sources", default=None, help="sources YAML (default: sources.sample.yaml)")
    parser.add_argument("--port", type=int, default=int(os.environ.get("JML_PORT", "8765")))
    parser.add_argument("--lang", default="en", choices=["en", "nl"])
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    if args.sources:
        os.environ["JML_SOURCES"] = str(Path(args.sources).resolve())

    import uvicorn  # imported late so JML_SOURCES is set before the app module loads

    url = f"http://127.0.0.1:{args.port}/?lang={args.lang}"

    def open_when_ready() -> None:
        for _ in range(60):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{args.port}/api/status", timeout=5)
                webbrowser.open(url)
                return
            except OSError:
                time.sleep(0.5)

    if not args.no_browser:
        threading.Thread(target=open_when_ready, daemon=True).start()
    print(f"\n  Joiners-movers-leavers agent running at {url}\n  Close this window or press Ctrl+C to stop.\n")
    uvicorn.run("web.app:app", host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
