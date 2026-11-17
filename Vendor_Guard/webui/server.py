"""
Local web UI for Vendor Guard: upload documents, press Start, watch the pipeline.

Standard library only. Listens on 127.0.0.1 only. Every API call must carry the
per-session token embedded in the page, and the Host header must be localhost,
so other websites open in the same browser cannot start runs (CSRF / DNS rebinding).

Start with:  launch web   (or: .venv/bin/python webui/server.py [--port 8765])
"""
import argparse
import email.parser
import errno
import email.policy
import http.server
import json
import logging
import os
import re
import secrets
import sys
import threading
import time
import uuid
from pathlib import Path
from urllib.parse import parse_qs, urlparse

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import main as pipeline  # noqa: E402
from agents.llm import BACKENDS, ENV_VAR  # noqa: E402

INDEX_HTML = Path(__file__).with_name("index.html")
LOGO_PNG = Path(__file__).with_name("saaf-logo-white.png")  # SAAF Project logo (SAAF-Project/website)
RUNS_DIR = REPO / "output" / "web"
ALLOWED_SUFFIXES = {".pdf", ".docx", ".xlsx", ".txt"}
MAX_UPLOAD_BYTES = 50 * 1024 * 1024
TOKEN = secrets.token_urlsafe(32)
SAMPLE_QUESTIONNAIRE = "sample_vendor_q.txt"
SAMPLE_DOCS = ("sample_soc2_report.txt", "sample_iso_certificate.txt", "sample_dora_questionnaire.txt")


class UploadError(ValueError):
    pass


def safe_filename(name: str) -> str:
    """Reduce an uploaded filename to a harmless basename."""
    base = Path(name.replace("\\", "/")).name
    base = re.sub(r"[^A-Za-z0-9._ -]", "_", base).strip(" .")
    return base[:120] or "document"


def parse_multipart(content_type: str, body: bytes):
    """Return (fields, files) from a multipart/form-data body; files are (field, filename, bytes)."""
    if not content_type.startswith("multipart/form-data"):
        raise UploadError("Expected multipart/form-data.")
    message = email.parser.BytesParser(policy=email.policy.HTTP).parsebytes(
        b"Content-Type: " + content_type.encode("latin-1") + b"\r\n\r\n" + body
    )
    if not message.is_multipart():
        raise UploadError("Malformed upload.")
    fields, files = {}, []
    for part in message.iter_parts():
        name = part.get_param("name", header="content-disposition")
        filename = part.get_filename()
        payload = part.get_payload(decode=True) or b""
        if filename:
            files.append((name, filename, payload))
        elif name:
            fields[name] = payload.decode("utf-8", "replace")
    return fields, files


class Run:
    def __init__(self, run_id: str, directory: Path, backend: str):
        self.id = run_id
        self.dir = directory
        self.backend = backend
        self.started = time.monotonic()
        self.events: list[dict] = []
        self.status = "running"
        self.lock = threading.Lock()

    def emit(self, stage: str, status: str, **data):
        with self.lock:
            self.events.append({
                "t": round(time.monotonic() - self.started, 1),
                "stage": stage, "status": status, "data": data,
            })

    def snapshot(self, since: int) -> dict:
        with self.lock:
            return {"status": self.status, "events": self.events[since:], "next": len(self.events)}


RUNS: dict[str, Run] = {}
ACTIVE = threading.Lock()  # one pipeline run at a time


class _RunLogHandler(logging.Handler):
    """Forward warnings (e.g. truncated model responses) into the run's event log."""

    def __init__(self, run: Run):
        super().__init__(level=logging.WARNING)
        self.run = run

    def emit(self, record):
        self.run.emit("log", "warning", message=record.getMessage())


def start_run(fields: dict, files: list) -> Run:
    backend = fields.get("backend", "claude-code")
    if backend not in BACKENDS:
        raise UploadError(f"Unknown backend {backend!r}.")
    if backend == "api" and not os.environ.get("ANTHROPIC_API_KEY"):
        raise UploadError("ANTHROPIC_API_KEY is not set in the terminal that started Vendor Guard.")

    questionnaire = [f for f in files if f[0] == "questionnaire"]
    docs = [f for f in files if f[0] == "docs"]
    if len(questionnaire) != 1:
        raise UploadError("Upload exactly one questionnaire.")
    for _, filename, _ in questionnaire + docs:
        if Path(filename).suffix.lower() not in ALLOWED_SUFFIXES:
            raise UploadError(f"{filename}: only PDF, DOCX, XLSX and TXT are supported.")

    if not ACTIVE.acquire(blocking=False):
        raise UploadError("A run is already in progress. Wait for it to finish.")

    try:
        run_id = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]
        run_dir = RUNS_DIR / run_id
        inputs = run_dir / "inputs"
        inputs.mkdir(parents=True)
        paths, used = [], set()
        for index, (_, filename, payload) in enumerate(questionnaire + docs):
            name = safe_filename(filename)
            if name in used:
                name = f"{index}_{name}"
            used.add(name)
            path = inputs / name
            path.write_bytes(payload)
            paths.append(path)
        run = Run(run_id, run_dir, backend)
        RUNS[run_id] = run
    except Exception:
        ACTIVE.release()
        raise

    thread = threading.Thread(target=_execute, args=(run, paths[0], paths[1:]), daemon=True)
    thread.start()
    return run


def _execute(run: Run, questionnaire: Path, docs: list[Path]):
    handler = _RunLogHandler(run)
    logging.getLogger().addHandler(handler)
    try:
        os.environ[ENV_VAR] = run.backend
        run.emit("run", "running", backend=run.backend)
        pipeline.run_pipeline(questionnaire, docs, run.dir / "outputs", progress=run.emit)
        run.status = "done"
        run.emit("run", "done")
    except Exception as exc:  # surfaced in the UI; the run stops, no partial report is offered
        run.status = "error"
        run.emit("run", "error", error=f"{type(exc).__name__}: {exc}")
    finally:
        logging.getLogger().removeHandler(handler)
        ACTIVE.release()


def sdk_installed() -> bool:
    try:
        import claude_agent_sdk  # noqa: F401
        return True
    except ImportError:
        return False


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "VendorGuard"

    # --- helpers -------------------------------------------------------------------
    def _host_ok(self) -> bool:
        port = self.server.server_address[1]
        return self.headers.get("Host", "") in {f"127.0.0.1:{port}", f"localhost:{port}"}

    def _token_ok(self, query: dict) -> bool:
        supplied = self.headers.get("X-VG-Token") or (query.get("token") or [""])[0]
        return secrets.compare_digest(supplied, TOKEN)

    def _send(self, status: int, body: bytes, content_type: str, extra: dict | None = None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, data: dict):
        self._send(status, json.dumps(data).encode(), "application/json")

    def log_message(self, fmt, *args):  # keep the terminal quiet; runs print their own progress
        pass

    # --- routes ------------------------------------------------------------------
    def do_GET(self):
        if not self._host_ok():
            return self._json(403, {"error": "Forbidden host."})
        url = urlparse(self.path)
        query = parse_qs(url.query)

        if url.path == "/":
            page = INDEX_HTML.read_text(encoding="utf-8").replace("__VG_TOKEN__", TOKEN)
            return self._send(200, page.encode(), "text/html; charset=utf-8", {
                "Content-Security-Policy": "default-src 'self'; style-src 'self' 'unsafe-inline'; "
                                           "script-src 'self' 'unsafe-inline'; img-src 'self' data:; "
                                           "frame-ancestors 'none'",
            })

        if url.path == "/saaf-logo.png":
            return self._send(200, LOGO_PNG.read_bytes(), "image/png")

        if not self._token_ok(query):
            return self._json(403, {"error": "Missing or invalid token."})

        if url.path == "/api/config":
            return self._json(200, {
                "backends": list(BACKENDS),
                "api_key_set": bool(os.environ.get("ANTHROPIC_API_KEY")),
                "sdk_installed": sdk_installed(),
                "allowed": sorted(ALLOWED_SUFFIXES),
                "max_upload_mb": MAX_UPLOAD_BYTES // (1024 * 1024),
            })

        if url.path == "/api/samples":
            read = lambda name: {"name": name, "text": (REPO / name).read_text(encoding="utf-8")}
            return self._json(200, {
                "questionnaire": read(SAMPLE_QUESTIONNAIRE),
                "docs": [read(name) for name in SAMPLE_DOCS],
            })

        match = re.fullmatch(r"/api/runs/([\w-]+)", url.path)
        if match:
            run = RUNS.get(match.group(1))
            if not run:
                return self._json(404, {"error": "Unknown run."})
            since = int((query.get("since") or ["0"])[0] or 0)
            return self._json(200, run.snapshot(max(since, 0)))

        match = re.fullmatch(r"/api/runs/([\w-]+)/files/([\w.]+)", url.path)
        if match:
            run = RUNS.get(match.group(1))
            name = match.group(2)
            if not run or run.status != "done" or name not in pipeline.OUTPUT_FILES:
                return self._json(404, {"error": "Not available."})
            path = run.dir / "outputs" / name
            return self._send(200, path.read_bytes(), "application/octet-stream",
                              {"Content-Disposition": f'attachment; filename="{name}"'})

        return self._json(404, {"error": "Not found."})

    def do_POST(self):
        if not self._host_ok():
            return self._json(403, {"error": "Forbidden host."})
        url = urlparse(self.path)
        if not self._token_ok(parse_qs(url.query)):
            return self._json(403, {"error": "Missing or invalid token."})
        if url.path != "/api/runs":
            return self._json(404, {"error": "Not found."})

        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > MAX_UPLOAD_BYTES:
            return self._json(413, {"error": f"Upload must be between 1 byte and {MAX_UPLOAD_BYTES // (1024 * 1024)} MB."})
        body = self.rfile.read(length)
        try:
            fields, files = parse_multipart(self.headers.get("Content-Type", ""), body)
            run = start_run(fields, files)
        except UploadError as exc:
            return self._json(400, {"error": str(exc)})
        return self._json(202, {"id": run.id})


def main():
    parser = argparse.ArgumentParser(description="Vendor Guard local web UI")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    try:
        server = http.server.ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    except OSError as exc:
        if exc.errno == errno.EADDRINUSE:
            print(f"Port {args.port} is already in use. Is Vendor Guard already running? "
                  f"Open http://127.0.0.1:{args.port}/ or start on another port: launch web --port {args.port + 1}",
                  file=sys.stderr)
            sys.exit(1)
        raise
    url = f"http://127.0.0.1:{args.port}/"
    print(f"Vendor Guard web UI running at {url}", flush=True)
    print("Only reachable from this computer. Press Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
