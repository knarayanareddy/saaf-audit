"""Runner for the UC7 voice walkthrough.

Two modes:

    # Live voice — talk to the ElevenLabs agent (needs a mic, ELEVENLABS_API_KEY,
    # ELEVENLABS_AGENT_ID, and — for UC7 refine — ANTHROPIC_API_KEY):
    python -m tools.scripts.uc7_voice_walkthrough.walkthrough --live

    # Offline — replay a scripted synthetic walkthrough through the same tools
    # (no mic, no ElevenLabs, no API key):
    python -m tools.scripts.uc7_voice_walkthrough.walkthrough --simulate

Design: plans/hackathon-4/p-papen-uc7-voice-rcm-walkthrough.md
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

if __package__:
    from . import agent_config
    from .rcm_tools import RcmSession
else:  # pragma: no cover - direct-script convenience
    sys.path.insert(0, str(Path(__file__).parent))
    import agent_config  # type: ignore
    from rcm_tools import RcmSession  # type: ignore

logger = logging.getLogger("walkthrough")

DEFAULT_BUNDLE = Path(__file__).parent / "sample_data" / "walkthrough_accounts_payable.json"


def _run_id(process: str) -> str:
    slug = "".join(c if c.isalnum() else "-" for c in process.lower()).strip("-")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{slug or 'walkthrough'}-{stamp}"


def _anthropic_client() -> Optional[Any]:
    """Return an Anthropic client if a key is set, else None (skip UC7 refine)."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    try:
        from tools.scripts.audit_planning_orchestrator import sub_agents

        return sub_agents.make_client()  # honors ANTHROPIC_WORKSPACE_ID
    except ImportError:
        logger.warning("anthropic not installed; skipping UC7 refine.")
        return None


# --------------------------------------------------------------------------- #
# Offline simulate — replay a scripted walkthrough through the two client tools
# --------------------------------------------------------------------------- #

def run_simulate(bundle: Dict[str, Any]) -> str:
    """Drive capture_control + build_rcm from a scripted walkthrough (no API/mic)."""
    process_map = bundle["process_map"]
    run_id = _run_id(process_map.get("process", "walkthrough"))
    # Offline: no Anthropic client, so build_rcm assembles + validates locally.
    session = RcmSession(process_map, run_id=run_id, anthropic_client=None, refine=False)

    for turn in bundle.get("walkthrough", []):
        speaker = turn.get("speaker", "owner")
        if turn.get("utterance"):
            session.log_turn(speaker, turn["utterance"])
            print(f"[{speaker}] {turn['utterance']}")
        if "capture" in turn:
            confirmation = session.capture_control(turn["capture"])
            print(f"[agent] {confirmation}")

    summary = session.build_rcm({})
    print(f"[agent] {summary}")
    logger.info("RCM and transcript written under runs/%s/", run_id)
    return run_id


# --------------------------------------------------------------------------- #
# Live voice — ElevenLabs Conversational AI with client tools
# --------------------------------------------------------------------------- #

def run_live(bundle: Dict[str, Any]) -> str:
    """Start a live ElevenLabs voice session bound to the two client tools."""
    from elevenlabs import ElevenLabs
    from elevenlabs.conversational_ai.conversation import ClientTools, Conversation
    from elevenlabs.conversational_ai.default_audio_interface import DefaultAudioInterface

    api_key = os.environ["ELEVENLABS_API_KEY"]
    agent_id = os.environ["ELEVENLABS_AGENT_ID"]

    process_map = bundle["process_map"]
    run_id = _run_id(process_map.get("process", "walkthrough"))
    session = RcmSession(process_map, run_id=run_id, anthropic_client=_anthropic_client())

    tools = ClientTools()
    tools.register("capture_control", session.capture_control)
    tools.register("build_rcm", session.build_rcm)

    conversation = Conversation(
        client=ElevenLabs(api_key=api_key),
        agent_id=agent_id,
        requires_auth=True,
        client_tools=tools,
        audio_interface=DefaultAudioInterface(),
        callback_user_transcript=lambda text: session.log_turn("owner", text),
        callback_agent_response=lambda text: session.log_turn("agent", text),
    )

    logger.info("Starting live walkthrough for '%s'. Speak when ready; Ctrl+C to end.", process_map.get("process"))
    conversation.start_session()
    conversation.wait_for_session_end()
    logger.info("RCM and transcript written under runs/%s/", run_id)
    return run_id


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="UC7 voice walkthrough (ElevenLabs -> UC7 RCM Builder).")
    parser.add_argument("--input", type=Path, default=DEFAULT_BUNDLE, help="Walkthrough bundle JSON.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--simulate", action="store_true", help="Offline scripted run (no API/mic).")
    mode.add_argument("--live", action="store_true", help="Live ElevenLabs voice session.")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    if not args.input.exists():
        logger.error("Walkthrough bundle not found: %s", args.input)
        return 2
    bundle = json.loads(args.input.read_text(encoding="utf-8"))

    if args.live:
        missing = [k for k in ("ELEVENLABS_API_KEY", "ELEVENLABS_AGENT_ID") if not os.environ.get(k)]
        if missing:
            logger.error("Live mode needs env vars: %s. Use --simulate for an offline demo.", ", ".join(missing))
            return 2
        run_live(bundle)
    else:
        # Default to the offline path so the package is runnable with no setup.
        if not args.simulate:
            logger.info("No mode given; running --simulate. Use --live for the voice session.")
        run_simulate(bundle)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
