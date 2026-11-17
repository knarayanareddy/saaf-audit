"""Where this deployment keeps the things it must not lose.

On a laptop the database and the uploaded audit documents sit next to the code,
and that is fine. On a host it is not: the filesystem of a web service is rebuilt
on every deploy, so anything written next to the code is gone the next time the
service restarts — including every document an auditor uploaded.

So both move to a mounted volume, and the host says where that volume is.
`IA_WINGMAN_DATA_DIR` is the one handle for it: unset, nothing about local
development changes; set, the database and the uploads travel there together.
One variable rather than two, because a deployment with the database on the
volume and the uploads next to the code would lose half its evidence silently.

`IA_WINGMAN_STATIC_DIR` is the same idea for the built frontend. Unset means
there is nothing to serve and the backend only answers the API, which is exactly
what you want while Vite serves the frontend itself.
"""
from __future__ import annotations

import os
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent


def _dir_from_env(name: str) -> Path | None:
    raw = (os.environ.get(name) or "").strip()
    return Path(raw).resolve() if raw else None


#: The directory holding the database and the uploads. Defaults to the backend
#: itself, which is where a local run has always kept them.
DATA_DIR: Path = _dir_from_env("IA_WINGMAN_DATA_DIR") or _BACKEND

#: The SQLite file. Absolute, so it no longer depends on the working directory
#: the process happens to be started from — a host picks that, not you.
DB_PATH: Path = DATA_DIR / "ia_wingman.db"

#: Uploaded audit documents, one directory per engagement.
UPLOAD_ROOT: Path = DATA_DIR / "uploads"

#: The built frontend, when this process is the one serving it. None means the
#: backend answers the API only.
STATIC_DIR: Path | None = _dir_from_env("IA_WINGMAN_STATIC_DIR")


def ensure() -> None:
    """Create what the process is about to write to.

    Called once at startup rather than at import, so that merely importing this
    module — as the tests do — does not create directories as a side effect.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
