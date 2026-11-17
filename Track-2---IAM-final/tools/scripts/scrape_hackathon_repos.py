#!/usr/bin/env python3
"""
scrape_hackathon_repos.py
Fetches all repos from the SAAF-Project GitHub org and writes structured JSON.

Usage:
    python3 SAAF-Project/tools/scripts/scrape_hackathon_repos.py
"""

import json
import logging
import subprocess
import base64
from pathlib import Path
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

ORG = "SAAF-Project"
OUTPUT_DIR = Path(__file__).parents[2] / "hackathon-recap"
RAW_DIR = OUTPUT_DIR / "repo_data_raw"
OUTPUT_FILE = OUTPUT_DIR / "repo_data.json"

RAW_DIR.mkdir(parents=True, exist_ok=True)


def gh(*args) -> Optional[Any]:
    """Run a gh CLI command and return parsed JSON, or None on error."""
    cmd = ["gh"] + list(args)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        logger.warning("gh command failed: %s\nstderr: %s", " ".join(cmd), e.stderr.strip())
        return None
    except json.JSONDecodeError as e:
        logger.warning("JSON parse error for command %s: %s", " ".join(cmd), e)
        return None


def fetch_repos() -> List[Dict]:
    logger.info("Listing repos for org: %s", ORG)
    data = gh(
        "repo", "list", ORG,
        "--limit", "200",
        "--json", "name,description,url,isPrivate,isFork,isArchived,createdAt,pushedAt,languages,repositoryTopics,defaultBranchRef",
    )
    if not data:
        logger.error("Could not fetch repo list — aborting")
        raise SystemExit(1)
    logger.info("Found %d repos", len(data))
    return data


def fetch_readme(repo_name: str) -> Optional[str]:
    data = gh("api", f"repos/{ORG}/{repo_name}/readme")
    if not data:
        return None
    try:
        content_b64 = data.get("content", "")
        # GitHub pads with newlines inside the base64 string
        decoded = base64.b64decode(content_b64.replace("\n", "")).decode("utf-8", errors="replace")
        return decoded
    except Exception as e:
        logger.warning("Could not decode README for %s: %s", repo_name, e)
        return None


def fetch_commits(repo_name: str) -> List[Dict]:
    data = gh("api", f"repos/{ORG}/{repo_name}/commits")
    if not isinstance(data, list):
        return []
    simplified = []
    for c in data[:10]:
        simplified.append({
            "sha": c.get("sha", "")[:8],
            "message": (c.get("commit", {}).get("message") or "").splitlines()[0],
            "author": c.get("commit", {}).get("author", {}).get("name"),
            "date": c.get("commit", {}).get("author", {}).get("date"),
        })
    return simplified


def fetch_issues(repo_name: str) -> List[Dict]:
    data = gh("api", f"repos/{ORG}/{repo_name}/issues")
    if not isinstance(data, list):
        return []
    return [
        {
            "number": i.get("number"),
            "title": i.get("title"),
            "state": i.get("state"),
            "labels": [l.get("name") for l in i.get("labels", [])],
        }
        for i in data[:20]
        if i.get("pull_request") is None  # exclude PRs
    ]


def fetch_languages(repo_name: str) -> dict:
    return gh("api", f"repos/{ORG}/{repo_name}/languages") or {}


def enrich_repo(repo: dict) -> dict:
    name = repo["name"]
    logger.info("  Fetching details for: %s", name)

    readme = fetch_readme(name)
    commits = fetch_commits(name)
    issues = fetch_issues(name)
    # fetch_languages returns a dict {lang: bytes} from the API
    api_languages = fetch_languages(name)

    # Normalize topics — repositoryTopics may be null in JSON
    raw_topics = repo.get("repositoryTopics") or []
    topics = []
    for t in raw_topics:
        if isinstance(t, dict):
            topics.append(t.get("name") or (t.get("topic") or {}).get("name", ""))
        elif isinstance(t, str):
            topics.append(t)

    # Normalize languages — gh repo list returns [{size, node: {name}}], not a dict
    raw_langs = repo.get("languages") or []
    if isinstance(raw_langs, list):
        languages_dict = {item["node"]["name"]: item["size"] for item in raw_langs if isinstance(item, dict) and "node" in item}
    elif isinstance(raw_langs, dict):
        languages_dict = raw_langs
    else:
        languages_dict = {}
    # Merge with API language data (API is authoritative for byte counts)
    if api_languages:
        languages_dict = api_languages

    enriched = {
        "name": name,
        "description": repo.get("description"),
        "url": repo.get("url"),
        "is_private": repo.get("isPrivate"),
        "is_fork": repo.get("isFork"),
        "is_archived": repo.get("isArchived"),
        "created_at": repo.get("createdAt"),
        "pushed_at": repo.get("pushedAt"),
        "default_branch": (repo.get("defaultBranchRef") or {}).get("name"),
        "topics": topics,
        "languages": languages_dict,
        "readme": readme,
        "recent_commits": commits,
        "open_issues": issues,
    }

    # Write per-repo raw file
    raw_path = RAW_DIR / f"{name}.json"
    raw_path.write_text(json.dumps(enriched, indent=2, ensure_ascii=False))

    return enriched


def main():
    repos = fetch_repos()
    all_data = []

    for repo in repos:
        try:
            enriched = enrich_repo(repo)
            all_data.append(enriched)
        except Exception as e:
            logger.warning("Unexpected error for repo %s: %s", repo.get("name"), e)
            all_data.append({"name": repo.get("name"), "error": str(e)})

    OUTPUT_FILE.write_text(json.dumps(all_data, indent=2, ensure_ascii=False))
    logger.info("Written %d repos to %s", len(all_data), OUTPUT_FILE)
    print(f"\nDone. {len(all_data)} repos → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
