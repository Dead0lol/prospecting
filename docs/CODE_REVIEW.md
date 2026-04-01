# Comprehensive Code Review

## Review Summary

| Category       | Issues Found | Critical | Major | Minor | Info |
|----------------|-------------|----------|-------|-------|------|
| Bugs           | 7           | 2        | 3     | 2     | 0    |
| Security       | 4           | 1        | 2     | 1     | 0    |
| Architecture   | 8           | 0        | 4     | 2     | 2    |
| Code Quality   | 12          | 0        | 3     | 6     | 3    |
| Performance    | 5           | 0        | 2     | 2     | 1    |
| Testing        | 2           | 1        | 1     | 0     | 0    |
| Dependencies   | 3           | 1        | 1     | 1     | 0    |
| Documentation  | 3           | 0        | 1     | 1     | 1    |
| **Total**      | **44**      | **5**    | **17**| **15**| **7**|

**Overall Assessment:** The codebase is functional and achieves its goal of automated lead generation. However, it shows clear signs of rapid iteration and multiple refactors without cleanup. There are several bugs (including unreachable code and a broken UI tab loop), missing dependencies in `requirements.txt`, dead code from abandoned Instagram integration, no tests, and a monolithic 980-line pipeline module that handles too many responsibilities.

---

## CRITICAL Issues

### BUG-01: Unreachable code in `_extract_contact_name` return
**File:** `extraction/website_crawler.py:267-268`
**Severity:** Critical (dead code / logic error)

```python
    return " ".join(name_words)
    return ""  # <-- UNREACHABLE
```

Line 268 (`return ""`) is unreachable because line 267 already returns. This is harmless in practice (the first return covers all cases), but indicates a logic error during refactoring. The second `return ""` was likely the original fallback that was never removed.

**Fix:** Delete line 268.

---

### BUG-02: Streamlit tab content renders outside tab context
**File:** `app.py:278-344`
**Severity:** Critical (broken UI behavior)

```python
    for tab_name, df, tab in tab_map:
            if df.empty:                    # <-- over-indented, but NOT inside `with tab:`
                st.info(f"No leads in {tab_name}")
                continue

            col_search, col_tier, col_email, col_score_sort = st.columns([2, 1, 1, 1])
```

The loop body uses `st.columns()`, `st.text_input()`, `st.selectbox()`, `st.dataframe()`, etc. without wrapping them in `with tab:`. The `tab` variable from `tab_map` is never used as a context manager. This means all content renders on the main page body, not inside the respective tabs. All four tabs likely show the same (last iteration's) content.

**Fix:** Add `with tab:` as the first line inside the loop:
```python
    for tab_name, df, tab in tab_map:
        with tab:
            if df.empty:
                ...
```

---

### SEC-01: `service_account.json.json` committed to git history
**File:** `service_account.json.json`
**Severity:** Critical (credential exposure)

The service account private key file exists in the repository. While `.gitignore` lists it, the file was present in earlier commits. Anyone with access to the git history can extract the private key. The service account email `prospecting-bot@prospecting-491820.iam.gserviceaccount.com` and its private key are exposed.

**Fix:**
1. Revoke the current service account key in Google Cloud Console
2. Generate a new key
3. Use `git filter-branch` or `git-filter-repo` to remove the file from git history
4. Verify `.gitignore` covers all credential patterns

---

### DEP-01: `requirements.txt` is critically incomplete
**File:** `requirements.txt`
**Severity:** Critical (installation will fail)

Currently only lists:
```
streamlit
pandas
```

Missing at minimum:
```
ddgs
requests
beautifulsoup4
gspread
dnspython
python-dotenv
instaloader
google-generativeai
```

A fresh `pip install -r requirements.txt` will result in `ModuleNotFoundError` on first run.

**Fix:** Update `requirements.txt` to include all runtime dependencies, ideally with version pins.

---

### TEST-01: Zero test coverage
**Severity:** Critical (no safety net)

There are no test files, no test configuration, no `pytest.ini`, no `conftest.py`, and no testing infrastructure of any kind. For a 3,100-line codebase that handles SMTP connections, web scraping, API integrations, and data transformations, this is a significant risk.

**Recommended:** At minimum, add unit tests for:
- `models/lead.py` - `to_dict()` serialization, field defaults
- `extraction/email_extractor.py` - Email regex and prioritization
- `extraction/email_guesser.py` - Name extraction and guess generation
- `scoring/lead_scorer.py` - Score calculation correctness
- `verification/deduplicator.py` - Deduplication merge logic
- `discovery/web_search.py` - URL classification and blocklist logic

---

## MAJOR Issues

### BUG-03: `_parse_followers` regex misses "M" suffix for millions
**File:** `pipeline.py:439`
**Severity:** Major

```python
_FOLLOWER_RE = re.compile(r"([\d,.]+)\s*[Kk]\s*[Ff]ollower|(\d[\d,.]*)\s*[Ff]ollower")
```

The regex handles "K" (thousands) and raw numbers but does not handle "M" (millions) - e.g., "1.2M followers" will not match. While accounts with 1M+ followers are penalized in scoring, they would get `followers=0` instead of the actual count, which means the `-5` penalty for 100K+ followers is never applied for very large accounts.

**Fix:** Add `[MmKk]?` to the regex pattern:
```python
_FOLLOWER_RE = re.compile(r"([\d,.]+)\s*[MmKk]\s*[Ff]ollower|(\d[\d,.]*)\s*[Ff]ollower")
```
And handle the "M" multiplier in `_parse_followers()`.

---

### BUG-04: `resolve_external_url()` imported but never called
**File:** `pipeline.py:30`
**Severity:** Major (dead import / incomplete integration)

```python
from resolution.link_resolver import resolve_external_url
```

This function is imported but never used anywhere in `pipeline.py`. The link resolution functionality it provides (following redirects to find final URLs) is partially reimplemented inline in `_extract_targets_from_link_hub()` and `_find_website_for_ig_lead()`.

**Fix:** Remove the unused import, or refactor to use `resolve_external_url()` where appropriate.

---

### BUG-05: `enrich_lead_from_instagram()` is a no-op stub
**File:** `pipeline.py:364-369`
**Severity:** Major (dead code)

```python
def enrich_lead_from_instagram(lead: Lead) -> None:
    """Stub — Instaloader is blocked by Instagram without valid login."""
    pass
```

This function is still called at `pipeline.py:803`:
```python
enrich_lead_from_instagram(lead)
```

It does nothing. The call should be removed to avoid confusion.

---

### ARCH-01: `pipeline.py` is a 980-line God Module
**File:** `pipeline.py`
**Severity:** Major (maintainability)

`pipeline.py` contains:
- Discovery orchestration
- Pre-filtering logic
- Link hub extraction
- Instagram snippet parsing (100+ lines)
- Website candidate processing
- Instagram candidate processing
- Email finding
- SMTP verification orchestration
- Classification + scoring orchestration
- Deduplication orchestration
- Google Sheets export
- CLI argument parsing
- Checkpointing
- Seen-lead management
- Helper functions (`cast_list`, `cast_dict`, `cast_int`)
- Multiple large constant sets (`_SAAS_DOMAINS`, `_NOT_A_NAME`, `JUNK_DOMAINS`)

This module handles too many responsibilities. The Instagram snippet parsing, seen-lead management, pre-filtering, and helper functions should each be in their own modules.

**Recommended refactoring:**
1. Move `_parse_ig_snippet()`, `_parse_followers()`, `_is_likely_name()`, `_NOT_A_NAME` to `discovery/instagram_parser.py`
2. Move `load_seen_identities()`, `filter_seen_candidates()`, `is_seen_lead()`, `remember_lead_identities()` to `verification/seen_tracker.py`
3. Move `_SAAS_DOMAINS`, `JUNK_DOMAINS`, `quick_reject_website()`, `rank_website_candidates()` to `discovery/web_search.py`
4. Move `cast_list()`, `cast_dict()`, `cast_int()` to a `utils.py` module
5. Move checkpointing to a `cache/checkpoint.py` module

---

### ARCH-02: Duplicate domain blocklists across files
**Files:** `pipeline.py:237-481`, `discovery/web_search.py:21-50`
**Severity:** Major (maintenance burden)

There are three separate domain blocklists:
1. `DOMAIN_BLOCKLIST` in `discovery/web_search.py` (~50 domains)
2. `_SAAS_DOMAINS` in `pipeline.py` (~60 domains)
3. `JUNK_DOMAINS` in `pipeline.py` (8 domains)

These overlap partially and must be kept in sync manually. For example, `buzzfeed.com` appears in both `DOMAIN_BLOCKLIST` and `_SAAS_DOMAINS`. Adding a new blocked domain requires checking all three lists.

**Fix:** Consolidate into a single `config/blocklists.py` module with clearly separated categories.

---

### ARCH-03: Inconsistent platform domain definitions
**Files:** `config/keywords.py:104-114`, `discovery/web_search.py:59-66`
**Severity:** Major (data inconsistency)

`COACH_PLATFORM_DOMAINS` is defined in two places with different contents:

**`config/keywords.py`** (9 domains):
```python
{"kajabi.com", "gumroad.com", "thinkific.com", "teachable.com",
 "trainerize.com", "everfit.io", "caliber.com", "koji.io", "linkpop.com"}
```

**`discovery/web_search.py`** (6 domains):
```python
{"kajabi.com", "gumroad.com", "thinkific.com", "teachable.com",
 "trainerize.com", "caliber.com"}
```

The `web_search.py` version is missing `everfit.io`, `koji.io`, and `linkpop.com`. Meanwhile, `pipeline.py` imports `COACH_PLATFORM_DOMAINS` from `config/keywords.py` but `DOMAIN_BLOCKLIST` from `discovery/web_search.py`, where `everfit.io` and `trainerize.com` appear in the BLOCKLIST - contradicting their status as accepted platforms.

**Fix:** Define platform domains in a single location and import everywhere.

---

### ARCH-04: Contradictory treatment of `trainerize.com` and `everfit.io`
**Files:** `config/keywords.py:109-110`, `discovery/web_search.py:45`
**Severity:** Major (logical contradiction)

- In `config/keywords.py`, `trainerize.com` and `everfit.io` are listed as `COACH_PLATFORM_DOMAINS` (accepted)
- In `discovery/web_search.py`, both are listed in `DOMAIN_BLOCKLIST` (blocked)
- In `pipeline.py`, `everfit.io` and `trainerize.com` are in `_SAAS_DOMAINS` (blocked)

These domains are simultaneously "accepted coach platforms" and "blocked domains" depending on which module is checking. The blocklist wins in practice because filtering happens before platform acceptance in the flow.

**Fix:** Decide whether these are accepted or blocked and make it consistent across all files.

---

### PERF-01: Google Sheets loaded on every pipeline run for dedup
**File:** `pipeline.py:113-150`
**Severity:** Major (API rate limits + latency)

`load_seen_identities()` downloads the entire `All_Leads` sheet on every run. For a sheet with thousands of rows, this is slow and consumes Google Sheets API quota. The data is used only for set membership checks.

**Fix:** Cache seen identities locally in `.cache/seen_identities.json` and only refresh from Sheets periodically or on explicit request. Alternatively, maintain a local SQLite database of seen identities.

---

### PERF-02: SMTP catch-all check creates unnecessary connections
**File:** `verification/smtp_verifier.py:76-90`
**Severity:** Major (performance)

`is_catch_all_domain()` is called inside `verify_email_address()` for every email that returns SMTP 250. This creates an additional SMTP connection per email to test a random address. The result is cached per-run in memory (`_catch_all_domains` dict) but not to disk - so the same domain is re-tested every run.

**Fix:** Persist catch-all domain results to disk cache alongside email results.

---

### SEC-02: SMTP HELO uses suspicious domain name
**File:** `verification/smtp_verifier.py:65`
**Severity:** Major

```python
server.helo("verify.local")
```

Using `verify.local` as the HELO domain is suspicious and may trigger spam filters or IP blocks. Some mail servers log HELO domains and may blacklist IPs that use obviously fake domains.

**Fix:** Use a domain you control, or at minimum use a more generic HELO like the machine's hostname.

---

### SEC-03: SMTP MAIL FROM uses fake address
**File:** `verification/smtp_verifier.py:66`
**Severity:** Major

```python
server.mail("check@verify.local")
```

The MAIL FROM address `check@verify.local` is clearly fake. Stricter mail servers will reject this, and repeated use may cause your IP to be blacklisted. Some ISPs and cloud providers explicitly prohibit this type of SMTP probing.

**Fix:** Use a real, controlled email address for MAIL FROM, or consider using a third-party email verification API.

---

### DEP-02: `instaloader` dependency is unused but required at import
**File:** `resolution/instagram_profile.py:8`
**Severity:** Major

```python
import instaloader
```

This import runs at module load time. If `instaloader` is not installed, importing `resolution.instagram_profile` will fail with `ModuleNotFoundError`. Since `normalize_username()` from this module IS actively used (at `pipeline.py:29`), the `instaloader` package must be installed even though its actual functionality is blocked by Instagram.

**Fix:** Either:
1. Move `normalize_username()` to a separate file without the `instaloader` dependency
2. Make the `instaloader` import lazy (inside `fetch_profile()` only)

---

### DOC-01: README thresholds don't match code
**File:** `README.md:50-54`
**Severity:** Major (misleading documentation)

The README states:
```
Hot: >= 60
Good: >= 40
```

But the actual thresholds in `config/settings.py:59-60` are:
```python
hot_lead_threshold: int = int(os.getenv("HOT_LEAD_THRESHOLD", "65"))
good_lead_threshold: int = int(os.getenv("GOOD_LEAD_THRESHOLD", "45"))
```

Hot is >= 65 and Good is >= 45, not 60 and 40 as documented.

**Fix:** Update README to match actual default values.

---

## MINOR Issues

### BUG-06: `_extract_phone` re-imports `re` unnecessarily
**File:** `extraction/website_crawler.py:272`
**Severity:** Minor

```python
def _extract_phone(text: str) -> str:
    import re  # <-- already imported at top of file (line 3)
```

The `re` module is already imported at the top of the file. This local import is redundant.

**Fix:** Remove the local `import re`.

---

### BUG-07: `_try_accept_result` has side effect inside boolean helper
**File:** `pipeline.py:615-628`
**Severity:** Minor (confusing API)

```python
def _try_accept_result(rurl: str) -> bool:
    ...
    lead.website = rurl  # <-- side effect!
    return True
```

This nested function named like a predicate ("try accept") has a hidden side effect of setting `lead.website`. This makes the code harder to reason about. The function captures `lead` from the enclosing scope via closure.

**Fix:** Rename to `_set_website_if_valid()` or separate the validation from the assignment.

---

### ARCH-05: Inconsistent logging patterns
**Files:** Multiple
**Severity:** Minor

Each module implements its own `_log()` function:
- `pipeline.py:36` - `[HH:MM:SS] message`
- `discovery/duckduckgo_search.py:23` - `[HH:MM:SS] [discovery] message`
- `extraction/email_guesser.py:7` - `[HH:MM:SS] [email_guesser] message`
- `verification/smtp_verifier.py:27` - `[HH:MM:SS] [smtp] message`

All use slightly different formats and none use Python's `logging` module. This makes it impossible to filter, redirect, or configure log levels.

**Fix:** Use Python's standard `logging` module with a shared configuration.

---

### ARCH-06: `config/cities.py` is dead code
**File:** `config/cities.py`
**Severity:** Minor

The file is deprecated, contains only an empty list, and is not imported anywhere.

**Fix:** Delete the file.

---

### QUAL-01: Unused import `DOMAIN_BLOCKLIST` imported twice
**File:** `pipeline.py:16,21`
**Severity:** Minor

```python
from discovery.web_search import (
    ACCEPTED_SOURCE_DOMAINS,
    DOMAIN_BLOCKLIST,       # <-- first import
    LINK_HUB_DOMAINS,
)
...
from discovery.web_search import split_candidate_urls, DOMAIN_BLOCKLIST  # <-- duplicate
```

`DOMAIN_BLOCKLIST` is imported twice from the same module.

**Fix:** Remove the duplicate import on line 21.

---

### QUAL-02: `cast_list`, `cast_dict`, `cast_int` defined in `pipeline.py`
**File:** `pipeline.py:937-953`
**Severity:** Minor (wrong location)

These generic utility functions are defined at the bottom of the 980-line pipeline module. They should be in a shared `utils.py` module or in `models/lead.py` since they're used for Lead data processing.

---

### QUAL-03: `Iterable` import unused in `email_extractor.py`
**File:** `extraction/email_extractor.py:4`
**Severity:** Minor

```python
from typing import Iterable, List
```

`Iterable` is used in the `pick_best_email` signature, so this is actually correct. However, the type annotation could use the built-in `collections.abc.Iterable` from Python 3.10+.

---

### QUAL-04: Magic numbers in scoring
**File:** `scoring/lead_scorer.py`
**Severity:** Minor

All scoring weights are hardcoded magic numbers (20, 12, 8, -15, 5, 4, 10, 8, 15, -5, etc.). These are not configurable and require code changes to adjust.

**Fix:** Move scoring weights to `config/settings.py` or a dedicated `config/scoring.py` file.

---

### QUAL-05: `smtp_delay_seconds` setting is defined but never used
**File:** `config/settings.py:44`
**Severity:** Minor

```python
smtp_delay_seconds: float = float(os.getenv("SMTP_DELAY_SECONDS", "3"))
```

This setting exists in `Settings` but is never referenced anywhere in the SMTP verification code. The SMTP module uses its own hardcoded `SMTP_CONNECT_TIMEOUT = 5` instead.

---

### QUAL-06: `profile_batch_size` setting is defined but never used
**File:** `config/settings.py:46`
**Severity:** Minor

```python
profile_batch_size: int = int(os.getenv("PROFILE_BATCH_SIZE", "50"))
```

This setting is never referenced in any code. Likely a remnant from an earlier design.

---

### QUAL-07: `instagram_delay_seconds` setting only used in dead code
**File:** `config/settings.py:42`
**Severity:** Minor

```python
instagram_delay_seconds: float = float(os.getenv("INSTAGRAM_DELAY_SECONDS", "4"))
```

Only referenced in `resolution/instagram_profile.py:49` inside `fetch_profile()`, which is dead code (never called).

---

### QUAL-08: `search_query` imported but never directly called in `pipeline.py`
**File:** `pipeline.py:20`
**Severity:** Minor

```python
from discovery.duckduckgo_search import build_queries, discover_candidates, search_query
```

Wait - `search_query` IS used at `pipeline.py:633` inside `_find_website_for_ig_lead()`. This import is correct.

---

### QUAL-09: `_clean_df` handles NaN but data comes from `get_all_records()`
**File:** `app.py:91-99`
**Severity:** Minor

The `_clean_df()` function converts all values to strings and replaces NaN/None with empty strings. However, `gspread.worksheet.get_all_records()` already returns string values for empty cells. The NaN handling is defensive but largely unnecessary.

---

### PERF-03: Website crawler fetches all paths even if early pages have all data
**File:** `extraction/website_crawler.py:100`
**Severity:** Minor

The crawler always tries all paths in `PATH_HINTS` up to `max_pages_per_site`, even if the homepage already yielded an email, booking link, and all needed data. Early termination when "enough" data is found would reduce unnecessary HTTP requests and rate limiting delays.

---

### PERF-04: `_build_keys` called multiple times for the same lead during dedup
**File:** `verification/deduplicator.py:36`
**Severity:** Minor

After merging leads, `_build_keys(merged)` is called again to update the key map. This recalculates keys that were already computed. For large lead sets, this adds up.

---

### SEC-04: MD5 used for cache key hashing
**File:** `verification/smtp_verifier.py:33`
**Severity:** Minor (not a security hash, just a filename)

```python
h = hashlib.md5(email.lower().encode()).hexdigest()
```

MD5 is used to generate cache filenames. While this isn't a security concern (it's not used for authentication), using `hashlib.sha256` would be more modern and avoid potential collision issues with large caches.

---

### DOC-02: Docstrings missing on most functions
**Files:** Multiple
**Severity:** Minor

Many functions lack docstrings entirely. The ones that have docstrings are generally good, but coverage is inconsistent. Key functions without docstrings include `crawl_website()`, `score_lead()`, `_merge_leads()`, `_completeness_score()`, and most of the `app.py` functions.

---

### DOC-03: `nul` artifact file in project root
**File:** `nul`
**Severity:** Info

An empty file named `nul` exists in the project root. This is likely a Windows artifact from running a command like `command > nul` which on Windows creates a file instead of discarding output (unlike `/dev/null` on Unix).

**Fix:** Delete the file and add `nul` to `.gitignore`.

---

## INFO Items

### INFO-01: `SHEET_COLUMNS` missing `pricing_page` field
**File:** `models/lead.py:69-114`
**Severity:** Info

The `Lead` dataclass has a `pricing_page` field, but `SHEET_COLUMNS` only exports `has_pricing_page` (boolean). The actual pricing URL is lost during export. This may be intentional (the URL is less useful than knowing it exists), but worth noting.

---

### INFO-02: `to_dict()` includes `raw_payload` but Sheets export doesn't
**File:** `models/lead.py:61-66`
**Severity:** Info

`to_dict()` serializes all fields including `raw_payload` (which can be very large). However, `SHEET_COLUMNS` doesn't include `raw_payload`, so it's excluded from Sheets export. The `to_dict()` output is used for checkpoint files, where including `raw_payload` may cause unnecessarily large JSON files.

---

### INFO-03: Git history shows 10 commits with significant refactors
**Severity:** Info

The git history shows the project went through multiple refactors: initial commit, feature additions, UI addition, email quality improvements. Each refactor left some artifacts (dead code, unused settings, inconsistent domain lists). A cleanup pass focusing on removing dead code and consolidating duplicated definitions would improve maintainability.

---

## Refactoring Recommendations (Priority Order)

### 1. Fix Critical Bugs First
- [ ] Fix tab context bug in `app.py` (BUG-02)
- [ ] Remove unreachable code in `website_crawler.py` (BUG-01)
- [ ] Fix `requirements.txt` (DEP-01)

### 2. Security Remediation
- [ ] Rotate exposed service account key (SEC-01)
- [ ] Clean git history of credential files
- [ ] Improve SMTP HELO/MAIL FROM (SEC-02, SEC-03)

### 3. Code Cleanup
- [ ] Remove dead code: `enrich_lead_from_instagram()`, `config/cities.py`, `nul` file
- [ ] Remove unused imports: duplicate `DOMAIN_BLOCKLIST`, `resolve_external_url`
- [ ] Fix duplicate `import re` in `website_crawler.py`
- [ ] Consolidate domain blocklists into single module
- [ ] Resolve contradictory platform domain definitions

### 4. Architecture Improvements
- [ ] Break up `pipeline.py` into smaller modules
- [ ] Adopt Python `logging` module
- [ ] Move scoring weights to configuration
- [ ] Add local caching for seen identities
- [ ] Persist catch-all domain results to disk

### 5. Add Testing
- [ ] Set up `pytest` with `conftest.py`
- [ ] Add unit tests for core logic (scoring, dedup, email extraction)
- [ ] Add integration tests for pipeline phases
- [ ] Set up CI pipeline

### 6. Documentation
- [ ] Fix README threshold values
- [ ] Add docstrings to undocumented functions
- [ ] Remove or update deprecated references
