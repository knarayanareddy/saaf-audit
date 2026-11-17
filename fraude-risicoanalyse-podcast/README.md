# Fraud Risk Analysis → Podcast

Turns a fraud risk analysis into something people will actually consume: the failing controls are
performed as a multi-voice podcast, so an audit finding stops being a spreadsheet row and becomes a
conversation you can hear.

> **Fictional case.** Stichting Zorggroep Waterlinie does not exist. All people, conversations,
> systems and incidents are invented for a fraud risk assessment, and the published artifact carries
> that marking visibly. Keep the marking on any material you reuse — this exists to repair controls,
> not to depict anyone.

## How to run

```bash
pip install -r requirements.txt          # no third-party packages; Python 3.10+
python3 build_podcast.py                 # Dutch episode  → samples/aflevering.mp3
python3 build_podcast.py en              # English episode → samples/aflevering.en.mp3
python3 align_podcast.py                 # align transcript → samples/timings*.json
python3 build_page.py                    # bilingual page  → samples/groepsapp-waterlinie.html
```

All four commands run **offline from the bundled cache — no API key needed**. They only call
ElevenLabs when something is missing from `cache/`, which happens when you change a script.
`align_podcast.py` needs a key with the `forced_alignment` permission on a cache miss; unlike
rendering it costs no characters and leaves the audio untouched.

Rendering new audio needs a key:

```bash
export ELEVENLABS_API_KEY=...            # or ELEVENLABS_API_KEY_FILE=/path/to/key.txt
python3 build_podcast.py
```

Tests:

```bash
python3 -m unittest discover -s tests -v
```

## What it does

1. **Read** the chat transcript — 43 messages, 8 roles, 4 days — from `samples/chat.json`. Every
   message maps to a control from the Risk Control Matrix.
2. **Cast** a distinct voice per participant (`samples/cast.json`), separated by timbre rather than
   gender, because listeners have no chat bubbles to tell speakers apart.
3. **Adapt** the chat into a speakable script with narrator bridges for what text cannot carry — the
   attachment, the voice message, the deleted message.
4. **Chunk** the script under the 2,000-character limit of the ElevenLabs Text-to-Dialogue endpoint,
   splitting only on turn boundaries and never inside a question-and-answer beat.
5. **Render** each chunk on `eleven_v3`, cached by a hash of (cast + text + tags), so one corrected
   sentence re-renders one chunk instead of the whole episode.
6. **Assemble** the chunks at MP3 frame level, stripping the per-chunk Xing/Info header that would
   otherwise make players stop after the first chunk.
7. **Publish** both languages into one page with a language switch, each with its own episode and a
   transcript that follows along as it plays.

**The hard rule:** every spoken line carries either a `source` with message ids from `chat.json`, or
`synthetic: true` if it is a narrator line. A line with neither fails validation. That is what stops
a language model from quietly rewriting what people said, and it is enforced in the tests.

## Input / output

- **Input:** `samples/chat.json` (transcript, participants, personas), `samples/cast.json` (voice per
  participant), `samples/script.json` and `script.en.json` (the spoken scripts),
  `samples/artifact-base.html` (the chat page the bilingual build extends).
- **Output:** `samples/aflevering.mp3` (Dutch, 4:36), `samples/aflevering.en.mp3` (English, 4:48),
  `samples/timings.json` and `timings.en.json` (start and end per turn), and
  `samples/groepsapp-waterlinie.html` — one page, both languages, both episodes embedded, with a
  click-to-seek transcript that follows the audio.

### What each file does

| File | Role |
|---|---|
| `build_podcast.py` | Validate → chunk → render → assemble. Takes `nl` (default) or `en`. |
| `align_podcast.py` | Forced-aligns each chunk against its audio, giving a real start and end per turn. |
| `build_page.py` | Builds the bilingual page: two full document versions, one language switch. |
| `i18n.py` | NL→EN translation table (206 entries) plus number notation (21,25 → 21.25). |
| `samples/` | Example inputs and outputs — the complete Waterlinie case. |
| `cache/` | Per-chunk render cache, hashed. Lets the whole pipeline run offline. |
| `tests/` | Offline tests: traceability contract, chunk budget, beat integrity, MP3 headers. |
| `RCM-Builder-demo/` | Upstream pipeline that produced the matrix: 20 risks, 39 controls. Run it with `python3.12`, not `python3`. |
| `PLAN.md` | The approach behind the analysis. |

## Known limitations

- **The episodes have not been listened to end to end.** Frame structure and duration are verified;
  accent quality, whether the audio tags land, and whether the seams are audible are not.
- **No loudness mastering.** The episodes are not normalised to the −16 LUFS podcast standard.
  With ffmpeg: `ffmpeg -i samples/aflevering.mp3 -af "loudnorm=I=-16:TP=-1:LRA=11" -c:a libmp3lame -b:a 128k mastered.mp3`
- **20 of the 43 messages are omitted** from the episode to fit a five-minute run time; the omitted
  ids are listed under `_omitted` in the scripts.
- **Transcript timing is estimated**, apportioned by character count within each chunk, not true
  forced alignment.

## Related plan

[UC4 — Fraud Risk Assessment Agent](https://github.com/SAAF-Project/SAAF-Project/blob/main/plans/hackathon-2/frank-van-dissel-uc4-fraud-risk-assessment.md)
— this agent sits downstream of it: it takes the assessed fraud risks and the Risk Control Matrix
from [UC7 — RCM Builder](https://github.com/SAAF-Project/SAAF-Project/blob/main/plans/hackathon-2/the-control-freaks-uc7-rcm-builder.md)
and turns the result into something an audience will sit through.

## Part of SAAF Project

[saaf-portal.vercel.app](https://saaf-portal.vercel.app)
