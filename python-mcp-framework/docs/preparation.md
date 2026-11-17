# Preparation

Use a local folder you can edit. Install:

- [Git](https://git-scm.com/downloads): verify with `git --version`.
- [Python](https://www.python.org/downloads/) 3.11 or later: verify with
  `python3 --version` on macOS or `python --version` on Windows.
- [uv](https://docs.astral.sh/uv/getting-started/installation/): verify with
  `uv --version`. Restart your terminal after installation if it is not found.
- Codex or Claude Code to guide development. Claude Desktop is an optional
  destination for the finished server, not the coding environment for this guide.

On Windows, enable Python's PATH option during installation. On macOS, avoid
relying on an old system Python. The agent should check the actual interpreter.
An account/subscription for your coding app may be required separately.

## Set up your account and project

Sign in to Codex or Claude Code and confirm you can start a conversation. Clone
this repository using the README instructions. Open the cloned folder as a project
in Codex, or run `claude` from a terminal inside it. Start the task there so the
agent can read `AGENTS.md`, edit the source and run checks. A fresh clone provides
a separate starting point for each integration.

Choose a permanent source folder named for your use case. Later, installation
registers the finished server either for your user account or for a specific
project; see [Install locally](installation.md). No client settings are changed by
the preparation commands.

## Prepare the Python environment

From the project folder, run `python3 scripts/bootstrap.py` (Windows: `python`).
The helper verifies Git and uv, clones the official SDK at the version in
`reference.json`, and checks its origin, clean working tree, commit, and examples.
It reuses a matching clone without fetching or overwriting it. Then run
`uv sync --locked` to create `.venv` and install the locked packages.

If GitHub cannot be reached, resolve your network/proxy/access issue first. If an
existing reference is modified or at another revision, move it aside yourself
before rerunning. The helper does not delete your work or reset a checkout.
Never silently substitute an unverified download for the required clone.

Read the examples listed in `reference.json` from `.references/python-sdk`.
For a new integration, record the additional examples used in local progress.
The cloned quickstart uses HTTP; reuse its registration patterns, while retaining
this starter's stdio transport. SDK v1 and v2 APIs differ; use the pinned version.

`.env.example` documents variable names only. The starter reads process
environment variables and does not automatically load a `.env` file. During
integration, choose and document a private credential entry/storage method
appropriate for the selected app. Do not type credentials into the agent chat.
