# Install locally

## 1. Prepare your project

Install and sign in to your coding app, then open your cloned repository as its
project. See [Preparation](preparation.md) for Git, Python and uv setup. Run these
commands in a terminal inside the repository (the folder containing `pyproject.toml`):

```sh
python3 scripts/bootstrap.py
uv sync --locked
uv run python scripts/smoke_test.py --expect-empty
```

On Windows use `python` for the first command. The empty starter should connect
with `tools: []`. After building your integration, omit `--expect-empty` and check
the agreed tool list. A working Python environment is separate from registering
the server in your AI app; complete both steps.

Keep this repository in a permanent folder. The client starts its Python process;
you do not need a separate running terminal or a public URL. Moving the folder
requires recreating `.venv` and regenerating the client configuration.

## 2. Choose the server name and installation scope

Use the actual use case as the name, for example `invoice-search` or
`weather-forecast`. Replace `invoice-search` throughout this guide with your own
name. Use lowercase letters, digits and hyphens, starting with a letter.
The helper requires `--name` and uses it for both the registration key and
`MCP_SERVER_NAME`, so the server reports the same identity. `usecase_mcp` is the
internal Python module; you do not need to rename it for each integration.

Choose where the connection should be available:

- **User setup:** your account on this computer, across projects.
- **Project setup:** only the project where you want to use the tools. This can
  be a different folder from the server's source repository.

Generated absolute paths belong to your machine. This repository ignores local
client configuration files; teammates should generate their own paths. Never put
credentials in a shared configuration. Avoid registering the same name in multiple
scopes; update the intended entry and preserve all other settings.

## 3. Connect your client

### Codex

From the server repository, generate a TOML snippet:

```sh
uv run python scripts/client_config.py codex --name invoice-search
```

Copy the complete output into **one** location:

- User setup: `~/.codex/config.toml` (the `.codex` folder in your user home).
- Project setup: `.codex/config.toml` inside the project that will use the tools.
  Codex loads this configuration only for trusted projects.

Create the folder/file if missing. If it exists, add only the generated server
section and its environment subsection; do not overwrite the file. Open that
project in Codex, reconnect/restart and inspect the MCP connection. In the CLI,
`codex mcp list` lists registrations and `/mcp` shows active servers.

To remove it, delete only the matching server and environment sections from the
same file, then reconnect. For a user registration you can also use
`codex mcp remove invoice-search`.

Source: [Codex MCP configuration](https://developers.openai.com/codex/mcp).

### Claude Code

From the server repository, print the JSON configuration:

```sh
uv run python scripts/client_config.py claude --name invoice-search
```

For project setup, merge the generated entry into `mcpServers` in `.mcp.json` at
the target project's root. Create that JSON file if absent. Keep other entries
and valid JSON syntax. Open Claude Code in that project and accept its trust
prompt if appropriate.

For private CLI registration, copy the `command` path from the output, replacing
`ABSOLUTE-VENV-PYTHON` below. Keep the quotes around paths containing spaces.
Run from the project where you want to use the server:

```sh
claude mcp add --transport stdio --scope local --env MCP_SERVER_NAME=invoice-search invoice-search -- "ABSOLUTE-VENV-PYTHON" -m usecase_mcp
```

Choose one scope: `local` is private to you for this project (stored in your
home `~/.claude.json`); `user` makes it available across your projects; `project`
writes `.mcp.json` for the project. Change `--scope local` accordingly. File setup
and CLI registration are alternatives, so choose one.

Run `claude mcp list`, then `/mcp` inside Claude Code to inspect the connection.
Remove a CLI entry with `claude mcp remove --scope local invoice-search`, using
the scope you selected. For file setup, remove only its `.mcp.json` entry.
Restart/reconnect afterwards.

Source: [Claude Code MCP configuration](https://code.claude.com/docs/en/mcp).

### Claude Desktop

Claude Desktop is a destination for the finished server. Build the integration
using Codex or Claude Code first, then follow [Bundles](bundles.md) for packaging,
Python selection, installation, private settings and removal.

## 4. Verify credentials and your first question

The generated configuration contains only a non-secret server name. For your
integration, follow its private credential setup instructions. The starter does
not load `.env` automatically; a GUI app may not inherit your terminal variables.
Verify that required variables are available without printing their values.

Check that the expected tools appear and ask one of your agreed questions, such
as “Find the latest five invoices” for an implemented invoice lookup integration.
Inspect a bounded read result. Registration alone does not prove live access.
The starter has zero tools, so a client may flag it as empty until implementation.

## Troubleshooting and stopping

- Command not found: finish prerequisite installation and reopen your terminal.
- Python missing/startup failure: run `uv sync --locked` in the source repository,
  regenerate the configuration and confirm its command points inside `.venv`.
- Server absent: check the selected scope, target project and client trust state.
- Wrong name: regenerate with your use-case `--name` and remove the stale entry.
- No tools: expected for the starter; after implementation check tool registration.
- Authentication failure: check private credential availability and service scopes.

Run `uv run python scripts/smoke_test.py` to separate server startup failures from
client configuration problems. Logs must go to stderr. Disable/remove the client
entry and reconnect to stop its managed server. Use Ctrl+C for a manually started
process. Keep your source folder if you want to resume development later.
