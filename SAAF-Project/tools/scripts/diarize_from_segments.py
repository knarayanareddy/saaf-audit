"""
diarize_from_segments.py — Run pyannote diarization on existing Whisper segments.

Recovery helper for transcribe_audio.py: if the Whisper transcription succeeded
but the diarization step failed (e.g. unsupported audio format, missing
HF_TOKEN, dependency mismatch), use this script to skip the expensive
transcription and only run diarization + speaker mapping + markdown output.

Usage:
    HF_TOKEN=hf_xxx python3 tools/scripts/diarize_from_segments.py \\
        <audio-file> <segments.json> [--speaker-map "SPEAKER_00=Host,..."]

Note:
    pyannote uses the soundfile backend which does not support m4a.
    Convert with ffmpeg first if needed:
        ffmpeg -i input.m4a -ac 1 -ar 16000 input.wav
    Then pass the wav file as <audio-file>.
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

# Reuse helpers from transcribe_audio
sys.path.insert(0, str(Path(__file__).parent))
from transcribe_audio import (  # type: ignore  # noqa: E402
    assign_speakers,
    diarize,
    fmt_ts,
    heuristic_speaker_map,
    merge_consecutive,
    parse_speaker_map,
    slugify,
)

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run pyannote diarization on existing Whisper segments"
    )
    parser.add_argument("audio", help="Audio file (wav recommended; pyannote can't read m4a)")
    parser.add_argument("segments_json", help="Path to <slug>.segments.json from transcribe_audio.py")
    parser.add_argument("--speaker-map", default=None,
                       help='e.g. "SPEAKER_00=Host,SPEAKER_01=Guest"')
    parser.add_argument("--output", default=None,
                       help="Output directory (default: same as segments_json)")
    args = parser.parse_args()

    audio_path = Path(args.audio).expanduser()
    seg_path = Path(args.segments_json).expanduser()
    output_dir = Path(args.output).expanduser() if args.output else seg_path.parent

    hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
    if not hf_token:
        log.error("HF_TOKEN not set. See tools/scripts/README-audio.md for setup.")
        sys.exit(1)

    log.info("Loading segments from %s", seg_path)
    payload = json.loads(seg_path.read_text(encoding="utf-8"))
    segments = payload["segments"]
    log.info("  %d segments loaded.", len(segments))

    log.info("Running pyannote diarization (10–20 min on CPU) ...")
    diarization = diarize(audio_path, hf_token)
    diarized = assign_speakers(segments, diarization)
    labels = sorted({s["speaker"] for s in diarized})
    log.info("Diarization done. Labels: %s", labels)

    explicit = parse_speaker_map(args.speaker_map)
    speaker_map = explicit or heuristic_speaker_map(diarized)
    log.info("Speaker mapping: %s", speaker_map)

    slug = slugify(audio_path.stem)
    output_dir.mkdir(parents=True, exist_ok=True)

    payload["speaker_map"] = speaker_map
    payload["segments"] = diarized
    out_json = output_dir / f"{slug}.segments.json"
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                       encoding="utf-8")
    log.info("  wrote %s", out_json)

    md_path = output_dir / f"{slug}.diarized.md"
    merged = merge_consecutive(diarized)
    lines = [f"# Transcript — {audio_path.name}", ""]
    for block in merged:
        name = speaker_map.get(block["speaker"], block["speaker"])
        ts = fmt_ts(block["start"])
        lines.append(f"**{name}** [{ts}]")
        lines.append("")
        lines.append(block["text"])
        lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    log.info("  wrote %s", md_path)


if __name__ == "__main__":
    main()
