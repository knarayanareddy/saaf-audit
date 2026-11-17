"""Which model does which job, and what it costs.

Every one of the fifty-odd agent calls in this platform used the same model. A
sixty-token title suggestion and a twelve-criterion GIAS peer review were served
by identical machinery, which is wasteful in one direction and underpowered in
the other. Nowhere did an agent get room to think, not even the two whose entire
job is to disagree well.

Three tiers, and the rule for choosing between them is about consequence, not
about length:

* **quick** — the answer is short, the shape is obvious, and being wrong is
  cheap and instantly visible. Suggesting a title. Deciding whether to ask a
  question at all.
* **draft** — the agent produces something a human will read line by line before
  it counts. Most of this platform lives here; the human review is the safety
  net that makes it the right default.
* **judge** — the output IS the judgement. A peer-review rating, a challenge to
  another agent's severity call, an opinion on a finished report. Nobody downstream
  re-derives it, so it has to be right the first time and defensible afterwards.
  This tier gets the strongest model and explicit reasoning room.

Extended thinking is reserved for `judge` on purpose. It is exactly the tier
where a model that reasons before answering changes the answer, and exactly the
tier where the cost is justified by what depends on it.

**On prices.** The table below is configuration, not fact. It is what this
deployment has been told the models cost, so that spend can be reported in money
rather than in tokens — verify it against current published pricing and change it
here. Nothing computes anything but arithmetic on these numbers.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Tier:
    """A model, its ceiling, and whether it gets room to think."""
    name: str
    model: str
    max_tokens: int
    #: How hard this tier is asked to think, or "" for not at all. It used to be
    #: a token budget, which the API no longer accepts for this model: sending
    #: `thinking: {type: enabled, budget_tokens: N}` to claude-opus-5 returns
    #: 400 "not supported for this model. Use thinking.type.adaptive and
    #: output_config.effort". So every judge-tier agent — the GIAS peer review,
    #: the rating challenge, the coherence check, the report opinion — was
    #: failing outright on a rejected request, and the tests could not see it:
    #: they assert the shape of what gets sent against a scripted client, which
    #: answers whatever it is asked. See tests/test_model_tiers.
    effort: str = ""
    note: str = ""

    @property
    def thinks(self) -> bool:
        return bool(self.effort)


QUICK = Tier(
    # 1,536 rather than the 1,024 Haiku 4.5 had: Haiku 5.5's tokenizer counts the
    # same text as roughly 30% more tokens, so the old ceiling would cut off an
    # answer of the same length.
    "quick", "claude-haiku-5-5", 1536,
    note="short answers where being wrong is cheap and obvious",
)
DRAFT = Tier(
    "draft", "claude-sonnet-5-5", 4096,
    note="drafts a human reads line by line before they count",
)
JUDGE = Tier(
    # max_tokens must leave room for the reasoning AND the answer after it. With
    # adaptive thinking the model decides how much reasoning it needs, so the
    # ceiling is the one guard left: a run that truncates mid-thought produces
    # nothing at all.
    "judge", "claude-opus-5-5", 12_000, effort="high",
    note="the output is the judgement; nobody downstream re-derives it",
)

TIERS = {t.name: t for t in (QUICK, DRAFT, JUDGE)}

#: The generation before the 5.5 migration, kept so that an agent which measures
#: worse on the new model can be pinned back to the old one by name in
#: AGENT_TIER — with the reason beside it — instead of the whole tier moving back.
PREVIOUS = {
    "quick": Tier("quick", "claude-haiku-4-5-20251001", 1024, note=QUICK.note),
    "draft": Tier("draft", "claude-sonnet-5", 4096, note=DRAFT.note),
    "judge": Tier("judge", "claude-opus-5", 12_000, effort="high", note=JUDGE.note),
}


# ── What each model accepts ──────────────────────────────────────────────────
# The rules differ per model and they are not small: on Opus 5.5 thinking cannot
# be switched off at all; on Sonnet 5.5 "off" is spelled `between_tools` and
# `disabled` is a 400; on Haiku 5.5 `disabled` is fine. Before this function the
# same decision was written out in four places, and the judge tier was dead for
# weeks because one of them sent a shape the model had stopped accepting.
#: Models that may be served by Anthropic's server-side fallback when their own
#: safety classifier declines. Haiku 5.5 has none; the older models predate it.
_FALLBACK_MODELS = {"claude-opus-5-5", "claude-sonnet-5-5"}
_FALLBACK_BETA = "server-side-fallback-2026-07-01"


def request_params(tier: Tier) -> dict:
    """The thinking, effort and fallback settings for one call on this tier.

    Returns `{"extra_body": {...}, "extra_headers": {...}}`, which is how the
    installed SDK (0.40) forwards fields it has no parameter for. Callers that
    add their own `output_config` (structured outputs) merge into it rather
    than replace it — see `merge_output_config`.
    """
    model = tier.model
    body: dict = {}
    if model == "claude-opus-5-5":
        # Thinking is always on and cannot be disabled; effort is the only
        # control, and its default here is "medium", one below Opus 5's.
        body["output_config"] = {"effort": tier.effort or "medium"}
    elif model == "claude-sonnet-5-5":
        if tier.thinks:
            body["thinking"] = {"type": "adaptive"}
            body["output_config"] = {"effort": tier.effort}
        else:
            # The lowest thinking setting this model has. Valid at effort high
            # or below, with no other field inside `thinking`.
            body["thinking"] = {"type": "between_tools"}
            body["output_config"] = {"effort": "high"}
    elif tier.thinks:
        body["thinking"] = {"type": "adaptive"}
        body["output_config"] = {"effort": tier.effort}
    else:
        # Haiku 5.5 (at its default effort, medium) and the previous generation
        # all accept an explicit off — and need it, or the ceiling is spent on
        # reasoning nobody asked for.
        body["thinking"] = {"type": "disabled"}

    headers: dict = {}
    if model in _FALLBACK_MODELS:
        # A safety decline on a benign audit request (a cyber-controls review is
        # exactly that) is retried server-side on the model Anthropic recommends
        # for that category, instead of becoming an outage. Only some categories
        # are retried; the rest still arrive as a refusal and are reported.
        body["fallbacks"] = "default"
        headers["anthropic-beta"] = _FALLBACK_BETA
    return {"extra_body": body, "extra_headers": headers}


def merge_output_config(body: dict, **fields) -> dict:
    """Add to `output_config` without dropping the effort already in it."""
    merged = dict(body)
    merged["output_config"] = {**(body.get("output_config") or {}), **fields}
    return merged


# ── What each agent is worth ─────────────────────────────────────────────────
# Keyed by the schema or the agent it belongs to, so the choice is visible in one
# list instead of being an argument buried at fifty call sites. An agent with no
# entry gets DRAFT, which is the safe default: reviewed by a human either way.
AGENT_TIER: dict[str, Tier] = {
    # The output is the judgement.
    "PeerReview": JUDGE,          # rates a whole engagement against GIAS
    "RatingChallenge": JUDGE,     # exists to disagree with another agent, or not
    "coherence": JUDGE,           # engagement-wide contradictions
    "report_opinion": JUDGE,      # the overall audit opinion

    # Drafts a human will review.
    "GovernanceAssessment": DRAFT,
    "FindingDraft": DRAFT,
    "WorkProgram": DRAFT,        # the auditor signs it off row by row
    "DocumentRequestList": DRAFT,  # the auditor decides what is actually asked for
    "Frameworks": DRAFT,
    "Requirements": DRAFT,
    "ScopeContribution": DRAFT,
    "SupervisoryGuidance": DRAFT,
    "RcsaMappingProposal": DRAFT,   # a person confirms every column before anything is stored

    # Short, cheap, instantly checkable.
    "title_suggestion": QUICK,
    "proactive_question": QUICK,
    "query_generation": QUICK,
    "SearchQueries": QUICK,      # five short strings, checked by the search that follows
}


def tier_for(key: str | None) -> Tier:
    """The tier for an agent or schema name; DRAFT when nothing is registered."""
    return AGENT_TIER.get(key or "", DRAFT)


# ── Prices ───────────────────────────────────────────────────────────────────
# USD per million tokens, as configured for this deployment. VERIFY against
# current published pricing before relying on the money figures; they are here so
# that a run can report what it spent in a unit an auditor recognises, and the
# arithmetic is worth exactly as much as these numbers are.
PRICES_VERIFIED_ON = "2026-10-06, Anthropic model reference (first-party API list prices)"

# These were $15/$75 for Opus 5 and $3/$15 for Sonnet 5 until 2026-10-22 — the
# prices of an earlier generation, never updated. Every money figure the ledger
# showed was 1.5x (draft) to 3x (judge) too high, which is the one direction a
# cost report must never be wrong in silently: it made the platform look
# expensive in exactly the demos where it was being judged on that.
#
# Per model, because the cache is not priced as one fraction everywhere: Opus 5.5
# reads from cache at 0.05x its input rate, the others at 0.1x. `cache_write` is
# the 5-minute write, 1.25x input — the only TTL this platform uses.
PRICES: dict[str, dict[str, float]] = {
    "claude-opus-5": {"input": 5.0, "output": 25.0, "cache_read": 0.50, "cache_write": 6.25},
    "claude-sonnet-5": {"input": 2.0, "output": 10.0, "cache_read": 0.20, "cache_write": 2.50},
    "claude-haiku-4-5-20251001": {"input": 1.0, "output": 5.0, "cache_read": 0.10, "cache_write": 1.25},
    # Haiku 5.5 is listed for prompts up to 100K tokens; above that it costs
    # $0.50/$2.50, which no agent here comes near.
    "claude-opus-5-5": {"input": 4.0, "output": 20.0, "cache_read": 0.20, "cache_write": 5.00},
    "claude-sonnet-5-5": {"input": 2.0, "output": 10.0, "cache_read": 0.20, "cache_write": 2.50},
    "claude-haiku-5-5": {"input": 0.10, "output": 0.50, "cache_read": 0.01, "cache_write": 0.125},
}

#: What the copilot may spend on one engagement before it stops starting work by
#: itself. Expressed in money rather than in task count, because twenty tasks on
#: the judge tier and twenty title suggestions are not the same commitment.
#: Living here rather than with the orchestrator keeps it next to the prices that
#: give it meaning — and out of an import cycle with the routers.
AUTO_SPEND_BUDGET_USD = 5.00


def cost_usd(model: str, input_tokens: int, output_tokens: int, cached_tokens: int = 0,
             cache_write_tokens: int = 0) -> float | None:
    """What one call cost, or None when this model has no price configured.

    None rather than zero: a model nobody has priced costing "nothing" is the
    kind of silent falsehood this codebase has spent three layers removing.

    The three input figures are separate in the API's usage and are added, not
    netted: `input_tokens` is only the part that was neither read from nor
    written to the cache. This used to compute `input - cached` on the theory
    that cached tokens sat inside `input_tokens`. They do not — so the
    subtraction went negative, was floored at zero, and the call's genuinely
    uncached input was counted as free. Cache writes were not counted at all.
    Every call caches its system prompt, so every money figure was low; measured
    on 2026-10-22 when the governance passages were first cached and call 1
    showed 87 input tokens for a 28,000-character prompt.
    """
    price = PRICES.get(model)
    if not price:
        return None
    return (
        input_tokens * price["input"]
        + cached_tokens * price.get("cache_read", price["input"] * 0.10)
        + cache_write_tokens * price.get("cache_write", price["input"] * 1.25)
        + output_tokens * price["output"]
    ) / 1_000_000


def format_cost(value: float | None) -> str:
    """Money, at a precision that does not pretend to more accuracy than it has."""
    if value is None:
        return "cost not priced"
    if value < 0.01:
        return f"${value:.4f}"
    return f"${value:.2f}"


def estimate_cost(tier: Tier, prompt_chars: int, expected_output_tokens: int | None = None) -> float | None:
    """A rough cost for a run that has not happened yet — for a confirm dialog.

    Four characters to the token is the usual English approximation and is
    accurate enough to tell an auditor whether they are about to spend a cent or
    a euro, which is the only question the dialog is really asking.
    """
    input_tokens = prompt_chars // 4
    output_tokens = expected_output_tokens if expected_output_tokens is not None else tier.max_tokens // 2
    return cost_usd(tier.model, input_tokens, output_tokens)
