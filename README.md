# Fitness Coach Prospecting Pipeline

An automated B2B lead generation tool that discovers English-speaking fitness coaches globally, extracts their contact data, scores them, and exports results to Google Sheets for a cold email campaign selling a low-ticket digital product.

---

## What it does

1. **Discovers** fitness coaches via DuckDuckGo keyword searches (no city targeting — global reach)
2. **Looks up** coach websites via DuckDuckGo with enhanced retry logic for one-off queries
3. **Crawls** their websites and link hub pages for emails, booking links, Instagram, and social profiles
4. **Generates** personalized icebreakers for each lead using AI analysis of their website content
5. **Verifies** email deliverability via SMTP
6. **Scores** leads based on ICP signals (email validity, online coaching presence, digital seller indicators)
7. **Deduplicates** across all prior runs
8. **Exports** to Google Sheets split by tier: Hot / Good / Review

**Target:** 30–50 fresh, usable leads per run.

---

## How it works

```
Discovery (DuckDuckGo keyword search)
    ↓
Pre-filtering (blocklists, seen-lead suppression, query rotation)
    ↓
Enrichment (website crawl, email extraction, link hub resolution)
    ↓
Icebreaker generation (AI-powered personalized compliments)
    ↓
Verification (parallel SMTP check, disk-cached)
    ↓
Scoring + Classification (heuristic rules)
    ↓
Deduplication (email + Instagram + domain merge)
    ↓
Export (Google Sheets: Hot_Leads / Good_Leads / Review_Queue / All_Leads)
```

### Discovery lanes

The pipeline searches three types of sources:

| Lane | Source | Why it matters |
|---|---|---|
| Keyword search | DuckDuckGo | Primary surface — coaches with websites and IG presence |
| Link hubs | linktr.ee, beacons.ai, stan.store | Hub pages that link to coaches' real sites |
| Coach platforms | kajabi.com, gumroad.com, thinkific.com, trainerize.com | Coaches who are **already selling digitally** — perfect ICP match |

### Lead tiers

| Tier | Score | Meaning |
|---|---|---|
| Hot | ≥ 65 | Valid email + strong ICP signals — ready for outreach |
| Good | ≥ 45 | Has email but some signals missing — still usable |
| Review | < 45 | Weak signals or no email — review before using |

### ICP: Who is a lead?

A lead is a fitness coach who:
- Has a website or Instagram presence with a findable email
- Speaks English (websites in English)
- Is a solo practitioner (not a gym chain or franchise)
- Coaches online or serves clients remotely (understands digital delivery)
- Ideally already sells digital products (ebook, guide, program) — these convert best for low-ticket offers

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/Dead0lol/prospecting.git
cd prospecting
```

### 2. Create `.env`

Copy `.env.example` to `.env` and fill in:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Google Sheets
GOOGLE_SHEET_NAME=Fitness Coach Leads
GOOGLE_SERVICE_ACCOUNT_FILE=service_account.json.json

# AI (optional — leave false for faster heuristic-only runs)
ENABLE_AI=false
OPENROUTER_API_KEY=
OPENROUTER_MODEL=openai/gpt-4o-mini

# Discovery
DISCOVERY_DELAY_SECONDS=3
MAX_DISCOVERY_QUERIES=40
```

### 3. Set up Google Sheets

1. Create a new Google Spreadsheet named `Fitness Coach Leads` (or whatever you set in `.env`)
2. Share it with the service account email from your `service_account.json.json` file
3. The pipeline will create the required tabs automatically on first run

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Run

```bash
# Standard run — produces leads to Google Sheets
python pipeline.py --limit 30

# Debug mode — print leads to terminal instead of exporting
python pipeline.py --limit 10 --json

# Quiet run to log file (for long runs)
python pipeline.py --limit 50 > .cache/runs/my_run.log 2>&1
```

### 6. Run the UI (optional)

The pipeline has a Streamlit web UI with a dashboard, searchable lead tables, and run controls.

```bash
streamlit run app.py
```

This opens a browser at `http://localhost:8501` with:

| Page | What it does |
|---|---|
| **📊 Dashboard** | Lead count metrics, run history, latest leads |
| **📋 Leads** | Searchable/filterable lead table with CSV download |
| **▶️ Run** | Set lead count and run the pipeline with live log output |
| **⚙️ Settings** | View all config values, keyword counts, cache stats, clear cache |

The UI reads and writes to the same Google Sheets and checkpoint files as the CLI pipeline.

---

## Configuration

All settings are in `config/settings.py` or set via environment variables in `.env`.

| Setting | Default | What it does |
|---|---|---|
| `DISCOVERY_DELAY_SECONDS` | `3` | Delay between DuckDuckGo queries (rate limit protection) |
| `MAX_DISCOVERY_QUERIES` | `40` | Queries run per pipeline execution |
| `MAX_SEARCH_RESULTS_PER_QUERY` | `20` | Results pulled from each query |
| `hot_lead_threshold` | `65` | Minimum score for Hot tier |
| `good_lead_threshold` | `45` | Minimum score for Good tier |
| `ENABLE_AI` | `false` | Use OpenRouter for classification (slower, requires API key) |
| `ICEBREAKER_TONE` | `professional and respectful` | Tone/style for AI-generated icebreakers |
| `ICEBREAKER_LENGTH` | `2` | Number of sentences for icebreakers (1-3 recommended) |

### Adding keywords

Edit `config/keywords.py`. Keywords are organized in tiers by ICP priority:

```python
DIGITAL_SELLER_KEYWORDS  # Coaches selling digital products — highest conversion intent
ONLINE_COACH_KEYWORDS     # Coaches who coach remotely
TRANSFORMATION_KEYWORDS   # Body recomp / fat loss / weight loss
NICHE_COACH_KEYWORDS      # Niche audiences (women over 40, macro coaching, etc.)
BUSINESS_COACH_KEYWORDS   # Business-minded coaches (may buy business resources)
```

---

## Google Sheets tabs

| Tab | What it contains |
|---|---|
| `Hot_Leads` | Leads scored ≥ 65. Cleared each run — latest run only. |
| `Good_Leads` | Leads scored 45–64. Cleared each run — latest run only. |
| `Review_Queue` | Leads scored below 45. Review before using. |
| `All_Leads` | Every lead from every run. Never cleared. Used for deduplication. |
| `Run_Log` | Run history: date, status, lead counts, runtime. |
| `Config` | (Reserved for future settings display) |

---

## How leads are discovered

The pipeline does NOT use city-based searches. Instead:

1. **Keyword-only queries** — e.g. `"online fitness coach"`, `"macro coach"`, `"fitness ebook author"`
2. **Intent modifiers** — e.g. `"online fitness coach" "book a call"`, `"fitness coach" "work with me"`
3. **Platform searches** — e.g. `"fitness coach" site:kajabi.com` — finds coaches on course platforms
4. **Link hub searches** — e.g. `"fat loss coach" site:linktr.ee` — finds coaches' hub pages
5. **Individual website lookups** — when an Instagram lead needs a real site, the pipeline uses DuckDuckGo with enhanced retry logic

Each run searches 40 queries from a pool of ~1,274. The pool rotates each run so different keyword subsets are covered over time.

---

## How deduplication works

Before enrichment, the pipeline loads all identities from `All_Leads` and suppresses:
- Leads with the same email address
- Leads with the same Instagram username
- Leads with the same root domain (e.g. `example.com`)

This means each run produces **net-new leads** — you're not re-processing the same coaches.

---

## How email verification works

1. **On-page extraction** — regex scan of crawled pages for emails
   Vendor telemetry addresses such as Wix/Sentry service mailboxes are filtered out.
2. **Email guessing** — if no email found, generate patterns like `{first}@{domain}` and `{first}.{last}@{domain}`
3. **SMTP verification** — check if the mailbox actually exists via MX lookup + SMTP RCPT command
4. **Disk cache** — verified results are cached in `.cache/smtp/` so repeated runs are faster

---

## Directory structure

```
prospecting/
├── pipeline.py                  # Main orchestrator
├── config/
│   ├── settings.py              # All configurable settings
│   ├── keywords.py             # Discovery keyword tiers
│   └── cities.py               # DEPRECATED — not used
├── discovery/
│   ├── duckduckgo_search.py    # DuckDuckGo search + query builder
│   ├── individual_search.py    # Enhanced DDG single-query lookup
│   └── web_search.py          # URL filtering and classification
├── extraction/
│   ├── website_crawler.py      # Website content extraction
│   ├── email_extractor.py     # Regex email finding
│   └── linktree_parser.py      # Link hub page parsing
├── enrichment/
│   ├── ai_classifier.py        # OpenRouter or heuristic classification
│   └── icebreaker_generator.py # AI-powered personalized icebreakers
├── verification/
│   ├── email_verifier.py      # Unified Disify + SMTP verification
│   ├── disify_client.py       # Disify API for domain validation
│   ├── smtp_verifier.py       # Low-level SMTP probe (legacy)
│   └── deduplicator.py        # Lead deduplication
├── scoring/
│   └── lead_scorer.py         # 0–100 heuristic scoring
├── export/
│   └── sheets_writer.py       # Google Sheets API writer
├── models/
│   └── lead.py                # Lead dataclass (44 fields)
├── .env                       # Credentials (NOT committed)
├── .env.example               # Template
├── .cache/
│   ├── email_verification/    # Cached email verification results
│   ├── disify/                # Cached Disify API responses
│   └── runs/                  # Checkpoint files from each run
├── service_account.json.json  # Google service account key
└── requirements.txt
```

---

## Advanced Features

### Personalized Icebreakers

The pipeline can automatically generate personalized, authentic opening lines for cold outreach emails based on each lead's website content.

**What it does:**
- Analyzes the actual text content of each lead's website
- Uses OpenRouter AI to generate specific compliments that reference real details
- Stores the icebreaker in the `ice_breaker` column in Google Sheets

**Configuration:**
```env
ICEBREAKER_TONE=professional and respectful
ICEBREAKER_LENGTH=2
```

**Example output:**
> "I noticed your emphasis on science-based programming tailored to individual body types—that's a refreshing approach in an industry full of cookie-cutter plans."

**See:** `docs/ICEBREAKER.md` for full documentation

---

## Known limitations

- **Instagram data** — IG data is extracted from DuckDuckGo snippets instead of direct Instagram scraping. Follower counts are often unavailable.
- **Single-query stability** — coach-specific website lookups use DuckDuckGo with retry logic; results may occasionally be inconsistent.
- **SMTP verification** — some mail servers block verification probes, resulting in "risky" status. Disify provides domain-level validation as a fallback.
- **JavaScript sites** — website crawler uses raw HTML (no JS rendering). SPA sites may not crawl well.
- **No resume mode** — interrupted runs restart from scratch. Use checkpoint files in `.cache/runs/` to manually recover.

---

## Troubleshooting

**Pipeline produces 0 leads**
- Check `.cache/runs/` for the latest log file
- DuckDuckGo may be rate-limiting — increase `DISCOVERY_DELAY_SECONDS`
- Your IP may be temporarily blocked by DuckDuckGo — wait and retry

**All emails show "risky" or "invalid" status**
- Many mail servers block SMTP verification probes
- Check `.cache/email_verification/` for individual results
- Disify provides domain-level validation (format, MX, disposable) even when SMTP fails
- "risky" means domain is valid but mailbox couldn't be confirmed

**Pipeline finds the same leads repeatedly**
- This should be fixed by seen-lead suppression
- Check that `All_Leads` has data and is accessible by the service account
- Delete `.cache/discovery_state.json` to reset the query rotation offset

**Slow runs**
- SMTP verification is the biggest bottleneck (~5s per domain)
- Reduce `SMTP_MAX_WORKERS` in `verification/smtp_verifier.py` to slow it down
- Increase it to speed it up (but risk more timeouts)

---

## Rotating credentials

If credentials are ever exposed, rotate immediately:

1. OpenRouter: revoke the old key in OpenRouter and update `OPENROUTER_API_KEY` in `.env`
2. Google service account: revoke the old key in Google Cloud Console, create a new one, download and replace `service_account.json.json`
