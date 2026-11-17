# Python MCP Starter

An open-source starting point for anyone to build a local MCP server with guidance from Codex or Claude Code.
Describe your idea; your coding agent helps investigate it, asks the necessary
questions, builds the integration, tests it, and connects it to your app.

**This starter contains no ready-made tools.** It provides a runnable Python
server, a guided workflow, and installation helpers. No model API key is needed
for the server itself; your chosen coding agent has its own access requirements.

## What is MCP?

MCP (Model Context Protocol) is a shared way for AI applications to discover and
call tools. Your coding agent is the assistant; this Python server provides the
tools; an external API, website, or database supplies the data or actions.
The local app starts this server and communicates over **stdio** (standard input
and output). You do not need a public URL, web server, or cloud deployment.
External services may still require an internet connection and authentication.

## Start here

1. Install Git, Python 3.11+ and uv using [Preparation](docs/preparation.md).
2. Clone this repository into your own working folder. Replace `YOUR-REPO-URL`
   with this repository's GitHub URL once published:

   ```sh
   git clone YOUR-REPO-URL my-mcp
   cd my-mcp
   ```

3. Sign in to Codex or Claude Code. In Codex, add/open the cloned folder as a
   project and start a task in it. In Claude Code, open a terminal in this folder
   and run `claude`. The agent must see this repository's `AGENTS.md`. Send:

   > Read AGENTS.md and guide me through building my own MCP server. Start by
   > checking prerequisites and cloning the required SDK reference. My idea is: …

4. The agent runs the preparation steps below, asks about your needs, and builds
   only your chosen integration. You can also run preparation yourself:

   ```sh
   python3 scripts/bootstrap.py
   uv sync --locked
   uv run python scripts/smoke_test.py --expect-empty
   ```

   On Windows PowerShell, use `python` instead of `python3` for the first command.
   An empty tool list is expected until you build your integration.

5. Once your integration passes its tests, follow [Install locally](docs/installation.md).
   That guide explains naming, user versus project setup, connection checks and removal.

## What you will do together

Prepare → clone the SDK → describe your use case → verify access → agree on
tools and permissions → build and test → install → try your own example questions.
The agent saves non-secret progress in the ignored `.local/` folder so you can
continue later. You do not need to answer everything at once.

Ideas include checking public weather data, reading selected records from your
database, or looking up information behind an authenticated API. These are intake
examples, not implemented features. Writes are disabled by design until you and
the agent explicitly agree on them and implement appropriate restrictions.

## What's inside

- `AGENTS.md`: step-by-step instructions for your coding agent.
- `src/usecase_mcp/`: the empty server, settings, and places for tools/clients.
- `scripts/`: preparation, protocol check, config output and bundle builder.
- `reference.json`: pinned official SDK revision and example paths.
- `packaging/`: optional Claude Desktop bundle template and launcher.
- `docs/`: [intake](docs/intake-template.md), [security](docs/security.md),
  [installation](docs/installation.md), [bundles](docs/bundles.md),
  [testing](docs/testing.md), and [example scenarios](docs/scenarios.md).

The official SDK is installed as a locked dependency. Its separate Git clone is
mandatory learning/reference material and is excluded from your repository.
No external integrations, hosted services, Git repository, or GitHub remote are
created automatically. Before publishing, replace the clone URL above.

## Develop and check

```sh
uv sync --locked
uv run pytest
uv run ruff check .
uv run python scripts/smoke_test.py --expect-empty
```

`uv run mcp-starter` starts the stdio server and waits for protocol input; it does
not open a web page. Use the smoke test or a connected client to interact with it.
Press Ctrl+C to stop a manually started server.

## References

- [Official Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Python SDK documentation](https://py.sdk.modelcontextprotocol.io/)
- [Codex MCP configuration](https://developers.openai.com/codex/mcp)
- [Claude Code MCP configuration](https://code.claude.com/docs/en/mcp)
- [MCP Bundles specification](https://github.com/modelcontextprotocol/mcpb)

MIT licensed. See [LICENSE](LICENSE).
