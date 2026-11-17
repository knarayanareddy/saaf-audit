# Verification

Run from the project folder:

```sh
uv sync --locked
uv run pytest
uv run ruff check .
uv run python scripts/smoke_test.py --expect-empty
```

The smoke test starts a subprocess, initializes a real MCP session and lists
tools with a 20-second deadline. It never calls external tools. The starter must
return an empty list. Once you add tools, update the corresponding test to assert
their agreed names and omit `--expect-empty` for the manual smoke test.

Tests also cover clone/reuse behavior, origin/revision/local-change rejection,
missing prerequisites, a failed clone, parseable client configs and bundle source
exclusions. Mocked clone tests avoid requiring the network for every test run;
run the actual bootstrap separately to verify your real GitHub access.

For a clean installation, copy only distributable source to a fresh folder and
run `uv sync --locked` and the smoke test there. Test paths containing spaces.
For a bundle, validate its manifest with the official MCPB CLI and run its
extracted launcher with a matching clean Python environment, as in bundles.md.

Rehearse [the three scenarios](scenarios.md) against AGENTS.md. These prose
checks verify guidance coverage; they are not claims of live API/database tests.
After implementing a real integration, add its success and failure tests, including
denied writes, before using any account with write privileges.

Record actual checks and platform limitations in docs/verification.md. Never
equate protocol success with successful installation in a graphical client.
