"""pbc_intake agent — scans a watched folder for documents an auditee/auditor
has delivered for a PBC (Prepared-By-Client) request list.

New in this codebase (not ported from PBC-Assistant-Isabelle, which took
files through a web upload form instead — see app.py/static/ in the source,
which this repo does not include). This is the intake mechanism for
``pbc_validation``'s ``received_documents`` and ``pbc_document_analysis``'s
``file_path`` inputs when there is no such upload UI.

Folder convention — under ``intake/<engagement_id>/``:

    intake/<engagement_id>/<PBC-ID>/<file>       confirmed: the folder name
                                                  IS the PBC ID, no guessing
    intake/<engagement_id>/_unassigned/<file>    not yet filed under an ID

Filing a file under the matching ``<PBC-ID>/`` folder is the expected,
zero-ambiguity path — the auditee, the auditor, or whoever manages the
engagement's shared folder does this directly. ``_unassigned/`` is a
fallback for files nobody has filed yet: this agent can suggest a likely PBC
match for those (see ``pbc_intake`` prompts), but never assigns one itself —
an auditor must move (or otherwise confirm) a suggested file into its
``<PBC-ID>/`` folder before it is treated as received evidence.

``intake/`` is gitignored, the same as ``runs/`` — it holds real engagement
files.
"""

from __future__ import annotations

import json
from pathlib import Path

from agents.claude_init import ClaudeClient, extract_json_block, text_from_message
from agents.prompts.pbc_intake import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from agents.settings.pbc_intake import SETTINGS

INTAKE_DIR = Path(__file__).resolve().parent.parent / "intake"
_UNASSIGNED = "_unassigned"


def run(inputs: dict, client: ClaudeClient | None = None) -> dict:
    """Scan the intake folder for one engagement and return what was found.

    ``inputs`` keys:
        engagement_id (str), pbc_list (dict, optional — the output of
        ``pbc_creation.run``; if given and there are files under
        ``_unassigned/``, Claude suggests a likely PBC-ID match for each so
        an auditor can confirm it).

    Returns:
        received_documents: list[{filename, pbc_id, file_path}] — confirmed
            matches, ready to pass into ``pbc_validation`` /
            ``pbc_document_analysis``.
        unassigned_files: list[{filename, file_path}] — not yet filed under
            a PBC ID.
        suggestions: list[{filename, suggested_pbc_id, confidence,
            rationale}] — only populated when ``pbc_list`` was given and
            there were unassigned files; unconfirmed.
    """
    scanned = _scan_intake_folder(inputs["engagement_id"])

    result = {
        "received_documents": scanned["received_documents"],
        "unassigned_files": scanned["unassigned_files"],
        "suggestions": [],
    }

    pbc_list = inputs.get("pbc_list")
    if scanned["unassigned_files"] and pbc_list:
        pbc_items_json = json.dumps(
            [{"id": i["id"], "description": i["description"]} for i in pbc_list["items"]],
            indent=2,
        )
        filenames_json = json.dumps(
            [f["filename"] for f in scanned["unassigned_files"]], indent=2
        )

        user_prompt = USER_PROMPT_TEMPLATE.format(
            pbc_items_json=pbc_items_json, filenames_json=filenames_json
        )

        client = client or ClaudeClient()
        message = client.message(
            user_prompt,
            system=SYSTEM_PROMPT,
            model=SETTINGS["model"],
            max_tokens=SETTINGS["max_tokens"],
            thinking=SETTINGS["thinking"],
            agent="pbc_intake",
        )
        result["suggestions"] = extract_json_block(text_from_message(message))

    return result


def _scan_intake_folder(engagement_id: str) -> dict:
    """Deterministic folder scan — no Claude call, no guessing."""
    engagement_dir = INTAKE_DIR / engagement_id
    received_documents: list[dict] = []
    unassigned_files: list[dict] = []

    if not engagement_dir.is_dir():
        return {"received_documents": [], "unassigned_files": []}

    for child in sorted(engagement_dir.iterdir()):
        if not child.is_dir():
            continue  # a file dropped directly under the engagement folder is unfiled; ignore rather than guess
        if child.name == _UNASSIGNED:
            unassigned_files.extend(
                {"filename": f.name, "file_path": str(f)}
                for f in sorted(child.iterdir())
                if f.is_file()
            )
            continue
        pbc_id = child.name
        received_documents.extend(
            {"filename": f.name, "pbc_id": pbc_id, "file_path": str(f)}
            for f in sorted(child.iterdir())
            if f.is_file()
        )

    return {"received_documents": received_documents, "unassigned_files": unassigned_files}
