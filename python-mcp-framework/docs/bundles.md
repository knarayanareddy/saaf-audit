# Optional Claude Desktop bundle

A `.mcpb` (formerly `.dxt`) is a ZIP containing a server and manifest. This route
is for Claude Desktop clients supporting MCPB, not a universal Codex installer.
Use [stdio configuration](installation.md) for Codex and Claude Code.

## Build

Finish and test your integration first. Update `packaging/manifest.json` with its
use-case `name` (e.g. `invoice-search`), display name, version, description,
author, and required user settings. Set `server.mcp_config.env.MCP_SERVER_NAME`
to the same use-case name. Replace the generic starter identity before sharing. For secrets, use
the specification's `sensitive: true` settings and reference them in
`server.mcp_config.env` as `${user_config.setting_name}`. Never put actual values
in the manifest. Add privacy-policy URLs for any external data-processing services.

Run on the intended target OS and CPU architecture, using the target Python:

```sh
uv sync --locked
uv run python scripts/build_bundle.py
```

The builder exports locked runtime dependencies, installs their hash-verified
wheels into a temporary `lib/`, copies only Python files from `src/usecase_mcp`,
and adds the launcher, manifest, MIT license and build information. Third-party
package metadata/licenses stay with their wheels. It fails if compatible wheels
are unavailable rather than compiling silently. It needs network/cache access.

Output is `dist/USE-CASE-NAME-0.1.0-OS-ARCH-pyVERSION.mcpb`. It excludes your `.env`,
local progress, client configs, reference clone, tests and development environment.
The source allowlist does not detect secrets hardcoded inside Python; review
source before sharing. If your integration requires non-Python assets, deliberately
extend the allowlist and its tests. Do not package the entire project folder.

**Python is not included.** Native dependencies require the same OS, architecture
and Python major/minor as the build. `BUILD-INFO.json` states these requirements;
the launcher checks them. Build separate bundles for different targets. There is
no cross-platform or Python-free installer in this starter.

## Validate and try it

The official [MCPB CLI](https://github.com/modelcontextprotocol/mcpb/blob/main/CLI.md)
provides manifest validation. With Node/npm installed, extract the archive into a
temporary directory, then run `npx @anthropic-ai/mcpb validate PATH/manifest.json`.
Use `python -m zipfile -e PATH/FILE.mcpb PATH/EXTRACTED` to extract it. The archive
is already packed by the Python builder; do not repack the repository root.

Test the extracted server with the matching Python interpreter:

```sh
uv run python scripts/smoke_test.py --bundle PATH/EXTRACTED/server.py
```

Install the `.mcpb` through Claude Desktop's local extension settings (labels may
vary by version). Select the matching Python executable in the required setting,
enter any secrets privately, and verify the actual tool list and a safe call.
An empty starter bundle has no tools and is useful only as a packaging check.
Disable/uninstall through the same extension settings to stop using it.

If startup fails, compare the chosen interpreter against `BUILD-INFO.json`, inspect
stderr, and confirm that `src/` and `lib/` were packaged. GUI install success and
live authentication must be checked separately; CLI validation cannot prove them.

Source: [manifest specification](https://github.com/modelcontextprotocol/mcpb/blob/main/MANIFEST.md).
