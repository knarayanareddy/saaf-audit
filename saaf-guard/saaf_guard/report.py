"""Rapportage: bevindingen -> challenge-CSV + tweetalig (NL/EN) HTML-rapport, gegroepeerd per oorzaak.

Alleen standaardbibliotheek. Wordt aangeroepen door saaf_guard.scan, maar is ook los te gebruiken:
  from saaf_guard.report import write_csv, write_html
"""
from __future__ import annotations

import csv
import html
import os
import re

RATINGS = ["Critical", "High", "Medium", "Low", "Informational"]
COL = {"Critical": "#8f1d2c", "High": "#c0384a", "Medium": "#c2720a", "Low": "#5f6b7a", "Informational": "#93a0ae"}
SECRET = re.compile(r"(sk-ant-[A-Za-z0-9_-]{8,}|sk-proj-[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9]{24,}|ghp_[A-Za-z0-9]{20,}|"
                    r"github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{30,}|xox[bp]-[0-9A-Za-z-]{10,})")

# key -> (skill-regel(s), naam nl, naam en, wat nl, wat en, waarom nl, waarom en, fix nl, fix en)
CAUSES = {
    "secrets": ([7], "Sleutels in de git-geschiedenis", "Keys in git history",
                "Echte API-sleutels zijn ooit gecommit; verwijderen uit de huidige versie is niet genoeg.",
                "Real API keys were committed at some point; removing them from the current version is not enough.",
                "Iedereen met leestoegang of een oude clone kan de sleutel misbruiken.",
                "Anyone with read access or an old clone can abuse the key.",
                "Sleutel intrekken, geschiedenis opschonen, secret-scan over de volledige geschiedenis in CI.",
                "Revoke the key, purge history, run a full-history secret scan in CI."),
    "inject": ([1], "Documenten van de auditee sturen het oordeel", "Auditee documents steer the verdict",
               "Tekst uit beleid, rapporten, uploads of gescande repos gaat ongemarkeerd de prompt in.",
               "Text from policies, reports, uploads or scanned repos enters the prompt unmarked.",
               "De geauditeerde partij kan de uitkomst beïnvloeden; dat raakt de onafhankelijkheid (GIAS Std 14).",
               "The auditee can influence the outcome; this undermines independence (GIAS Std 14).",
               "fence() + FENCE_RULE; output van agent A nooit als systeemprompt van agent B.",
               "fence() + FENCE_RULE; never use agent A's output as agent B's system prompt."),
    "trust": ([3], "Wat het model zegt wordt niet gecontroleerd", "Model output is not checked",
              "Citaten, paginanummers, ID's en verdicts worden overgenomen zoals het model ze teruggeeft.",
              "Quotes, page numbers, IDs and verdicts are taken as the model returns them.",
              "Verzonnen bewijs of verwisselde controls belanden als 'onderbouwd' in het dossier.",
              "Invented evidence or swapped controls end up in the file as 'supported'.",
              "is_grounded() voor citaten; velden uit de bron overschrijven; enums strikt valideren.",
              "is_grounded() for quotes; overwrite fields from the source; validate enums strictly."),
    "failopen": ([2, 4], "Bij een fout wordt het toch 'goed'", "On error it still says 'fine'",
                 "Lege of kapotte uitvoer, NaN of onbekende labels leveren Green, MATCH, LOW of een echt ogend rapport op.",
                 "Empty or broken output, NaN or unknown labels yield Green, MATCH, LOW or a real-looking report.",
                 "Een mislukte toets ziet eruit als een geslaagde — het gevaarlijkste soort fout voor een auditor.",
                 "A failed test looks like a passed one — the most dangerous kind of error for an auditor.",
                 "rollup() => 'Inconclusive'; within_tolerance() weigert NaN; checks blokkeren, niet alleen loggen.",
                 "rollup() => 'Inconclusive'; within_tolerance() rejects NaN; checks block, not just log."),
    "gate": ([5], "Menselijke goedkeuring is te omzeilen", "Human approval can be bypassed",
             "Een LLM-oordeel zet zelf een status; de goedkeurder komt uit het verzoek; goedkeuring hangt niet aan de versie.",
             "An LLM verdict sets a status itself; the approver comes from the request; approval is not tied to a version.",
             "Het vier-ogenprincipe bestaat alleen op papier.",
             "The four-eyes principle exists on paper only.",
             "Status alleen via mens; identiteit uit de server-sessie; goedkeuring gekoppeld aan de hash.",
             "Status only via a human; identity from the server session; approval bound to the artefact hash."),
    "trail": ([8], "Audit-trail, bewijs en methode te vervalsen", "Audit trail, evidence and method can be forged",
              "Hashketens zonder sleutel, trails die opnieuw worden opgebouwd, methodes die iedereen kan vervangen.",
              "Hash chains without a key, trails rebuilt from editable files, methods anyone can replace.",
              "Achteraf aanpassen valt niet op; het dossier verliest zijn bewijskracht.",
              "Tampering after the fact goes unnoticed; the file loses its evidential value.",
              "AuditTrail met HMAC-sleutel buiten de data, alleen toevoegen, verify().",
              "AuditTrail with an HMAC key outside the data, append-only, verify()."),
    "open": ([6], "Servers open voor het netwerk of elke website", "Servers open to the network or any website",
             "Endpoints zonder inlog op 0.0.0.0, CORS '*', GET-routes met bijwerkingen, tokens naar vrije URL's.",
             "Endpoints without login on 0.0.0.0, CORS '*', GET routes with side effects, tokens sent to free-form URLs.",
             "Iemand op het netwerk of een willekeurige website kan data lezen of wissen en tegoed verbruiken.",
             "Anyone on the network or any website can read or delete data and spend credit.",
             "127.0.0.1, geen CORS '*', token op elk endpoint, geen GET met bijwerkingen, URL-delen allowlisten.",
             "127.0.0.1, no CORS '*', a token on every endpoint, no GET with side effects, allowlist URL parts."),
    "privacy": ([9], "Persoonsgegevens onvoldoende beschermd", "Personal data insufficiently protected",
                "Ongemaskeerde PII, masking die vrije tekst mist, echte namen naar het model of in publieke bestanden.",
                "Unmasked PII, masking that misses free text, real names sent to the model or into public files.",
                "AVG-risico, juist in tools die naleving moeten toetsen.",
                "GDPR risk, precisely in tools meant to test compliance.",
                "Maskeren vóór de prompt (ook vrije tekst); rollen via inlog; geen broninhoud in foutmeldingen.",
                "Mask before the prompt (incl. free text); roles via login; no source content in error messages."),
    "output": ([9], "Onveilige uitvoer en uitvoering", "Unsafe output and execution",
               "Formules in exports, onge-escapete HTML, shell=True, zwakke padcontrole, scripts zonder pin.",
               "Formulas in exports, unescaped HTML, shell=True, weak path checks, unpinned scripts.",
               "Wie een export of rapport opent kan ongemerkt code uitvoeren of gegevens lekken.",
               "Opening an export or report can silently run code or leak data.",
               "safe_cell(), escape per waarde, geen shell, paden via resolve(), scripts pinnen met integrity.",
               "safe_cell(), escape every value, no shell, paths via resolve(), pin scripts with integrity."),
}
RULE_CAUSE = {"SG01": "secrets", "SG02": "inject", "SG03": "failopen", "SG04": "failopen", "SG05": "open",
              "SG06": "output", "SG07": "trail", "SG08": "output", "SG09": "open", "SG10": "output",
              "SG11": "output", "SG12": "open", "SG13": "open", "SG14": "output", "SG15": "output",
              "SG16": "output", "SG17": "failopen"}


def infer_cause(f: dict) -> str:
    """Oorzaak bepalen: expliciet veld 'cause' > SAAF Guard-regel > categorie + trefwoorden in de titel.

    De reviewer-agent hoort 'cause' zelf te zetten; dit is alleen een vangnet.
    """
    if f.get("cause") in CAUSES:
        return f["cause"]
    if f.get("rule") in RULE_CAUSE:
        return RULE_CAUSE[f["rule"]]
    cat = (f.get("category") or "").lower()
    t = f.get("title", "").lower()
    failopen = re.search(r"fails? open|green|nan|dry-run|low.*supported|only logs|skipped for|yields a", t)
    if cat == "secrets":
        return "secrets"
    if cat == "privacy":
        return "privacy"
    if cat == "prompt-injection":
        if re.search(r"formula", t):
            return "output"
        if re.search(r"llm-echoed|accepted without|trusts|go/no-go|accepted on", t):
            return "trust"
        return "inject"
    if cat == "web":
        return "output" if re.search(r"xss|unescaped|escap", t) else "open"
    if cat == "audit-integrity":
        if failopen:
            return "failopen"
        if re.search(r"approv|validated|human gate|sign-off", t):
            return "gate"
        if re.search(r"hash|trail|audit log|tamper|forg|methodolog|checkpoint|rewrit|crash", t):
            return "trail"
        return "trust"
    if failopen:
        return "failopen"
    return "output"


# ------------------------------------------------------------------ CSV

def write_csv(findings: list[dict], path: str, team: str = "") -> int:
    rows = []
    for x in findings:
        if x["risk_rating"] not in RATINGS:
            raise ValueError(f"Ongeldige risk_rating: {x.get('title')}")
        obs = x["observation"]
        if x.get("location") and x["location"] not in obs:
            obs = f"{obs} [{x['location']}]"
        row = [x["title"], x["repo"], x["risk_rating"], obs, x["recommendation"],
               "yes" if str(x.get("verified")).lower() == "yes" else "no", team]
        if any(SECRET.search(str(c)) for c in row):
            raise ValueError(f"Sleutelachtige waarde in bevinding '{x['title']}' — eerst verwijderen")
        rows.append(row)
    rows.sort(key=lambda r: (RATINGS.index(r[2]), r[1].lower(), r[0].lower()))
    if len(rows) > 500:
        raise ValueError(f"{len(rows)} rijen; max 500 per CSV")
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["title", "repo", "risk_rating", "observation", "recommendation", "verified", "team"])
        w.writerows(rows)
    if os.path.getsize(path) >= 1_000_000:
        raise ValueError("CSV groter dan 1 MB; splitsen")
    return len(rows)


# ------------------------------------------------------------------ HTML

def _L(nl: str, en: str) -> str:
    """Tweetalige tekst: CSS toont alleen de actieve taal."""
    return f'<span class="nl">{nl}</span><span class="en">{en}</span>'


def write_html(findings: list[dict], path: str, lang: str = "nl", title: str = "SAAF security scan",
               repos: list[str] | None = None, solution_html: str | None = None, extra_css: str = "",
               subtitle: tuple[str, str] | None = None, related: list[tuple[str, str, str, str, str]] | None = None,
               issues_plan: list[dict] | None = None,
               extra_sections: list[tuple[str, str, str, str]] | None = None) -> None:
    """Interactief rapport: per oorzaak gegroepeerd, repo-overzicht, 'speelt in'-chips, zoeken en filters.

    repos          volledige lijst gescande repos (ook zonder bevindingen) voor het repo-overzicht
    solution_html  eigen oplossingssectie (standaard: korte SAAF Guard-uitleg)
    extra_css      extra CSS voor solution_html
    subtitle       (nl, en) ondertitel; standaard aantallen + werkwijze
    related        verwijzingen naar andere rapporten: (href, label_nl, label_en, uitleg_nl, uitleg_en)
    """
    esc = html.escape
    for i, f in enumerate(findings):
        f["_cause"] = infer_cause(f)
        f["_id"] = f"f{i}"
    groups = []
    for key, (rules, nn, ne, wn, we, yn, ye, fn, fe) in CAUSES.items():
        items = sorted((f for f in findings if f["_cause"] == key),
                       key=lambda r: (RATINGS.index(r["risk_rating"]), r["repo"].lower()))
        if items:
            groups.append(dict(key=key, rules=rules, nn=nn, ne=ne, wn=wn, we=we, yn=yn, ye=ye, fn=fn, fe=fe, items=items))
    groups.sort(key=lambda g: (-sum(r["risk_rating"] == "Critical" for r in g["items"]) * 100
                               - sum(r["risk_rating"] == "High" for r in g["items"]) * 10 - len(g["items"])))
    tot = {k: sum(f["risk_rating"] == k for f in findings) for k in RATINGS}
    repo_names = sorted({f["repo"] for f in findings} | set(repos or []), key=str.lower)
    n_aff = len({f["repo"] for f in findings})
    ver = sum(str(f.get("verified")).lower() == "yes" for f in findings)
    auto = sum(f.get("source") == "guard" for f in findings)
    cause_name = {k: (v[1], v[2]) for k, v in CAUSES.items()}

    def bar(items, style=""):
        n = len(items) or 1
        return f'<div class="bar"{style}>' + "".join(
            f'<span style="width:{100 * sum(r["risk_rating"] == k for r in items) / n:.1f}%;background:{COL[k]}"></span>'
            for k in RATINGS) + "</div>"

    def repo_chips(items, current=None):
        cnt = {}
        for r in items:
            cnt[r["repo"]] = cnt.get(r["repo"], 0) + 1
        return "".join(f'<button class="rchip{" cur" if rp == current else ""}" data-repo="{esc(rp)}">{esc(rp)} <b>{c}</b></button>'
                       for rp, c in sorted(cnt.items(), key=lambda x: (-x[1], x[0].lower())))

    def tags(r):
        yes = str(r.get("verified")).lower() == "yes"
        t = f'<span class="tag{" ok" if yes else ""}">{_L("geverifieerd", "verified") if yes else _L("niet geverifieerd", "not verified")}</span>'
        if r.get("source") == "guard":
            t += f'<span class="tag g">{_L("automatisch (SAAF Guard)", "automatic (SAAF Guard)")}</span>'
        if r.get("caught"):
            t += f'<span class="tag g">{_L("CI-check vangt", "caught by CI check")}</span>'
        return t

    # ---- per oorzaak
    sec = []
    for n, g in enumerate(groups, 1):
        rows = []
        for r in g["items"]:
            search = " ".join([r["title"], r["repo"], r["observation"], r["recommendation"], r.get("location", ""),
                               r["risk_rating"], cause_name[g["key"]][0], cause_name[g["key"]][1]]).lower()
            rows.append(f"""
<details class="f" id="{r['_id']}" data-repo="{esc(r['repo'])}" data-sev="{r['risk_rating']}" data-s="{esc(search)}">
<summary><span class="sev" style="--c:{COL[r['risk_rating']]}">{r['risk_rating']}</span>
<button class="repo rlink" data-repo="{esc(r['repo'])}" title="{_L('Alleen deze repo tonen', 'Show only this repo').replace('"', '&quot;')}">{esc(r['repo'])}</button>
<span class="t">{esc(r['title'])}</span><span class="tags">{tags(r)}</span></summary>
<div class="body"><p><b>{_L('Observatie', 'Observation')}.</b> {esc(r['observation'])}</p>
<p><b>{_L('Aanbeveling', 'Recommendation')}.</b> {esc(r['recommendation'])}</p>
{f'<p class="loc">{esc(r["location"])}</p>' if r.get('location') else ''}
<div class="also"><span>{_L('Zelfde oorzaak speelt in', 'Same root cause in')}:</span> {repo_chips(g['items'], r['repo'])}</div></div></details>""")
        pills = " ".join(f'<span class="pill" style="--c:{COL[k]}">{sum(r["risk_rating"] == k for r in g["items"])} {k}</span>'
                         for k in RATINGS if any(r["risk_rating"] == k for r in g["items"]))
        nrep = len({r["repo"] for r in g["items"]})
        sec.append(f"""
<section class="grp" id="{g['key']}"><div class="gh"><div class="num">{n:02d}</div><div class="gt">
<h2>{_L(esc(g['nn']), esc(g['ne']))} <span class="cnt">{len(g['items'])}</span></h2>{bar(g['items'])}
<div class="pills">{pills} <a class="pill rule" href="#oplossing">{_L('Skill-regel', 'Skill rule')} {' + '.join(map(str, g['rules']))}</a></div>
<div class="also top"><span>{_L(f'Speelt in {nrep} repo(s)', f'Affects {nrep} repo(s)')}:</span> {repo_chips(g['items'])}</div></div></div>
<div class="three"><div><h4>{_L('Wat gaat er mis', 'What goes wrong')}</h4><p>{_L(esc(g['wn']), esc(g['we']))}</p></div>
<div><h4>{_L('Waarom het ertoe doet', 'Why it matters')}</h4><p>{_L(esc(g['yn']), esc(g['ye']))}</p></div>
<div><h4>{_L('Structurele oplossing', 'Structural fix')}</h4><p>{_L(esc(g['fn']), esc(g['fe']))}</p></div></div>
{''.join(rows)}<p class="none">{_L('Geen bevindingen in deze groep voor het huidige filter.', 'No findings in this group for the current filter.')}</p></section>""")

    # ---- per repo
    def repo_row(rp):
        items = [f for f in findings if f["repo"] == rp]
        c = {k: sum(f["risk_rating"] == k for f in items) for k in RATINGS}
        score = c["Critical"] * 1000 + c["High"] * 100 + c["Medium"] * 10 + c["Low"]
        causes = sorted({f["_cause"] for f in items}, key=lambda k: list(CAUSES).index(k))
        cz = "".join(f'<span class="cz">{_L(esc(cause_name[k][0]), esc(cause_name[k][1]))}</span>' for k in causes)
        cells = "".join(f'<td class="n">{c[k] or ""}</td>' for k in ("Critical", "High", "Medium", "Low"))
        empty = "" if items else f'<span class="muted">{_L("geen bevindingen in deze scan", "no findings in this scan")}</span>'
        return score, (f'<tr class="rrow{"" if items else " zero"}" data-repo="{esc(rp)}" data-s="{esc(rp.lower())}">'
                       f'<td class="repo">{esc(rp)}</td><td class="n tot">{len(items)}</td>{cells}'
                       f'<td>{bar(items, " style=\"width:120px;height:6px;margin:0\"") if items else ""}</td><td>{cz}{empty}</td></tr>')

    rrows = sorted((repo_row(rp) for rp in repo_names), key=lambda x: -x[0])
    repo_table = f"""
<section id="repos" class="card"><div class="cardh"><h3 class="sec">{_L('Per repository', 'Per repository')}</h3>
<span class="muted">{_L(f'{n_aff} van {len(repo_names)} repos met bevindingen — klik op een repo om te filteren', f'{n_aff} of {len(repo_names)} repos with findings — click a repo to filter')}</span></div>
<div class="tblwrap"><table class="rt"><thead><tr><th>Repo</th><th class="n">{_L('Totaal', 'Total')}</th><th class="n">C</th><th class="n">H</th><th class="n">M</th><th class="n">L</th><th></th><th>{_L('Oorzaken', 'Root causes')}</th></tr></thead>
<tbody>{''.join(r for _, r in rrows)}</tbody></table></div></section>"""

    ov = "".join(f'<a class="ov" href="#{g["key"]}"><div class="ovn">{len(g["items"])}</div><div><div class="ovt">{_L(esc(g["nn"]), esc(g["ne"]))}</div>{bar(g["items"], " style=\"width:200px;height:6px;margin:0\"")}<div class="muted sm">{_L(str(len({r["repo"] for r in g["items"]})) + " repos", str(len({r["repo"] for r in g["items"]})) + " repos")}</div></div></a>' for g in groups)
    top = sorted((f for f in findings if f["risk_rating"] in ("Critical", "High")),
                 key=lambda r: (RATINGS.index(r["risk_rating"]), r["repo"].lower()))
    toprows = "".join(f'<tr class="go" data-go="{r["_id"]}"><td><span class="sev" style="--c:{COL[r["risk_rating"]]}">{r["risk_rating"]}</span></td><td class="repo">{esc(r["repo"])}</td><td>{esc(r["title"])}</td></tr>' for r in top)
    kpi = lambda v, nl, en, c="": f'<div class="kpi"><div class="v"{c}>{v}</div><div class="l">{_L(nl, en)}</div></div>'
    sevbtns = "".join(f'<button class="sevf" data-sev="{k}" style="--c:{COL[k]}">{k} <b>{tot[k]}</b></button>' for k in RATINGS if tot[k])
    filterbar = f"""
<div class="fbar" id="fbar"><input id="q" type="search" placeholder="" autocomplete="off">
<div class="sevs">{sevbtns}</div>
<span id="repoflt" class="repoflt" hidden><span id="reponame"></span><button id="clrrepo" title="x">✕</button></span>
<span class="count" id="count"></span><button id="reset" class="reset">{_L('Wis filters', 'Clear filters')}</button></div>"""
    if solution_html is None:
        solution_html = f"""
<section id="oplossing" class="sol"><div class="kick">{_L('Oplossing', 'Solution')}</div>
<h2>{_L('SAAF Guard: deze fouten tegenhouden tijdens het bouwen', 'SAAF Guard: stop these flaws while building')}</h2>
<div class="layers">
<div class="layer"><h4>1 · {_L('Skill met negen bouwregels', 'Skill with nine build rules')}</h4><p>{_L('De coding-agent volgt de regels vóór hij code schrijft.', 'The coding agent follows the rules before writing code.')}</p><code>skills/saaf-guard/SKILL.md</code></div>
<div class="layer"><h4>2 · {_L('Veilige bouwstenen', 'Safe building blocks')}</h4><p><code>fence()</code> · <code>rollup()</code> · <code>within_tolerance()</code> · <code>is_grounded()</code> · <code>safe_cell()</code> · <code>AuditTrail</code></p><code>saaf_guard/safe.py</code></div>
<div class="layer"><h4>3 · {_L('CI-check', 'CI check')}</h4><p>{_L('17 regels + sleutelscan over de git-geschiedenis; build faalt op high.', '17 rules + key scan over git history; build fails on high.')}</p><code>python -m saaf_guard.check . --history</code></div>
</div></section>"""
    sub = subtitle or (f'{len(findings)} bevindingen in {n_aff} repositories ({len(repo_names)} gescand), gegroepeerd naar onderliggende oorzaak. Statische, lokale review; geen live systemen getest, geen sleutelwaarden opgenomen.',
                       f'{len(findings)} findings in {n_aff} repositories ({len(repo_names)} scanned), grouped by root cause. Static, local review; no live systems tested, no key values included.')

    issues_html = _issues_section(findings, issues_plan, bar) if issues_plan else ""
    extra = extra_sections or []
    extra_nav = "".join(f'<a href="#{sid}">{_L(ln, le)}</a>' for sid, ln, le, _ in extra)
    extra_html = "".join(h for *_, h in extra)
    rel = related or []
    rel_nav = "".join(f'<a class="rel" href="{esc(h)}">↗ {_L(esc(ln), esc(le))}</a>' for h, ln, le, _, _ in rel)
    rel_box = "".join(f'<div class="relbox"><b>{_L("Zie ook", "See also")}:</b> <a href="{esc(h)}">{_L(esc(ln), esc(le))}</a> — '
                      f'{_L(esc(un), esc(ue))}</div>' for h, ln, le, un, ue in rel)
    css = _CSS + extra_css + ".top-nav a.rel{background:rgba(255,255,255,.14)}.relbox{background:#e3f4f1;border:1px solid #bfe3dc;border-radius:10px;padding:10px 14px;margin:0 0 14px;font-size:13px}.relbox a{color:var(--acc);font-weight:600}"
    page = f"""<!DOCTYPE html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><style>{css}</style></head><body class="lang-{lang}">
<header><div class="langsw"><button data-l="nl">NL</button><button data-l="en">EN</button></div>
<h1>{esc(title)}</h1><p>{_L(esc(sub[0]), esc(sub[1]))}</p>
<nav class="top-nav"><a href="#repos">{_L('Per repository', 'Per repository')}</a><a href="#oorzaken">{_L('Per oorzaak', 'By root cause')}</a>{('<a href="#meldingen">' + _L('Meldingen', 'Reporting') + '</a>') if issues_html else ''}<a href="#oplossing">{_L('Oplossing', 'Solution')}</a>{extra_nav}{rel_nav}</nav></header>
<main><div class="kpis">{kpi(len(findings), 'bevindingen', 'findings')}{kpi(n_aff, 'repos geraakt', 'repos affected')}{kpi(tot['Critical'], 'Critical', 'Critical', f' style="color:{COL["Critical"]}"')}{kpi(tot['High'], 'High', 'High', f' style="color:{COL["High"]}"')}{kpi(tot['Medium'], 'Medium', 'Medium', f' style="color:{COL["Medium"]}"')}{kpi(tot['Low'], 'Low', 'Low')}{kpi(ver, 'geverifieerd', 'verified')}{kpi(auto or sum(bool(f.get('caught')) for f in findings), 'automatisch / CI', 'automatic / CI', ' style="color:var(--acc)"')}</div>
{rel_box}{filterbar}
{repo_table}
<h3 class="sec" id="oorzaken">{_L('Oorzaken', 'Root causes')}</h3><div class="ovs">{ov}</div>
<h3 class="sec">{_L('Eerst oplossen: Critical en High', 'Fix first: Critical and High')} ({len(top)})</h3>
<div class="tblwrap"><table class="top"><tr><th>{_L('Ernst', 'Severity')}</th><th>Repo</th><th>{_L('Bevinding', 'Finding')}</th></tr>{toprows}</table></div>
<div id="results">{''.join(sec)}</div><p class="empty" id="empty" hidden>{_L('Geen bevindingen voor deze zoekopdracht.', 'No findings match this search.')}</p>
{issues_html}
{solution_html}
{extra_html}
<p class="note">{_L('Klik op een repo-naam om alleen die repo te tonen; klik op een bevinding voor details en de andere repos met dezelfde oorzaak. "Geverifieerd" = codepad nagelopen of lokaal gereproduceerd zonder netwerk. "Automatisch" = statische heuristiek van SAAF Guard; handmatig bevestigen.',
                     'Click a repo name to show only that repo; click a finding for details and the other repos with the same root cause. "Verified" = code path traced or reproduced locally without network. "Automatic" = SAAF Guard static heuristic; confirm manually.')}</p>
</main><script>{_JS.replace("__LANG__", lang)}</script></body></html>"""
    if SECRET.search(page):
        raise ValueError("Sleutelachtige waarde in rapport — afgebroken")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(page)


_CSS = """
:root{--bg:#f4f6f8;--s:#fff;--s2:#eef2f5;--b:#d9e0e7;--t:#14202e;--d:#566475;--dd:#93a0ae;--ink:#1d3557;--acc:#0e7c72}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:80px}body{margin:0;background:var(--bg);color:var(--t);font:14px/1.55 system-ui,'Segoe UI',sans-serif}
body.lang-nl .en,body.lang-en .nl{display:none}
header{background:var(--ink);color:#fff;padding:24px 36px 56px;position:relative}header h1{margin:0;font:600 26px Georgia,serif}header p{margin:6px 0 0;color:#c5d1df;max-width:900px}
.kpis.inline{margin:6px 0 10px}.kpis.inline .kpi{box-shadow:none}.pubgrid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.pubrepo h4{margin:0 0 6px}@media(max-width:900px){.pubgrid{grid-template-columns:1fr}}
.langsw{position:absolute;top:22px;right:36px;display:flex;border:1px solid rgba(255,255,255,.35);border-radius:8px;overflow:hidden}
.langsw button{background:transparent;color:#fff;border:0;padding:6px 12px;cursor:pointer;font:600 12px system-ui}.langsw button.on{background:rgba(255,255,255,.18)}
.top-nav{display:flex;gap:8px;margin-top:14px}.top-nav a{color:#fff;text-decoration:none;border:1px solid rgba(255,255,255,.3);border-radius:8px;padding:5px 11px;font-size:12.5px}.top-nav a:hover{background:rgba(255,255,255,.1)}
main{max-width:1180px;margin:0 auto;padding:0 36px 70px}
.kpis{display:flex;gap:10px;flex-wrap:wrap;margin:-36px 0 18px;position:relative;z-index:2}.kpi{background:var(--s);border:1px solid var(--b);border-radius:12px;padding:10px 16px;min-width:105px;box-shadow:0 4px 14px rgba(0,0,0,.06)}
.kpi .v{font:600 24px Georgia,serif}.kpi .l{color:var(--d);font-size:12px}
.fbar{position:sticky;top:0;z-index:5;display:flex;flex-wrap:wrap;gap:8px;align-items:center;background:rgba(244,246,248,.96);backdrop-filter:blur(4px);padding:10px 0;border-bottom:1px solid var(--b);margin-bottom:6px}
.fbar input{flex:1;min-width:220px;padding:8px 12px;border:1px solid var(--b);border-radius:8px;font:14px system-ui;background:var(--s)}
.fbar input:focus{outline:2px solid var(--acc);border-color:transparent}
.sevs{display:flex;gap:4px;flex-wrap:wrap}.sevf{border:1px solid color-mix(in srgb,var(--c) 40%,transparent);color:var(--c);background:var(--s);border-radius:999px;padding:4px 10px;font:600 12px system-ui;cursor:pointer}
.sevf.on{background:var(--c);color:#fff}
.repoflt{display:inline-flex;align-items:center;gap:6px;background:var(--acc);color:#fff;border-radius:999px;padding:4px 6px 4px 12px;font:600 12px ui-monospace,Consolas,monospace}
.repoflt[hidden]{display:none}.repoflt button{border:0;background:rgba(255,255,255,.25);color:#fff;border-radius:999px;width:20px;height:20px;cursor:pointer}
.count{color:var(--d);font-size:12.5px}.reset{border:1px solid var(--b);background:var(--s);border-radius:8px;padding:5px 10px;cursor:pointer;font-size:12px}
h3.sec{font:600 18px Georgia,serif;margin:22px 0 10px}
.card{background:var(--s);border:1px solid var(--b);border-radius:14px;padding:6px 18px 12px;margin-top:14px}.cardh{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap}.cardh h3{margin:12px 0 8px}
.tblwrap{overflow:auto;max-height:520px}
table.rt,table.top{width:100%;border-collapse:collapse}table.rt th,table.rt td,table.top td,table.top th{text-align:left;padding:6px 8px;border-top:1px solid var(--s2);font-size:13px;vertical-align:middle}
table.rt th,table.top th{background:var(--s2);color:var(--d);position:sticky;top:0}table.rt .n{text-align:center;width:44px}.tot{font-weight:700}
tr.rrow,tr.go{cursor:pointer}tr.rrow:hover,tr.go:hover{background:#f3faf9}tr.rrow.sel{background:#e3f4f1}tr.rrow.zero{color:var(--dd)}
.cz{display:inline-block;font-size:11px;background:var(--s2);border-radius:999px;padding:1px 7px;margin:1px 3px 1px 0;color:var(--d)}
.muted{color:var(--dd);font-size:12px}.sm{font-size:11px;margin-top:3px}
table.top{background:var(--s);border:1px solid var(--b)}
.ovs{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.ov{display:flex;gap:12px;align-items:center;background:var(--s);border:1px solid var(--b);border-radius:10px;padding:10px 12px;text-decoration:none;color:inherit}
.ov:hover{border-color:var(--acc)}.ovn{font:600 22px Georgia,serif;min-width:30px;text-align:center}.ovt{font-weight:600;font-size:13px;margin-bottom:5px}
.bar{display:flex;height:9px;border-radius:5px;overflow:hidden;background:var(--s2);margin:8px 0;max-width:520px}.bar span{display:block;height:100%}
.grp{background:var(--s);border:1px solid var(--b);border-radius:14px;margin-top:18px;padding:20px 22px}.gh{display:flex;gap:16px}.num{font:600 28px Georgia,serif;color:var(--dd)}.gt{flex:1}
.gh h2{margin:0;font:600 20px Georgia,serif}.cnt{font:500 13px system-ui;background:var(--s2);border-radius:999px;padding:2px 9px;color:var(--d)}
.pills{display:flex;flex-wrap:wrap;gap:6px;align-items:center}.pill{font-size:11.5px;padding:2px 8px;border-radius:999px;border:1px solid color-mix(in srgb,var(--c) 35%,transparent);color:var(--c);background:color-mix(in srgb,var(--c) 8%,transparent);text-decoration:none}.pill.rule{--c:var(--acc)}
.also{display:flex;flex-wrap:wrap;gap:5px;align-items:center;margin-top:8px;font-size:12px;color:var(--d)}.also.top{margin-top:10px}
.rchip{border:1px solid var(--b);background:var(--s);border-radius:999px;padding:2px 9px;font:12px ui-monospace,Consolas,monospace;cursor:pointer;color:var(--t)}
.rchip b{color:var(--acc);font-family:system-ui}.rchip:hover{border-color:var(--acc)}.rchip.cur{background:var(--s2)}
.three{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:14px 0 8px;padding:14px;background:var(--s2);border-radius:10px}.three h4{margin:0 0 4px;font-size:11.5px;text-transform:uppercase;letter-spacing:.05em;color:var(--d)}.three p{margin:0;font-size:13px}
details.f{border-top:1px solid var(--s2)}details.f summary{list-style:none;cursor:pointer;display:grid;grid-template-columns:96px 220px 1fr auto;gap:10px;align-items:center;padding:8px 2px}details.f summary::-webkit-details-marker{display:none}
details.f summary:hover{background:#fafbfc}details.f.flash{animation:flash 1.6s}@keyframes flash{0%{background:#d9f2ee}100%{background:transparent}}
.sev{font-size:11.5px;font-weight:600;color:#fff;background:var(--c);border-radius:6px;padding:2px 8px;text-align:center}
.repo{font:12px ui-monospace,Consolas,monospace;color:var(--d);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
button.rlink{border:0;background:none;text-align:left;cursor:pointer;padding:0}button.rlink:hover{color:var(--acc);text-decoration:underline}.t{font-weight:500}
.tags{display:flex;gap:4px}.tag{font-size:10.5px;border:1px solid var(--b);color:var(--dd);border-radius:999px;padding:1px 7px;white-space:nowrap}.tag.ok{color:#1a9e6e}.tag.g{color:var(--acc)}
.body{padding:4px 4px 12px 106px;font-size:13px;color:#2a3746}.body p{margin:6px 0}.loc{font:12px ui-monospace,Consolas,monospace;color:var(--d)}
mark{background:#fff3b0;padding:0 1px;border-radius:2px}
.none{display:none;color:var(--dd);font-size:12.5px;margin:10px 0 0}.grp.filtered .none{display:block}.grp.hide{display:none}.empty{color:var(--d);text-align:center;padding:24px}
.sol{margin-top:40px;border-top:3px solid var(--acc);padding-top:12px}.kick{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--acc);font-weight:600}.sol h2{font:600 22px Georgia,serif;margin:4px 0 12px}
.layers{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.layer{background:var(--s);border:1px solid var(--b);border-top:4px solid var(--acc);border-radius:12px;padding:14px}.layer h4{margin:0 0 6px}.layer p{margin:0 0 8px;font-size:13px}
code{font:12px ui-monospace,Consolas,monospace;background:var(--s2);border-radius:4px;padding:1px 5px}.note{color:var(--d);font-size:12.5px;margin-top:28px}
@media(max-width:900px){.ovs,.three,.layers{grid-template-columns:1fr}details.f summary{grid-template-columns:80px 1fr}.repo,.tags{display:none}.body{padding-left:4px}}
@media print{.fbar,.langsw{display:none}details.f{break-inside:avoid}}
"""

_JS = r"""
const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
const st={q:'',sev:new Set(),repo:''};
const PH={nl:'Zoek op repo, titel, bestand of trefwoord (bijv. NaN, CORS, prompt)…',en:'Search repo, title, file or keyword (e.g. NaN, CORS, prompt)…'};
let lang='__LANG__';
function setLang(l){lang=l;document.body.className='lang-'+l;document.documentElement.lang=l;
  $$('.langsw button').forEach(b=>b.classList.toggle('on',b.dataset.l===l));$('#q').placeholder=PH[l];
  try{localStorage.setItem('saafLang',l)}catch(e){};apply()}
function apply(){
  const q=st.q.trim().toLowerCase(),terms=q?q.split(/\s+/):[];let n=0;
  $$('details.f').forEach(d=>{
    const ok=terms.every(t=>d.dataset.s.includes(t))&&(!st.sev.size||st.sev.has(d.dataset.sev))&&(!st.repo||d.dataset.repo===st.repo);
    d.hidden=!ok;if(ok)n++;
  });
  const active=!!(terms.length||st.sev.size||st.repo);
  $$('section.grp').forEach(g=>{const v=g.querySelectorAll('details.f:not([hidden])').length;
    g.classList.toggle('hide',active&&v===0);g.classList.toggle('filtered',active&&v===0);
    const c=g.querySelector('.cnt');if(c){c.dataset.all=c.dataset.all||c.textContent;c.textContent=active?v+' / '+c.dataset.all:c.dataset.all}});
  $$('tr.rrow').forEach(r=>{r.classList.toggle('sel',r.dataset.repo===st.repo);
    r.hidden=!!(terms.length&&!st.repo&&!terms.every(t=>r.dataset.s.includes(t))&&!$$('details.f:not([hidden])').some(d=>d.dataset.repo===r.dataset.repo))});
  $$('.sevf').forEach(b=>b.classList.toggle('on',st.sev.has(b.dataset.sev)));
  const rf=$('#repoflt');rf.hidden=!st.repo;$('#reponame').textContent=st.repo;
  const total=$$('details.f').length;
  $('#count').textContent=active?(lang==='en'?`${n} of ${total} findings`:`${n} van ${total} bevindingen`):(lang==='en'?`${total} findings`:`${total} bevindingen`);
  $('#empty').hidden=!(active&&n===0);
  try{const h=new URLSearchParams();if(st.q)h.set('q',st.q);if(st.repo)h.set('repo',st.repo);if(st.sev.size)h.set('sev',[...st.sev].join(','));
    history.replaceState(null,'',h.toString()?'#'+h.toString():location.pathname)}catch(e){}
}
function setRepo(r,scroll){st.repo=(st.repo===r&&!scroll)?'':r;apply();if(st.repo&&scroll!==false)$('#oorzaken').scrollIntoView()}
document.addEventListener('click',e=>{
  if(e.target.closest('a[href^="http"]'))return;  // externe link (issue) gewoon openen
  const rb=e.target.closest('[data-repo]');
  if(rb&&(rb.classList.contains('rchip')||rb.classList.contains('rlink')||rb.classList.contains('rrow'))){e.preventDefault();e.stopPropagation();setRepo(rb.dataset.repo,true);return}
  const go=e.target.closest('tr.go');
  if(go){const d=document.getElementById(go.dataset.go);st.q='';$('#q').value='';st.sev.clear();st.repo='';apply();d.open=true;d.scrollIntoView({block:'center'});d.classList.add('flash');setTimeout(()=>d.classList.remove('flash'),1700)}
},true);
$$('.sevf').forEach(b=>b.onclick=()=>{st.sev.has(b.dataset.sev)?st.sev.delete(b.dataset.sev):st.sev.add(b.dataset.sev);apply()});
let tm;$('#q').addEventListener('input',e=>{clearTimeout(tm);tm=setTimeout(()=>{st.q=e.target.value;apply()},120)});
$('#q').addEventListener('keydown',e=>{if(e.key==='Escape'){e.target.value='';st.q='';apply()}});
$('#clrrepo').onclick=()=>{st.repo='';apply()};
$('#reset').onclick=()=>{st.q='';$('#q').value='';st.sev.clear();st.repo='';apply()};
$$('.langsw button').forEach(b=>b.onclick=()=>setLang(b.dataset.l));
document.addEventListener('keydown',e=>{if(e.key==='/'&&document.activeElement!==$('#q')){e.preventDefault();$('#q').focus()}});
try{const h=new URLSearchParams(location.hash.slice(1));if(h.get('q')){st.q=h.get('q');$('#q').value=st.q}if(h.get('repo'))st.repo=h.get('repo');(h.get('sev')||'').split(',').filter(Boolean).forEach(s=>st.sev.add(s))}catch(e){}
let s0=null;try{s0=localStorage.getItem('saafLang')}catch(e){}setLang(s0||lang);
"""


def _issues_section(findings: list[dict], plan: list[dict], bar) -> str:
    """Hoofdstuk 'Gemeld in de online repos': resultaat van saaf_guard.issues per repo + niet-gemelde (publieke) repos."""
    esc = html.escape
    by_repo = {}
    for f in findings:
        by_repo.setdefault(f["repo"], []).append(f)
    done = [p for p in plan if p.get("url")]
    skipped = [p for p in plan if str(p.get("action", "")).startswith("OVERGESLAGEN")]
    errors = [p for p in plan if str(p.get("result", "")).startswith("FOUT") or p.get("action") == "fout"]

    def counts(rp):
        it = by_repo.get(rp, [])
        return "".join(f'<td class="n">{sum(f["risk_rating"] == k for f in it) or ""}</td>'
                       for k in ("Critical", "High", "Medium", "Low"))

    red = 'style="color:#c0384a;border-color:#e8b3bb"'
    rows = ""
    for p in sorted(done, key=lambda x: -x["n"]):
        num = p.get("number") or p["url"].rsplit("/", 1)[-1]
        rows += (f'<tr class="rrow" data-repo="{esc(p["repo"])}" data-s="{esc(p["repo"].lower())}">'
                 f'<td class="repo">{esc(p["repo"])}</td><td>{_L("privé", "private")}</td>'
                 f'<td class="n tot">{p["n"]}</td>{counts(p["repo"])}'
                 f'<td><a href="{esc(p["url"])}" target="_blank" rel="noopener">#{esc(str(num))} ↗</a></td>'
                 f'<td><span class="tag ok">{_L("gemeld als issue", "reported as issue")}</span></td></tr>')
    for p in sorted(skipped, key=lambda x: -x["n"]):
        rows += (f'<tr class="rrow" data-repo="{esc(p["repo"])}" data-s="{esc(p["repo"].lower())}">'
                 f'<td class="repo">{esc(p["repo"])}</td><td><b>{_L("publiek", "public")}</b></td>'
                 f'<td class="n tot">{p["n"]}</td>{counts(p["repo"])}<td>—</td>'
                 f'<td><span class="tag" {red}>{_L("niet gemeld: actie nodig", "not reported: action needed")}</span></td></tr>')

    blocks = []
    for p in sorted(skipped, key=lambda x: -x["n"]):
        items = sorted(by_repo.get(p["repo"], []), key=lambda r: RATINGS.index(r["risk_rating"]))
        lis = "".join(f'<tr class="go" data-go="{r["_id"]}"><td><span class="sev" style="--c:{COL[r["risk_rating"]]}">'
                      f'{r["risk_rating"]}</span></td><td>{esc(r["title"])}</td></tr>' for r in items)
        blocks.append(f'<div class="pubrepo"><h4><button class="rchip" data-repo="{esc(p["repo"])}">{esc(p["repo"])} '
                      f'<b>{p["n"]}</b></button></h4><table class="top">{lis}</table></div>')
    n_done = sum(p["n"] for p in done)
    n_skip = sum(p["n"] for p in skipped)
    err_kpi = (f'<div class="kpi"><div class="v" style="color:#c0384a">{len(errors)}</div>'
               f'<div class="l">{_L("fouten", "errors")}</div></div>') if errors else ""
    advice = _L(
        "Deze repos zijn <b>publiek</b>. Een publiek issue zou een nog open lek voor iedereen leesbaar maken, dus de agent "
        "heeft hier bewust niets gemeld. Oplossing: een beheerder zet <b>Private Vulnerability Reporting</b> aan "
        "(Settings → Security); daarna meldt dezelfde agent de bevindingen privé. Tot die tijd: benader de beheerders "
        "rechtstreeks. Klik op een bevinding om de details te openen.",
        "These repos are <b>public</b>. A public issue would make a still-open weakness readable for everyone, so the agent "
        "deliberately reported nothing here. Fix: a maintainer enables <b>Private Vulnerability Reporting</b> "
        "(Settings → Security); the same agent then reports privately. Until then: contact the maintainers directly. "
        "Click a finding to open its details.")
    return f"""
<section id="meldingen" class="card"><div class="cardh"><h3 class="sec">{_L('Gemeld in de online repos (GitHub)', 'Reported in the online repos (GitHub)')}</h3>
<span class="muted">{_L('resultaat van de issues-agent (saaf_guard.issues)', 'result of the issues agent (saaf_guard.issues)')}</span></div>
<div class="kpis inline">
 <div class="kpi"><div class="v" style="color:var(--acc)">{len(done)}</div><div class="l">{_L('issues in privé-repos', 'issues in private repos')}</div></div>
 <div class="kpi"><div class="v">{n_done}</div><div class="l">{_L('bevindingen gemeld', 'findings reported')}</div></div>
 <div class="kpi"><div class="v" style="color:#c0384a">{len(skipped)}</div><div class="l">{_L('publieke repos niet gemeld', 'public repos not reported')}</div></div>
 <div class="kpi"><div class="v" style="color:#c0384a">{n_skip}</div><div class="l">{_L('bevindingen nog te melden', 'findings still to report')}</div></div>
 {err_kpi}
</div>
<p class="muted">{_L('Eén issue per repo met een afvinklijst; een volgende scan werkt hetzelfde issue bij (onzichtbare marker). Klik op een repo om de bevindingen te filteren, of op het nummer om het issue op GitHub te openen.',
                     'One issue per repo with a checklist; a later scan updates the same issue (hidden marker). Click a repo to filter its findings, or the number to open the issue on GitHub.')}</p>
<div class="tblwrap"><table class="rt"><thead><tr><th>Repo</th><th>{_L('Zichtbaarheid', 'Visibility')}</th><th class="n">{_L('Totaal', 'Total')}</th><th class="n">C</th><th class="n">H</th><th class="n">M</th><th class="n">L</th><th>Issue</th><th>Status</th></tr></thead>
<tbody>{rows}</tbody></table></div>
<h3 class="sec">{_L('Niet online gemeld: actie nodig', 'Not reported online: action needed')} ({len(skipped)} repos, {n_skip} {_L('bevindingen', 'findings')})</h3>
<div class="relbox" style="background:#fdf1f2;border-color:#f0c9cf">{advice}</div>
<div class="pubgrid">{''.join(blocks)}</div></section>"""
