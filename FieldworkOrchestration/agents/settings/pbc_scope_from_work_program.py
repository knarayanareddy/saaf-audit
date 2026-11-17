"""Run configuration for the pbc_scope_from_work_program agent."""

# Phase 1 — per-control atomization, run in a batch (ClaudeClient.message_batch):
# splitting one control's short evidence strings into parts is simple
# extraction, not judgement, and batching ~halves the per-token cost on top.
#
# max_tokens sized for a control with many/verbose test steps, not just the
# demo file's 9 controls — a real work program can have far more ToE steps
# per control, and 1024 truncated (JSONDecodeError) on one. The extraction
# loop also falls back to un-split items per step if a response still can't
# be parsed, so a single bad control can't crash the whole work program.
EXTRACT_SETTINGS = {
    "model": "claude-sonnet-4-6",
    "max_tokens": 3072,
    "thinking": None,
}

# Phase 2 — single call over the already-atomized list: matching "is this
# the same underlying document as that" across controls is a judgement
# call, but the input is now short tagged phrases, not the full verbose
# work program, so this stays fast and cheap despite using Opus.
#
# thinking deliberately off: measured against a real 158-item work program,
# "adaptive" thinking consumed its entire token budget on thinking alone
# even at max_tokens=12000, leaving zero room to write the actual JSON
# (stop_reason "max_tokens", output all thinking_tokens) -- disproportionate
# for what is fundamentally short-phrase clustering, not multi-step
# reasoning. Without it, the same task needs far fewer tokens and actually
# completes.
CONSOLIDATE_SETTINGS = {
    "model": "claude-opus-4-8",
    "max_tokens": 8192,
    "thinking": None,
}
