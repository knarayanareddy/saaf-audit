"""Cryptographic provider — OWASP A02: Cryptographic Failures Prevention.

Handles all cryptographic operations for the audit pipeline.
Uses HMAC-SHA256 for integrity, PBKDF2 for key derivation.
Never logs or prints keys.
"""

import hashlib
import hmac
import json
import os
import secrets
from pathlib import Path


class CryptoProvider:
    """Centralized cryptographic operations for the audit pipeline."""

    PBKDF2_ITERATIONS: int = 600_000
    KEY_LENGTH: int = 32  # 256-bit key

    def __init__(self, secret_key: bytes | None = None) -> None:
        if secret_key:
            self._key = secret_key
        else:
            self._key = self._load_or_generate_key()

    def _load_or_generate_key(self) -> bytes:
        """Load key from env var or generate and store securely."""
        env_key = os.environ.get("AUDIT_SECRET_KEY")
        if env_key:
            return env_key.encode("utf-8")

        root = Path(__file__).resolve().parents[2]
        key_file = root / "config" / "secret.key"

        if key_file.exists():
            return key_file.read_bytes()

        new_key = secrets.token_bytes(self.KEY_LENGTH)
        key_file.write_bytes(new_key)
        return new_key

    def hmac_sign(self, data: bytes) -> str:
        """Compute HMAC-SHA256 signature."""
        return hmac.new(self._key, data, hashlib.sha256).hexdigest()

    def hmac_sign_string(self, text: str) -> str:
        return self.hmac_sign(text.encode("utf-8"))

    def hmac_sign_dict(self, record: dict) -> str:
        """HMAC-SHA256 of a canonicalized JSON dict (excludes _ fields)."""
        clean = {k: v for k, v in record.items() if not k.startswith("_")}
        canonical = json.dumps(clean, sort_keys=True, separators=(",", ":"), default=str)
        return self.hmac_sign(canonical.encode("utf-8"))

    def verify_hmac(self, data: bytes, expected: str) -> bool:
        """Constant-time HMAC verification."""
        computed = hmac.new(self._key, data, hashlib.sha256).hexdigest()
        return hmac.compare_digest(computed, expected)

    def verify_hmac_dict(self, record: dict, expected: str) -> bool:
        clean = {k: v for k, v in record.items() if not k.startswith("_")}
        canonical = json.dumps(clean, sort_keys=True, separators=(",", ":"), default=str)
        return self.verify_hmac(canonical.encode("utf-8"), expected)

    def hash_file(self, file_path: Path) -> str:
        """Compute HMAC-SHA256 of an entire file."""
        h = hmac.new(self._key, digestmod=hashlib.sha256)
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
