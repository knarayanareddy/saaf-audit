# AI-Digital-Resilience-Hero

This agent scans all repositories for AI Enabled Cyber Threats such as Prompt Injection.

It finds content in a repository that tries to manipulate the AI models and coding agents that read it: hidden instructions, invisible Unicode smuggling, fake chat-role delimiters and similar payloads. Fast pattern rules do the detection. Claude can optionally review the findings to filter out false positives.

## Requirements

- Node.js 20 or newer
- git
- A GitHub token (`GITHUB_TOKEN`) for private repositories and higher API rate limits
- For `--llm`: an Anthropic API key (`ANTHROPIC_API_KEY`) or an `ant auth login` profile

## Install

```bash
npm install
npm install @anthropic-ai/sdk
npm install -D typescript tsx @types/node
npm run build
```

## Usage

```bash
# Scan every repository in a GitHub organization
GITHUB_TOKEN=ghp_... node dist/cli.js --org SAAF-Project

# Scan a local checkout
node dist/cli.js --path ../some-repo

# Let Claude review the findings and hide the false positives
node dist/cli.js --org SAAF-Project --llm --hide-benign

# Write a JSON report for CI
node dist/cli.js --org SAAF-Project --format json --output drh-report.json
```

Exit codes: `0` means nothing at or above `--fail-on` was found (default `high`), `1` means such findings exist, `2` means an error occurred. This lets the scanner fail a CI job.

## Detection rules

| ID    | Severity | What it detects |
|-------|----------|-----------------|
| PI001 | critical | Unicode tag characters (U+E0000–E007F) that hide ASCII text from humans; the hidden text is decoded in the report |
| PI002 | high     | Bidirectional control characters (Trojan Source) |
| PI003 | medium   | Clusters of zero-width characters |
| PI010 | high     | Instruction-override phrases ("ignore previous instructions", "you are now…", Dutch variants) |
| PI011 | medium   | Fake chat-template or role delimiters (`<\|im_start\|>`, `[INST]`, `System:`) in text and markup files |
| PI020 | high     | HTML comments that address an AI model with instructions |
| PI021 | medium   | Text hidden with CSS (`display:none`, `font-size:0`) in Markdown, HTML or SVG |
| PI030 | high     | Base64 blobs that decode to an injection phrase |
| PI040 | medium   | Markdown links or images with placeholders that an agent could fill with secrets (data exfiltration) |

Snippets in the report are sanitized: invisible characters are shown as `<U+XXXX>` instead of being printed raw.

## Development

```bash
npm test          # run the rule tests
npm run dev -- --path .
```
