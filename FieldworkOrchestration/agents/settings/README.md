# `agents/settings/`

Per-agent run configuration: which model, how many tokens, whether to think,
which tools. Keeping it here means model choices can be reviewed and changed in
one place instead of being buried in call sites.

## What to add

One module per agent, named after the agent slug:

```
settings/
  <agent_name>.py       # one per fieldwork agent
  orchestrator.py       # settings for the orchestrator run itself
  defaults.py           # optional: values the agent modules build on
```

## Conventions

- Export a single module-level `SETTINGS` dict (or dataclass) the agent passes
  straight into `ClaudeClient`:

  ```python
  SETTINGS = {
      "model": "claude-opus-4-8",   # heavy reasoning; use a cheaper model where it fits
      "max_tokens": 16000,
      "thinking": "adaptive",       # or omit for simple extraction/classification
  }
  ```

- Pick the model per agent on purpose — Opus for planning and judgement, Sonnet
  for the middle ground, Haiku for cheap classification and extraction. Say why
  in a comment.
- **Configuration only, no secrets.** API keys come from the environment
  (`ANTHROPIC_API_KEY` via `.env`); `CLAUDE_MODEL` overrides the default model
  globally for local experiments.
- Anything that changes per run (paths, the report being processed, dates) is an
  argument to the agent, not a setting.
