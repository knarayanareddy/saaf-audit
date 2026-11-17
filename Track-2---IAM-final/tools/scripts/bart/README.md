# SAAF Local User Access Review Comparator

**Author:** Bart van den Broek
**Purpose:** Detect user access control exceptions by comparing an HR active-employee list against a user access system export. Fully local — no data leaves your machine.

---

## Quick start

### 1. Install dependencies

```bash
pip3 install -r tools/scripts/bart/requirements.txt
```

### 2. CLI

```bash
python3 tools/scripts/bart/access_review_agent.py \
  --hr tools/scripts/bart/test_data/hr_export.csv \
  --access tools/scripts/bart/test_data/ad_export.csv \
  --out outputs/examples \
  --match-key username \
  --stale-days 90
```

### 3. Web app

```bash
cd tools/scripts/bart && python3 -m uvicorn web.app:app --host 127.0.0.1 --port 8000 --reload
```

Open http://127.0.0.1:8000

### 4. Tests

```bash
cd /path/to/Track-2---IAM-final
python3 -m pytest tools/scripts/bart/tests/ -v
```

---

## File layout

```
tools/scripts/bart/
├── access_review_agent.py     Core logic + CLI (no web imports)
├── web/
│   ├── app.py                 FastAPI web application
│   ├── templates/index.html   Jinja2 single-page UI
│   └── static/styles.css      CSS — no CDN dependencies
├── tests/
│   └── test_access_review_agent.py
├── test_data/
│   ├── ad_export.csv          Synthetic access export
│   └── hr_export.csv          Synthetic HR export
├── requirements.txt
└── README.md
```

Run outputs: `outputs/runs/<timestamp>/`

---

## Detection logic

| Exception type | Risk   | Trigger |
|---------------|--------|---------|
| Orphaned      | High   | Account in access system but not in HR |
| Departed      | High   | HR status != Active OR termination_date <= today, AND access enabled |
| Role/dept mismatch | Medium | HR role/dept differs from access system (case-insensitive) |
| Stale         | Low    | last_login older than --stale-days threshold |
| Duplicate     | Medium | Same match_key appears >1 time with enabled=true |

Accounts matching exclusion patterns (default: `svc*`, `service*`, `app*`, `*_svc`) are excluded from findings.

---

## Output files (per run)

| File | Description |
|------|-------------|
| `findings.json` | Anonymized findings (USER-NNN refs only) |
| `findings.csv`  | Same findings in CSV format |
| `summary.json`  | Record counts and finding totals by risk |
| `user_mapping.csv` | **SENSITIVE** — maps USER-NNN to real identifiers |

---

## Control references

- ISO/IEC 27001:2022 A.5.18 — Access rights management
- SOC 2 CC6.2 — Prior to issuing system credentials
- SOC 2 CC6.3 — Role-based access control
- ISAE 3402 — User access review control objective
