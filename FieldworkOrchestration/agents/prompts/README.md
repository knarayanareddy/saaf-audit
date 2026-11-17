# `agents/prompts/`

Prompt text for every agent. **Prompts only** — no API calls, no file I/O, no
business logic. A module here should import nothing but the standard library.

## What to add

One module per agent, named after the agent slug (`basic.py` is the existing
example — a connection check used as the default prompt by `claude_init.py`):

```
prompts/
  basic.py              # default connection-check prompt
  <agent_name>.py       # one per fieldwork agent
  orchestrator.py       # prompts the orchestrator itself uses
```

## Conventions

- Export prompts as module-level `UPPER_SNAKE_CASE` constants:
  `SYSTEM_PROMPT`, `USER_PROMPT_TEMPLATE`, and any extras the agent needs.
- Use `str.format` placeholders for anything variable
  (`"Review this report:\n\n{report_text}"`); the agent fills them in. Do not
  build prompts by concatenating in the agent module.
- Never inline field data, client names, or other input content here — that
  belongs in `../data/` and gets injected through a placeholder.
- Give each module a docstring saying which agent owns it and what the prompt is
  for.
- Prompts are reviewed like code: change them in a commit of their own so the
  diff shows exactly what wording changed.
