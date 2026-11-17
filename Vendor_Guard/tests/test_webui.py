"""
AC-12: the local web UI (see AUDIT-CRITERIA.md).

A real server is started on 127.0.0.1 with a fake pipeline; no model is called.
"""
import http.client
import json
import threading
import time
import uuid
from pathlib import Path

import pytest

import main
from webui import server as web

PDF = b"%PDF-1.4 fake"


# --- helpers -----------------------------------------------------------------------

def multipart(fields=None, files=None):
    boundary = uuid.uuid4().hex
    parts = []
    for name, value in (fields or {}).items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    for name, filename, payload in files or []:
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
            f"Content-Type: application/octet-stream\r\n\r\n".encode() + payload + b"\r\n"
        )
    parts.append(f"--{boundary}--\r\n".encode())
    return f"multipart/form-data; boundary={boundary}", b"".join(parts)


class Client:
    def __init__(self, port):
        self.port = port

    def request(self, method, path, body=None, headers=None, token=True, host=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        h = {"Host": host or f"127.0.0.1:{self.port}"}
        if token:
            h["X-VG-Token"] = web.TOKEN
        h.update(headers or {})
        conn.request(method, path, body=body, headers=h)
        res = conn.getresponse()
        data = res.read()
        conn.close()
        return res, data

    def json(self, method, path, **kw):
        res, data = self.request(method, path, **kw)
        return res.status, json.loads(data)

    def start(self, fields=None, files=None):
        content_type, body = multipart(fields, files)
        return self.json("POST", "/api/runs", body=body, headers={"Content-Type": content_type})

    def wait(self, run_id, timeout=5):
        deadline = time.time() + timeout
        while time.time() < deadline:
            status, data = self.json("GET", f"/api/runs/{run_id}?since=0")
            if data["status"] != "running":
                return data
            time.sleep(0.05)
        raise AssertionError("run did not finish")


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(web, "RUNS_DIR", tmp_path / "runs")
    monkeypatch.setattr(web, "RUNS", {})
    httpd = web.http.server.ThreadingHTTPServer(("127.0.0.1", 0), web.Handler)
    thread = threading.Thread(target=httpd.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    yield Client(httpd.server_address[1])
    httpd.shutdown()
    httpd.server_close()


@pytest.fixture
def fake_pipeline(monkeypatch):
    """Replace run_pipeline with one that emits the real stage sequence and writes outputs."""
    calls = []

    def fake(questionnaire, docs, output_dir, progress):
        calls.append({"questionnaire": questionnaire, "docs": docs})
        output_dir.mkdir(parents=True)
        progress("documents", "running", count=1 + len(docs))
        progress("documents", "done", count=1 + len(docs))
        progress("profile", "done", vendor="Acme", sector="Finance")
        progress("security", "done", findings=3, gaps=1)
        progress("scorecard", "done", scorecard={"ISO 27001": {"rag": "Red"}}, findings=3, review_flags=0)
        for name in main.OUTPUT_FILES:
            (output_dir / name).write_bytes(b"content of " + name.encode())
        progress("outputs", "done")

    monkeypatch.setattr(web.pipeline, "run_pipeline", fake)
    return calls


# --- access control ----------------------------------------------------------------

def test_ac12_page_is_served_with_token_and_csp(client):
    res, body = client.request("GET", "/", token=False)
    assert res.status == 200
    assert web.TOKEN.encode() in body
    assert "frame-ancestors 'none'" in res.getheader("Content-Security-Policy")


@pytest.mark.parametrize("path", ["/api/config", "/api/samples", "/api/runs/x"])
def test_ac12_api_requires_token(client, path):
    status, data = client.json("GET", path, token=False)
    assert status == 403


def test_ac12_wrong_token_is_rejected(client):
    status, _ = client.json("GET", "/api/config", token=False, headers={"X-VG-Token": "guess"})
    assert status == 403


@pytest.mark.parametrize("host", ["evil.example", "evil.example:8765", "192.168.1.5:8765"])
def test_ac12_foreign_host_header_is_rejected(client, host):
    """Blocks DNS-rebinding: a page on another domain resolving to 127.0.0.1."""
    res, _ = client.request("GET", "/", host=host)
    assert res.status == 403


def test_ac12_post_without_token_cannot_start_a_run(client, fake_pipeline):
    content_type, body = multipart({"backend": "claude-code"}, [("questionnaire", "q.txt", b"x")])
    res, _ = client.request("POST", "/api/runs", body=body, token=False, headers={"Content-Type": content_type})
    assert res.status == 403
    assert fake_pipeline == []


def test_ac12_server_binds_loopback_only():
    import inspect
    assert '("127.0.0.1", args.port)' in inspect.getsource(web.main)


# --- uploads -----------------------------------------------------------------------

@pytest.mark.parametrize("name,expected", [
    ("../../etc/passwd", "passwd"),
    ("..\\..\\windows\\evil.txt", "evil.txt"),
    ("report<script>.pdf", "report_script_.pdf"),
    ("...", "document"),
    ("normal name.docx", "normal name.docx"),
])
def test_ac12_uploaded_filenames_are_sanitised(name, expected):
    assert web.safe_filename(name) == expected


def test_ac12_run_completes_and_events_stream(client, fake_pipeline):
    status, data = client.start({"backend": "claude-code"}, [
        ("questionnaire", "q.txt", b"questions"),
        ("docs", "soc2.pdf", PDF),
        ("docs", "../../evil.txt", b"x"),
    ])
    assert status == 202
    result = client.wait(data["id"])
    assert result["status"] == "done"
    stages = [(e["stage"], e["status"]) for e in result["events"]]
    assert stages[0] == ("run", "running")
    assert ("security", "done") in stages and stages[-1] == ("run", "done")
    saved = [Path(p).name for p in [fake_pipeline[0]["questionnaire"], *fake_pipeline[0]["docs"]]]
    assert saved == ["q.txt", "soc2.pdf", "evil.txt"]
    assert all(web.RUNS_DIR in Path(p).parents for p in [fake_pipeline[0]["questionnaire"], *fake_pipeline[0]["docs"]])


def test_ac12_incremental_polling(client, fake_pipeline):
    _, data = client.start({"backend": "claude-code"}, [("questionnaire", "q.txt", b"x")])
    full = client.wait(data["id"])
    status, tail = client.json("GET", f"/api/runs/{data['id']}?since={full['next'] - 1}")
    assert tail["events"] == full["events"][-1:]


@pytest.mark.parametrize("files,match", [
    ([], "exactly one questionnaire"),
    ([("questionnaire", "a.txt", b"x"), ("questionnaire", "b.txt", b"x")], "exactly one questionnaire"),
    ([("questionnaire", "q.exe", b"MZ")], "only PDF, DOCX, XLSX and TXT"),
    ([("questionnaire", "q.txt", b"x"), ("docs", "old.xls", b"x")], "only PDF, DOCX, XLSX and TXT"),
])
def test_ac12_invalid_uploads_are_rejected(client, fake_pipeline, files, match):
    status, data = client.start({"backend": "claude-code"}, files)
    assert status == 400 and match in data["error"]
    assert fake_pipeline == []


def test_ac12_unknown_backend_rejected(client, fake_pipeline):
    status, data = client.start({"backend": "openai"}, [("questionnaire", "q.txt", b"x")])
    assert status == 400 and "Unknown backend" in data["error"]


def test_ac12_api_backend_without_key_rejected(client, fake_pipeline):
    status, data = client.start({"backend": "api"}, [("questionnaire", "q.txt", b"x")])
    assert status == 400 and "ANTHROPIC_API_KEY" in data["error"]


def test_ac12_oversized_upload_rejected(client, monkeypatch):
    monkeypatch.setattr(web, "MAX_UPLOAD_BYTES", 100)
    content_type, body = multipart({"backend": "claude-code"}, [("questionnaire", "q.txt", b"x" * 500)])
    res, _ = client.request("POST", "/api/runs", body=body, headers={"Content-Type": content_type})
    assert res.status == 413


def test_ac12_only_one_run_at_a_time(client, monkeypatch):
    release = threading.Event()

    def slow(questionnaire, docs, output_dir, progress):
        release.wait(5)

    monkeypatch.setattr(web.pipeline, "run_pipeline", slow)
    status1, first = client.start({"backend": "claude-code"}, [("questionnaire", "q.txt", b"x")])
    status2, second = client.start({"backend": "claude-code"}, [("questionnaire", "q.txt", b"x")])
    release.set()
    client.wait(first["id"])
    assert status1 == 202
    assert status2 == 400 and "already in progress" in second["error"]


# --- results & failures ------------------------------------------------------------

def test_ac12_outputs_downloadable_after_success(client, fake_pipeline):
    _, data = client.start({"backend": "claude-code"}, [("questionnaire", "q.txt", b"x")])
    client.wait(data["id"])
    res, body = client.request("GET", f"/api/runs/{data['id']}/files/gap_register.xlsx")
    assert res.status == 200 and body == b"content of gap_register.xlsx"
    assert "attachment" in res.getheader("Content-Disposition")


@pytest.mark.parametrize("name", ["inputs", "..%2F..%2Fmain.py", "q.txt", "audit_memo.docx.bak"])
def test_ac12_only_whitelisted_outputs_are_served(client, fake_pipeline, name):
    _, data = client.start({"backend": "claude-code"}, [("questionnaire", "q.txt", b"x")])
    client.wait(data["id"])
    res, _ = client.request("GET", f"/api/runs/{data['id']}/files/{name}")
    assert res.status == 404


def test_ac12_failed_run_reports_error_and_offers_no_files(client, monkeypatch):
    def broken(questionnaire, docs, output_dir, progress):
        progress("profile", "running")
        output_dir.mkdir(parents=True)
        (output_dir / "scorecard.csv").write_text("partial")
        raise RuntimeError("Claude Code is not logged in")

    monkeypatch.setattr(web.pipeline, "run_pipeline", broken)
    _, data = client.start({"backend": "claude-code"}, [("questionnaire", "q.txt", b"x")])
    result = client.wait(data["id"])
    assert result["status"] == "error"
    assert "not logged in" in result["events"][-1]["data"]["error"]
    res, _ = client.request("GET", f"/api/runs/{data['id']}/files/scorecard.csv")
    assert res.status == 404


def test_ac12_warnings_reach_the_ui(client, monkeypatch):
    import logging

    def warns(questionnaire, docs, output_dir, progress):
        logging.getLogger("agents.base").warning("Model response was truncated; salvaged 3 record(s).")

    monkeypatch.setattr(web.pipeline, "run_pipeline", warns)
    _, data = client.start({"backend": "claude-code"}, [("questionnaire", "q.txt", b"x")])
    result = client.wait(data["id"])
    assert any(e["stage"] == "log" and "truncated" in e["data"]["message"] for e in result["events"])


def test_ac12_samples_endpoint_serves_bundled_files_only(client):
    status, data = client.json("GET", "/api/samples")
    assert status == 200
    assert data["questionnaire"]["name"] == "sample_vendor_q.txt"
    assert [d["name"] for d in data["docs"]] == list(web.SAMPLE_DOCS)


# --- real pipeline emits the stages the UI draws ----------------------------------

def test_ac12_run_pipeline_reports_every_stage(tmp_path, mocker):
    from models.finding import Finding, VendorProfile
    q = tmp_path / "q.txt"
    q.write_text("questionnaire")
    profile = VendorProfile(name="Acme", sector="Finance", services=[], processes_personal_data=False,
                            is_ai_system=False, is_dutch_government_vendor=False, applicable_frameworks=[])
    f = Finding(framework="ISO 27001", control_id="1", control_name="n", status="Gap",
                severity="High", evidence="e", recommendation="r")
    mocker.patch("main.build_vendor_profile", return_value=profile)
    mocker.patch.dict(main.AGENT_MAP, {"security": lambda d: [f], "resilience": lambda d: []})
    mocker.patch("main.run_document_validity_agent", return_value=[])
    client = mocker.MagicMock()
    client.messages.create.return_value.content = [mocker.MagicMock(text="memo")]
    mocker.patch("anthropic.Anthropic", return_value=client)

    events = []
    main.run_pipeline(q, [], tmp_path / "out", progress=lambda s, st, **d: events.append((s, st)))
    for stage in ["documents", "profile", "security", "resilience", "document_validity",
                  "scorecard", "memo", "outputs"]:
        assert (stage, "done") in events, stage
    assert ("routing", "done") in events
    assert events.index(("profile", "done")) < events.index(("security", "running"))
    assert events.index(("memo", "done")) < events.index(("outputs", "done"))


def test_ac12_logo_is_served_locally(client):
    """Branding is served from the repo; the page makes no external requests."""
    res, body = client.request("GET", "/saaf-logo.png", token=False)
    assert res.status == 200 and res.getheader("Content-Type") == "image/png"
    assert body.startswith(b"\x89PNG")
    page = (web.INDEX_HTML).read_text(encoding="utf-8")
    assert "http://" not in page.replace("http://127.0.0.1", "") and "https://" not in page
