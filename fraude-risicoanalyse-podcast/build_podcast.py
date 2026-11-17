#!/usr/bin/env python3
"""Route A — bouwt aflevering.mp3 uit script.json + cast.json.

Stappen: valideren -> chunken (<=1400 tekens, alleen op beat-grenzen)
-> renderen via POST /v1/text-to-dialogue (met cache) -> monteren.

ffmpeg is niet beschikbaar in deze omgeving, dus de montage gebeurt op
MP3-frameniveau: ID3-tags eraf, frames aan elkaar. Loudness-normalisatie
naar -16 LUFS vraagt wel ffmpeg; zie master.sh.
"""
import hashlib, json, os, pathlib, sys, time, urllib.error, urllib.request

ROOT = pathlib.Path(__file__).parent
def api_key() -> str:
    """Sleutel uit de omgeving, nooit uit de broncode.

    Volgorde: ELEVENLABS_API_KEY, anders het pad in ELEVENLABS_API_KEY_FILE,
    anders ./ELEVENLABS_API_KEY.txt naast dit script (staat in .gitignore).
    """
    key = os.environ.get("ELEVENLABS_API_KEY")
    if key:
        return key.strip()
    path = os.environ.get("ELEVENLABS_API_KEY_FILE") or (ROOT / "ELEVENLABS_API_KEY.txt")
    path = pathlib.Path(path)
    if path.is_file():
        return path.read_text(encoding="utf8").strip()
    sys.exit(
        "Geen ElevenLabs-sleutel gevonden.\n"
        "  export ELEVENLABS_API_KEY=...            of\n"
        "  export ELEVENLABS_API_KEY_FILE=/pad/naar/sleutel.txt  of\n"
        f"  leg de sleutel in {ROOT / 'ELEVENLABS_API_KEY.txt'}"
    )
SAMPLES = ROOT / "samples"   # voorbeeldinvoer en -uitvoer
CACHE = ROOT / "cache"       # render-cache per chunk
MAX_CHARS = 1400          # marge onder de 2000 van het endpoint; NL-woorden zijn langer
MODEL = "eleven_v3"
URL = "https://api.elevenlabs.io/v1/text-to-dialogue?output_format=mp3_44100_128"

# taal: 'nl' (standaard) of 'en'. Beide talen gebruiken dezelfde cast, zodat een
# personage in beide afleveringen dezelfde stem houdt.
LANG = sys.argv[1] if len(sys.argv) > 1 else "nl"
assert LANG in ("nl", "en"), "taal moet nl of en zijn"
SCRIPT = SAMPLES / ("script.json" if LANG == "nl" else "script.en.json")
CHUNKDIR = CACHE / ("chunks" if LANG == "nl" else "chunks-en")
AUDIODIR = CACHE / ("audio" if LANG == "nl" else "audio-en")
EPISODE = SAMPLES / ("aflevering.mp3" if LANG == "nl" else "aflevering.en.mp3")
CHUNKDIR.mkdir(exist_ok=True)
AUDIODIR.mkdir(exist_ok=True)

cast = json.loads((SAMPLES / "cast.json").read_text(encoding="utf8"))
script = json.loads(SCRIPT.read_text(encoding="utf8"))
turns = script["turns"]


def validate():
    """Stage 03-rem: elke turn traceerbaar naar een bericht, of expliciet synthetisch."""
    bad = []
    for i, t in enumerate(turns):
        if not t.get("source") and not t.get("synthetic"):
            bad.append(f"turn {i} ({t['speaker']}): geen source en niet synthetic")
        if t["speaker"] not in cast:
            bad.append(f"turn {i}: onbekende spreker {t['speaker']!r}")
        if not t.get("text", "").strip():
            bad.append(f"turn {i}: lege tekst")
    if bad:
        print("VALIDATIE GEFAALD:")
        for b in bad:
            print("  -", b)
        sys.exit(1)
    n_src = sum(1 for t in turns if t.get("source"))
    n_syn = sum(1 for t in turns if t.get("synthetic"))
    chars = sum(len(t["text"]) for t in turns)
    print(f"validatie OK — {len(turns)} turns ({n_src} uit chat, {n_syn} verteller), {chars} tekens")
    return chars


def chunk():
    """Splits alleen op beat-grenzen, nooit binnen een beat."""
    beats, cur, key = [], [], None
    for t in turns:
        if t.get("beat") != key and cur:
            beats.append(cur)
            cur = []
        key = t.get("beat")
        cur.append(t)
    if cur:
        beats.append(cur)

    chunks, cur = [], []
    for b in beats:
        size = sum(len(t["text"]) for t in b)
        cursize = sum(len(t["text"]) for t in cur)
        if cur and cursize + size > MAX_CHARS:
            chunks.append(cur)
            cur = []
        cur.extend(b)
    if cur:
        chunks.append(cur)

    out = []
    for i, c in enumerate(chunks):
        payload = [{"text": t["text"], "voice_id": cast[t["speaker"]]["voice_id"]} for t in c]
        h = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:12]
        size = sum(len(t["text"]) for t in c)
        out.append({"idx": i, "hash": h, "chars": size, "turns": len(c), "inputs": payload})
        (CHUNKDIR / f"{i:02d}-{h}.json").write_text(
            json.dumps(out[-1], ensure_ascii=False, indent=2), encoding="utf8")
    print(f"chunking OK — {len(out)} chunks, grootste {max(c['chars'] for c in out)} tekens")
    return out


def render(chunks):
    key = None
    for c in chunks:
        dest = AUDIODIR / f"{c['idx']:02d}-{c['hash']}.mp3"
        if dest.exists():
            print(f"  chunk {c['idx']:02d} cache-hit ({dest.stat().st_size} bytes)")
            continue
        if key is None:
            key = api_key()   # pas opvragen als er echt gerenderd moet worden
        body = json.dumps({"inputs": c["inputs"], "model_id": MODEL}).encode()
        for attempt in range(5):
            try:
                req = urllib.request.Request(
                    URL, data=body,
                    headers={"xi-api-key": key, "Content-Type": "application/json"})
                data = urllib.request.urlopen(req, timeout=600).read()
                dest.write_bytes(data)
                print(f"  chunk {c['idx']:02d} gerenderd — {c['chars']} tekens, {len(data)} bytes")
                break
            except urllib.error.HTTPError as e:
                msg = e.read()[:300].decode("utf8", "replace")
                if e.code in (429, 500, 502, 503) and attempt < 4:
                    wait = 2 ** attempt * 5
                    print(f"  chunk {c['idx']:02d} HTTP {e.code}, opnieuw over {wait}s")
                    time.sleep(wait)
                    continue
                print(f"  chunk {c['idx']:02d} FOUT HTTP {e.code}: {msg}")
                sys.exit(1)
            except Exception as e:
                if attempt < 4:
                    time.sleep(2 ** attempt * 5)
                    continue
                print(f"  chunk {c['idx']:02d} FOUT: {e!r}")
                sys.exit(1)


BITRATES = {1:32,2:40,3:48,4:56,5:64,6:80,7:96,8:112,9:128,10:160,11:192,12:224,13:256,14:320}
RATES = {0:44100, 1:48000, 2:32000}


def strip_tags(b: bytes) -> bytes:
    """ID3-tags eraf, plus het Xing/Info-headerframe vooraan.

    Elke chunk die ElevenLabs teruggeeft begint met een Info-frame dat de lengte
    van ALLEEN die chunk declareert. Bij naief aan elkaar plakken leest de speler
    de eerste en stopt daar (in ons geval na 1:09 in plaats van 4:32). Het is
    bovendien een stil frame. Weghalen dus: de stroom is CBR 128 kbps, dus zonder
    Xing-header leidt de speler de duur correct af uit de bestandsgrootte.
    """
    if b[:3] == b"ID3":
        size = (b[6] & 0x7F) << 21 | (b[7] & 0x7F) << 14 | (b[8] & 0x7F) << 7 | (b[9] & 0x7F)
        b = b[10 + size:]
    if b[-128:-125] == b"TAG":
        b = b[:-128]
    if len(b) > 4 and b[0] == 0xFF and (b[1] & 0xE0) == 0xE0:
        br = BITRATES.get((b[2] >> 4) & 0xF)
        sr = RATES.get((b[2] >> 2) & 0x3)
        if br and sr:
            flen = int(144 * br * 1000 / sr) + ((b[2] >> 1) & 1)
            if any(m in b[:min(flen, 200)] for m in (b"Xing", b"Info", b"VBRI")):
                b = b[flen:]
    return b


def assemble(chunks):
    parts = [strip_tags((AUDIODIR / f"{c['idx']:02d}-{c['hash']}.mp3").read_bytes()) for c in chunks]
    out = b"".join(parts)
    dest = EPISODE
    dest.write_bytes(out)
    # 128 kbps CBR -> bytes/16000 = seconden
    secs = len(out) / 16000
    print(f"montage OK — {dest} · {len(out)} bytes · circa {int(secs)//60}:{int(secs)%60:02d}")
    return dest


if __name__ == "__main__":
    validate()
    cs = chunk()
    render(cs)
    assemble(cs)
