# Tools

Scripts, APIs, and integrations that power audit agent capabilities.

> **Shared utilities only.** This folder is for shared, reusable scripts and integrations
> (data extraction, generators, the transcription tooling, MCP connectors, etc.) — **not**
> full standalone agents. A complete agent belongs in its **own dedicated repo** in the
> SAAF-Project org. See [`../docs/getting-started.md`](../docs/getting-started.md#building-an-agent).

## Subfolders

| Folder | Contents |
|---|---|
| [`scripts/`](scripts/) | Python and shell scripts for data extraction, transformation, and analysis |
| [`strapi/`](strapi/) | Local Strapi sandbox with deterministic synthetic audit datasets and API schemas |
| [`apis/`](apis/) | API connection templates and connector utilities |
| [`integrations/`](integrations/) | MCP servers, GitHub CLI hooks, version control integrations |
| [`automation/`](automation/) | File organization and workflow automation utilities |

## Contributing

- Include a docstring or header comment in every script explaining its purpose, inputs, and outputs.
- Read credentials from environment variables — never hardcode secrets.
- Test scripts against synthetic or anonymized data before sharing.
- Add a `requirements.txt` or inline comment listing any non-standard dependencies.
