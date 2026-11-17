"""
transcribe_audio.py — Transcribe audio files (m4a/mp3/wav/...) with Whisper
and optionally label speakers using pyannote.audio diarization.

Designed for podcast-style recordings with two or more known speakers
(e.g. recordings of SAAF interviews, leeravonden, podcast appearances).

Output is written to a configurable directory (default: ~/Desktop/podcast-transcripts/)
which is intentionally OUTSIDE the repo, since recordings often contain
non-public context. Output language matches the source language.

Usage:
    python3 tools/scripts/transcribe_audio.py <audio-file-or-dir> [options]

Examples:
    # Quick smoke test, transcript only
    python3 tools/scripts/transcribe_audio.py recording.m4a --no-diarize --model base

    # Full run with diarization, large model, named speakers
    HF_TOKEN=hf_xxx python3 tools/scripts/transcribe_audio.py recording.m4a \\
        --model large-v3 --speaker-map "SPEAKER_00=Host,SPEAKER_01=Guest"

Options:
    --model        Whisper model: tiny, base, small, medium, large-v3 (default: large-v3)
    --language     Force language (default: nl)
    --output       Output directory (default: ~/Desktop/podcast-transcripts)
    --no-diarize   Skip pyannote diarization
    --speaker-map  Map pyannote labels to names, e.g. "SPEAKER_00=Host,SPEAKER_01=Guest".
                   If omitted with diarization on, a heuristic infers the host as
                   the speaker with most question marks in the first five minutes.
    --no-resume    Re-process even if output already exists

Dependencies:
    pip install -r tools/scripts/requirements-audio.txt

Diarization setup:
    See tools/scripts/README-audio.md for HuggingFace token setup and license
    acceptance steps required by pyannote.

Note on m4a files:
    pyannote uses the soundfile backend which does not support m4a. Convert
    first with ffmpeg: ffmpeg -i input.m4a -ac 1 -ar 16000 input.wav
"""

import argparse
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

AUDIO_EXTENSIONS = {".m4a", ".mp3", ".wav", ".aac", ".flac", ".ogg", ".mp4"}

DEFAULT_OUTPUT = Path.home() / "Desktop" / "podcast-transcripts"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def slugify(stem: str) -> str:
    return re.sub(r"[^\w\-]+", "_", stem).strip("_")


def fmt_ts(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"


def collect_files(input_path: Path) -> List[Path]:
    if input_path.is_file():
        return [input_path]
    if input_path.is_dir():
        return sorted(
            f for f in input_path.iterdir()
            if f.suffix.lower() in AUDIO_EXTENSIONS
        )
    log.error("Not a file or directory: %s", input_path)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Whisper
# ---------------------------------------------------------------------------

def transcribe(model, audio_path: Path, language: str) -> dict:
    """Return Whisper result dict with 'text' and 'segments'."""
    return model.transcribe(str(audio_path), language=language, verbose=False)


# ---------------------------------------------------------------------------
# Diarization
# ---------------------------------------------------------------------------

def diarize(audio_path: Path, hf_token: str):
    """Return a pyannote diarization annotation."""
    # PyTorch 2.6+ defaults torch.load to weights_only=True, which rejects
    # pyannote's checkpoints (they pickle several custom classes). Force the
    # legacy behaviour for the duration of this call.
    import torch
    _orig_load = torch.load

    def _patched_load(*a, **kw):
        kw["weights_only"] = False
        return _orig_load(*a, **kw)

    torch.load = _patched_load  # type: ignore

    from pyannote.audio import Pipeline  # type: ignore

    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        use_auth_token=hf_token,
    )
    return pipeline(str(audio_path))


def assign_speakers(whisper_segments: List[dict], diarization) -> List[dict]:
    """Attach a 'speaker' label to each Whisper segment using maximum overlap."""
    turns = [
        (turn.start, turn.end, label)
        for turn, _, label in diarization.itertracks(yield_label=True)
    ]

    out = []
    for seg in whisper_segments:
        best_label: Optional[str] = None
        best_overlap = 0.0
        for t_start, t_end, label in turns:
            overlap = max(0.0, min(seg["end"], t_end) - max(seg["start"], t_start))
            if overlap > best_overlap:
                best_overlap = overlap
                best_label = label
        out.append({**seg, "speaker": best_label or "UNKNOWN"})
    return out


def parse_speaker_map(arg: Optional[str]) -> Dict[str, str]:
    if not arg:
        return {}
    mapping: Dict[str, str] = {}
    for pair in arg.split(","):
        if "=" in pair:
            k, v = pair.split("=", 1)
            mapping[k.strip()] = v.strip()
    return mapping


def heuristic_speaker_map(
    segments: List[dict],
    default_first: str = "Host",
    default_second: str = "Guest",
) -> Dict[str, str]:
    """Infer host/guest from question-mark density in the first five minutes."""
    counts: Dict[str, int] = {}
    for seg in segments:
        if seg["start"] > 300:
            break
        label = seg.get("speaker", "UNKNOWN")
        counts[label] = counts.get(label, 0) + seg["text"].count("?")

    if len(counts) < 2:
        # Fall back to chronological order if we can't tell from questions.
        seen: List[str] = []
        for seg in segments:
            label = seg.get("speaker")
            if label and label not in seen:
                seen.append(label)
            if len(seen) == 2:
                break
        mapping: Dict[str, str] = {}
        if len(seen) >= 1:
            mapping[seen[0]] = default_first
        if len(seen) >= 2:
            mapping[seen[1]] = default_second
        return mapping

    ranked = sorted(counts.items(), key=lambda kv: -kv[1])
    mapping = {ranked[0][0]: default_first}
    if len(ranked) >= 2:
        mapping[ranked[1][0]] = default_second
    return mapping


def merge_consecutive(segments: List[dict]) -> List[dict]:
    """Merge consecutive same-speaker segments into single blocks."""
    merged: List[dict] = []
    for seg in segments:
        if merged and merged[-1]["speaker"] == seg["speaker"]:
            merged[-1]["end"] = seg["end"]
            merged[-1]["text"] += " " + seg["text"].strip()
        else:
            merged.append({
                "start": seg["start"],
                "end": seg["end"],
                "speaker": seg["speaker"],
                "text": seg["text"].strip(),
            })
    return merged


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------

def write_outputs(
    audio_path: Path,
    whisper_result: dict,
    diarized_segments: Optional[List[dict]],
    speaker_map: Dict[str, str],
    output_dir: Path,
) -> None:
    slug = slugify(audio_path.stem)
    output_dir.mkdir(parents=True, exist_ok=True)

    txt_path = output_dir / f"{slug}.txt"
    txt_path.write_text(whisper_result["text"].strip(), encoding="utf-8")
    log.info("  wrote %s", txt_path)

    json_path = output_dir / f"{slug}.segments.json"
    payload = {
        "audio": str(audio_path),
        "language": whisper_result.get("language"),
        "speaker_map": speaker_map,
        "segments": diarized_segments if diarized_segments else whisper_result["segments"],
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    log.info("  wrote %s", json_path)

    if diarized_segments:
        md_path = output_dir / f"{slug}.diarized.md"
        merged = merge_consecutive(diarized_segments)
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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Transcribe audio with Whisper and optional pyannote diarization"
    )
    parser.add_argument("input", help="Audio file or directory of audio files")
    parser.add_argument("--model", default="large-v3",
                       help="Whisper model size (default: large-v3)")
    parser.add_argument("--language", default="nl",
                       help="Language code (default: nl)")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT),
                       help="Output directory")
    parser.add_argument("--no-diarize", action="store_true",
                       help="Skip speaker diarization")
    parser.add_argument("--speaker-map", default=None,
                       help='e.g. "SPEAKER_00=Host,SPEAKER_01=Guest"')
    parser.add_argument("--no-resume", action="store_true",
                       help="Re-process even if output already exists")
    args = parser.parse_args()

    input_path = Path(args.input).expanduser()
    output_dir = Path(args.output).expanduser()
    files = collect_files(input_path)

    if not files:
        log.error("No audio files found at %s", input_path)
        sys.exit(1)

    log.info("Found %d audio file(s).", len(files))
    log.info("Loading Whisper model '%s' ...", args.model)

    import whisper  # type: ignore
    model = whisper.load_model(args.model)
    log.info("Whisper loaded.")

    hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
    if not args.no_diarize and not hf_token:
        log.warning("HF_TOKEN not set; running without diarization. "
                   "See tools/scripts/README-audio.md for setup.")
        args.no_diarize = True

    explicit_map = parse_speaker_map(args.speaker_map)

    for i, audio_path in enumerate(files, start=1):
        slug = slugify(audio_path.stem)
        txt_path = output_dir / f"{slug}.txt"
        if txt_path.exists() and not args.no_resume:
            log.info("[%d/%d] SKIP (exists): %s", i, len(files), audio_path.name)
            continue

        log.info("[%d/%d] Transcribing: %s", i, len(files), audio_path.name)
        result = transcribe(model, audio_path, args.language)
        log.info("  Whisper done (%d segments).", len(result["segments"]))

        diarized_segments: Optional[List[dict]] = None
        speaker_map: Dict[str, str] = {}

        if not args.no_diarize:
            log.info("  Running pyannote diarization (this can take a while) ...")
            try:
                diarization = diarize(audio_path, hf_token)
                diarized_segments = assign_speakers(result["segments"], diarization)
                speaker_map = explicit_map or heuristic_speaker_map(diarized_segments)
                labels = sorted({s["speaker"] for s in diarized_segments})
                log.info("  Diarization done. Labels: %s. Mapping: %s",
                        labels, speaker_map)
            except Exception as exc:
                log.error("  Diarization failed: %s", exc)
                log.error("  Falling back to plain transcript only.")
                diarized_segments = None

        write_outputs(audio_path, result, diarized_segments, speaker_map, output_dir)

    log.info("Done. Output dir: %s", output_dir)


if __name__ == "__main__":
    main()
