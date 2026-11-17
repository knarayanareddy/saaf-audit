"""The contract an agent's output has to keep.

Every agent in this platform used to ask the model for JSON in prose and then
hope. Behind that hope sat a sixty-line repair routine: strip a code fence, slice
the outermost braces out of a sentence, delete trailing commas and — as a last
resort — cut a truncated array short and return it as though it were complete.
Each call site then wrote its own `if not isinstance(result, dict)` and reached
for `.get()` on fields nobody had checked were there.

Three things were wrong with that, in order of how much they cost:

1. **A cut-off answer came back looking finished.** A work program that hit the
   token ceiling after eleven of twenty rows was saved, displayed and signed off
   as a twenty-row program with nine rows quietly missing. Nothing in the file
   said so.
2. **Nothing checked the shape.** A missing "rating" became None, flowed into the
   UI and read as "unrated" rather than as a failed run.
3. **A malformed answer was fatal.** The transport retry covers a 529; it does
   nothing for a model that returned prose, so the agent simply failed.

All three go away by asking for the answer as a tool call against a schema. The
model fills in a typed form instead of writing JSON into a paragraph, the reply
is validated before any caller sees it, and a validation failure is handed back
to the model once — with its own error — before anything is given up on.

`run_agent_to_json` in ai_service.py still exists for the call sites that have
not moved yet, but it no longer lies about truncation: see `AgentTruncated`.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Type, TypeVar

from pydantic import BaseModel, ValidationError

from services.agent_ledger import record_call

logger = logging.getLogger("ia.wingman")

T = TypeVar("T", bound=BaseModel)

# The one tool every typed agent call uses. The name is deliberately bland: it
# is a delivery mechanism, not a capability the model should reason about.
_SUBMIT = "submit_result"


class AgentTruncated(RuntimeError):
    """The model hit the token ceiling before it finished.

    Raised rather than repaired. A partial answer presented as a whole one is
    the worst failure this platform can produce, because it is invisible: the
    auditor signs off a work program that is missing the rows nobody mentioned.
    """


class AgentContractError(RuntimeError):
    """The model could not produce an answer matching the schema, twice."""


class AgentTimedOut(RuntimeError):
    """The run took longer than the platform will wait for it.

    Its own type so the screen can say what happened — "stopped after five
    minutes" — instead of the generic failure, and so nobody reads a timeout as
    the model having nothing to say.
    """


class AgentRefused(RuntimeError):
    """The model declined the request on a safety ground.

    Different from every other failure here, and it has to look different. The
    API answers with a normal 200 and `stop_reason: "refusal"`, so until this
    existed a declined request fell through to the JSON parser and surfaced as
    "No JSON found" — which reads as a broken agent, and invites a retry that
    will be declined again. This platform audits IT security and cyber controls,
    and the current models carry a `cyber` classifier: a refusal is an expected
    event here, not an exotic one, and the auditor needs to be told which.
    """

    def __init__(self, category: str | None, explanation: str | None = None):
        self.category = category or "unspecified"
        self.explanation = explanation or ""
        super().__init__(
            f"The model declined this request (category: {self.category})."
            + (f" {self.explanation}" if self.explanation else "")
        )


def prompt_version(system_prompt, schema: dict | None = None) -> str:
    """A short, stable name for the instructions a call ran on.

    The system prompt plus the schema the API was held to, hashed. Two calls with
    the same version were given the same instructions; a changed prompt or field
    description gives a new one. The task template in the user prompt is not in
    it (template and data share one string there) — said on the ledger column.
    """
    import hashlib

    text = system_prompt if isinstance(system_prompt, str) else json.dumps(system_prompt, sort_keys=True)
    if schema:
        text += "\n" + json.dumps(schema, sort_keys=True)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def failure_message(exc: Exception) -> str:
    """What to store and show when an agent run fails.

    Two failures are already explained in words the auditor can act on — a
    refusal (which category) and a truncation (how far it got). Everything else
    stays generic on purpose: an internal exception text is for the server log,
    not for the screen.
    """
    if isinstance(exc, (AgentRefused, AgentTruncated, AgentTimedOut)):
        return str(exc)
    return "Agent run failed. Check server logs."


def refusal_of(message) -> tuple[str | None, str | None] | None:
    """(category, explanation) when the reply is a refusal, else None.

    Read defensively: the installed SDK predates `stop_details`, so it arrives
    as an untyped extra — an object on some versions, a dict on others.
    """
    if getattr(message, "stop_reason", None) != "refusal":
        return None
    details = getattr(message, "stop_details", None)
    if details is None:
        extra = getattr(message, "model_extra", None) or {}
        details = extra.get("stop_details")
    if isinstance(details, dict):
        return details.get("category"), details.get("explanation")
    return getattr(details, "category", None), getattr(details, "explanation", None)


#: What each kind of repair reads as, for a receipt a person has to judge. The
#: two on the typed path are the model correcting itself; the three below them
#: are this codebase cutting prose into shape, which is a weaker claim about the
#: answer and has to say so rather than share one word with the others.
_REPAIR_PHRASES = {
    "schema-retry": "schema corrected on retry",
    "no-tool-call": "answered in prose, asked again",
    "unstringified": "arrived as text, parsed back into a structure",
    "fence": "unwrapped from a code fence",
    "sliced": "JSON sliced out of surrounding text",
    "commas": "trailing commas removed before it would parse",
}


def repair_phrase(repair: str) -> str:
    return _REPAIR_PHRASES.get(repair, f"repaired: {repair}" if repair else "")


@dataclass
class AgentMeta:
    """What one agent call cost and how it went.

    Captured for every call — the SDK has always returned `usage` and this
    platform has always thrown it away, which is why no agent run has ever been
    able to say what it spent.
    """
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0          # read from the prompt cache (cheap)
    cache_write_tokens: int = 0     # written to it (1.25x input) — once uncounted
    duration_ms: int = 0
    stop_reason: str = ""
    repaired: bool = False          # the answer needed fixing before it could be used
    # What the fixing was. `retry` is this path, handing the model its own
    # validation error; the untyped path fills in which piece of text surgery it
    # needed. One bool could not tell those apart, and they are not the same
    # event: one is a model correcting itself, the other is a regex guessing.
    repair: str = ""
    schema: str = ""
    tier: str = ""                  # quick | draft | judge
    prompt_version: str = ""        # see prompt_version() — which instructions produced this
    thinking_tokens: int = 0        # reasoning the model did before answering, where visible
    # Whether the model reasoned at all. The current models hide their reasoning
    # by default (display "omitted"): the blocks arrive empty, so the count above
    # is 0 while the model did think. Saying "0" — or nothing — about a judge
    # that reasoned at length is the wrong way round; this says it reasoned, and
    # the count stays honest about being unavailable.
    reasoned: bool = False

    @property
    def cost_usd(self) -> float | None:
        from services.model_tiers import cost_usd
        return cost_usd(self.model, self.input_tokens, self.output_tokens, self.cached_tokens,
                        self.cache_write_tokens)

    def as_dict(self) -> dict:
        return {
            "model": self.model,
            "tier": self.tier,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cached_tokens": self.cached_tokens,
            "cache_write_tokens": self.cache_write_tokens,
            "thinking_tokens": self.thinking_tokens,
            "reasoned": self.reasoned,
            "duration_ms": self.duration_ms,
            "stop_reason": self.stop_reason,
            "repaired": self.repaired,
            "repair": self.repair,
            "schema": self.schema,
            "cost_usd": self.cost_usd,
        }

    def sentence(self) -> str:
        """One line for a run summary or a receipt in the UI."""
        from services.model_tiers import format_cost

        secs = self.duration_ms / 1000
        parts = [f"{secs:.1f}s", f"{self.input_tokens:,} in / {self.output_tokens:,} out"]
        if self.thinking_tokens:
            parts.append(f"{self.thinking_tokens:,} thinking")
        elif self.reasoned:
            parts.append("reasoning not shown")
        if self.cached_tokens:
            parts.append(f"{self.cached_tokens:,} cached")
        parts.append(format_cost(self.cost_usd))
        if self.repaired:
            parts.append(repair_phrase(self.repair))
        return " · ".join(parts)


@dataclass
class AgentResult:
    """A validated answer, and the account of how it was produced."""
    data: BaseModel
    meta: AgentMeta = field(default_factory=AgentMeta)

    def dump(self) -> dict:
        return self.data.model_dump(mode="json")


def schema_for(model: Type[BaseModel]) -> dict:
    """The model's JSON schema, flattened enough for the tools API.

    Pydantic emits $defs/$ref for nested models. The tools API accepts them, but
    inlining keeps what the model is shown simple and self-contained, which in
    practice produces cleaner first attempts.
    """
    raw = model.model_json_schema()
    defs = raw.pop("$defs", {})

    def inline(node):
        if isinstance(node, dict):
            if "$ref" in node and node["$ref"].startswith("#/$defs/"):
                target = defs.get(node["$ref"].split("/")[-1], {})
                merged = {k: v for k, v in node.items() if k != "$ref"}
                return {**inline(target), **merged}
            return {k: inline(v) for k, v in node.items()}
        if isinstance(node, list):
            return [inline(v) for v in node]
        return node

    return inline(raw)


def _tool_use_block(message):
    for block in message.content:
        if block.type == "tool_use" and block.name == _SUBMIT:
            return block
    return None


def _thinking_chars(message) -> int:
    return sum(len(getattr(b, "thinking", "") or "")
               for b in message.content if getattr(b, "type", "") == "thinking")


def _reasoned(message) -> bool:
    """Any thinking block at all — present even when its text is withheld."""
    return any(getattr(b, "type", "") in ("thinking", "redacted_thinking")
               for b in (getattr(message, "content", None) or []))


def _unstringify(payload, schema: Type[BaseModel]) -> tuple[object, str]:
    """Undo a tool input the model handed over as text instead of as a structure.

    Found by measuring, not by reasoning. Three of the frameworks and guidance
    prompts needed a correction round on **every** run after they were moved onto
    this path, which looked like a schema too strict for what the model produces.
    It was not. The model filled the tool's single array property with a
    stringified copy of the whole object:

        {"frameworks": '{"frameworks": [{...}, {...}]}'}

    Pydantic reported "Input should be a valid list", the error went back, and the
    second attempt answered properly — so every one of those runs was paid for
    twice, at twice the latency, for a reply that had arrived complete the first
    time.

    Undone here rather than prompted away, because it is the transport that went
    wrong and not the judgement. It is recorded as a repair like any other: a
    reply this code had to reshape is not the same event as one that arrived in
    the shape it was asked for, and the ledger has to keep them apart.
    """
    if payload is None:
        return None, ""

    fields = getattr(schema, "model_fields", {})

    def parse(text):
        try:
            return json.loads(text), True
        except (json.JSONDecodeError, TypeError):
            return None, False

    # The whole input as one string.
    if isinstance(payload, str):
        value, ok = parse(payload)
        return (value, "unstringified") if ok else (payload, "")

    if not isinstance(payload, dict):
        return payload, ""

    out, changed = dict(payload), False
    for name in fields:
        value = out.get(name)
        if not isinstance(value, str):
            continue
        parsed, ok = parse(value)
        if not ok:
            continue
        # The copy is usually the entire object, key and all; sometimes it is
        # only the field's own value.
        if isinstance(parsed, dict) and name in parsed:
            parsed = parsed[name]
        out[name], changed = parsed, True

    return (out, "unstringified") if changed else (payload, "")


def _meta_from(message, started: float, tier, schema_name: str, repair: str) -> AgentMeta:
    usage = getattr(message, "usage", None)
    return AgentMeta(
        # The model that answered: after a server-side fallback that is not
        # the one the tier asked for, and it is billed at its own price.
        model=getattr(message, "model", None) or tier.model,
        tier=tier.name,
        input_tokens=getattr(usage, "input_tokens", 0) or 0,
        output_tokens=getattr(usage, "output_tokens", 0) or 0,
        cached_tokens=(getattr(usage, "cache_read_input_tokens", 0) or 0),
        cache_write_tokens=(getattr(usage, "cache_creation_input_tokens", 0) or 0),
        # The API bills thinking inside output_tokens; this is reported separately
        # so a judge-tier run can show how much of its answer was reasoning.
        thinking_tokens=_thinking_chars(message) // 4,
        reasoned=_reasoned(message),
        duration_ms=int((time.monotonic() - started) * 1000),
        stop_reason=getattr(message, "stop_reason", "") or "",
        repaired=bool(repair),
        repair=repair,
        schema=schema_name,
    )


#: Schema keywords structured outputs does not accept. They are removed from the
#: schema the API sees and enforced here instead, by Pydantic.
_UNSUPPORTED_KEYWORDS = {
    "minLength", "maxLength", "minimum", "maximum", "exclusiveMinimum",
    "exclusiveMaximum", "multipleOf", "minItems", "maxItems", "pattern", "uniqueItems",
}


def structured_schema(model: Type[BaseModel]) -> dict:
    """`schema_for(model)`, made acceptable to structured outputs.

    The API constrains the reply to a JSON schema, but not to every keyword a
    schema can carry: lengths and numeric bounds are rejected, and every object
    must say `additionalProperties: false`. So those keywords are taken out of
    what is sent and the closure is added — and nothing is lost by it, because
    `schema.model_validate` still enforces every one of them on the reply, with
    one correction round when it fails. The field descriptions, which are the
    instructions, go through unchanged.
    """
    def clean(node, is_property_map: bool = False):
        if isinstance(node, dict):
            out = {}
            removed = {}
            for key, value in node.items():
                # Inside "properties" the keys are field names, not keywords: a
                # field that happened to be called "pattern" must survive.
                if not is_property_map and key in _UNSUPPORTED_KEYWORDS:
                    removed[key] = value
                    continue
                out[key] = clean(value, is_property_map=(key == "properties" and not is_property_map))
            if removed:
                # Taken out of the schema, so said in words instead. Without this
                # the model never learned a field had a limit — the first 5.5 eval
                # run wrote a 200+ character `why` and failed validation twice.
                said = _say_constraints(removed)
                if said:
                    out["description"] = (str(out.get("description") or "") + f" ({said})").strip()
            if not is_property_map and (out.get("type") == "object" or "properties" in out):
                out["additionalProperties"] = False
                # Every field is asked for. With structured outputs the model
                # leaves out what is optional — the first 5.5 eval run returned
                # frameworks without `specific_provision` (the article number)
                # and lens answers without sources, because both had a default.
                # A field that may genuinely be empty is nullable in its type,
                # so requiring it asks for an explicit null, not an invention.
                if "properties" in out:
                    out["required"] = list(out["properties"])
            return out
        if isinstance(node, list):
            return [clean(v) for v in node]
        return node

    return clean(schema_for(model))


def _say_constraints(removed: dict) -> str:
    """The removed schema keywords, as the sentence a person would write."""
    parts = []
    if "maxLength" in removed:
        parts.append(f"at most {removed['maxLength']} characters")
    if "minLength" in removed and removed["minLength"] > 1:
        parts.append(f"at least {removed['minLength']} characters")
    if "maxItems" in removed:
        parts.append(f"at most {removed['maxItems']} items")
    if "minItems" in removed and removed["minItems"] > 1:
        parts.append(f"at least {removed['minItems']} items")
    if "minimum" in removed or "exclusiveMinimum" in removed:
        parts.append(f"minimum {removed.get('minimum', removed.get('exclusiveMinimum'))}")
    if "maximum" in removed or "exclusiveMaximum" in removed:
        parts.append(f"maximum {removed.get('maximum', removed.get('exclusiveMaximum'))}")
    return "; ".join(parts)


def _reply_json(message):
    """The JSON the reply carries, or None.

    With a server tool such as web search a reply can hold more than one text
    block — a sentence before searching, the answer after. The answer is the
    last block, so that is tried when the whole does not parse.
    """
    texts = [b.text for b in message.content if getattr(b, "type", "") == "text"]
    for candidate in ("".join(texts), texts[-1] if texts else ""):
        candidate = (candidate or "").strip()
        if not candidate:
            continue
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None


def _as_param(block):
    """A response block, in a form that can be sent back as-is (pause_turn)."""
    return block.model_dump(exclude_none=True) if hasattr(block, "model_dump") else block


#: How often a long server-tool turn may be resumed before it is given up on.
_MAX_RESUMES = 3


async def run_agent(
    system_prompt: str,
    user_prompt: str,
    schema: Type[T],
    *,
    max_tokens: int | None = None,
    description: str = "",
    tier=None,
    server_tools: list | None = None,
    report: dict | None = None,
) -> AgentResult:
    """Run one agent call and return a validated `schema` instance.

    The answer comes back through **structured outputs**: the schema travels as
    `output_config.format` and the API constrains the reply to it. This replaced
    a forced `submit_result` tool, which the current models reject outright
    (400), and with it most of what that tool needed repairing — the fences, the
    "answered in prose" retry. `_unstringify` stays as a net; the ledger's
    `repair` column says whether it still ever catches anything.

    The tier decides the model, the thinking and the effort (model_tiers.
    request_params); left unset it is looked up from the schema name.

    `server_tools` (web search) may be passed. `report`, when given with them, is
    filled with what the searching actually did — counted from the reply, not
    taken from the model's own account of it.

    Raises `AgentTruncated` if the model ran out of room, `AgentRefused` if it
    declined (raised in _call_with_retry), and `AgentContractError` if it could
    not produce a valid answer even after being shown its own validation error.
    """
    # Imported here rather than at module scope: ai_service imports this module
    # for its exceptions, and a top-level import back would close the loop.
    from services.ai_service import _call_with_retry, _tier_kwargs, search_report
    from services.model_tiers import tier_for

    tier = tier or tier_for(schema.__name__)
    ceiling = max_tokens or tier.max_tokens
    fmt = {"type": "json_schema", "schema": structured_schema(schema)}
    version = prompt_version(system_prompt, fmt["schema"])
    # A prompt may be content blocks rather than one string, so a caller can mark
    # the part it shares across calls with `cache_control` (the governance
    # assessor sends the same passages for every framework).
    if isinstance(user_prompt, list):
        ask = list(user_prompt) + ([{"type": "text", "text": description}] if description else [])
    else:
        ask = user_prompt + (f"\n\n{description}" if description else "")
    messages = [{"role": "user", "content": ask}]
    repair = ""

    for attempt in (1, 2):
        kwargs = _tier_kwargs(tier, ceiling, system_prompt, messages, format=fmt)
        if server_tools:
            kwargs["tools"] = server_tools
        call_started = time.monotonic()
        message = await _call_with_retry(**kwargs)

        # A long server-tool turn can pause; it is resumed by sending the reply
        # back unchanged and asking again — append-only, so preserved thinking
        # stays valid. Each part is its own billed request and gets its own
        # ledger row, and the searches of every part are counted: recording only
        # the last part would hide both the money and the research done before it.
        allowed = next((t.get("max_uses", 0) for t in (server_tools or []) if "max_uses" in t), 0)
        parts = []
        resumes = 0
        while getattr(message, "stop_reason", "") == "pause_turn" and resumes < _MAX_RESUMES:
            resumes += 1
            parts.append(message)
            paused = _meta_from(message, call_started, tier, schema.__name__, "paused")
            paused.prompt_version = version
            await record_call(paused, ok=True)
            kwargs["messages"] = list(kwargs["messages"]) + [
                {"role": "assistant", "content": [_as_param(b) for b in message.content]}]
            call_started = time.monotonic()
            message = await _call_with_retry(**kwargs)

        if report is not None and server_tools:
            found = [search_report(m, allowed) for m in (*parts, message)]
            report.update({
                "web_search": True,
                "searches_used": sum(f["searches_used"] for f in found),
                "searches_allowed": allowed,
                "search_errors": [e for f in found for e in f["search_errors"]],
                "queries": [q for f in found for q in f["queries"]],
                # A page returned in two parts of one run is listed once.
                "results": list({hit["url"]: hit for f in found for hit in f["results"]}.values()),
                "parts": len(found),
            })

        payload, unstrung = _unstringify(_reply_json(message), schema)
        meta = _meta_from(message, call_started, tier, schema.__name__,
                          "+".join(p for p in (repair, unstrung) if p))
        meta.prompt_version = version
        truncated = message.stop_reason == "max_tokens"
        # One ledger row per API call, not per run: a run that needed a
        # correction round made two calls and was billed for two.
        await record_call(meta, ok=not truncated and payload is not None,
                          error=None if payload is not None or truncated else "reply was not JSON")

        if truncated:
            raise AgentTruncated(
                f"{schema.__name__} was cut off at {kwargs['max_tokens']:,} tokens "
                f"({meta.output_tokens:,} produced). Nothing partial is returned."
            )

        if payload is None:
            if attempt == 2:
                raise AgentContractError(
                    f"{schema.__name__}: the reply was not JSON (stop_reason={message.stop_reason})."
                )
            repair = "unparsed"
            messages = [{"role": "user", "content": ask}]
            continue

        try:
            data = schema.model_validate(payload)
            return AgentResult(data=data, meta=meta)
        except ValidationError as exc:
            if attempt == 2:
                raise AgentContractError(
                    f"{schema.__name__} did not validate after a correction round: {exc.errors()[:3]}"
                ) from exc
            # Structured outputs already holds the shape; what can still fail is
            # a constraint the API does not enforce (a length, a bound). Hand the
            # model its own error — it names the field and the reason — and ask
            # again from the start rather than replaying an assistant turn, which
            # on a thinking model would have to carry its thinking blocks back.
            logger.info("Agent %s failed validation, asking for a correction: %s",
                        schema.__name__, exc.errors()[:3])
            repair = "schema-retry"
            problem = ("Your previous answer did not meet these constraints:\n"
                       + json.dumps(exc.errors()[:8], default=str, indent=1)
                       + "\nAnswer again, with those fields corrected.")
            messages = [
                {"role": "user", "content": ask},
                {"role": "user", "content": problem},
            ]

    raise AgentContractError(f"{schema.__name__} could not be produced.")  # unreachable
