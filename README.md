# THEeye — AI-Assisted Research Platform

A legitimate, integrity-compliant research assistance platform for literature discovery, structured data extraction, and academic drafting — with full source provenance and journal-compliant AI disclosure.

## Core Principle

**AI assists, humans decide.** THEeye accelerates the research workflow but never replaces the researcher. Every AI-assisted action is tracked, every source is documented, and every draft includes a disclosure statement compliant with major publisher policies (Elsevier, Springer Nature, Wiley).

## Features

### 1. Literature Discovery
- Searches **OpenAlex** (250M+ works), **Crossref** (150M+ works), and **Semantic Scholar** (200M+ papers) concurrently
- Filters results by **SJR quartile** (Q1/Q2/Q3) using SCImago journal rank data
- Deduplicates across databases, sorts by citation count
- Filters by year range, minimum citations, and open access availability
- Displays AI-generated TLDRs from Semantic Scholar

### 2. Data Extraction
- Extracts structured data from paper abstracts: methodology, sample size, data source, variables, key findings, effect sizes, limitations
- Generates a **comparison table** across multiple papers for systematic review
- Pattern-based extraction works without any external LLM (no API key required)

### 3. Drafting Assistant
- Generates academic draft sections: **literature review, introduction, abstract, conclusion, summary**
- All drafts are grounded in retrieved source papers with proper **in-text citations and numbered references**
- Every draft includes an **integrity disclaimer** reminding the researcher to review and verify
- Template-based synthesis (no external LLM required); LLM integration is pluggable

### 4. Provenance & Integrity Audit
- Tracks every action (search, extraction, drafting) with timestamps
- Generates a **journal-compliant AI use disclosure statement** automatically
- Records which sections were AI-assisted and whether they've been human-verified
- Verification status tracking: pending → partial → verified

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
cd THEeye
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Open in browser
# http://localhost:8000
```

## Project Structure

```
THEeye/
├── backend/
│   ├── __init__.py
│   ├── main.py            # FastAPI application & API routes
│   ├── models.py          # Pydantic data models
│   ├── services.py        # OpenAlex, Crossref, Semantic Scholar API integration
│   ├── quartiles.py       # SJR quartile database & lookup
│   ├── extraction.py      # Structured data extraction service
│   ├── drafting.py        # Academic draft generation service
│   └── audit.py           # Provenance tracking & integrity audit
├── frontend/
│   ├── index.html         # Web UI
│   ├── css/style.css      # Styling
│   └── js/app.js          # Frontend logic
├── requirements.txt
└── README.md
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/journals` | List all journals in quartile database |
| GET | `/api/quartile/{name}` | Look up quartile for a journal |
| POST | `/api/search` | Search across databases with quartile filtering |
| POST | `/api/extract` | Extract data from a single paper |
| POST | `/api/extract/batch` | Extract data from multiple papers + comparison table |
| POST | `/api/draft` | Generate an academic draft section |
| POST | `/api/audit/session` | Create an audit session |
| GET | `/api/audit/sessions` | List all audit sessions |
| GET | `/api/audit/{id}` | Get full audit report with disclosure |
| POST | `/api/audit/{id}/verify` | Mark records as human-verified |

## Configuration

Edit `backend/services.py` to configure:

```python
CONTACT_EMAIL = "your-email@institution.edu"  # For polite API pools
SEMANTIC_SCHOLAR_API_KEY = "your-key"          # For higher rate limits (optional)
```

## Data Sources

| Source | Access | Key Required | Coverage |
|--------|--------|-------------|----------|
| OpenAlex | Free | No (email recommended) | 250M+ works |
| Crossref | Free | No (email recommended) | 150M+ works |
| Semantic Scholar | Free | API key recommended | 200M+ papers |
| SCImago SJR | Open | No | Journal quartiles |

## Academic Integrity Notice

THEeye is designed to **assist** researchers, not to replace them or deceive reviewers:

- All AI-generated drafts must be reviewed, verified, and revised by the human author(s)
- AI assistance must be disclosed in the manuscript per journal policy
- AI cannot be listed as an author or take responsibility for the work
- THEeye does not include any feature designed to evade AI detection or hide AI use

## Tech Stack

- **Backend**: Python 3.10+, FastAPI, httpx (async HTTP), Pydantic
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **APIs**: OpenAlex, Crossref, Semantic Scholar
- **Data**: SCImago SJR quartile database
