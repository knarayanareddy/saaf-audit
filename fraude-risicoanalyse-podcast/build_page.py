#!/usr/bin/env python3
"""Bouwt het tweetalige Waterlinie-artifact.

Twee volledige documentversies (NL en EN) in één pagina, met een taalschakelaar
in de balk. Elke versie heeft zijn eigen aflevering, eigen transcript en eigen
auditmodus. De id's uit de bron worden classes, zodat beide versies naast
elkaar kunnen bestaan zonder dubbele id's.
"""
import base64, html, json, pathlib, re, sys

import i18n

ROOT = pathlib.Path(__file__).parent
# De chat-pagina zonder audio, waar beide taalversies op voortbouwen.
SAMPLES = ROOT / "samples"
CACHE = ROOT / "cache"
SRC = SAMPLES / "artifact-base.html"

BR = {1:32,2:40,3:48,4:56,5:64,6:80,7:96,8:112,9:128,10:160,11:192,12:224,13:256,14:320}
SR = {0:44100,1:48000,2:32000}
COLOR = {"SK":"--c-1","BW":"--c-2","DE":"--c-3","MD":"--c-4",
         "MV":"--c-5","RV":"--c-6","EK":"--c-7","MH":"--c-8"}

cast = json.loads((SAMPLES / "cast.json").read_text(encoding="utf8"))
chat = json.loads((SAMPLES / "chat.json").read_text(encoding="utf8"))
NAMES = {p["id"]: p["name"] for p in chat["participants"]}

LABELS = {
    "nl": dict(
        eyebrow="Podcast · ElevenLabs eleven_v3 · text-to-dialogue",
        h2="De aflevering",
        sub=("Hetzelfde gesprek, uitgevoerd. Elke deelnemer heeft een eigen stem; een verteller zet de vier "
             "momenten neer en beschrijft wat in tekst niet hoorbaar is — de bijlage, het spraakbericht, het "
             "verwijderde bericht. Klik een regel om daarheen te springen."),
        dur="duur", voices="stemmen", msgs="berichten", of="van", narr="vertellerzinnen",
        narrator="Verteller"),
    "en": dict(
        eyebrow="Podcast · ElevenLabs eleven_v3 · text-to-dialogue",
        h2="The episode",
        sub=("The same conversation, performed. Every participant has their own voice; a narrator sets up the "
             "four moments and describes what text cannot carry — the attachment, the voice message, the deleted "
             "message. Click a line to jump there."),
        dur="length", voices="voices", msgs="messages", of="of", narr="narrator lines",
        narrator="Narrator"),
}


def mp3_duration(b: bytes) -> float:
    i, dur = 0, 0.0
    while i < len(b) - 4:
        if b[i] == 0xFF and (b[i+1] & 0xE0) == 0xE0:
            br = BR.get((b[i+2] >> 4) & 0xF); sr = SR.get((b[i+2] >> 2) & 0x3)
            if br and sr:
                dur += 1152 / sr
                i += int(144 * br * 1000 / sr) + ((b[i+2] >> 1) & 1)
                continue
        i += 1
    return dur


def podcast_section(lang: str) -> str:
    L = LABELS[lang]
    script = json.loads((SAMPLES / ("script.json" if lang == "nl" else "script.en.json")).read_text(encoding="utf8"))
    turns = script["turns"]
    chunkdir = CACHE / ("chunks" if lang == "nl" else "chunks-en")
    audiodir = CACHE / ("audio" if lang == "nl" else "audio-en")
    episode = SAMPLES / ("aflevering.mp3" if lang == "nl" else "aflevering.en.mp3")

    timings = SAMPLES / ("timings.json" if lang == "nl" else "timings.en.json")

    if timings.exists():
        # Echte uitlijning uit align_podcast.py: tijd per teken via forced alignment.
        real = json.loads(timings.read_text(encoding="utf8"))
        assert len(real) == len(turns), f"{lang}: {len(real)} tijden op {len(turns)} beurten"
        timed = [{**t, "start": r["start"], "end": r["end"]} for t, r in zip(turns, real)]
        clock = mp3_duration(episode.read_bytes())
    else:
        # Terugval: tijd binnen een chunk verdelen naar rato van tekstlengte.
        chunks = [json.loads(p.read_text(encoding="utf8")) for p in sorted(chunkdir.glob("*.json"))]
        timed, ti, clock = [], 0, 0.0
        for c in chunks:
            dur = mp3_duration((audiodir / f"{c['idx']:02d}-{c['hash']}.mp3").read_bytes())
            ct = turns[ti:ti + c["turns"]]
            total = sum(len(t["text"]) for t in ct)
            t0 = clock
            for t in ct:
                share = dur * len(t["text"]) / total
                timed.append({**t, "start": round(t0, 2), "end": round(t0 + share, 2)})
                t0 += share
            clock += dur
            ti += c["turns"]
        assert ti == len(turns), f"{lang}: {ti} turns gedekt van {len(turns)}"

    # De markering doorlopend maken: een beurt blijft oplichten tot de volgende
    # begint, zodat er tijdens een pauze geen regel onbelicht valt.
    for i, t in enumerate(timed):
        nxt = timed[i + 1]["start"] if i + 1 < len(timed) else clock
        if nxt > t["end"]:
            t["end"] = round(nxt, 3)

    rows = []
    for t in timed:
        sp = t["speaker"]
        if sp == "narrator":
            rows.append(f'<button class="ln nr" data-s="{t["start"]}" data-e="{t["end"]}" type="button">'
                        f'<span class="lw">{L["narrator"]}</span>'
                        f'<span class="lt">{html.escape(t["text"])}</span></button>')
        else:
            rows.append(f'<button class="ln" data-s="{t["start"]}" data-e="{t["end"]}" type="button">'
                        f'<span class="lw" style="color:var({COLOR[sp]})">{html.escape(NAMES[sp])}</span>'
                        f'<span class="lt">{html.escape(t["text"])}</span>'
                        f'<span class="ls">{" · ".join(t.get("source", []))}</span></button>')

    b64 = base64.b64encode(episode.read_bytes()).decode()
    mins, secs = int(clock) // 60, int(clock) % 60
    n_src = sum(1 for t in turns if t.get("source"))
    n_syn = sum(1 for t in turns if t.get("synthetic"))

    return f"""
<section id="podcast">
  <div class="pod">
    <span class="k">{L['eyebrow']}</span>
    <h2>{L['h2']}</h2>
    <p class="sub">{L['sub']}</p>
    <audio controls preload="metadata" src="data:audio/mpeg;base64,{b64}"></audio>
    <div class="podmeta">
      <span>{L['dur']} <b>{mins}:{secs:02d}</b></span>
      <span>{L['voices']} <b>9</b></span>
      <span>{L['msgs']} <b>{n_src} {L['of']} 43</b></span>
      <span>{L['narr']} <b>{n_syn}</b></span>
    </div>
    <div class="tr">{''.join(rows)}</div>
  </div>
</section>
"""


def translate(doc: str) -> tuple[str, list[str]]:
    """Past de vertaaltabel toe, langste sleutel eerst, daarna de getalnotatie."""
    missed = []
    for nl in sorted(i18n.DICT, key=len, reverse=True):
        if nl in doc:
            doc = doc.replace(nl, i18n.DICT[nl])
        else:
            missed.append(nl)
    for nl, en in sorted(i18n.NUMBERS, key=lambda p: len(p[0]), reverse=True):
        doc = doc.replace(nl, en)
    return doc, missed


LANGSW = ('<div class="langsw" role="group" aria-label="Taal / Language">'
          '<button type="button" data-go="nl"{nl}>NL</button>'
          '<button type="button" data-go="en"{en}>EN</button></div>')

EXTRA_CSS = """
/* ---------- taalschakelaar ---------- */
.langsw{display:flex;border:1px solid var(--line);border-radius:3px;overflow:hidden;flex:none}
.langsw button{
  font:600 11px/1 "IBM Plex Mono",monospace;letter-spacing:.08em;
  background:var(--paper);color:var(--muted);border:0;padding:7px 11px;cursor:pointer;
}
.langsw button + button{border-left:1px solid var(--line)}
.langsw button[aria-pressed="true"]{background:var(--audit);color:var(--paper)}
.langsw button:focus-visible{outline:2px solid var(--audit);outline-offset:-2px}

/* ---------- podcast ---------- */
.pod{border:1px solid var(--audit);background:var(--audit-bg);padding:20px 22px 22px;display:flex;flex-direction:column;gap:14px}
.pod .k{font:600 11px/1 "IBM Plex Mono",monospace;letter-spacing:.14em;text-transform:uppercase;color:var(--audit)}
.pod h2{margin:0}
.pod .sub{font-size:13.5px;color:var(--ink-soft);max-width:72ch}
.pod audio{width:100%;max-width:560px;height:38px}
.podmeta{display:flex;flex-wrap:wrap;gap:8px 22px;font:400 12px/1 "IBM Plex Mono",monospace;color:var(--muted)}
.podmeta b{color:var(--ink);font-weight:600}
/* position:relative maakt .tr de offsetParent van de regels; zonder dat meet
   offsetTop tot de bovenkant van de pagina en klopt elke scrollberekening niet */
.tr{position:relative;margin-top:4px;border:1px solid var(--line);background:var(--paper);max-height:330px;overflow-y:auto;overscroll-behavior:contain}
.ln{display:grid;grid-template-columns:132px 1fr;gap:3px 12px;width:100%;text-align:left;background:none;border:0;
    border-bottom:1px solid var(--line-soft);padding:8px 12px;cursor:pointer;font:inherit;color:inherit}
.ln:last-child{border-bottom:0}
.ln:hover{background:var(--panel)}
.ln:focus-visible{outline:2px solid var(--audit);outline-offset:-2px}
.ln.on{background:var(--audit-bg)}
.ln .lw{font:600 12.5px/1.45 "IBM Plex Sans",sans-serif}
.ln.nr .lw{color:var(--muted);font-weight:500;font-style:italic}
.ln .lt{font-size:13.5px;line-height:1.45}
.ln.nr .lt{color:var(--ink-soft);font-style:italic}
.ln .ls{grid-column:2;font:400 10.5px/1 "IBM Plex Mono",monospace;color:var(--muted);letter-spacing:.04em}
@media (max-width:640px){.ln{grid-template-columns:1fr}.ln .ls{grid-column:1}}
"""

SCRIPT = """
<script>
(function(){
  var docs = { nl: document.querySelector('.doc-nl'), en: document.querySelector('.doc-en') };
  var chats = {}, started = {};

  /* ---- chatweergave, gescoped op één taalversie ---- */
  function makeChat(root){
    var toggle = root.querySelector('.auditToggle');
    var skip   = root.querySelector('.skipBtn');
    var stream = root.querySelector('.stream');
    var wrap   = root.querySelector('.wrap');
    var items  = Array.prototype.filter.call(stream.children, function(el){
      return el.classList.contains('msg') || el.classList.contains('day');
    });

    var TYPING = 850, GAP = 1150;
    var i = 0, timer = null, typingEl = null, done = false;

    function applyAudit(){ wrap.classList.toggle('audit', toggle.checked); }
    function nearBottom(){ return stream.scrollHeight - stream.scrollTop - stream.clientHeight < 90; }
    function follow(stick){ if (stick) stream.scrollTop = stream.scrollHeight; }
    function clearTyping(){
      if (typingEl && typingEl.parentNode) typingEl.parentNode.removeChild(typingEl);
      typingEl = null;
    }
    function showTyping(msg){
      var out = msg.classList.contains('out');
      var who = msg.querySelector('.who');
      typingEl = document.createElement('div');
      typingEl.className = 'msg typing shown' + (out ? ' out' : '');
      var bubble = document.createElement('div');
      bubble.className = 'bubble';
      if (who){
        var nm = document.createElement('span');
        nm.className = 'who'; nm.style.color = who.style.color; nm.textContent = who.textContent;
        bubble.appendChild(nm);
      }
      var dots = document.createElement('span');
      dots.className = 'dots'; dots.innerHTML = '<i></i><i></i><i></i>';
      bubble.appendChild(dots);
      typingEl.appendChild(bubble);
      typingEl.setAttribute('aria-hidden', 'true');
      var stick = nearBottom();
      stream.appendChild(typingEl);
      follow(stick);
    }
    function reveal(el){ var stick = nearBottom(); el.classList.add('shown'); follow(stick); }
    function finish(){
      done = true; clearTimeout(timer); clearTyping();
      stream.classList.remove('playing'); skip.hidden = true;
    }
    function revealAll(){ items.forEach(function(el){ el.classList.add('shown'); }); finish(); }
    function step(){
      if (done) return;
      if (i >= items.length){ finish(); return; }
      var el = items[i];
      if (el.classList.contains('day')){
        reveal(el); i++; timer = setTimeout(step, 900); return;
      }
      showTyping(el);
      timer = setTimeout(function(){
        clearTyping(); reveal(el); i++; timer = setTimeout(step, GAP);
      }, TYPING);
    }

    toggle.addEventListener('change', function(){
      applyAudit();
      if (toggle.checked && !done) revealAll();
    });
    skip.addEventListener('click', revealAll);
    applyAudit();

    var still = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    return {
      play: function(){
        if (toggle.checked || still){ revealAll(); }
        else { stream.classList.add('playing'); skip.hidden = false; timer = setTimeout(step, 700); }
      },
      revealAll: revealAll
    };
  }

  /* ---- podcastspeler met meelopend transcript ---- */
  function initPlayer(root){
    var a = root.querySelector('#podcast audio, .pod audio');
    if (!a) return;
    var box = root.querySelector('.pod .tr');
    var lines = [].slice.call(root.querySelectorAll('.pod .ln'));
    var cur = null, handScroll = 0;
    var still = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    /* Wie zelf scrollt wil niet teruggesleept worden. Alleen echte
       invoergebeurtenissen tellen; het scroll-event vuurt ook op ons eigen werk. */
    ['wheel', 'touchmove'].forEach(function(ev){
      box.addEventListener(ev, function(){ handScroll = Date.now(); }, {passive: true});
    });

    function follow(el){
      if (Date.now() - handScroll < 4000) return;
      /* Met rechthoeken in plaats van offsetTop: dat werkt ongeacht welke
         voorouder toevallig de offsetParent is. */
      var br = box.getBoundingClientRect(), cr = el.getBoundingClientRect();
      if (cr.top >= br.top && cr.bottom <= br.bottom) return;   /* al in beeld */
      var top = box.scrollTop + (cr.top - br.top) - (br.height - cr.height) / 2;
      top = Math.max(0, Math.min(top, box.scrollHeight - box.clientHeight));
      if (box.scrollTo) box.scrollTo({top: top, behavior: still ? 'auto' : 'smooth'});
      else box.scrollTop = top;
    }

    lines.forEach(function(l){
      l.addEventListener('click', function(){
        handScroll = 0;                 /* klikken is de regel volgen, niet wegkijken */
        a.currentTime = parseFloat(l.dataset.s);
        a.play();
      });
    });

    a.addEventListener('timeupdate', function(){
      var t = a.currentTime, hit = null;
      for (var i = 0; i < lines.length; i++){
        if (t >= parseFloat(lines[i].dataset.s) && t < parseFloat(lines[i].dataset.e)){ hit = lines[i]; break; }
      }
      if (hit === cur) return;
      if (cur) cur.classList.remove('on');
      cur = hit;
      if (cur){
        cur.classList.add('on');
        follow(cur);
      }
    });
  }

  /* ---- taalwissel ---- */
  function show(lang){
    Object.keys(docs).forEach(function(k){
      docs[k].hidden = (k !== lang);
      if (k !== lang){
        var a = docs[k].querySelector('audio');
        if (a && !a.paused) a.pause();
      }
    });
    document.documentElement.lang = lang;
    try { localStorage.setItem('waterlinie-lang', lang); } catch (e) {}
    if (!started[lang]){
      started[lang] = true;
      /* bij wisselen niet opnieuw animeren: het gesprek staat er meteen */
      chats[lang].revealAll();
    }
  }

  Object.keys(docs).forEach(function(k){
    chats[k] = makeChat(docs[k]);
    initPlayer(docs[k]);
    docs[k].querySelectorAll('.langsw button').forEach(function(b){
      b.addEventListener('click', function(){ show(b.dataset.go); });
    });
  });

  var start = 'nl';
  try { var s = localStorage.getItem('waterlinie-lang'); if (s === 'en' || s === 'nl') start = s; } catch (e) {}

  Object.keys(docs).forEach(function(k){ docs[k].hidden = (k !== start); });
  document.documentElement.lang = start;
  started[start] = true;
  chats[start].play();
})();
</script>
"""


def main():
    raw = SRC.read_text(encoding="utf8")
    body = raw.split("<body>", 1)[1].rsplit("</body>", 1)[0]

    head, rest = body.split('<div class="band">', 1)
    rest = '<div class="band">' + rest
    content, _oldscript = rest.split("<script>", 1)
    content = content.rstrip()

    # id's -> classes, zodat beide taalversies naast elkaar kunnen bestaan
    content = content.replace('class="skip" id="skipBtn"', 'class="skip skipBtn"')
    content = content.replace('<input type="checkbox" id="auditToggle">', '<input type="checkbox" class="auditToggle">')
    assert "skipBtn" in content and "auditToggle" in content

    # auditmodus wordt per taalversie gezet, niet op body
    head = head.replace("body.audit .ann{display:block}", ".audit .ann{display:block}")
    assert ".audit .ann{display:block}" in head
    head = head.replace("@media (prefers-reduced-motion: reduce){*{transition:none !important}}",
                        EXTRA_CSS + "@media (prefers-reduced-motion: reduce){*{transition:none !important}}", 1)

    nl_base = content
    en_base, missed = translate(content)

    docs = []
    for lang, base in (("nl", nl_base), ("en", en_base)):
        d = base.replace('<section id="cast">', podcast_section(lang) + '\n<section id="cast">', 1)
        if lang == "en":
            # sectie-id's uniek houden: beide taalversies staan tegelijk in de DOM
            d = re.sub(r'id="(podcast|cast|chat|collusie|bevindingen|tests)"', r'id="\1-en"', d)
        sw = LANGSW.format(nl=' aria-pressed="true"' if lang == "nl" else "",
                           en=' aria-pressed="true"' if lang == "en" else "")
        d = d.replace('<div class="bar">', '<div class="bar">\n  ' + sw, 1)
        docs.append(f'<div class="doc doc-{lang}"{"" if lang == "nl" else " hidden"}>\n{d}\n</div>')

    out = SAMPLES / "groepsapp-waterlinie.html"
    out.write_text(head + "\n".join(docs) + SCRIPT, encoding="utf8")

    print(f"geschreven: {out} · {out.stat().st_size/1024/1024:.2f} MB")
    if missed:
        print(f"LET OP — {len(missed)} vertaalregels vonden geen match:")
        for m in missed[:12]:
            print("  -", m[:90])
    else:
        print("alle 206 vertaalregels toegepast")
    return out, missed


if __name__ == "__main__":
    main()
