# Pipeline Flow Documentation

## Overview

The pipeline (`pipeline.py`) orchestrates the entire lead generation process in 7 sequential phases. A typical run for 30 leads takes 15-30 minutes.

---

## Phase 1: Discovery

**Function:** `run_discovery()` (line 214)
**Modules:** `discovery/duckduckgo_search.py`, `config/keywords.py`

### What happens:

1. `build_queries()` generates ~1,274 search queries by combining:
   - 48 base keywords (5 tiers) x bare queries
   - 48 keywords x 10 modifiers = 480 keyword+modifier queries
   - 48 keywords x Instagram `site:` prefix = 48 IG bare queries
   - 48 keywords x top 5 modifiers x IG = 240 IG+modifier queries
   - 48 keywords x 9 platforms = 432 platform queries

2. `_rotate_queries()` reads the offset from `.cache/discovery_state.json` and rotates the query pool so each run searches different keywords. At 30-40 queries per run, it takes ~31-42 runs to cycle through the full pool.

3. `discover_candidates()` executes up to `max_discovery_queries` (default: 40) DuckDuckGo queries via the `ddgs` library, collecting raw candidate URLs with titles and body snippets.

### Query rotation mechanism:

```
Run 1: queries[0:40]    -> offset saved as 40
Run 2: queries[40:80]   -> offset saved as 80
Run 3: queries[80:120]  -> offset saved as 120
...
Run N: wraps around to start
```

### Output:
- Raw list of candidate dictionaries: `{url, title, body, query}`

---

## Phase 2: Pre-filtering

**Functions:** `split_candidate_urls()`, `filter_seen_candidates()`, `rank_website_candidates()` (lines 153-282)
**Module:** `discovery/web_search.py`

### What happens:

1. **URL classification** (`split_candidate_urls()`):
   - Separates candidates into Instagram profiles vs. websites
   - Validates IG paths (rejects `/explore`, `/reels`, `/p`, etc.)
   - Applies domain blocklist (Reddit, YouTube, Facebook, Wikipedia, gym chains, etc.)
   - Accepts link hubs (linktr.ee, beacons.ai, stan.store) and coach platforms
   - Rejects article/directory pages based on URL path and title patterns
   - Requires fitness-related keywords in title/body for generic websites

2. **Seen-lead suppression** (`load_seen_identities()` + `filter_seen_candidates()`):
   - Loads all previously exported leads from the `All_Leads` Google Sheet
   - Builds identity sets: emails, Instagram usernames, website domains
   - Suppresses any candidate whose email/IG/domain was already processed

3. **Ranking** (`rank_website_candidates()`):
   - Sorts website candidates by relevance score
   - Boosts: personal domains, link hubs, coaching signals, personal coach mentions
   - Penalizes: aggregator/directory patterns ("top 10", "best", "list of")

### Output:
- Categorized dict: `{instagram: [...], websites: [...]}`
- Websites sorted by relevance (most promising first)

---

## Phase 3: Enrichment

**Functions:** `process_website_candidate()`, `process_instagram_candidate()` (lines 716-807)
**Modules:** `extraction/website_crawler.py`, `extraction/email_extractor.py`, `extraction/linktree_parser.py`

### Website candidates (processed first, higher quality):

1. If the URL is a link hub, `_extract_targets_from_link_hub()` resolves it to find the real website + IG URL
2. `enrich_lead_from_website()` crawls the website (up to 5 pages: `/`, `/about`, `/contact`, `/services`, `/coaching`, `/work-with-me`)
3. Extracts from each page:
   - Emails (regex scan)
   - Phone numbers
   - Social links (LinkedIn, YouTube, TikTok, Instagram from `<a>` tags)
   - Booking links (Calendly, Acuity, TidyCal)
   - Pricing pages
   - Lead magnets, testimonials
   - Services (1:1 coaching, nutrition coaching, etc.)
   - Platform detection (WordPress, Squarespace, Wix, Kajabi, Showit)
   - Online coaching signals
   - Contact name extraction from title/meta description
4. `_has_coach_signals()` rejects sites with fewer than 2 coaching indicators

### Instagram candidates (fill remaining slots):

1. `_parse_ig_snippet()` extracts name, followers, bio from the DuckDuckGo search result text (no direct Instagram API call)
2. `_find_website_for_ig_lead()` runs a targeted follow-up search to find the coach's website, with relevance validation
3. That single-query path uses DuckDuckGo with enhanced retry logic for reliability
4. IG-only leads without a discoverable website are **dropped** (they score 16-24, considered useless for cold email)
5. Same website crawl and email extraction as above

### Processing order:
```
Website candidates first (limit * 3 max attempts)
    -> If limit reached, stop
    -> Otherwise, fill remaining slots from IG candidates (remaining * 2 max attempts)
```

### Output:
- List of `Lead` objects with populated fields

---

## Phase 4: Verification

**Function:** `verify_leads_in_batch()` (line 398)
**Modules:** `verification/email_verifier.py`, `verification/disify_client.py`

### What happens:

1. Separates leads with emails from those without (mark as "missing")
2. Runs parallel verification using `ThreadPoolExecutor` (5 workers)
3. For each email:
   - Check disk cache first (`.cache/email_verification/{hash}.json`)
   - **Disify API** (domain-level): format, MX records, disposable check
   - If domain invalid/disposable → skip SMTP, return early
   - **SMTP probe** (mailbox-level): RCPT TO check against mail server
   - Catch-all domain detection (tests if domain accepts random addresses)
4. Results cached to disk for future runs

### Email status values:
| Status       | Meaning                                          |
|--------------|--------------------------------------------------|
| `valid`      | Mailbox exists and accepts mail                  |
| `invalid`    | Mailbox rejected (550/551/553) or no MX          |
| `catch-all`  | Domain accepts all addresses indiscriminately    |
| `risky`      | Domain OK but SMTP inconclusive (blocked/timeout)|
| `disposable` | Disposable email domain detected                 |
| `missing`    | No email was found for this lead                 |

---

## Phase 5: Classification & Scoring

**Functions:** `classify_and_score()` (line 416)
**Modules:** `enrichment/ai_classifier.py`, `scoring/lead_scorer.py`

### Classification:

**Heuristic mode (default):**
- Keyword-based analysis of bio + website text
- Detects specialty (fat loss, strength, macro, nutrition, etc.)
- Determines maturity level:
  - `early` - default
  - `established` - has testimonials + pricing page
  - `scaled` - 15,000+ followers
- Identifies weakness for outreach angle
- Generates outreach angle and personalization note

**OpenRouter AI mode (optional, disabled by default):**
- Sends structured prompt data through OpenRouter chat completions
- Expects JSON response with classification fields
- Falls back to heuristic on any error

### Scoring (0-100 scale):

| Category              | Signal                        | Points |
|-----------------------|-------------------------------|--------|
| **Email quality**     | Valid email                   | +20    |
|                       | Catch-all email               | +12    |
|                       | Unknown status with email     | +8     |
|                       | No email at all               | -15    |
| **Email source**      | Found on website              | +5     |
|                       | Found via link hub            | +4     |
| **Location**          | US                            | +10    |
|                       | UK/Canada/Australia           | +8     |
| **ICP match**         | Yes                           | +15    |
|                       | Uncertain                     | -5     |
| **Business presence** | Has website                   | +5     |
|                       | Has booking link              | +5     |
|                       | Has phone                     | +3     |
|                       | Has Instagram                 | +3     |
| **Offer signals**     | Offers online coaching        | +10    |
|                       | Has pricing page              | +5     |
|                       | Has testimonials              | +5     |
|                       | Has lead magnet               | +3     |
| **Followers**         | 1K-50K (sweet spot)           | +8     |
|                       | 500-1K                        | +3     |
|                       | 100K+ (too big)               | -5     |
| **Opportunity**       | No lead magnet (can pitch)    | +3     |
|                       | No booking link (can pitch)   | +2     |
|                       | Weakness identified           | +3     |
| **Services**          | 2+ services found             | +3     |

### Tiering:
| Tier   | Score Range | Meaning                           |
|--------|-------------|-----------------------------------|
| Hot    | >= 65       | Ready for outreach                |
| Good   | >= 45       | Usable, some signals missing      |
| Review | < 45        | Review before using               |

---

## Phase 6: Deduplication

**Function:** `deduplicate_leads()` (called at line 894)
**Module:** `verification/deduplicator.py`

### What happens:

1. Builds identity keys for each lead: email, IG username, website domain, source domain
2. Uses union-find-style bucket merging with `OrderedDict`
3. Leads sharing any key are merged:
   - The more "complete" lead becomes primary
   - Blank fields filled from secondary
   - Lists and dicts merged
   - Higher score preserved

### Merge strategy:
```
Lead A: email=john@example.com, ig=johnfit, website=example.com
Lead B: email=john@example.com, ig=, website=johnfitness.com

Result: Merged lead with all fields from both, keeping higher score
```

---

## Phase 7: Export

**Function:** `export_run()` (line 906)
**Module:** `export/sheets_writer.py`

### What happens:

1. Connects to Google Sheets via `gspread` service account
2. Ensures all required tabs exist (creates if missing)
3. Clears priority tabs (Hot_Leads, Good_Leads, Review_Queue) - latest run snapshot only
4. Writes leads to appropriate tier tabs
5. Appends all leads to All_Leads (cumulative, never cleared)
6. Logs run metadata to Run_Log tab

### Google Sheets tabs:

| Tab           | Behavior       | Purpose                        |
|---------------|----------------|--------------------------------|
| Hot_Leads     | Cleared/rewritten each run | Latest run's hot leads     |
| Good_Leads    | Cleared/rewritten each run | Latest run's good leads    |
| Review_Queue  | Cleared/rewritten each run | Latest run's review leads  |
| All_Leads     | Append-only    | Cumulative history (dedup source)|
| Run_Log       | Append-only    | Run metadata and counts        |
| Config        | Static         | Reserved for settings display  |

---

## Checkpointing

The pipeline saves checkpoints every 10 leads to `.cache/runs/{run_id}.json`. This provides:
- Progress visibility during long runs
- Partial data recovery if a run is interrupted
- Historical run data viewable in the Streamlit UI

**Note:** There is no automatic resume from checkpoint. Interrupted runs restart from scratch.

---

## Error Handling

- **Discovery errors:** Retries with different DDG region/safesearch combos
- **Crawl errors:** Logged to `lead.notes`, lead may still be processed
- **SMTP errors:** Returns "unknown" status, cached to prevent re-checking
- **Classification errors:** Falls back to heuristic mode
- **KeyboardInterrupt:** Gracefully stops, deduplicates partial results, exports what was collected
- **Google Sheets errors:** Logged but may cause data loss if export fails
