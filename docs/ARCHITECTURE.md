# Architecture Overview

## System Summary

The Fitness Coach Prospecting Pipeline is an automated B2B lead generation system that discovers English-speaking fitness coaches globally, extracts their contact data, scores them by ICP (Ideal Customer Profile) fit, and exports results to Google Sheets for cold email outreach selling a low-ticket digital product.

**Target output:** 30-50 fresh, usable leads per run.

---

## Tech Stack

| Layer              | Technology                          | Purpose                                      |
|--------------------|-------------------------------------|----------------------------------------------|
| Language           | Python 3.12                         | Core runtime                                 |
| Web UI             | Streamlit                           | Dashboard, lead browser, run controls        |
| Data manipulation  | Pandas                              | DataFrames for UI tables/charts              |
| Search engine      | DuckDuckGo (`ddgs`)                 | Bulk discovery and one-off coach-site lookups |
| Web scraping       | Scrapling                           | Website crawling and HTML parsing            |
| Email verification | Raw SMTP (`smtplib`) + DNS (`dnspython`) | Mailbox existence checks               |
| AI classification  | OpenRouter chat completions (optional) | Lead classification (disabled by default) |
| Instagram          | URL normalization + DDG snippets    | IG data now parsed from DDG snippets         |
| Google Sheets      | `gspread` + Service Account auth    | Lead export and deduplication store          |
| Config             | `python-dotenv` + `dataclasses`     | Environment-based settings                   |
| Concurrency        | `concurrent.futures.ThreadPoolExecutor` | Parallel SMTP verification             |

---

## High-Level Architecture Diagram

```
                         +------------------+
                         |   Entry Points   |
                         +--------+---------+
                                  |
                    +-------------+-------------+
                    |                           |
              +-----v-----+             +------v------+
              | pipeline.py|             |   app.py    |
              | (CLI batch)|             | (Streamlit) |
              +-----+------+             +------+------+
                    |                           |
                    |    (spawns as subprocess)  |
                    +<--------------------------+
                    |
         +----------v----------+
         |    Pipeline Flow    |
         +---------------------+
         |                     |
    +----v----+          +-----v------+
    |Discovery|          |Pre-filtering|
    +---------+          +------------+
         |                     |
    +----v---------+     +-----v----------+
    | Enrichment   |     | Seen-lead      |
    | (crawl+email)|     | suppression    |
    +--------------+     +----------------+
         |
    +----v-----------+
    | Verification   |
    | (SMTP parallel)|
    +----------------+
         |
    +----v-----------+
    | Classification |
    | + Scoring      |
    +----------------+
         |
    +----v-----------+
    | Deduplication  |
    +----------------+
         |
    +----v-----------+
    | Export         |
    | (Google Sheets)|
    +----------------+
```

---

## Directory Structure

```
prospecting/
├── pipeline.py                    # Main pipeline orchestrator (980 lines)
├── app.py                         # Streamlit web UI (545 lines)
├── config/
│   ├── __init__.py
│   ├── settings.py                # Centralized settings dataclass (65 lines)
│   ├── keywords.py                # Discovery keyword tiers (122 lines)
│   └── cities.py                  # DEPRECATED - not used (13 lines)
├── discovery/
│   ├── __init__.py
│   ├── duckduckgo_search.py       # DDG search + query builder (171 lines)
│   ├── individual_search.py       # Single-query website lookup routing
│   └── web_search.py              # URL classification/filtering (155 lines)
├── extraction/
│   ├── __init__.py
│   ├── website_crawler.py         # Website content extraction (275 lines)
│   ├── email_extractor.py         # Regex email finding (31 lines)
│   └── linktree_parser.py         # Link hub page parsing (26 lines)
├── enrichment/
│   ├── __init__.py
│   └── ai_classifier.py           # OpenRouter/heuristic classification
├── verification/
│   ├── __init__.py
│   ├── email_verifier.py          # Unified Disify + SMTP verification
│   ├── disify_client.py           # Disify API for domain validation
│   ├── smtp_verifier.py           # Low-level SMTP probe (legacy)
│   └── deduplicator.py            # Lead deduplication engine (127 lines)
├── scoring/
│   ├── __init__.py
│   └── lead_scorer.py             # 0-100 heuristic scoring (86 lines)
├── export/
│   ├── __init__.py
│   └── sheets_writer.py           # Google Sheets API writer (76 lines)
├── models/
│   ├── __init__.py
│   └── lead.py                    # Lead dataclass - 44 fields (114 lines)
├── resolution/
│   ├── __init__.py
│   ├── instagram_profile.py       # Instagram username normalization
│   └── link_resolver.py           # External URL resolver (41 lines)
├── .env                           # Live credentials (git-ignored)
├── .env.example                   # Credential template
├── .gitignore
├── README.md
├── requirements.txt               # Incomplete - see SETUP.md
├── service_account.json.json      # Google service account key (git-ignored)
└── .cache/
    ├── discovery_state.json       # Query rotation offset
    ├── ui_state.json              # Streamlit UI persistence
    ├── email_verification/        # Cached email verification results
    ├── disify/                    # Cached Disify API responses
    └── runs/                      # Pipeline checkpoint files
```

**Total source files:** 21 Python files (excluding `__init__.py`)
**Total lines of code:** ~3,108 lines

---

## Entry Points

### CLI: `pipeline.py`

```bash
python pipeline.py --limit 30
python pipeline.py --limit 10 --json
```

| Argument    | Default | Description                                |
|-------------|---------|--------------------------------------------|
| `--country` | `US`    | Country code (mostly cosmetic)             |
| `--limit`   | `10`    | Number of leads to find                    |
| `--json`    | flag    | Print JSON output instead of just exporting|

### Web UI: `app.py`

```bash
streamlit run app.py
# Opens http://localhost:8501
```

The UI spawns `pipeline.py` as a subprocess when the user clicks "Run Pipeline".

---

## Data Flow

1. **Input:** Keywords from `config/keywords.py` + modifiers
2. **Processing:** Discovery -> Filter -> Crawl -> Verify -> Score -> Deduplicate
3. **Storage:** Google Sheets (persistent), `.cache/` (local disk cache)
4. **Output:** Tiered lead lists in Google Sheets tabs

---

## External Dependencies

| Service              | Required | Purpose                        |
|----------------------|----------|--------------------------------|
| DuckDuckGo           | Yes      | Search engine for discovery    |
| Google Sheets API    | Yes      | Lead storage and dedup source  |
| Target websites      | Yes      | Crawled for contact data       |
| Target mail servers  | Yes      | SMTP verification              |
| OpenRouter API       | No       | Optional AI classification     |

---

## Concurrency Model

- **Pipeline:** Single-threaded except for SMTP verification
- **SMTP verification:** `ThreadPoolExecutor` with 5 workers (configurable)
- **Streamlit UI:** Runs pipeline as a subprocess via `threading.Thread`
- **Caching:** File-based (JSON on disk), no database

---

## Security Considerations

- Credentials stored in `.env` (git-ignored)
- Google service account key stored as JSON file (git-ignored)
- No authentication on the Streamlit UI (local-only assumed)
- SMTP verification uses `verify.local` as HELO domain
- No rate limiting enforcement beyond configurable delays
