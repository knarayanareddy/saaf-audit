# SAAF Hackathon — Session 1 Recap

This folder contains the recap for the first SAAF hackathon (March 10, 2026, Mollie Amsterdam).

## Files

| File | Description |
|------|-------------|
| `recap-session-1.md` | Publishable Markdown recap document |
| `recap-session-1.pdf` | Final PDF for GitHub (generated from Markdown) |
| `repo_data.json` | _(gitignored)_ Raw repo data fetched from GitHub API |
| `repo_data_raw/` | _(gitignored)_ Per-repo JSON files |
| `overlap_analysis.json` | _(gitignored)_ Domain/tech overlap analysis |

## How to regenerate

### Prerequisites

```bash
brew install gh pandoc
gh auth login   # needs repo + read:org scopes
```

### Steps

```bash
# 1. Fetch all SAAF-Project org repos
python3 SAAF-Project/tools/scripts/scrape_hackathon_repos.py

# 2. Analyze domain and tech overlaps
python3 SAAF-Project/tools/scripts/analyze_overlaps.py

# 3. Generate the Markdown recap
python3 SAAF-Project/tools/scripts/generate_recap.py

# 4. Review and edit recap-session-1.md as needed, then convert to PDF
pandoc \
  "SAAF-Project/hackathon-recap/recap-session-1.md" \
  --output "SAAF-Project/hackathon-recap/recap-session-1.pdf" \
  --pdf-engine=xelatex \
  --table-of-contents --toc-depth=3 --number-sections \
  --highlight-style=tango
```

> **Note:** `repo_data.json` and `repo_data_raw/` are gitignored because they contain private repository information. The `overlap_analysis.json` is also gitignored as it is a generated artifact derived from private data.
