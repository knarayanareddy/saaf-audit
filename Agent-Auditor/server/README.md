# Agent Auditor — Server

Lichte FastAPI-server die de browser-UI (`../dashboard.html` + `../audit-criteria-sheet.html`) koppelt aan Claude én aan de GitHub-API.

| | |
|---|---|
| Tool-versie | `0.5.0` |
| Build | `2026-06-17-ac-summary-sync` |
| Poort | `127.0.0.1:8765` (localhost-only) |
| Auto-docs | <http://127.0.0.1:8765/docs> |

## Vereisten

1. **Python 3.10+**
2. **Claude Code** geïnstalleerd en `claude login` gedaan — de Claude Agent SDK hergebruikt deze sessie.
3. **GitHub-toegang** voor de doel-repos:
   - **Read-only flow** (dashboard browse, audit-trail, evaluate): `gh auth login` met `read:org` is genoeg voor publieke repos; voor private repos ook `repo`.
   - **Write flow** (audit-branch + commit van `AUDIT_FIXES.md`): vereist `repo`-scope én collaborator-rechten op de target-repo.

## Installatie

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Starten

```powershell
.venv\Scripts\python server.py
```

De server luistert standaard op `http://127.0.0.1:8765`. Hij start in een **onge­configureerde** toestand: er moet eerst een target geladen worden (via dashboard → "Add organisatie" of via de criteria-sheet → "Apply target").

## Endpoint-overzicht

### Health & target

| Method | Pad | Doel |
|---|---|---|
| `GET`  | `/ping`            | versie + build + routes + integrity-hashes + actieve target |
| `POST` | `/configure-target`| `{owner, repo, ref?, files?}` — resolved ref naar SHA, fetch bundle, schrijft `repo.lock.json` |
| `POST` | `/list-commits`    | recente commits voor de picker |
| `POST` | `/reload`          | bundle opnieuw ophalen op dezelfde target |
| `POST` | `/scan-secrets`    | secrets-scan losstaand op huidige bundle |

### AI-evaluatie

| Method | Pad | Doel |
|---|---|---|
| `POST` | `/evaluate`        | één acceptance criterium door Claude laten beoordelen; evidence wordt server-side gevalideerd |
| `POST` | `/audit-trail`     | issues × commits × AI-adequaatheid; ook secrets en orphan-AI-pass; updatet dashboard-metrics |

### Multi-org dashboard

| Method | Pad | Doel |
|---|---|---|
| `GET`  | `/orgs`                          | lijst alle bekende orgs + repos + tags + metrics |
| `POST` | `/orgs`                          | `{owner, classify, model}` — voegt org toe; classificeert elke README via Claude |
| `DELETE` | `/orgs/{owner}`                | verwijdert org uit dashboard-state |
| `POST` | `/orgs/{owner}/rescan`           | her-classificeer non-manual repos |
| `POST` | `/repos/{owner}/{repo}/tag`      | `{is_agent, source, reasoning}` — handmatige tag-override |
| `POST` | `/repos/{owner}/{repo}/classify` | enkele repo herclassificeren |
| `POST` | `/repos/{owner}/{repo}/audit`    | light-scan zonder Claude per issue (counts + secrets) — voor de "Run audit"-knop |
| `POST` | `/repos/{owner}/{repo}/ac-summary` | A2 acceptance-criteria scoring uit de criteria-sheet — pusht pass/fail/na/open counts + verdict zodat het dashboard de echte score laat zien (D-6) |

### Audit-branch flow

| Method | Pad | Doel |
|---|---|---|
| `POST` | `/repos/{owner}/{repo}/audit-branch` | `{reviewer, from_ref?, findings, generate_fixes, model}` — maakt branch `auditedby_<reviewer-slug>_<YYYY-MM-DD>`, commits `AUDIT_FIXES.md` met Claude-fix-voorstellen |

### Audit log

| Method | Pad | Doel |
|---|---|---|
| `POST` | `/log`            | append browser-event aan `actions.log.jsonl` (whitelist op `type`) |
| `GET`  | `/log?limit=N`    | tail van het auditor-actie-log |

## Audit-defensibility per endpoint

- `/configure-target` resolved de gebruikersinput (branch/tag/SHA) naar een concrete SHA en cached die in `TARGET["sha"]`. Daarna refereren alle endpoints aan precies die commit.
- `repo.lock.json` wordt naast de server geschreven met de complete target-staat.
- `/audit-trail` heeft een cache-key over `(commit, model, prompt_hash, bundle_hash, exclude_files, wow_hash)` — wijzigt één van die velden, dan vervalt de cache automatisch.
- `/evaluate` valideert per evidence-quote substring-match in de bundle; hallucinaties degraderen pass/fail naar `unknown` met expliciete reden.
- `/audit-branch` log een `audit_branch_created`-event in `actions.log.jsonl` met reviewer + branch + commit-base + #proposals.
- `/orgs` POST en `/repos/.../tag` schrijven `manual_notes` per repo met timestamp + reasoning.

## Agent-classifier (D-1)

Bij `POST /orgs?classify=true` fetcht de server voor elke repo de README via de GitHub Contents-API en stuurt hem naar Claude met `SYSTEM_PROMPT_CLASSIFY`. Output:

```json
{
  "verdict": "agent" | "not_agent" | "unclear",
  "reasoning": "1-2 zinnen NL",
  "agent_signals": ["gebruikt anthropic SDK", "heeft systeemprompt", "CLI met taak X"]
}
```

Manual tags (`tag_source: "manual"`) worden gerespecteerd: een rescan overschrijft ze niet.

## Way-of-working override (F-2)

Zowel `/evaluate` als `/audit-trail` accepteren een `way_of_working: str` veld. De inhoud wordt geïnjecteerd in een `<team_way_of_working>` XML-blok in de prompt, vóór de repo-bundel. `wow_hash` zit in de cache-key zodat een nieuw kader een verse AI-call uitlokt; de UI markeert het in suggesties met een `WoW`-badge.

## Secrets-scan (F-1)

`scan_bundle_for_secrets()` scant alle bundle-bestanden op:

- Anthropic / OpenAI / GitHub / AWS / Slack / Google API-keys
- PEM private keys (RSA, EC, OPENSSH, DSA, PGP)
- Generieke hardcoded credentials (`api_key = "..."`)
- Mongo / Postgres connection-strings met password

False-positive-onderdrukking:

- **Path-patronen**: `*example*`, `*.sample`, `*.template`, `/tests/`, `/fixtures/`
- **Placeholder-markers** in de regel zelf: `your-`, `xxxx`, `REPLACE_ME`, `EXAMPLE`, `FAKE`, `DUMMY`, `example.com`

Findings die door deze heuristiek matchen worden naar `severity: low` gedegradeerd; de UI rendert ze met een gele "voorbeeld/placeholder" markering.

## Audit-branch met `AUDIT_FIXES.md` (D-5)

`POST /repos/{o}/{r}/audit-branch` doet vier stappen:

1. **Resolve `from_ref`** naar SHA (default = repo's default branch).
2. **Branch aanmaken** via `POST /repos/{o}/{r}/git/refs` met `ref: refs/heads/auditedby_<slug>_<YYYY-MM-DD>`. Bij 422 (bestaat al) hergebruiken we de branch.
3. **Per finding** een fix-voorstel vragen aan Claude met `SYSTEM_PROMPT_AUTOFIX`. Output per voorstel: `title, root_cause, proposed_change, files_likely_affected, verification, complexity ∈ {trivial, moderate, research}`.
4. **AUDIT_FIXES.md committen** naar de branch via de Contents-API.

De auditor zelf raakt **nooit `main`** — die blijft van het dev-team. De branch ligt klaar voor review; het dev-team beslist over implementatie.

**Vereiste rechten** voor stap 2 en 4: token met `repo`-scope én collaborator op de target-repo. Zonder rechten krijgt de UI een duidelijke 403-foutmelding met advies.

## Provenance — welke commit heb je beoordeeld?

Bij elke `POST /configure-target` schrijft de server **`../repo.lock.json`** met commit-hash, branch, remote, datum, auteur, commit-message. De webapp leest het automatisch en toont de commit in:

- de pill rechts naast de titel (`main · 152b6df`);
- het metadata-veld "Agent-versie / commit" (alleen als dat nog leeg is);
- het provenance-blok in sectie 0;
- de caption van elke AI-suggestie (`commit 152b6df`);
- en daarmee óók in de geëxporteerde PDF.

De commit-hash gaat tevens mee in de prompt naar Claude, zodat de AI evidence-verwijzingen scopet op die specifieke versie van de agent.

## Troubleshooting

| Foutmelding | Oorzaak / fix |
|---|---|
| `Geen target geconfigureerd` | Vanuit dashboard: voeg eerst een org toe. Vanuit criteria-sheet: drawer → Apply target. |
| `Server draait, maar mist het /orgs endpoint` | Server is een oudere build. Ctrl+C + `python server.py` opnieuw. |
| `Claude Agent SDK fout: ...` | Check `claude --version` en `claude login`. SDK gebruikt dezelfde auth. |
| `GitHub API 403` op classifier | Rate-limit of geen toegang. `gh auth login` met `read:org` + (private) `repo`. |
| `GitHub API 403` op audit-branch | Token mist `repo`-scope of je bent geen collaborator op de target-repo. |
| `GitHub API 404 — Repo niet vindbaar` | Private repo zonder geldige token. |
| CORS-fout in browser-console | Server staat uit, of luistert op een ander adres dan ingevuld in de drawer. |
| Lege bundle bij target-load | Auto-discover-patronen pakken niets in jouw repo; geef expliciet `files` mee in `configure-target` of breid `DEFAULT_FILE_PATTERNS` uit. |
| Branch-aanmaken levert 422 op | Branch met die naam bestaat al — server hergebruikt automatisch. |

## Configuratie

Geen `.env` nodig. Optionele environment-variables:

- `GITHUB_TOKEN` / `GH_TOKEN` — overrides `gh auth token` indien aanwezig.

Bestanden die de server schrijft (allemaal gitignored):

- `../repo.lock.json` — actieve target-snapshot
- `../audit-trail.cache.json` — laatste audit-trail-resultaat
- `../actions.log.jsonl` — append-only auditor-actie-log
- `../orgs.json` — multi-org dashboard-state
