import asyncio
import re
import socket
import ipaddress
import zipfile
from pathlib import Path
from urllib.parse import urlparse

import httpx
from pypdf import PdfReader
from docx import Document

# Extra blocked ranges on top of Python's built-in is_private/is_loopback/etc.
PRIVATE_IP_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("0.0.0.0/8"),        # "this host" / unspecified block
    ipaddress.ip_network("100.64.0.0/10"),    # CGNAT
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),         # unique local
    ipaddress.ip_network("fe80::/10"),        # IPv6 link-local
    ipaddress.ip_network("::ffff:0:0/96"),    # IPv4-mapped IPv6
]

# Parser limits — untrusted PDFs/DOCX must not be able to burn unbounded CPU/RAM.
_MAX_PDF_PAGES = 300
_MAX_DOCX_ENTRIES = 2000
_MAX_DOCX_UNCOMPRESSED = 200 * 1024 * 1024  # 200 MB total inflated size
_MAX_DOCX_RATIO = 200                        # inflate ratio above this = likely zip bomb


def extract_pdf_text(file_path: str) -> str:
    reader = PdfReader(file_path)
    parts = []
    for i, page in enumerate(reader.pages):
        if i >= _MAX_PDF_PAGES:
            break
        parts.append(page.extract_text() or "")
    return "\n".join(parts).strip()


def _guard_docx_zip(file_path: str) -> None:
    """Reject decompression-bomb .docx archives before python-docx inflates them."""
    with zipfile.ZipFile(file_path) as z:
        infos = z.infolist()
        if len(infos) > _MAX_DOCX_ENTRIES:
            raise ValueError("DOCX has too many internal entries")
        total_unc = sum(i.file_size for i in infos)
        total_comp = sum(i.compress_size for i in infos) or 1
        if total_unc > _MAX_DOCX_UNCOMPRESSED:
            raise ValueError("DOCX uncompressed size exceeds limit")
        if total_unc > 10 * 1024 * 1024 and (total_unc / total_comp) > _MAX_DOCX_RATIO:
            raise ValueError("DOCX compression ratio too high (possible zip bomb)")


def extract_docx_text(file_path: str) -> str:
    _guard_docx_zip(file_path)
    doc = Document(file_path)
    return "\n".join(p.text for p in doc.paragraphs).strip()


# Plain-text family — read directly, capped so an untrusted upload can't exhaust RAM.
_MAX_TEXT_BYTES = 5 * 1024 * 1024  # 5 MB of raw text is plenty for audit docs
_TEXT_SUFFIXES = (".txt", ".md", ".markdown", ".csv", ".tsv", ".text", ".log")


def extract_plaintext(file_path: str) -> str:
    with open(file_path, "rb") as f:
        raw = f.read(_MAX_TEXT_BYTES)
    return raw.decode("utf-8", errors="replace").strip()


def extract_text(file_path: str, mime_type: str) -> str:
    suffix = Path(file_path).suffix.lower()
    if suffix == ".pdf":
        return extract_pdf_text(file_path)
    if suffix in (".docx", ".doc"):
        return extract_docx_text(file_path)
    if suffix in _TEXT_SUFFIXES:
        return extract_plaintext(file_path)
    raise ValueError(f"Unsupported file type: {suffix}")


def _is_private(ip_str: str) -> bool:
    ip = ipaddress.ip_address(ip_str)
    mapped = getattr(ip, "ipv4_mapped", None)
    if mapped is not None:
        ip = mapped  # judge IPv4-mapped IPv6 by its embedded IPv4
    if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast
            or ip.is_reserved or ip.is_unspecified):
        return True
    return any(ip in net for net in PRIVATE_IP_RANGES)


async def _validate_url(url: str) -> None:
    """Resolve hostname (all A/AAAA records) and block private/internal addresses.

    Uses getaddrinfo so IPv6-only and multi-homed hosts are checked too, not just
    the first IPv4. Note: this validates at resolve time; a hostname that re-resolves
    to a different address at connect time (DNS rebinding) is a known residual risk
    we accept here rather than pinning the socket to the vetted IP.
    """
    parsed = urlparse(url)
    if parsed.scheme.lower() not in ("http", "https"):
        raise ValueError("Only http:// and https:// URLs are accepted")
    hostname = parsed.hostname  # handles [ipv6] brackets and :port correctly
    if not hostname:
        raise ValueError("URL has no host")
    loop = asyncio.get_event_loop()
    try:
        infos = await loop.run_in_executor(None, socket.getaddrinfo, hostname, None)
    except socket.gaierror:
        raise ValueError(f"Could not resolve hostname: {hostname}")
    addrs = {info[4][0] for info in infos}
    if not addrs:
        raise ValueError(f"Could not resolve hostname: {hostname}")
    for addr in addrs:
        if _is_private(addr):
            raise ValueError(f"URL resolves to a blocked internal address ({addr}) — not allowed")


async def fetch_url_text(url: str) -> str:
    """Fetch a URL and return its text content. Blocks SSRF (private IPs, non-http schemes, redirects to private IPs)."""
    await _validate_url(url)

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as http:
        current_url = url
        for _ in range(3):
            response = await http.get(current_url, headers={"User-Agent": "IAWingman/1.0"})
            if response.status_code in (301, 302, 303, 307, 308):
                location = response.headers.get("location", "").strip()
                if not location:
                    raise ValueError("Redirect with empty Location header")
                await _validate_url(location)
                current_url = location
            else:
                response.raise_for_status()
                text = re.sub(r"<script.*?</script>", " ", response.text, flags=re.DOTALL | re.IGNORECASE)
                text = re.sub(r"<style.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
                text = re.sub(r"<[^>]+>", " ", text)
                text = re.sub(r"\s+", " ", text)
                return text[:50_000]
        raise ValueError("Too many redirects")
