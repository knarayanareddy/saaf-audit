#!/usr/bin/env python3
"""Lijnt het transcript uit op de audio en monteert de aflevering opnieuw.

Waarom: het meelopende transcript op de pagina verdeelde de tijd binnen een chunk
naar rato van tekstlengte. Dat is een schatting die binnen een chunk seconden kan
weglopen. Deze stap vraagt /v1/forced-alignment om de werkelijke tijd per teken,
en leidt daar de start en het eind van elke beurt uit af.

Forced alignment lijnt BESTAANDE audio uit tegen bekende tekst: het kost geen
tekens en verandert de audio niet. De sleutel heeft er wel de permissie
`forced_alignment` voor nodig.

Audiotags als [laughs] worden niet uitgesproken en gaan er dus uit voordat de
tekst wordt aangeboden; de tijden worden teruggekoppeld aan de oorspronkelijke
beurten via de tekenposities.

Schrijft:
  cache/alignment[-en]/NN-hash.json ruwe alignment per chunk
  samples/timings[.en].json         absolute start/eind per beurt
  samples/aflevering[.en].mp3       opnieuw gemonteerd uit dezelfde chunks
"""
import json, os, pathlib, re, sys, time, urllib.error, urllib.request, uuid

ROOT = pathlib.Path(__file__).parent
SAMPLES = ROOT / "samples"
CACHE = ROOT / "cache"
URL = "https://api.elevenlabs.io/v1/forced-alignment"

BITRATES = {1:32,2:40,3:48,4:56,5:64,6:80,7:96,8:112,9:128,10:160,11:192,12:224,13:256,14:320}
RATES = {0:44100, 1:48000, 2:32000}
FRAME = 1152 / 44100  # het Xing/Info-frame dat bij de montage vooraan wegvalt


def api_key() -> str:
    key = os.environ.get("ELEVENLABS_API_KEY")
    if key:
        return key.strip()
    path = pathlib.Path(os.environ.get("ELEVENLABS_API_KEY_FILE") or (ROOT / "ELEVENLABS_API_KEY.txt"))
    if path.is_file():
        return path.read_text(encoding="utf8").strip()
    sys.exit("Geen ElevenLabs-sleutel gevonden (ELEVENLABS_API_KEY of ELEVENLABS_API_KEY_FILE).")


def spoken(text: str) -> str:
    """Tekst zoals hij klinkt: audiotags eruit, witruimte genormaliseerd."""
    return re.sub(r"\s+", " ", re.sub(r"\[[^\]]*\]", "", text)).strip()


def strip_tags(b: bytes):
    """ID3 eraf plus het Xing/Info-headerframe. Meldt of dat frame er was."""
    if b[:3] == b"ID3":
        size = (b[6] & 0x7F) << 21 | (b[7] & 0x7F) << 14 | (b[8] & 0x7F) << 7 | (b[9] & 0x7F)
        b = b[10 + size:]
    if b[-128:-125] == b"TAG":
        b = b[:-128]
    stripped = False
    if len(b) > 4 and b[0] == 0xFF and (b[1] & 0xE0) == 0xE0:
        br = BITRATES.get((b[2] >> 4) & 0xF)
        sr = RATES.get((b[2] >> 2) & 0x3)
        if br and sr:
            flen = int(144 * br * 1000 / sr) + ((b[2] >> 1) & 1)
            if any(m in b[:min(flen, 200)] for m in (b"Xing", b"Info", b"VBRI")):
                b = b[flen:]
                stripped = True
    return b, stripped


def duration(b: bytes) -> float:
    i, dur = 0, 0.0
    while i < len(b) - 4:
        if b[i] == 0xFF and (b[i+1] & 0xE0) == 0xE0:
            br = BITRATES.get((b[i+2] >> 4) & 0xF); sr = RATES.get((b[i+2] >> 2) & 0x3)
            if br and sr:
                dur += 1152 / sr
                i += int(144 * br * 1000 / sr) + ((b[i+2] >> 1) & 1)
                continue
        i += 1
    return dur


def align(audio: bytes, text: str, key: str) -> dict:
    b = uuid.uuid4().hex
    body = b"".join([
        (f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="c.mp3"\r\n'
         f'Content-Type: audio/mpeg\r\n\r\n').encode() + audio + b"\r\n",
        f'--{b}\r\nContent-Disposition: form-data; name="text"\r\n\r\n'.encode() + text.encode() + b"\r\n",
        f"--{b}--\r\n".encode(),
    ])
    for attempt in range(5):
        try:
            req = urllib.request.Request(URL, data=body, headers={
                "xi-api-key": key, "Content-Type": f"multipart/form-data; boundary={b}"})
            return json.load(urllib.request.urlopen(req, timeout=900))
        except urllib.error.HTTPError as e:
            msg = e.read()[:200].decode("utf8", "replace")
            if e.code in (429, 500, 502, 503) and attempt < 4:
                time.sleep(2 ** attempt * 5)
                continue
            sys.exit(f"forced-alignment HTTP {e.code}: {msg}")
    sys.exit("forced-alignment: geen antwoord")


def run(lang: str, key: str) -> None:
    script = json.loads((SAMPLES / ("script.json" if lang == "nl" else "script.en.json")).read_text(encoding="utf8"))
    turns = script["turns"]
    chunkdir = CACHE / ("chunks" if lang == "nl" else "chunks-en")
    audiodir = CACHE / ("audio" if lang == "nl" else "audio-en")
    timedir = CACHE / ("alignment" if lang == "nl" else "alignment-en")
    timedir.mkdir(exist_ok=True)
    episode = SAMPLES / ("aflevering.mp3" if lang == "nl" else "aflevering.en.mp3")
    out_timings = SAMPLES / ("timings.json" if lang == "nl" else "timings.en.json")

    chunks = [json.loads(p.read_text(encoding="utf8")) for p in sorted(chunkdir.glob("*.json"))]
    print(f"[{lang}] {len(chunks)} chunks, {len(turns)} beurten")

    parts, timings, clock, ti = [], [], 0.0, 0
    for c in chunks:
        audio = (audiodir / f"{c['idx']:02d}-{c['hash']}.mp3").read_bytes()
        cache_j = timedir / f"{c['idx']:02d}-{c['hash']}.json"

        chunk_turns = turns[ti:ti + c["turns"]]
        pieces = [spoken(t["text"]) for t in chunk_turns]
        text = " ".join(pieces)

        if cache_j.exists():
            res = json.loads(cache_j.read_text(encoding="utf8"))
            print(f"  chunk {c['idx']:02d} cache-hit")
        else:
            res = align(audio, text, key)
            cache_j.write_text(json.dumps(res), encoding="utf8")
            print(f"  chunk {c['idx']:02d} uitgelijnd — {len(text)} tekens, loss {res.get('loss'):.4f}")

        ch = res["characters"]
        assert len(ch) == len(text), f"chunk {c['idx']}: {len(ch)} tekens terug op {len(text)} aangeboden"

        body_bytes, had_header = strip_tags(audio)
        shift = FRAME if had_header else 0.0
        parts.append(body_bytes)

        pos = 0
        for t, piece in zip(chunk_turns, pieces):
            st = max(0.0, ch[pos]["start"] - shift)
            en = max(0.0, ch[pos + len(piece) - 1]["end"] - shift)
            timings.append({"speaker": t["speaker"],
                            "start": round(clock + st, 3),
                            "end": round(clock + en, 3)})
            pos += len(piece) + 1          # +1 voor de spatie tussen twee beurten

        clock += duration(body_bytes)
        ti += c["turns"]

    assert ti == len(turns), f"{ti} beurten gedekt van {len(turns)}"
    episode.write_bytes(b"".join(parts))
    out_timings.write_text(json.dumps(timings, indent=2), encoding="utf8")

    dalend = [i for i in range(1, len(timings)) if timings[i]["start"] < timings[i-1]["start"] - 0.01]
    buiten = [i for i, t in enumerate(timings) if t["end"] > clock + 0.5]
    leeg = [i for i, t in enumerate(timings) if t["end"] <= t["start"]]
    print(f"[{lang}] aflevering {int(clock)//60}:{int(clock)%60:02d} · {len(timings)} beurten uitgelijnd"
          f" · oplopend {'OK' if not dalend else f'FOUT {dalend}'}"
          f" · binnen duur {'OK' if not buiten else f'FOUT {buiten}'}"
          f" · lege beurten {'geen' if not leeg else leeg}")


if __name__ == "__main__":
    key = api_key()
    for lang in (sys.argv[1:] or ["nl", "en"]):
        run(lang, key)
