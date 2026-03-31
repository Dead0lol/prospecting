# Fitness Coach Prospecting Pipeline

An automated B2B lead generation tool that discovers English-speaking fitness coaches globally, extracts their contact data, scores them, and exports results to Google Sheets for a cold email campaign selling a low-ticket digital product.

---

## What it does

1. **Discovers** fitness coaches via DuckDuckGo keyword searches (no city targeting — global reach)
2. **Crawls** their websites and link hub pages for emails, booking links, Instagram, and social profiles
3. **Verifies** email deliverability via SMTP
4. **Scores** leads based on ICP signals (email validity, online coaching presence, digital seller indicators)
5. **Deduplicates** across all prior runs
6. **Exports** to Google Sheets split by tier: Hot / Good / Review

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
| Hot | ≥ 60 | Valid email + strong ICP signals — ready for outreach |
| Good | ≥ 40 | Has email but some signals missing — still usable |
| Review | < 40 | Weak signals or no email — review before using |

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
GEMINI_API_KEY=

# Instagram (currently unused — Instaloader is blocked by IG)
IG_USERNAME=
IG_PASSWORD=

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
| `ENABLE_AI` | `false` | Use Gemini for classification (slower, requires API key) |

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
| `Hot_Leads` | Leads scored ≥ 60. Cleared each run — latest run only. |
| `Good_Leads` | Leads scored 45–59. Cleared each run — latest run only. |
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
│   └── web_search.py          # URL filtering and classification
├── extraction/
│   ├── website_crawler.py      # Website content extraction
│   ├── email_extractor.py     # Regex email finding
│   ├── email_guesser.py        # Email pattern generation
│   └── linktree_parser.py      # Link hub page parsing
├── enrichment/
│   └── gemini_classifier.py   # AI or heuristic classification
├── verification/
│   ├── smtp_verifier.py        # Email SMTP validation
│   └── deduplicator.py         # Lead deduplication
├── scoring/
│   └── lead_scorer.py         # 0–100 heuristic scoring
├── export/
│   └── sheets_writer.py       # Google Sheets API writer
├── models/
│   └── lead.py                # Lead dataclass (44 fields)
├── .env                       # Credentials (NOT committed)
├── .env.example               # Template
├── .cache/
│   ├── smtp/                  # Cached SMTP verification results
│   └── runs/                  # Checkpoint files from each run
├── service_account.json.json  # Google service account key
└── requirements.txt
```

---

## Known limitations

- **Instagram data** — Instaloader is blocked by Instagram. IG data is extracted from DuckDuckGo snippets instead. Follower counts are usually 0.
- **SMTP verification** — some mail servers are slow or silently reject checks, resulting in "unknown" status. The cache mitigates this.
- **JavaScript sites** — website crawler uses raw HTML (no JS rendering). SPA sites may not crawl well.
- **Email guessing** — generates plausible patterns but doesn't verify them until the batch SMTP step.
- **No resume mode** — interrupted runs restart from scratch. Use checkpoint files in `.cache/runs/` to manually recover.

---

## Troubleshooting

**Pipeline produces 0 leads**
- Check `.cache/runs/` for the latest log file
- DuckDuckGo may be rate-limiting — increase `DISCOVERY_DELAY_SECONDS`
- Your IP may be temporarily blocked by DuckDuckGo — wait and retry

**All emails show "unknown" status**
- The domain's mail server may be slow to respond
- Check `.cache/smtp/` for individual verification results
- Free SMTP verification is inherently unreliable — consider a paid service for production

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

1. Instagram: change password and update `IG_PASSWORD` in `.env`
2. Gemini: regenerate API key in Google AI Studio and update `GEMINI_API_KEY` in `.env`
3. Google service account: revoke the old key in Google Cloud Console, create a new one, download and replace `service_account.json.json`
