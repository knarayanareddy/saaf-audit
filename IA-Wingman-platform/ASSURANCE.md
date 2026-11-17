# AI Assurance Center

The Assurance Center makes the platform's own security posture visible and
testable — for an audit tool, demonstrable trustworthiness is the feature. It is
deliberately **honest**: it separates "are the defenses wired up" from "does the
model actually resist attack", and it shows residual risks rather than hiding
them behind a green checkmark.

Open it in the app via the **AI Assurance** item in the left sidebar (route
`/assurance`), or the card in a Planning hub's "Quality & assurance" section.

## What it shows

- **Control coverage** (deterministic, free): a static suite proves each curated
  injection payload is fenced (isolated) and detected. Proves the *plumbing* — not
  that the model resists a persuasive injection.
- **Empirical resistance** (live, opt-in, spends AI budget): the red-team actually
  sends payloads to the model and scores the response with a canary. This is the
  only measure of real resistance. It never runs automatically — a human clicks
  "Run live red-team" and confirms a cost warning; it is rate-limited to once/min.
- **Security controls**: a checklist with status (Implemented / Partial / Residual
  risk / N/A), what each defends, evidence, and residual risk.
- **Flagged documents** and **run history**.

There is intentionally **no single fabricated "security score"** — a made-up
number would be exactly the kind of false precision this tool exists to avoid.

## The controls

| Control | Status | Notes |
|---|---|---|
| Prompt-injection isolation | Implemented | Untrusted content fenced with a per-call nonce + isolation preamble. Defense-in-depth, not a guarantee. |
| Untrusted-content scanning | Implemented | Low-false-positive heuristics flag uploads; informational only, never blocks. |
| Web-search result isolation | Partial | Tavily results fenced; Anthropic server-side web-search is provider-side and **not isolatable**. |
| Authentication | Implemented | Shared login, fail-closed default, constant-time compare, delay-based throttling. |
| Upload & parser limits | Implemented | PDF page cap, DOCX zip-bomb guard, streaming size cap, parser timeout. |
| SSRF egress filtering | Implemented | All resolved IPv4/IPv6 checked; residual: DNS-rebinding not fully pinned. |
| Tenant isolation | Residual | Single shared login by design — any login sees every engagement. Accounts + per-engagement authorisation are future work. |

## How injection isolation works

Untrusted text (uploaded documents, fetched URLs, search results, pasted
interview answers, auditor-entered finding fields) is wrapped by
`services/prompt_safety.py::wrap_untrusted` between `<<UNTRUSTED:{nonce}>>` /
`<<END:{nonce}>>` markers with a random per-call nonce. Because the nonce is
unguessable, embedded text cannot forge the closing marker to "break out". Task
and output instructions are placed **after** the fenced block (recency) so
untrusted content can't push the model off its output contract. A standing
clause in `BASE_SYSTEM_PROMPT` tells every agent to treat fenced content as data.

This reduces prompt-injection risk; it does not eliminate it. Measure real
resistance with the live red-team.

## Running the suites

Deterministic security regression net (no AI, safe for CI):

```
cd backend
venv/Scripts/python.exe -m tests.test_security   # full security suite
venv/Scripts/python.exe -m tests.smoke           # app + golden path + assurance
```

Via the API (behind auth):

- `GET  /api/assurance/posture` — control checklist + coverage + last live result
- `POST /api/assurance/suite/run` body `{"mode":"static"}` — free, deterministic
- `POST /api/assurance/suite/run` body `{"mode":"live","confirm":"RUN-LIVE"}` — spends AI budget
- `GET  /api/assurance/runs` — history · `GET /api/assurance/documents/flags`

## Configuration (backend/.env)

| Variable | Default | Effect |
|---|---|---|
| `APP_PASSWORD` | *(empty)* | Shared login password. **Empty = fail-closed** (all requests 503) unless `IA_WINGMAN_DEV_OPEN=1`. |
| `IA_WINGMAN_DEV_OPEN` | `false` | Explicitly run with authentication disabled — local dev only, never in a demo/prod. |
| `EXPOSE_API_DOCS` | `true` | Serve `/docs` + `/openapi.json`. Set `false` to lock them down. |
| `ANTHROPIC_API_KEY` | *(required)* | Model access. Only used server-side; never sent to the frontend. |
| `TAVILY_API_KEY` | *(empty)* | Optional web search. Results are fenced before reaching the model. |

## Known residual risks (documented, not hidden)

1. **Prompt injection is mitigated, not solved** — verify with the live red-team.
2. **Anthropic server-side web-search** results cannot be fenced by this app.
3. **DNS-rebinding** — SSRF validation is at resolve time; the socket is not pinned to the vetted IP.
4. **No tenant isolation** — a single shared login can access all engagements.
5. **Rate-limiting is per-IP** — behind the Vite dev proxy all traffic shares one IP, so it is mainly meaningful under direct exposure.
