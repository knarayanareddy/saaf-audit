import ipaddress
import socket
import subprocess
import tempfile
import urllib.request
from urllib.parse import urlsplit

import requests
from flask import Flask, request

app = Flask(__name__)
UPDATE_URL = "https://example.invalid/defs.json"
ALLOWED_HOSTS = {"github.com"}


def _validate(url):
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in ALLOWED_HOSTS:
        raise ValueError("host not allowed")
    ip = ipaddress.ip_address(socket.gethostbyname(parts.hostname))
    if ip.is_private or ip.is_loopback or ip.is_link_local:
        raise ValueError("address not allowed")
    return url


@app.route("/fetch-repo", methods=["POST"])
def fetch_repo():
    data = request.get_json(silent=True) or {}
    url = _validate((data.get("url") or "").strip())
    tmp_dir = tempfile.mkdtemp()
    res = subprocess.run(["git", "clone", "--depth", "1", "--", url, tmp_dir], capture_output=True, text=True)
    return {"ok": res.returncode == 0}


@app.route("/proxy")
def proxy():
    item = request.args.get("item_id", "")
    return requests.get(f"https://api.example.invalid/items/{item}", timeout=10).text


@app.route("/owasp-update", methods=["POST"])
def owasp_update():
    # the caller cannot choose the URL: only the configured one is fetched
    with urllib.request.urlopen(UPDATE_URL, timeout=15) as resp:
        return {"size": len(resp.read())}
