import subprocess
import tempfile
import urllib.request

import requests
from flask import Flask, request

app = Flask(__name__)
UPDATE_URL = "https://example.invalid/defs.json"


@app.route("/fetch-repo", methods=["POST"])
def fetch_repo():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    tmp_dir = tempfile.mkdtemp()
    res = subprocess.run(["git", "clone", "--depth", "1", url, tmp_dir], capture_output=True, text=True)
    return {"ok": res.returncode == 0}


@app.route("/proxy")
def proxy():
    target = request.args.get("target_url")
    return requests.get(target, timeout=10).text


def refresh(url=UPDATE_URL):
    with urllib.request.urlopen(url, timeout=15) as resp:
        return resp.read()


@app.route("/owasp-update", methods=["POST"])
def owasp_update():
    data = request.get_json(silent=True) or {}
    url = data.get("url") or UPDATE_URL
    return {"size": len(refresh(url))}
