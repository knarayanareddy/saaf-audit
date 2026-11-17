# Track-4-Audit-Report-Generator
**Group 8, Track 4** — AI-powered audit report generator that fills your company's Word template.

---

## What it does

1. You upload your company's `.docx` Word template (with `{{PLACEHOLDER}}` tags)
2. You provide audit data via a form, free text notes, or a CSV/Excel file
3. Claude AI generates professional content for every placeholder
4. You download the completed Word report

Supports all audit types with a focus on **Operational** and **IT Audits**.

---

## How to prepare your Word template

Add placeholders anywhere in your `.docx` file using double curly braces:

| Placeholder | Content generated |
|---|---|
| `{{EXECUTIVE_SUMMARY}}` | 2–3 paragraph summary |
| `{{SCOPE}}` | Audit scope statement |
| `{{AUDIT_OBJECTIVES}}` | Objectives list |
| `{{METHODOLOGY}}` | Methods used |
| `{{FINDINGS}}` | Numbered findings with risk & recommendation |
| `{{RECOMMENDATIONS}}` | Consolidated recommendations |
| `{{CONCLUSION}}` | Closing paragraphs |

You can use **any placeholder name** — the AI will fill them all.

---

## Setup

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/Track-4-Audit-Report-Generator.git
cd Track-4-Audit-Report-Generator
```

### 2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate        # Mac / Linux
venv\Scripts\activate           # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set your Anthropic API key
```bash
cp .env.example .env
# Edit .env and add your key:
# ANTHROPIC_API_KEY=sk-ant-...
```

Get a key at https://console.anthropic.com

### 5. Run the app
```bash
python run.py
```

Open http://localhost:8000 in your browser.

---

## Project structure

```
Track-4-Audit-Report-Generator/
├── app/
│   ├── main.py                  # FastAPI app & routes
│   ├── services/
│   │   ├── claude_service.py    # Claude AI integration
│   │   ├── document_service.py  # Word template processing
│   │   └── data_service.py      # CSV/Excel parsing
│   └── templates/
│       └── index.html           # Frontend UI
├── run.py                       # Entry point
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## Tech stack

- **Backend**: Python, FastAPI
- **AI**: Claude claude-sonnet-4-6 via Anthropic SDK
- **Word processing**: python-docx
- **Data parsing**: pandas, openpyxl
- **Frontend**: HTML, CSS, Vanilla JS
