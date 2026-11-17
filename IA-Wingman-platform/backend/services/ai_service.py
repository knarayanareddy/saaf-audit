import re
import json
import time
import asyncio
import logging
from contextvars import ContextVar
from anthropic import AsyncAnthropic
from fastapi.responses import StreamingResponse
from config import settings

logger = logging.getLogger("ia.wingman")

client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

#: The draft tier's model — kept as a name because older call sites import it.
#: The tier is the source of truth; this follows it rather than being set twice.
from services.model_tiers import DRAFT as _DRAFT_TIER
MODEL = _DRAFT_TIER.model

# Every call has always come back with usage and a stop reason, and this platform
# has always thrown both away — which is why no agent run can say what it cost or
# how long it took. They are recorded here, per async task, so the 50-odd
# existing call sites pick it up without changing a single signature: after an
# agent call, `last_call_meta()` describes the call that just happened.
_LAST_META: ContextVar[object] = ContextVar("ia_last_agent_meta", default=None)


def last_call_meta():
    """Meta for the most recent agent call on this task, or None."""
    return _LAST_META.get()


def _record(message, started: float, model: str, schema: str = "", tier: str = "",
            system_prompt: str | None = None):
    from services.agent_contract import AgentMeta, prompt_version
    usage = getattr(message, "usage", None)
    meta = AgentMeta(
        # The model that answered, not the one asked: with server-side fallback a
        # declined request is served by another model, at that model's price.
        model=getattr(message, "model", None) or model,
        tier=tier,
        input_tokens=getattr(usage, "input_tokens", 0) or 0,
        output_tokens=getattr(usage, "output_tokens", 0) or 0,
        cached_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
        cache_write_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
        duration_ms=int((time.monotonic() - started) * 1000),
        stop_reason=getattr(message, "stop_reason", "") or "",
        schema=schema,
        prompt_version=prompt_version(system_prompt) if system_prompt else "",
        reasoned=any(getattr(b, "type", "") in ("thinking", "redacted_thinking")
                     for b in (getattr(message, "content", None) or [])),
    )
    _LAST_META.set(meta)
    return meta

# ── Resilience + cost helpers ──────────────────────────────────────────────────

# HTTP statuses worth retrying — transient server/throughput conditions.
_RETRYABLE_STATUS = {408, 409, 429, 500, 502, 503, 529}
_MAX_RETRIES = 3


def _system_blocks(system_prompt: str) -> list[dict]:
    """Wrap the system prompt as a cacheable block.

    Anthropic prompt caching stores the system prefix for ~5 minutes. Since the
    large BASE_SYSTEM_PROMPT is reused across nearly every call, caching it cuts
    input-token cost dramatically and lowers latency on repeat calls. Blocks below
    the cache minimum are simply not cached — adding the marker is always safe.
    """
    return [{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}]


async def _record_refusal(model: str, exc: Exception) -> None:
    """One row for a call the API would not make. Best-effort, like the rest."""
    from services.agent_contract import AgentMeta
    from services.model_tiers import TIERS

    tier = next((t.name for t in TIERS.values() if t.model == model), "")
    try:
        await record_call(AgentMeta(model=model, tier=tier, stop_reason="refused"),
                          ok=False, error=f"{type(exc).__name__}: {exc}"[:200])
    except Exception:  # noqa: BLE001
        logger.exception("Could not record a refused request")


def _is_retryable(exc: Exception) -> bool:
    status = getattr(exc, "status_code", None)
    if status in _RETRYABLE_STATUS:
        return True
    name = type(exc).__name__
    # Connection/timeout/overloaded errors from the SDK
    return any(k in name for k in ("APIConnection", "Timeout", "Overloaded", "InternalServer", "RateLimit"))


async def _call_with_retry(**kwargs):
    """Call client.messages.create with exponential backoff on transient errors.

    Authentication errors (401) and other client errors are NOT retried — they
    will never succeed and should surface immediately.

    A request the API refuses is recorded before it is raised. The ledger's own
    first line says every call leaves a row whether it succeeded or not, and this
    was the hole in it: a rejected request never reached `record_call`, so the
    four judge-tier agents failing on a parameter this deployment had outgrown
    left no row, no cost and no trace anywhere. Nothing in the platform could
    have told you they were dead.
    """
    last_exc = None
    for attempt in range(_MAX_RETRIES):
        try:
            started = time.monotonic()
            message = await client.messages.create(**kwargs)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if not _is_retryable(exc) or attempt == _MAX_RETRIES - 1:
                await _record_refusal(kwargs.get("model", ""), exc)
                raise
            delay = 2 ** attempt  # 1s, 2s, 4s
            logger.warning("Anthropic call failed (%s), retry %d/%d in %ds",
                           type(exc).__name__, attempt + 1, _MAX_RETRIES, delay)
            await asyncio.sleep(delay)
            continue
        await _raise_if_refused(message, started, kwargs.get("model", ""))
        return message
    raise last_exc


async def _raise_if_refused(message, started: float, model: str) -> None:
    """Turn a declined request into a declined request, before anything parses it.

    Checked here because every non-streaming call passes through this function,
    so no call site can forget it. The row is written with the category the API
    gave, so the ledger can say "declined: cyber" where it used to say a JSON
    parse had failed. A refusal is not retried: the same request would be
    declined the same way, and paid for twice.
    """
    from services.agent_contract import AgentRefused, refusal_of

    refused = refusal_of(message)
    if refused is None:
        return
    category, explanation = refused
    meta = _record(message, started, model)
    await record_call(meta, ok=False, error=f"refused: {category or 'unspecified'}")
    logger.warning("Model declined a request (%s): %s", category, explanation or "no explanation")
    raise AgentRefused(category, explanation)

from organization import ORG, org_system_context
from services.prompt_safety import UNTRUSTED_DATA_CLAUSE
from services.agent_ledger import record_call

BASE_SYSTEM_PROMPT = f"""You are IA Wingman, an expert internal audit AI assistant for an organisation's
Internal Audit (IA) function.

{org_system_context()}

REGULATORY & FRAMEWORK KNOWLEDGE (financial-services reference — apply what is relevant):
AML/CTF: EU AMLD framework, national AML laws (e.g. WWFT/NL, MLR 2017/UK), EBA/GL/2022/05, FATF standards
Capital & prudential: CRR2/CRD5, EBA ICAAP/ILAAP Guidelines, IRRBB, SREP
ESG: SFDR, EU Taxonomy, CSRD, EBA ESG Risk Guidelines
Payments & operational resilience: PSD2, SEPA, DORA, EBA ICT Risk Guidelines, CASS (UK)
Governance & outsourcing: EBA Outsourcing GL, EBA Remuneration GL, Investment Firms Directive
Lending: EBA Lending Guidelines
Data/Privacy: GDPR, EBA Data Governance Guidelines
Deposit: Deposit Guarantee Schemes Directive
(For non-financial organisations, apply the frameworks the user provides rather than assuming these.)

ALWAYS:
- Cite specific article numbers and section references where you can
- Distinguish regulatory requirements by jurisdiction / entity where it matters
- Show confidence: HIGH (directly applicable) / MEDIUM (likely applicable) / LOW (consider)
- Mark built-in knowledge vs. user-provided documents (provenance matters in audit)
- Be honest about knowledge cutoff: flag that recent developments should be verified
- Propose; never decide. The human always confirms and owns the conclusion.
- Use whatever identifier the user provides for team members; never guess real names

OUTPUT STYLE (readability first — a medior auditor must scan it without being overwhelmed):
- Lead with a short summary, then structured bullet points — never a wall of text
- Keep bullets concise; put detail in clearly-labelled sub-points
- Where relevant, tag items with severity (must-fix / suggestion) and confidence (high / medium / low)

ACTIONS:
You have tools to PROPOSE creating an engagement or adding a framework. When the user asks for such an
action, briefly explain what you will propose in text, then call the matching tool. Never assume the
action is done — a human reviews and confirms every proposal. Only propose adding a framework when the
user is working within a specific engagement.
""" + UNTRUSTED_DATA_CLAUSE


# Chat-only style blocks. They are appended to BASE_SYSTEM_PROMPT by the /ai/chat
# route and by nothing else: the document-writing agents (ANL, work program,
# audit report, board narrative) share the base prompt and must stay thorough.
# In a chat the opposite is true — the auditor asked one question and wants the
# answer, not an essay around it.
CHAT_STYLE_BRIEF = """

CHAT LENGTH — BRIEF (the auditor chose this):
- Lead with the answer in the first sentence. No preamble, no restating the question.
- Stay under roughly 120 words, or 5 bullets. One idea per bullet.
- No closing paragraph that summarises what you just said.
- Leave out caveats the auditor already knows (that AI proposes and a human decides,
  that findings need evidence). State a caveat only when it changes the answer.
- If you deliberately left detail out, end with one short line offering it.
- Formatting: plain sentences or "-" bullets. Bold at most a couple of key terms,
  and no markdown headings — this is a chat panel, not a document.
"""

CHAT_STYLE_DETAILED = """

CHAT LENGTH — DETAILED (the auditor chose this):
- Short summary first, then the reasoning in structured bullets with sub-points.
- Include the caveats, alternatives and references that matter for an audit file.
- Formatting: "-" bullets and sparing bold; no markdown headings in a chat panel.
"""


# Tools the chat can use to PROPOSE actions. The model never executes them —
# each tool_use becomes an action card the human accepts or dismisses (human-in-the-loop).
CHAT_TOOLS = [
    {
        "name": "propose_create_engagement",
        "description": "Propose creating a new audit engagement. Only proposes — the human must confirm before anything is created. Use when the user asks to create/add/start an audit or engagement.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Concise audit title"},
                "entity": {"type": "string", "enum": ORG.entity_codes()},
                "audit_type": {"type": "string", "enum": ORG.audit_types},
                "summary": {"type": "string", "description": "1-2 sentence summary"},
            },
            "required": ["name", "entity", "audit_type"],
        },
    },
    {
        "name": "propose_add_framework",
        "description": "Propose adding a regulatory framework to the CURRENT engagement. Only proposes — the human must confirm. Use when the user asks to add/apply a regulation or framework to the audit they are working on.",
        "input_schema": {
            "type": "object",
            "properties": {
                "framework_name": {"type": "string", "description": "Full framework name, e.g. 'WWFT (Wet ter voorkoming van witwassen, 2024)'"},
                "framework_code": {"type": "string", "description": "Short code, e.g. 'WWFT'"},
                "applicability_rationale": {"type": "string", "description": "Why it applies to this audit"},
            },
            "required": ["framework_name"],
        },
    },
    {
        "name": "propose_run_stage",
        "description": (
            "Propose running a specific AI drafting/analysis stage of the CURRENT engagement's "
            "lifecycle (e.g. draft the BRA, generate the Work Program, run the RACM governance "
            "assessment). Only proposes — the human must confirm. Use when the user asks to "
            "draft/generate/run/analyse a specific stage, or asks what to do next and agrees to run it. "
            "Topic Intelligence is not here on purpose: the auditor adds documents and what they already "
            "know, then presses Run on its own page. If they ask for it, say that and point them there."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                # Keep in sync with services/stage_actions.py:STAGE_RUN_ACTIONS keys.
                "stage_key": {
                    "type": "string",
                    "enum": [
                        "frameworks", "process_understanding", "bra", "anl",
                        "kickoff", "work_program", "drl", "interview_guide", "racm_scoping",
                        "racm_governance", "racm_data_analysis", "report_draft",
                        "quality_review", "quality_peer_review",
                    ],
                },
                "rationale": {"type": "string", "description": "One short sentence: why run this now"},
            },
            "required": ["stage_key"],
        },
    },
    {
        "name": "propose_promote_finding",
        "description": (
            "Propose promoting a RACM control test's exceptions into a formal 5C finding. Only "
            "proposes — the human must confirm. Use ONLY with a real test_id from the "
            "'RACM tests with exceptions' list in the engagement context — never invent one."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "test_id": {"type": "string", "description": "The RACM test's id, from the engagement context"},
                "test_title": {"type": "string", "description": "The test's title, for display only"},
            },
            "required": ["test_id"],
        },
    },
    {
        "name": "propose_update_engagement_status",
        "description": (
            "Propose updating the CURRENT engagement's lifecycle status label. Only proposes — the "
            "human must confirm. Use when the user asks to move the engagement to a new phase "
            "(e.g. 'mark this as in fieldwork')."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "new_status": {
                    "type": "string",
                    "enum": ["to_be_scheduled", "in_planning", "in_fieldwork", "in_reporting", "closed"],
                },
                "rationale": {"type": "string", "description": "One short sentence: why this transition"},
            },
            "required": ["new_status"],
        },
    },
    {
        "name": "propose_update_engagement_details",
        "description": (
            "Propose correcting details of the CURRENT engagement: its name (for example a typo), "
            "audit code, summary, lead auditor or scope period. Only proposes — the human must confirm "
            "and sees exactly what changes. Include ONLY the fields that change, with their full new "
            "value. Use when the user asks to rename or correct the audit. Do not use it for the "
            "lifecycle status (use propose_update_engagement_status) or for dates, team and entity "
            "(point the user to the edit pencil next to the active engagement in the left sidebar)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "The corrected audit name, complete"},
                "audit_code": {"type": "string", "description": "The corrected audit code, e.g. 26-047"},
                "summary": {"type": "string", "description": "The new summary, complete"},
                "lead_auditor": {"type": "string", "description": "The lead auditor's name"},
                "scope_period": {"type": "string", "description": "The scope period, e.g. 2026"},
                "rationale": {"type": "string", "description": "One short sentence: why this change"},
            },
        },
    },
    {
        "name": "propose_open_engagement",
        "description": (
            "Propose navigating to a specific engagement. Only use when NO engagement is currently "
            "open (the portfolio Dashboard context) and the user asks about, or agrees to focus on, "
            "one specific audit from the attention digest. Only proposes — a click navigates there; "
            "nothing runs automatically. Never invent an engagement_id — use only one named in the "
            "portfolio digest already given to you."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "engagement_id": {"type": "string", "description": "The engagement's id, from the portfolio digest"},
                "engagement_name": {"type": "string", "description": "The engagement's name, for display only"},
                "rationale": {"type": "string", "description": "One short sentence: why open this one now"},
            },
            "required": ["engagement_id", "engagement_name"],
        },
    },
]


def stream_chat(
    system_prompt: str, messages: list, max_tokens: int = 4096, with_tools: bool = True,
    on_tool_use=None, on_complete=None,
) -> StreamingResponse:
    """SSE streaming for the AI chat panel. Frontend reads via fetch + getReader (POST).

    Emits three event types:
      - delta:    a chunk of streamed text
      - action:   a proposed tool call {tool, input, ...} for the human to accept/dismiss
      - complete: the full assembled text

    on_tool_use, if given, is an async callback(tool_name, tool_input) -> dict, invoked
    per tool_use block BEFORE its 'action' event is sent — e.g. to persist the proposal
    and return {"proposal_id": ...} to merge into the event payload, so the frontend can
    act on a specific persisted proposal from the moment it appears.

    on_complete, if given, is an async callback(full_text, tool_calls) invoked once
    the turn is fully assembled, before the 'complete' event is sent — e.g. to
    persist the turn. Both callbacks are best-effort: a failure never breaks the
    user-facing stream, it only means that part isn't saved.
    """

    async def generate():
        try:
            from services.model_tiers import DRAFT
            # The chat speaks as the draft tier, with that model's own thinking
            # and fallback settings. The history it sends is text only, so there
            # are no thinking blocks to carry back between turns.
            kwargs = _tier_kwargs(DRAFT, max_tokens, system_prompt, messages)
            if with_tools:
                kwargs["tools"] = CHAT_TOOLS
            async with client.messages.stream(**kwargs) as stream:
                async for text in stream.text_stream:
                    yield f"event: delta\ndata: {json.dumps({'text': text})}\n\n"
                final = await stream.get_final_message()
                from services.agent_contract import refusal_of
                refused = refusal_of(final)
                if refused is not None:
                    # Said in words, with the category, and the turn is not
                    # stored as an answer: an empty or half-streamed reply saved
                    # as the assistant's turn would read as the model having
                    # nothing to say about a cyber control.
                    category, _ = refused
                    msg = (f"The model declined this request (category: {category or 'unspecified'}). "
                           "Rephrasing will not change that for the same request; this is a "
                           "safety decision by the model provider, not an error in IA Wingman.")
                    yield f"event: error\ndata: {json.dumps({'message': msg, 'refusal': category})}\n\n"
                    return
                full = "".join(b.text for b in final.content if b.type == "text")
                tool_calls = []
                for block in final.content:
                    if block.type == "tool_use":
                        extra = {}
                        if on_tool_use:
                            try:
                                extra = await on_tool_use(block.name, block.input) or {}
                            except Exception:  # noqa: BLE001
                                logger.exception("stream_chat on_tool_use callback failed")
                        call = {"tool": block.name, "input": block.input, **extra}
                        tool_calls.append(call)
                        yield f"event: action\ndata: {json.dumps(call)}\n\n"
                if on_complete:
                    try:
                        await on_complete(full, tool_calls)
                    except Exception:  # noqa: BLE001
                        logger.exception("stream_chat on_complete callback failed")
                yield f"event: complete\ndata: {json.dumps({'content': full})}\n\n"
        except Exception as _exc:  # noqa: BLE001
            err_str = str(_exc)
            if "401" in err_str or "authentication_error" in err_str or "invalid x-api-key" in err_str:
                msg = (
                    "API key not configured or invalid. "
                    "Add your real ANTHROPIC_API_KEY to backend/.env and restart the backend."
                )
            elif "rate_limit" in err_str or "429" in err_str:
                msg = "Anthropic rate limit reached — please wait a moment and try again."
            else:
                # Log the real error server-side; never surface internal detail to the UI.
                logger.exception("AI chat stream failed")
                msg = "The AI service is temporarily unavailable — please try again."
            yield f"event: error\ndata: {json.dumps({'message': msg})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _tier_kwargs(tier, max_tokens: int, system_prompt: str, messages: list, **output) -> dict:
    """The request for one call on `tier`: model, ceiling, and what that model
    accepts for thinking, effort and fallback (model_tiers.request_params).

    `output` adds to `output_config` — structured outputs pass `format=` here —
    without dropping the effort the tier already set. The installed SDK (0.40)
    has no parameters for any of this, so it travels in extra_body/extra_headers.
    """
    from services.model_tiers import merge_output_config, request_params

    params = request_params(tier)
    body = params["extra_body"]
    if output:
        body = merge_output_config(body, **output)
    kwargs = dict(
        model=tier.model,
        max_tokens=max(max_tokens, tier.max_tokens) if tier.thinks else max_tokens,
        system=_system_blocks(system_prompt),
        messages=messages,
        extra_body=body,
    )
    if params["extra_headers"]:
        kwargs["extra_headers"] = params["extra_headers"]
    return kwargs


async def run_agent_to_json(system_prompt: str, user_prompt: str, max_tokens: int = 4096,
                            tier=None) -> dict | list:
    """Non-streaming agent call — returns parsed JSON object or array.

    The untyped path, kept for the call sites that have not moved to
    services/agent_contract.run_agent() and its schema yet. It no longer returns
    a cut-off answer as though it were a whole one: a run that hits the token
    ceiling raises AgentTruncated, because a work program silently missing nine
    of its twenty rows is worse than a run that admits it failed.
    """
    from services.agent_contract import AgentTruncated
    from services.model_tiers import DRAFT

    tier = tier or DRAFT
    started = time.monotonic()
    # Thinking, effort and fallback come from one place, per model. A tier that
    # does not think must say so explicitly, because the model thinks by default
    # on a hard prompt and `max_tokens` covers reasoning and answer together: the
    # work program generator once asked for 12,000 and got one thinking block
    # plus 7,806 characters of JSON cut off mid-row. A tier that does think gets
    # its ceiling raised so the answer still has room after the reasoning.
    kwargs = _tier_kwargs(tier, max_tokens, system_prompt,
                          [{"role": "user", "content": user_prompt}])
    message = await _call_with_retry(**kwargs)
    meta = _record(message, started, tier.model, tier=tier.name, system_prompt=system_prompt)
    if message.stop_reason == "max_tokens":
        # The same sentence into the exception and into the ledger. `error` was
        # null on all five truncated calls on record: the row said a run failed
        # and never said why.
        cut = (f"The answer was cut off at {max_tokens:,} tokens "
               f"({meta.output_tokens:,} produced). Nothing partial is returned.")
        await record_call(meta, ok=False, error=cut)
        raise AgentTruncated(cut)
    raw = "".join(b.text for b in message.content if b.type == "text")
    # The ledger row is written after the parse, not before it. Written before,
    # it recorded every one of these calls as a success — including the ones
    # where `_extract_json` then raised, which is how a path that loses roughly
    # one work program in two could show a clean record.
    return await _json_or_record(meta, raw)


#: How many searches each Topic Intelligence lens may run. It was 5, and it is 8
#: now — but that is a guess, not a finding. Measured: at 5 every lens used all
#: 5, and at 8 a lens used all 8. The model spends whatever it is offered, so
#: "used it all" says nothing about whether it was enough. What would show a
#: budget being too small is a refused search, and that is what `search_report`
#: now records. Raise or lower this only on that evidence.
LENS_SEARCH_BUDGET = 8

#: Pages kept per lens run from the search results. Eight searches return about ten
#: hits each; this keeps the stored report small and the first hits are the relevant ones.
MAX_RESULTS_KEPT = 40


def search_report(message, allowed: int) -> dict:
    """What actually happened to the searching, read off the reply itself.

    A model that could not search says so in its own words — "web search was
    unavailable" — and until now that sentence was the only record, repeated on
    screen as though it were a fact. It may well be one. But it is also exactly
    what a model writes after using up its allowance and being refused one more
    search, and the two are different situations with different remedies: the
    first is an outage, the second is a budget.

    So this counts the searches that ran and collects the error codes the tool
    returned, which is the only way to tell the two apart afterwards.
    """
    errors: list[str] = []
    queries: list[str] = []
    results: list[dict] = []
    seen_urls: set[str] = set()
    for block in getattr(message, "content", None) or []:
        # What was asked: the model's own search queries, in order.
        if getattr(block, "type", "") == "server_tool_use" and getattr(block, "name", "") == "web_search":
            query = (getattr(block, "input", None) or {}).get("query")
            if isinstance(query, str) and query.strip():
                queries.append(query.strip()[:200])
        if getattr(block, "type", "") not in ("web_search_tool_result", "code_execution_tool_result"):
            continue
        content = getattr(block, "content", None)
        # What came back: the pages the search returned, whatever the model then
        # chose to cite. Kept so a lens that cited nothing can still be shown its
        # own sources, and so a cited link can be checked against them.
        if isinstance(content, list) and getattr(block, "type", "") == "web_search_tool_result":
            for hit in content:
                # The API returns each hit as a plain dict; read an object too, so a client
                # that parses them into models keeps working.
                get = hit.get if isinstance(hit, dict) else lambda key, _hit=hit: getattr(_hit, key, None)
                url = get("url")
                if isinstance(url, str) and url and url not in seen_urls and len(results) < MAX_RESULTS_KEPT:
                    seen_urls.add(url)
                    results.append({"title": (get("title") or url)[:200], "url": url})
        # A successful result is a list of hits; a failed one is a single error
        # object carrying a code.
        code = None if isinstance(content, list) else getattr(content, "error_code", None)
        if code:
            errors.append(str(code))
        # The dynamic-filtering search tool runs its searches inside code
        # execution, and when that code asks for more than the allowance left, the
        # failure is not an error code but a line on stderr. It went unseen: the
        # report read "used all 8 searches" while a lens had in fact lost the rest.
        stderr = None if isinstance(content, list) else getattr(content, "stderr", None)
        if isinstance(stderr, str) and "limit exceeded" in stderr.lower():
            errors.append("tool_use_limit_exceeded")

    tool_use = getattr(getattr(message, "usage", None), "server_tool_use", None)
    used = tool_use.get("web_search_requests") if isinstance(tool_use, dict) \
        else getattr(tool_use, "web_search_requests", None)

    return {
        "web_search": True,
        "searches_used": int(used or 0),
        "searches_allowed": allowed,
        "search_errors": errors,
        "queries": queries,
        "results": results,
    }


async def run_agent_to_json_with_web_search(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 4096,
    max_search_uses: int = 5,
    report: dict | None = None,
) -> dict | list:
    """Agent call with Anthropic built-in web search. Claude searches the web server-side.
    No separate search API key required — uses the existing ANTHROPIC_API_KEY.

    Pass an empty dict as `report` and it is filled in with what the searching
    did (see `search_report`). It is a parameter rather than part of the return
    value so that the existing callers, which expect the parsed answer alone,
    keep working unchanged."""
    from services.model_tiers import DRAFT

    started = time.monotonic()
    kwargs = _tier_kwargs(DRAFT, max_tokens, system_prompt,
                          [{"role": "user", "content": user_prompt}])
    kwargs["tools"] = [{
        "type": "web_search_20260209",
        "name": "web_search",
        "max_uses": max_search_uses,
    }]
    message = await _call_with_retry(**kwargs)
    meta = _record(message, started, DRAFT.model, tier=DRAFT.name, system_prompt=system_prompt)
    found = search_report(message, max_search_uses)
    if report is not None:
        report.update(found)
    if found["search_errors"]:
        logger.warning("Web search reported errors (%s) after %d of %d searches",
                       ", ".join(sorted(set(found["search_errors"]))),
                       found["searches_used"], found["searches_allowed"])
    if message.stop_reason == "max_tokens":
        from services.agent_contract import AgentTruncated
        cut = f"The search answer was cut off at {max_tokens:,} tokens."
        await record_call(meta, ok=False, error=cut)
        raise AgentTruncated(cut)
    raw = "".join(b.text for b in message.content if b.type == "text")
    return await _json_or_record(meta, raw)


async def _json_or_record(meta, raw: str) -> dict | list:
    """Parse the reply, and write down honestly how that went.

    Three outcomes, three different rows. It parsed as it stood; it parsed only
    after this code cut it into shape, which is recorded by name; or nothing
    resembling JSON was in it, which is a failed call and is now recorded as one
    instead of as a success followed by an exception nobody joined to it.
    """
    from services.agent_ledger import caller_of

    try:
        value, repair = _extract_json(raw)
    except ValueError as exc:
        await record_call(meta, ok=False, error=str(exc))
        raise
    meta.repair = repair
    meta.repaired = bool(repair)
    if repair:
        # At warning level because it is not free: the repair worked this time on
        # a reply the model was asked to produce cleanly, and the call site that
        # needed it is a candidate for the typed path.
        logger.warning("Repaired a model reply (%s) for %s — it did not parse as returned",
                       repair, caller_of())
    await record_call(meta)
    return value


def _extract_json(raw: str) -> tuple[dict | list, str]:
    """Extract a JSON object or array from a model response, and say what it cost.

    Handles the common failure modes: markdown ```json fences, leading prose,
    and trailing commas — without needing tool-use, so existing call sites are
    unchanged.

    It returns the repair it had to perform alongside the value, and that second
    half is the point. This function did its work silently, so a call whose reply
    only parsed after the braces were sliced out of a paragraph was indistinguishable
    in the ledger from one that came back clean — and there is no ranking the forty
    call sites still on this path without knowing which of them are being carried.
    An empty string means the model's own JSON parsed as it stood.
    """
    text = raw.strip()
    repair = ""

    # 1. Strip a surrounding ```json ... ``` (or plain ```) fence if present.
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
        repair = "fence"
    else:
        # A truncated response (hit max_tokens mid-generation) has an opening fence
        # but never reaches a closing one — strip the opening marker anyway so the
        # slicing/repair steps below see the real JSON instead of the ``` prefix.
        leading = re.match(r"^```(?:json)?\s*", text)
        if leading:
            text = text[leading.end():]
            repair = "fence"

    # 2. Direct parse — fastest path when the model returned clean JSON.
    try:
        return json.loads(text), repair
    except json.JSONDecodeError:
        pass

    # 3. Fall back to slicing the outermost object or array out of the text —
    # whichever opens first, rather than objects always before arrays. Fixed
    # order meant a single-row array with a sentence in front of it came back as
    # the bare object inside it: `[{"id": "wp_1"}]` sliced to `{"id": "wp_1"}`,
    # which every caller here then discarded on `isinstance(rows, list)`. A whole
    # answer became an empty one, and the ledger recorded a clean success. Found
    # by giving this function a voice: it had been reporting "sliced" on replies
    # it was quietly reshaping.
    pairs = sorted((("{", "}"), ("[", "]")),
                   key=lambda p: text.find(p[0]) if p[0] in text else len(text) + 1)
    for open_ch, close_ch in pairs:
        start = text.find(open_ch)
        end = text.rfind(close_ch)
        if start != -1 and end > start:
            candidate = text[start:end + 1]
            try:
                return json.loads(candidate), "sliced"
            except json.JSONDecodeError:
                # Last resort: remove trailing commas before } or ]
                cleaned = re.sub(r",(\s*[}\]])", r"\1", candidate)
                try:
                    return json.loads(cleaned), "commas"
                except json.JSONDecodeError:
                    continue

    # There used to be a fourth step here: close a cut-off array after its last
    # complete element and return that. It was removed deliberately. The caller
    # could not tell "the model returned eleven rows" from "the model was cut off
    # after eleven and the rest are gone", and neither could the auditor reading
    # the result. Truncation is now caught at its source, by stop_reason, and
    # raised — see run_agent_to_json.
    raise ValueError(f"No JSON found in agent response. Raw: {raw[:500]}")


async def run_text(system_prompt: str, user_prompt: str, max_tokens: int = 1024, tier=None) -> str:
    """Non-streaming plain-text call. Used for simple suggestions (e.g. summary draft)."""
    from services.model_tiers import DRAFT

    tier = tier or DRAFT
    started = time.monotonic()
    kwargs = _tier_kwargs(tier, max_tokens, system_prompt,
                          [{"role": "user", "content": user_prompt}])
    message = await _call_with_retry(**kwargs)
    await record_call(_record(message, started, tier.model, tier=tier.name, system_prompt=system_prompt))
    # A thinking model returns its reasoning as its own block type; only the
    # text blocks are the answer.
    return "".join(b.text for b in message.content if b.type == "text").strip()
