# Module Reference

Complete reference for every module in the codebase, organized by package.

---

## `config/` - Configuration

### `config/settings.py` (65 lines)

Central settings management using a Python dataclass.

**Key exports:**
- `settings` - Singleton `Settings` instance, created at import time

**Functions:**
- `_split_csv(value, default)` - Parses comma-separated string into list
- `_get_bool(value, default)` - Parses boolean from string ("1", "true", "yes", "on")

**Notes:**
- All environment variables read at import time via `os.getenv()`
- Automatically creates `.cache/` directory on import
- Uses `@dataclass(slots=True)` for memory efficiency

---

### `config/keywords.py` (122 lines)

Discovery keyword definitions organized by ICP conversion priority.

**Key exports:**
- `DISCOVERY_KEYWORDS` - Combined list of all 48 keywords (tier-ordered)
- `DISCOVERY_MODIFIERS` - 10 intent modifier phrases
- `COACH_PLATFORM_DOMAINS` - 9 accepted coach platform domains
- `COACH_DIRECTORY_DOMAINS` - 4 accepted directory domains
- Individual tier lists: `DIGITAL_SELLER_KEYWORDS`, `ONLINE_COACH_KEYWORDS`, `TRANSFORMATION_KEYWORDS`, `NICHE_COACH_KEYWORDS`, `BUSINESS_COACH_KEYWORDS`

---

### `config/cities.py` (13 lines)

**DEPRECATED.** Contains only `US_TARGET_CITIES = []`. Not imported or used anywhere.

---

## `discovery/` - Search & URL Classification

### `discovery/duckduckgo_search.py` (171 lines)

DuckDuckGo search integration using the `ddgs` library.

**Key functions:**

| Function               | Signature                                                    | Description                           |
|------------------------|--------------------------------------------------------------|---------------------------------------|
| `build_queries()`      | `(keywords, modifiers, platforms) -> List[str]`              | Generates ~1,274 search queries       |
| `search_query()`       | `(query, max_results=None) -> List[Dict]`                    | Executes single query with retry      |
| `discover_candidates()`| `(queries, target=200) -> List[Dict]`                        | Runs queries until target reached     |

**Internal functions:**
- `_search_ddgs_once()` - Single DDG API call
- `_query_variants()` - Generates alternate query forms for Instagram queries
- `_log()` - Timestamped logging

**Retry strategy:** For each query, tries `us-en` region first, then `wt-wt` (worldwide). For Instagram queries, also tries rearranged `site:` prefix position.

---

### `discovery/web_search.py` (155 lines)

URL classification, filtering, and blocklist management.

**Key exports:**

| Export                    | Type  | Description                                      |
|---------------------------|-------|--------------------------------------------------|
| `DOMAIN_BLOCKLIST`        | `set` | ~50 blocked domains (social media, news, gyms)   |
| `LINK_HUB_DOMAINS`       | `set` | 5 link hub domains (linktr.ee, beacons.ai, etc.) |
| `COACH_PLATFORM_DOMAINS`  | `set` | 6 coach platform domains                        |
| `COACH_DIRECTORY_DOMAINS` | `set` | 4 coach directory domains                       |
| `ACCEPTED_SOURCE_DOMAINS` | `set` | Union of hubs + platforms + directories          |

**Key functions:**

| Function                 | Description                                               |
|--------------------------|-----------------------------------------------------------|
| `split_candidate_urls()` | Separates candidates into Instagram vs. website buckets   |

**Internal functions:**
- `_is_blocked_domain()` - Checks against blocklist
- `_is_accepted_source()` - Checks against accepted domains
- `_looks_like_article()` - Detects article/blog URLs

---

## `extraction/` - Data Extraction

### `extraction/website_crawler.py` (275 lines)

Website content extraction via HTTP + BeautifulSoup.

**Key function:**

| Function          | Signature                              | Description                              |
|-------------------|----------------------------------------|------------------------------------------|
| `crawl_website()` | `(base_url: str) -> Dict[str, object]` | Crawls up to 5 pages, extracts all data  |

**Returns dict with:**
- `website`, `website_title`, `website_description`, `contact_name`
- `pages` (list of crawled URLs), `page_text` (full text)
- `emails`, `phone`, `booking_link`, `pricing_page`
- `has_pricing_page`, `has_lead_magnet`, `has_testimonials`
- `services_found`, `socials`, `platform`, `offers_online_coaching`

**Internal functions:**
- `_fetch()` - HTTP GET with user-agent and rate limiting
- `_extract_contact_name()` - Parses person's name from site title/meta description
- `_clean_name_candidate()` - Validates and cleans name candidates
- `_extract_phone()` - US phone number regex extraction

**Pages crawled (in order):** `/`, `/about`, `/contact`, `/services`, `/coaching`, `/work-with-me`

---

### `extraction/email_extractor.py` (31 lines)

Regex-based email extraction.

| Function           | Description                                                   |
|--------------------|---------------------------------------------------------------|
| `extract_emails()` | Regex scan for email patterns in text, returns sorted unique  |
| `pick_best_email()`| Prioritizes domain-matching emails, then common prefixes      |

**Priority order for `pick_best_email()`:** hello@ > contact@ > info@ > coach@ > admin@

---

### `extraction/email_guesser.py` (69 lines)

Email pattern generation for leads without discovered emails.

| Function         | Description                                             |
|------------------|---------------------------------------------------------|
| `guess_emails()` | Generates up to 3 email guesses from name + domain      |

**Guess patterns (in order):**
1. `{first}@domain` (if name found)
2. `{first}.{last}@domain` (if full name found)
3. `{first}{last}@domain` (if full name found)
4. `hello@domain` (always)
5. `info@domain` (always)
6. `contact@domain` (always)

Returns top 3 unique guesses.

---

### `extraction/linktree_parser.py` (26 lines)

Link hub page parser for Linktree, Beacons, Stan Store.

| Function          | Description                                    |
|-------------------|------------------------------------------------|
| `parse_link_hub()`| Fetches hub page, extracts all `<a>` links and text |

---

## `enrichment/` - Classification

### `enrichment/gemini_classifier.py` (140 lines)

AI and heuristic lead classification.

| Function              | Description                                              |
|-----------------------|----------------------------------------------------------|
| `classify_lead()`     | Dispatches to Gemini AI or heuristic based on settings   |
| `heuristic_classify()`| Keyword-based classification (default mode)              |

**Gemini mode:**
- Sends structured prompt with lead data to `gemini-2.0-flash`
- Expects JSON response with 9 classification fields
- Falls back to heuristic on any error

**Heuristic mode detects:**
- Specialty via keyword matching (fat loss, strength, macro, nutrition, etc.)
- Solo coach vs. generic fitness (is_solo_online_coach)
- Maturity level (early/established/scaled)
- Weakness identification
- Outreach angle generation
- Personalization note

---

## `verification/` - Email Verification & Deduplication

### `verification/smtp_verifier.py` (182 lines)

Email deliverability verification via SMTP.

**Key functions:**

| Function                 | Description                                        |
|--------------------------|----------------------------------------------------|
| `verify_email_address()` | Full verification: cache -> MX -> SMTP -> catch-all|
| `verify_emails_batch()`  | Parallel verification with ThreadPoolExecutor      |
| `is_catch_all_domain()`  | Detects domains accepting all addresses            |

**Verification flow:**
1. Check disk cache (`.cache/smtp/{md5}.json`)
2. MX record lookup via `dns.resolver`
3. SMTP RCPT TO check (connect, HELO, MAIL FROM, RCPT TO)
4. If 250 response: check if domain is catch-all
5. Cache result to disk

**Status codes:**
- SMTP 250 + not catch-all = `valid`
- SMTP 250 + catch-all = `catch-all`
- SMTP 550/551/553 = `invalid`
- No MX records = `invalid`
- Any exception = `unknown`

---

### `verification/deduplicator.py` (127 lines)

Lead deduplication using union-find-style bucket merging.

**Key function:**

| Function              | Description                                        |
|-----------------------|----------------------------------------------------|
| `deduplicate_leads()` | Merges leads sharing email, IG, or domain keys     |

**Internal functions:**
- `_build_keys()` - Generates identity keys for a lead
- `_merge_leads()` - Merges two leads, keeping the more complete one as primary
- `_pick_better()` - Selects the more complete lead
- `_completeness_score()` - Scores lead completeness for merge priority

---

## `scoring/` - Lead Scoring

### `scoring/lead_scorer.py` (86 lines)

Heuristic scoring engine that assigns 0-100 scores and tier labels.

| Function       | Description                                    |
|----------------|------------------------------------------------|
| `score_lead()` | Assigns score (0-100) and tier (hot/good/review) |

See [PIPELINE.md](PIPELINE.md#phase-5-classification--scoring) for the full scoring breakdown.

---

## `export/` - Google Sheets Export

### `export/sheets_writer.py` (76 lines)

Google Sheets API integration via `gspread`.

**Class: `SheetsWriter`**

| Method                    | Description                                     |
|---------------------------|-------------------------------------------------|
| `__init__()`              | Authenticates and opens the Google Sheet         |
| `ensure_tabs()`           | Creates required tabs if missing                 |
| `clear_priority_tabs()`   | Clears Hot/Good/Review tabs (latest run only)    |
| `ensure_all_leads_header()`| Ensures All_Leads has correct header row        |
| `write_leads()`           | Appends lead rows to a tab                       |
| `log_run()`               | Appends run metadata to Run_Log tab              |

---

## `models/` - Data Models

### `models/lead.py` (114 lines)

See [DATA_MODEL.md](DATA_MODEL.md) for complete field reference.

---

## `resolution/` - URL Resolution

### `resolution/instagram_profile.py` (61 lines)

Instagram profile handling. **Note:** `fetch_profile()` is dead code - blocked by Instagram.

| Function               | Description                                           |
|------------------------|-------------------------------------------------------|
| `normalize_username()` | Extracts IG username from URL or handle (ACTIVE)      |
| `fetch_profile()`      | Instaloader profile fetch (DEAD CODE - blocked by IG) |
| `get_loader()`         | Lazy Instaloader initialization (DEAD CODE)           |

Only `normalize_username()` is actively used by the pipeline.

---

### `resolution/link_resolver.py` (41 lines)

External URL type detection and redirect resolution.

| Function               | Description                                    |
|------------------------|------------------------------------------------|
| `detect_link_type()`   | Classifies URL by domain (linktree/beacons/etc)|
| `resolve_external_url()`| Follows redirects to find final URL and type  |

**Note:** `resolve_external_url()` is imported in `pipeline.py` but never actually called in the current codebase.

---

## `pipeline.py` (980 lines) - Main Orchestrator

The central module that ties everything together. See [PIPELINE.md](PIPELINE.md) for the full flow documentation.

**Key functions defined here (not in sub-modules):**

| Function                         | Line | Description                                     |
|----------------------------------|------|-------------------------------------------------|
| `log()`                          | 36   | Timestamped logging to stdout                   |
| `save_checkpoint()`              | 52   | Saves leads to JSON checkpoint file             |
| `load_seen_identities()`         | 113  | Loads all identities from All_Leads sheet       |
| `filter_seen_candidates()`       | 153  | Suppresses already-processed candidates         |
| `is_seen_lead()`                 | 176  | Checks if a lead was already processed          |
| `remember_lead_identities()`     | 194  | Adds lead identities to the seen set            |
| `run_discovery()`                | 214  | Runs DuckDuckGo discovery phase                 |
| `quick_reject_website()`         | 243  | Fast rejection of junk URLs                     |
| `rank_website_candidates()`      | 255  | Sorts websites by relevance                     |
| `enrich_lead_from_website()`     | 322  | Crawls website and fills lead fields            |
| `find_email_for_lead()`          | 372  | Email guessing fallback                         |
| `verify_leads_in_batch()`        | 398  | Batch SMTP verification                         |
| `classify_and_score()`           | 416  | Classification + scoring                        |
| `_parse_ig_snippet()`            | 512  | Extracts IG data from DDG search results        |
| `_find_website_for_ig_lead()`    | 591  | Finds website for an IG-discovered lead         |
| `process_instagram_candidate()`  | 716  | Full IG candidate processing                    |
| `process_website_candidate()`    | 768  | Full website candidate processing               |
| `run()`                          | 834  | Main pipeline execution                         |
| `export_run()`                   | 906  | Google Sheets export                            |
| `main()`                         | 960  | CLI argument parsing and execution              |

---

## `app.py` (545 lines) - Streamlit UI

See [UI.md](UI.md) for complete UI documentation.
