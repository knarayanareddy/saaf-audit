# Pattern scan (10 Nov 2026)

Read-only grep across the 47 repos. I skipped .venv, node_modules, .git, dist, build, .next, our `four_eyes` additions, `agents/approval_seal.py` and test files. I checked each hit by reading the code around it. I ran no code and made no network calls. Output: `findings/new-patterns.csv`.

## What I searched

- **Python:** `shell=True`, `os.system`, `subprocess.*`, `eval`/`exec`, `pickle`, `yaml.load`, `torch.load`, `marshal`, `verify=False`, `0.0.0.0`, `allow_origins`/`CORS(`, `debug=True`, `send_file`/`FileResponse`, `|safe`/`Markup(`/bare `Template(`, SQL built with f-strings or `+`, `urlopen`/`requests.get(url`, and CSV/Excel writers (`csv.writer`, `DictWriter`, `to_csv`, openpyxl `ws.cell`/`ws.append`).
- **JS/TS/HTML:** `dangerouslySetInnerHTML`, `innerHTML =`, `insertAdjacentHTML`, `eval(`, `new Function(`, `NEXT_PUBLIC_*KEY|SECRET|TOKEN`, `Access-Control-Allow-Origin`, CDN `<script src>` with no version or integrity, and every Next.js `app/api/**/route.ts`.

## Counts

- About 25 candidates looked at in detail. The pattern hits were in the hundreds, mostly `innerHTML` lines.
- **12 confirmed, all new.** None duplicates a row in RAG-TAG-findings.csv.
  - High: 5
  - Medium: 4
  - Low: 3

## False positives I rejected

- **FieldworkOrchestration `agents/cli_runner.py` `shell=True`:** commands come from an allowlist and every parameter is wrapped in `shlex.quote`. The `/static/{filename}` and `/{page}.html` routes cannot take a `/`, and document downloads check the resolved path with `.resolve()` and `parents`.
- **Track-2---IAM-final `bart/web/app.py` downloads:** run_id and filename are cleaned with a regex and `_sanitize_filename`.
- **Finding-analysis `/download/<upload_id>`:** uses `secure_filename`.
- **PBC-Assistant upload:** has an extension allowlist, a 50 MB cap and filename cleaning. The `onclick` handlers use only server-generated IDs.
- **Vendor_Guard CSV and Excel output:** already guarded by `synthesizer/sanitize.py` (`csv_safe`, `set_text_cell`).
- **joiners-movers-leavers-agent `claude_runner.py`:** runs the Claude CLI with `--tools ""` and an argument list, and the server binds to 127.0.0.1.
- **Executive-Summary-Writer `/api/agent/[...path]`:** path allowlist by regex, origin check, size cap and a fixed upstream. This is good practice.
- **saaf-portal:**
  - `layout.tsx` `dangerouslySetInnerHTML` is a constant theme script.
  - The admin routes check the username.
  - repo-claims checks team membership.
- **Stress-test `web.py` git clone:** a local Streamlit scanner where local paths are intended input.
- **SAAF-Project leaderboard.html:** PR titles are escaped. Plan filenames are not, but they only come from merged PRs, so I did not report it.
- **Team-HighTable extension:** all model fields go through `escapeHtml`. A `javascript:` href is possible in theory, but I could not confirm that the URL comes from the model.
- **Not found anywhere:** `pickle`, `yaml.load`, `torch.load`, `eval`/`exec` on input, `verify=False`, SQL string building, `NEXT_PUBLIC_` secrets.

## Not done

- FieldworkOrchestration `quality.verdict` is inserted into the page unescaped. I could not confirm in time whether it is schema-validated, so it is not reported.
- Agent-Auditor `dashboard.html` org cards were not read in full.
- The Excel exports in SAAF-Project `audit_program_to_excel.py` and Team-HighTable `build_workpaper.py` were not checked (they are scripts).

No repo file I read contained instructions aimed at an AI.
