# Configuration Documentation

## Overview

All settings are managed through the `Settings` dataclass in `config/settings.py`. Values are loaded from environment variables (`.env` file) at import time via `python-dotenv`.

---

## Environment Variables

### Credentials

| Variable                       | Required | Default                      | Description                          |
|--------------------------------|----------|------------------------------|--------------------------------------|
| `OPENROUTER_API_KEY`           | No       | `""`                         | OpenRouter API key for AI classification |
| `OPENROUTER_MODEL`             | No       | `openai/gpt-4o-mini`         | OpenRouter model for AI classification |
| `GOOGLE_SERVICE_ACCOUNT_FILE`  | Yes      | `service_account.json.json`  | Path to Google Cloud service account key |
| `GOOGLE_SHEET_NAME`            | Yes      | `Fitness Coach Leads`        | Name of the Google Spreadsheet       |

### Feature Flags

| Variable     | Required | Default | Description                              |
|--------------|----------|---------|------------------------------------------|
| `ENABLE_AI`  | No       | `false` | Enable OpenRouter AI classification. When false, uses heuristic-only mode (faster, no API cost). |

### Rate Limiting

| Variable                      | Default | Description                                          |
|-------------------------------|---------|------------------------------------------------------|
| `DISCOVERY_DELAY_SECONDS`     | `3`     | Delay between DuckDuckGo queries                     |
| `WEBSITE_DELAY_SECONDS`       | `2`     | Delay between website page fetches                   |
| `OPENROUTER_DELAY_SECONDS`   | `4`     | Delay between OpenRouter API calls                   |

### Discovery Settings

| Variable                       | Default | Description                                       |
|--------------------------------|---------|---------------------------------------------------|
| `MAX_DISCOVERY_QUERIES`        | `40`    | Maximum DuckDuckGo queries per pipeline run       |
| `MAX_SEARCH_RESULTS_PER_QUERY` | `20`    | Maximum results pulled from each DDG query        |
| `DDGS_TIMEOUT_SECONDS`         | `15`    | Timeout for each DDG search request               |
| `TARGET_COUNTRY`               | `US`    | Default country code (mostly cosmetic)            |

### Crawling Settings

| Variable                  | Default | Description                                     |
|---------------------------|---------|-------------------------------------------------|
| `MAX_PAGES_PER_SITE`      | `5`     | Maximum pages crawled per website                |
| `REQUEST_TIMEOUT_SECONDS`  | `20`    | HTTP request timeout for crawling                |
| `USER_AGENT`               | Chrome 124 | Browser user-agent string for HTTP requests   |

### Scoring Thresholds

| Variable              | Default | Description                               |
|-----------------------|---------|-------------------------------------------|
| `HOT_LEAD_THRESHOLD`  | `65`    | Minimum score for "hot" tier              |
| `GOOD_LEAD_THRESHOLD` | `45`    | Minimum score for "good" tier             |

---

## Settings Dataclass

**File:** `config/settings.py`

```python
@dataclass(slots=True)
class Settings:
    root: Path                          # Project root directory
    openrouter_api_key: str             # OpenRouter API key
    openrouter_model: str               # OpenRouter model name
    enable_ai: bool                     # AI classification toggle
    google_sheet_name: str              # Google Sheet name
    google_service_account_file: Path   # Service account JSON path
    target_country: str                 # Default country code
    discovery_delay_seconds: float      # DDG query delay
    website_delay_seconds: float        # Page crawl delay
    openrouter_delay_seconds: float     # OpenRouter API delay
    request_timeout_seconds: int        # HTTP timeout
    max_search_results_per_query: int   # DDG results per query
    ddgs_timeout_seconds: int           # DDG search timeout
    max_discovery_queries: int          # Queries per run
    max_pages_per_site: int             # Pages crawled per site
    user_agent: str                     # Browser user-agent
    hot_lead_threshold: int             # Hot tier threshold
    good_lead_threshold: int            # Good tier threshold
    output_cache_dir: Path              # Cache directory path
```

A singleton `settings` instance is created at module level and imported by all other modules.

---

## Keyword Configuration

**File:** `config/keywords.py`

Keywords are organized in 5 tiers by ICP conversion priority:

| Tier | Constant                    | Count | Priority | Description                          |
|------|-----------------------------|-------|----------|--------------------------------------|
| 1    | `DIGITAL_SELLER_KEYWORDS`   | 11    | Highest  | Coaches already selling digital products |
| 2    | `ONLINE_COACH_KEYWORDS`     | 9     | High     | Coaches who coach remotely           |
| 3    | `TRANSFORMATION_KEYWORDS`   | 8     | Medium   | Results-based coaches                |
| 4    | `NICHE_COACH_KEYWORDS`      | 14    | Medium   | Niche audience coaches               |
| 5    | `BUSINESS_COACH_KEYWORDS`   | 6     | Lower    | Business-minded coaches              |

**Total:** 48 base keywords combined into `DISCOVERY_KEYWORDS`.

### Modifiers

10 intent modifiers in `DISCOVERY_MODIFIERS`: "apply now", "book a call", "work with me", "1:1 coaching", "online coaching", "client results", "free consultation", "start today", "coaching program", "join now".

### Platform & Directory Domains

- `COACH_PLATFORM_DOMAINS` (9): kajabi, gumroad, thinkific, teachable, trainerize, everfit, caliber, koji, linkpop
- `COACH_DIRECTORY_DOMAINS` (4): getmisfit, coachcaller, yogaia, fitnessnetwork

---

## Cache Files

| File                           | Purpose                             | Format    |
|--------------------------------|-------------------------------------|-----------|
| `.cache/discovery_state.json`  | Query rotation offset across runs   | JSON      |
| `.cache/ui_state.json`         | Streamlit UI state persistence      | JSON      |
| `.cache/smtp/{md5hash}.json`   | Individual SMTP verification results| JSON      |
| `.cache/runs/{run_id}.json`    | Pipeline checkpoint/result files    | JSON      |

### Discovery State Schema
```json
{
  "next_offset": 420,
  "saved_at": "2025-01-01T00:00:00+00:00"
}
```

### UI State Schema
```json
{
  "run_limit": 35,
  "last_run_id": "",
  "sheet_name": "Fitness Coach Leads"
}
```

### SMTP Cache Schema
```json
{
  "email": "john@example.com",
  "status": "valid"
}
```

---

## Hardcoded Constants

These values are not configurable via `.env` and require code changes:

| Constant              | Location                    | Value | Description                    |
|-----------------------|-----------------------------|-------|--------------------------------|
| `CHECKPOINT_EVERY`    | `pipeline.py:44`            | `10`  | Save checkpoint every N leads  |
| `SMTP_CONNECT_TIMEOUT`| `smtp_verifier.py:24`       | `5`   | SMTP connection timeout (sec)  |
| `SMTP_MAX_WORKERS`    | `smtp_verifier.py:135`      | `5`   | Thread pool size for SMTP      |
| `PATH_HINTS`          | `website_crawler.py:15`     | 6 paths| Pages to crawl per website    |

---

## .env.example Template

```env
OPENROUTER_API_KEY=
OPENROUTER_MODEL=openai/gpt-4o-mini
ENABLE_AI=false
GOOGLE_SHEET_NAME=Fitness Coach Leads
GOOGLE_SERVICE_ACCOUNT_FILE=service_account.json.json
TARGET_COUNTRY=US
DISCOVERY_DELAY_SECONDS=3
WEBSITE_DELAY_SECONDS=2
OPENROUTER_DELAY_SECONDS=4
REQUEST_TIMEOUT_SECONDS=20
MAX_SEARCH_RESULTS_PER_QUERY=20
MAX_PAGES_PER_SITE=5
MAX_DISCOVERY_QUERIES=40
DDGS_TIMEOUT_SECONDS=15
```
