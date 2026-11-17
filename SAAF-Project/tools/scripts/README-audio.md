# Audio transcription & speaker diarization

Two scripts in this directory transcribe audio recordings (interviews, podcasts,
SAAF leeravonden) and label who spoke when:

- `transcribe_audio.py` — main pipeline: audio → Whisper transcript → optional
  pyannote diarization → markdown with speaker labels.
- `diarize_from_segments.py` — recovery helper: if Whisper succeeded but
  diarization failed, re-run only the diarization step on the saved segments.

Output is written outside the repo by default
(`~/Desktop/podcast-transcripts/`) since recordings often contain non-public
context.

---

## 1. Install dependencies

```bash
pip install -r tools/scripts/requirements-audio.txt
```

Whisper alone is enough for transcription. Diarization (Eduward vs Mathijs vs
guest) requires `pyannote.audio` plus a HuggingFace token (see below).

`ffmpeg` must be installed system-wide (Whisper uses it to decode audio):

```bash
brew install ffmpeg     # macOS
```

---

## 2. HuggingFace token setup (for diarization only)

Pyannote downloads its model weights from HuggingFace Hub and requires you to
accept two model licenses before the first run.

### Step 1 — Create a HuggingFace account

https://huggingface.co/join

### Step 2 — Generate a Read access token

1. Open https://huggingface.co/settings/tokens
2. Click **New token**
3. Token type: **Read** (write/fine-grained not needed)
4. Name it something like `saaf-podcast-diarization`
5. Click **Create token** and copy the token immediately (it starts with `hf_`).
   You will only see it once.

### Step 3 — Accept the pyannote model licenses

You must click "Agree and access repository" on **both** of these pages, while
logged in to HuggingFace:

- https://huggingface.co/pyannote/speaker-diarization-3.1
- https://huggingface.co/pyannote/segmentation-3.0

The form asks for name, organization, and intended use — `SAAF Project / audio
transcription` is fine.

### Step 4 — Make the token available to your shell

For a single session:

```bash
export HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

To persist across sessions, append it to your shell config:

```bash
echo 'export HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx' >> ~/.zshrc
source ~/.zshrc
```

Verify:

```bash
echo $HF_TOKEN     # should print hf_...
```

The scripts also accept `HUGGINGFACE_TOKEN` as an alternative name.

---

## 3. Usage

### Transcript only (fast, no token needed)

```bash
python3 tools/scripts/transcribe_audio.py recording.m4a --no-diarize --model base
```

`--model base` runs in a few minutes per hour of audio. Use it for quick
checks; quality on Dutch with technical jargon is mediocre.

### Full pipeline (transcript + speaker labels)

```bash
python3 tools/scripts/transcribe_audio.py recording.m4a --model large-v3
```

`large-v3` produces noticeably better Dutch transcripts but takes roughly the
duration of the audio itself on a CPU laptop (e.g. ~80 minutes for 50 minutes
of audio).

If you already know which pyannote label is which person, pass an explicit
mapping:

```bash
python3 tools/scripts/transcribe_audio.py recording.m4a \
    --speaker-map "SPEAKER_00=Eduward,SPEAKER_01=Mathijs"
```

Otherwise the script uses a heuristic: the speaker who asks the most questions
in the first five minutes is labelled the host.

### Recovery: re-run diarization only

If `transcribe_audio.py` finished Whisper but diarization failed, you don't
have to redo the transcription. The Whisper segments are saved to
`<slug>.segments.json` and can be re-fed:

```bash
python3 tools/scripts/diarize_from_segments.py \
    recording.wav \
    ~/Desktop/podcast-transcripts/recording.segments.json
```

Note the `.wav` — see m4a caveat below.

---

## 4. Output files

For an audio file `Foo Bar.m4a`, the script writes to the output directory:

| File | Contents |
|---|---|
| `Foo_Bar.txt` | Plain Whisper transcript, single block of text. |
| `Foo_Bar.segments.json` | Whisper segments + speaker labels + speaker map (machine-readable). |
| `Foo_Bar.diarized.md` | Human-readable markdown with `**Host** [mm:ss]` headers per turn. Only written when diarization succeeds. |

---

## 5. Known issues and workarounds

### m4a not supported by pyannote

Whisper handles m4a fine (via ffmpeg), but pyannote uses the `soundfile`
backend which does not. If you see:

```
soundfile.LibsndfileError: Error opening '...m4a': Format not recognised.
```

Convert to wav first:

```bash
ffmpeg -i "input.m4a" -ac 1 -ar 16000 "input.wav"
```

Then point the script at the wav file. (Mono 16 kHz is what pyannote uses
internally anyway, so there is no quality loss.)

### `hf_hub_download() got an unexpected keyword argument 'use_auth_token'`

`pyannote.audio` 3.x still uses the legacy `use_auth_token=` argument that was
removed in `huggingface_hub` 0.30+. The pinned `huggingface_hub<0.30` in
`requirements-audio.txt` avoids this. If you upgraded by mistake:

```bash
pip install 'huggingface_hub<0.30'
```

### `Weights only load failed` from `torch.load`

PyTorch 2.6+ defaults `weights_only=True`, which rejects pyannote checkpoints
because they pickle several custom classes. The script monkey-patches
`torch.load` to set `weights_only=False` for the duration of the diarization
call. No action needed.

### large-v3 is slow

CPU-only inference of `large-v3` on a MacBook can be roughly real-time
(a 50-minute recording takes ~80 minutes of wall clock). Use `--model medium`
or `--model base` if you need a faster, lower-quality pass.

---

## 6. Privacy and language

- Recordings often contain non-public conversations. Output is written to
  `~/Desktop/podcast-transcripts/` by default, **outside the repo**, and is
  not committed.
- The repo-wide "English only" rule (see `CLAUDE.md`) does not apply to these
  transcripts: they are kept in the source language. Only the script code,
  comments and this README are in English.
