"""Tests voor de podcast-pijplijn. Draaien offline, zonder API-sleutel.

    python3 -m unittest discover -s tests -v
"""
import importlib.util
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "samples"


def _load(name):
    """build_podcast.py leest zijn taal uit sys.argv, dus die zetten we vooraf."""
    argv = sys.argv
    sys.argv = [name]
    try:
        spec = importlib.util.spec_from_file_location(name, ROOT / f"{name}.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        sys.argv = argv


build = _load("build_podcast")
i18n = _load("i18n")

CHAT = json.loads((SAMPLES / "chat.json").read_text(encoding="utf8"))
CAST = json.loads((SAMPLES / "cast.json").read_text(encoding="utf8"))
MSG_IDS = {m["id"] for m in CHAT["messages"]}

BITRATES = {1:32,2:40,3:48,4:56,5:64,6:80,7:96,8:112,9:128,10:160,11:192,12:224,13:256,14:320}
RATES = {0:44100, 1:48000, 2:32000}


def scan_mp3(data):
    """Loopt de MP3-frames af. Geeft (frames, seconden, aantal Xing/Info-headers)."""
    i = frames = xing = 0
    seconds = 0.0
    while i < len(data) - 4:
        if data[i] == 0xFF and (data[i + 1] & 0xE0) == 0xE0:
            br = BITRATES.get((data[i + 2] >> 4) & 0xF)
            sr = RATES.get((data[i + 2] >> 2) & 0x3)
            if br and sr:
                flen = int(144 * br * 1000 / sr) + ((data[i + 2] >> 1) & 1)
                if any(m in data[i:i + min(flen, 200)] for m in (b"Xing", b"Info", b"VBRI")):
                    xing += 1
                frames += 1
                seconds += 1152 / sr
                i += flen
                continue
        i += 1
    return frames, seconds, xing


def scripts():
    for lang, name in (("nl", "script.json"), ("en", "script.en.json")):
        yield lang, json.loads((SAMPLES / name).read_text(encoding="utf8"))["turns"]


class TestScriptContract(unittest.TestCase):
    """De harde regel: geen enkele uitgesproken zin zonder herkomst."""

    def test_every_turn_is_traceable(self):
        for lang, turns in scripts():
            for i, t in enumerate(turns):
                with self.subTest(lang=lang, turn=i):
                    self.assertTrue(
                        t.get("source") or t.get("synthetic"),
                        f"turn {i} heeft geen source en is niet als synthetic gemarkeerd")

    def test_sources_point_at_real_messages(self):
        for lang, turns in scripts():
            for i, t in enumerate(turns):
                for mid in t.get("source", []):
                    with self.subTest(lang=lang, turn=i, message=mid):
                        self.assertIn(mid, MSG_IDS, f"onbekend bericht-id {mid}")

    def test_speakers_are_cast(self):
        for lang, turns in scripts():
            for i, t in enumerate(turns):
                with self.subTest(lang=lang, turn=i):
                    self.assertIn(t["speaker"], CAST)

    def test_both_languages_cover_the_same_messages(self):
        seen = [{m for t in turns for m in t.get("source", [])} for _lang, turns in scripts()]
        self.assertEqual(seen[0], seen[1], "NL en EN moeten dezelfde berichten dekken")


class TestChunking(unittest.TestCase):

    def test_chunks_stay_within_budget(self):
        for chunk in build.chunk():
            with self.subTest(chunk=chunk["idx"]):
                self.assertLessEqual(chunk["chars"], build.MAX_CHARS)

    def test_beats_are_never_split(self):
        """Een vraag en het antwoord horen in hetzelfde request te blijven."""
        turns, chunks = build.turns, build.chunk()
        start = 0
        for c in chunks[:-1]:
            start += c["turns"]
            with self.subTest(boundary=start):
                self.assertNotEqual(turns[start - 1].get("beat"), turns[start].get("beat"),
                                    "chunkgrens ligt midden in een beat")


class TestAssembly(unittest.TestCase):
    """Regressietest: losse Xing/Info-headers lieten spelers na 1:09 stoppen."""

    def test_strip_tags_removes_xing_header(self):
        chunk = sorted((ROOT / "cache" / "audio").glob("*.mp3"))[0].read_bytes()
        self.assertGreater(scan_mp3(chunk)[2], 0, "de ruwe chunk hoort een Info-header te hebben")
        self.assertEqual(scan_mp3(build.strip_tags(chunk))[2], 0)

    def test_declared_and_actual_duration_agree(self):
        """Framelengte moet overeenkomen met wat een speler uit de bestandsgrootte afleidt."""
        for name in ("aflevering.mp3", "aflevering.en.mp3"):
            data = (SAMPLES / name).read_bytes()
            _frames, seconds, xing = scan_mp3(data)
            estimate = len(data) / 16000  # 128 kbps CBR
            with self.subTest(episode=name):
                self.assertEqual(xing, 0, "gemonteerde aflevering mag geen Xing/Info-header bevatten")
                self.assertAlmostEqual(seconds, estimate, delta=1.0)
                self.assertGreater(seconds, 240, "aflevering hoort ruim vier minuten te zijn")


class TestTranslation(unittest.TestCase):

    def test_no_dangerously_short_keys(self):
        """Losse sleutels als 'naar' zouden overal in de tekst toeslaan."""
        for key in i18n.DICT:
            with self.subTest(key=key):
                self.assertGreaterEqual(len(key), 6)

    def test_number_notation_is_converted(self):
        self.assertEqual(dict(i18n.NUMBERS)["21,25"], "21.25")


if __name__ == "__main__":
    unittest.main()
