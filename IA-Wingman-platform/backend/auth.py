import asyncio
import logging
import secrets
import time

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from config import settings

logger = logging.getLogger("ia.wingman")

# auto_error=False so we can distinguish "no credentials sent" from "wrong
# credentials" and handle the fail-closed / dev-open cases ourselves.
_security = HTTPBasic(auto_error=False)

# ── Delay-based throttling ──────────────────────────────────────────────────
# We slow brute-force guessing with a growing per-IP delay rather than a hard
# lockout. A hard lockout would be a self-DoS here: behind the Vite dev proxy
# every browser request arrives as 127.0.0.1, so one bad actor (or one fat-
# fingered retry) could lock out the real user mid-demo. A correct credential
# always passes immediately (below), so a legitimate user is never blocked;
# only repeated *failures* from an IP accrue delay, and it decays on its own.
_FAIL_WINDOW = 60.0   # seconds; a burst of failures decays after this idle gap
_DELAY_STEP = 0.5     # seconds added per recent failure
_MAX_DELAY = 3.0      # cap so a single mistyped password isn't punished for long
_PRUNE_AT = 1024      # bound the in-memory table

# ip -> {"count": int, "last": monotonic_ts}
_attempts: dict[str, dict] = {}

# Deliberately NO WWW-Authenticate header on 401s. The app signs in through its
# own screen and sends the Basic header itself (frontend/src/api/client.js); a
# challenge header would make the browser pop its native credentials dialog on
# top of that screen, asking for the same password twice.


if not settings.APP_PASSWORD and not settings.IA_WINGMAN_DEV_OPEN:
    logger.critical(
        "APP_PASSWORD is empty and IA_WINGMAN_DEV_OPEN is not set — the API is "
        "FAIL-CLOSED and will reject every request with 503. Set APP_PASSWORD in "
        "backend/.env, or IA_WINGMAN_DEV_OPEN=1 for an explicitly open local dev run."
    )
elif not settings.APP_PASSWORD and settings.IA_WINGMAN_DEV_OPEN:
    logger.warning(
        "IA_WINGMAN_DEV_OPEN=1 with empty APP_PASSWORD — authentication is DISABLED. "
        "Never run this outside local development."
    )


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _register_failure(ip: str) -> float:
    """Record a failed attempt and return how long to tarpit before replying."""
    now = time.monotonic()
    st = _attempts.get(ip)
    count = st["count"] + 1 if st and now - st["last"] <= _FAIL_WINDOW else 1
    _attempts[ip] = {"count": count, "last": now}

    if len(_attempts) > _PRUNE_AT:
        cutoff = now - _FAIL_WINDOW
        for stale in [k for k, v in _attempts.items() if v["last"] < cutoff]:
            _attempts.pop(stale, None)

    logger.warning("Failed auth attempt from %s (%d within %.0fs)", ip, count, _FAIL_WINDOW)
    # First failure = no delay (honest typo); each further recent failure adds a
    # step, capped at _MAX_DELAY.
    return min(_MAX_DELAY, _DELAY_STEP * (count - 1))


async def require_auth(
    request: Request,
    credentials: HTTPBasicCredentials | None = Depends(_security),
) -> None:
    if not settings.APP_PASSWORD:
        if settings.IA_WINGMAN_DEV_OPEN:
            return
        # Fail closed: no password configured and no explicit dev-open opt-in.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Server authentication is not configured.",
        )

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing credentials",
        )

    user_ok = secrets.compare_digest(
        credentials.username.encode("utf-8"), settings.APP_USERNAME.encode("utf-8")
    )
    pass_ok = secrets.compare_digest(
        credentials.password.encode("utf-8"), settings.APP_PASSWORD.encode("utf-8")
    )
    if user_ok and pass_ok:
        _attempts.pop(_client_ip(request), None)  # success clears the IP's slate
        return

    delay = _register_failure(_client_ip(request))
    if delay:
        await asyncio.sleep(delay)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
    )
